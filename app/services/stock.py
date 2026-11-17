"""Transactional stock changes. All callers must commit or rollback as one unit."""
from decimal import Decimal, InvalidOperation
from sqlalchemy import update
from ..extensions import db
from ..models import Product, StockMovement

class StockError(ValueError):
    pass

def money(value, name='Amount'):
    try:
        d = Decimal(str(value))
        if not d.is_finite() or d < 0 or d.as_tuple().exponent < -2 or d > Decimal('999999999999.99'):
            raise ValueError
        return d.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        raise StockError(f'{name} must be a nonnegative number with at most two decimal places.')

def positive_int(value, name='Quantity'):
    try:
        value = str(value)
        if not value.isdecimal() or int(value) < 1 or int(value) > 100000000:
            raise ValueError
        return int(value)
    except (TypeError, ValueError):
        raise StockError(f'{name} must be a positive whole number.')

def change_stock(product_id, delta, *, user_id, kind, reason='', reference_id=None):
    """Atomic conditional UPDATE prevents negative stock across concurrent requests.

    Only commit at the route's transaction boundary. An update returns new stock
    and computes before = after - delta, avoiding stale ORM reads.
    """
    if not isinstance(delta, int) or abs(delta) > 1000000000:
        raise StockError('Stock change exceeds allowed limit.')
    product = db.session.get(Product, product_id)
    if not product or not product.active:
        raise StockError('Selected product is unavailable.')
    stmt = (update(Product).where(Product.id == product_id, Product.active.is_(True),
                                  Product.stock_quantity + delta >= 0,
                                  Product.stock_quantity + delta <= 1000000000)
            .values(stock_quantity=Product.stock_quantity + delta)
            .returning(Product.stock_quantity))
    result = db.session.execute(stmt).scalar_one_or_none()
    if result is None:
        raise StockError(f'Not enough stock for {product.name}.')
    # Prevent later ORM flush of a stale product.stock_quantity.
    db.session.expire(product, ['stock_quantity'])
    db.session.add(StockMovement(product_id=product_id, user_id=user_id,
        movement_type=kind, quantity=delta, stock_before=result - delta,
        stock_after=result, reason=reason[:255], reference_id=reference_id))
    return result
