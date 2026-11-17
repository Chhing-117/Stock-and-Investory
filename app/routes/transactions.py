from decimal import Decimal
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from ..extensions import db
from ..models import Product, Supplier, Customer, Purchase, PurchaseItem, Sale, SaleItem, StockMovement
from ..services.stock import StockError, change_stock, money, positive_int
from .common import admin_required

transactions_bp = Blueprint('transactions', __name__)

def get_lines():
    ids = request.form.getlist('product_id[]')
    qtys = request.form.getlist('quantity[]')
    if not ids or len(ids) != len(qtys) or len(ids) > 100:
        raise StockError('Add between 1 and 100 product lines.')
    result = {}
    for pid, qty in zip(ids, qtys):
        if not str(pid).isdecimal():
            raise StockError('Choose a valid product.')
        pid = int(pid)
        qty = positive_int(qty)
        if pid in result:
            raise StockError('Each product may appear only once per transaction.')
        product = db.session.get(Product, pid)
        if not product or not product.active:
            raise StockError('Product is unavailable.')
        result[pid] = (product, qty)
    return result

def choices():
    return {'products': Product.query.filter_by(active=True).order_by(Product.name).all(),
            'suppliers': Supplier.query.filter_by(active=True).order_by(Supplier.name).all(),
            'customers': Customer.query.filter_by(active=True).order_by(Customer.name).all()}

@transactions_bp.get('/purchases')
@login_required
def purchases():
    page = request.args.get('page', 1, type=int)
    return render_template('transactions/history.html', title='Purchases', kind='purchase',
         rows=db.paginate(db.select(Purchase).order_by(Purchase.id.desc()), page=page, per_page=15, error_out=False))

@transactions_bp.route('/purchases/new', methods=['GET','POST'])
@login_required
def purchase_new():
    if request.method == 'POST':
        try:
            supplier_id = int(request.form.get('supplier_id','0'))
            supplier = db.session.get(Supplier, supplier_id)
            if not supplier or not supplier.active: raise StockError('Choose an active supplier.')
            lines = get_lines()
            costs = request.form.getlist('unit_cost[]')
            if len(costs) != len(lines): raise StockError('Every line requires a unit cost.')
            unit_costs = [money(c, 'Unit cost') for c in costs]
            total = sum((unit_costs[i] * qty for i, (_,qty) in enumerate(lines.values())), Decimal('0.00'))
            if total > Decimal('999999999999.99'): raise StockError('Total exceeds maximum amount.')
            purchase = Purchase(supplier_id=supplier.id, user_id=current_user.id, total=total)
            db.session.add(purchase)
            db.session.flush()
            for i,(pid,(product,qty)) in enumerate(lines.items()):
                cost=unit_costs[i]
                db.session.add(PurchaseItem(purchase_id=purchase.id, product_id=pid, quantity=qty, unit_cost=cost, subtotal=cost*qty))
                change_stock(pid, qty, user_id=current_user.id, kind='purchase', reason='Received purchase', reference_id=purchase.id)
            db.session.commit()
            flash('Purchase recorded and stock increased.', 'success')
            return redirect(url_for('transactions.purchase_detail', item_id=purchase.id))
        except (StockError, ValueError, SQLAlchemyError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc, (StockError, ValueError)) else 'Could not record purchase.', 'danger')
    return render_template('transactions/new.html', title='New purchase', kind='purchase', **choices())

@transactions_bp.get('/purchases/<int:item_id>')
@login_required
def purchase_detail(item_id):
    return render_template('transactions/detail.html', title='Purchase details', kind='purchase', transaction=db.get_or_404(Purchase, item_id))

@transactions_bp.get('/sales')
@login_required
def sales():
    page = request.args.get('page',1,type=int)
    return render_template('transactions/history.html', title='Sales / POS', kind='sale',
        rows=db.paginate(db.select(Sale).order_by(Sale.id.desc()), page=page, per_page=15, error_out=False))

@transactions_bp.route('/sales/new', methods=['GET','POST'])
@login_required
def sale_new():
    if request.method == 'POST':
        try:
            cid=request.form.get('customer_id','0')
            if not str(cid).isdecimal(): raise StockError('Invalid customer.')
            cid=int(cid)
            customer=db.session.get(Customer,cid) if cid else None
            if cid and (not customer or not customer.active): raise StockError('Choose an active customer.')
            lines=get_lines()
            subtotal=sum((money(p.selling_price,'Selling price')*q for p,q in lines.values()),Decimal('0.00'))
            discount=money(request.form.get('discount','0'),'Discount')
            if discount>subtotal: raise StockError('Discount cannot exceed subtotal.')
            tax_rate=money(request.form.get('tax_rate','0'),'Tax rate')
            if tax_rate > 100: raise StockError('Tax rate cannot exceed 100%.')
            tax=((subtotal-discount)*tax_rate/Decimal('100')).quantize(Decimal('0.01'))
            total=subtotal-discount+tax
            if total > Decimal('999999999999.99'): raise StockError('Total exceeds maximum amount.')
            method=request.form.get('payment_method','')
            if method not in ('cash','bank_transfer','khqr'): raise StockError('Choose a valid payment method.')
            ref=request.form.get('payment_reference','').strip()[:120]
            status=request.form.get('payment_status','')
            if status not in ('recorded','pending','paid'): raise StockError('Choose a payment status.')
            if method=='khqr' and status=='paid' and not ref:
                raise StockError('Enter a reference when marking KHQR as paid.')
            sale=Sale(customer_id=cid or None, user_id=current_user.id, subtotal=subtotal,
                      discount=discount,tax=tax,total=total,payment_method=method,
                      payment_reference=ref,payment_status=status)
            db.session.add(sale)
            db.session.flush()
            for pid,(product,qty) in lines.items():
                price=money(product.selling_price,'Selling price')
                cost=money(product.purchase_price,'Purchase cost')
                db.session.add(SaleItem(sale_id=sale.id,product_id=pid,quantity=qty,
                                        unit_price=price,unit_cost=cost,subtotal=price*qty))
                change_stock(pid,-qty,user_id=current_user.id,kind='sale',reason='Completed sale', reference_id=sale.id)
            db.session.commit()
            flash('Sale recorded and stock decreased.', 'success')
            return redirect(url_for('transactions.sale_detail',item_id=sale.id))
        except (StockError, ValueError, SQLAlchemyError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc,(StockError,ValueError)) else 'Could not record sale.', 'danger')
    return render_template('transactions/new.html',title='New sale',kind='sale', **choices())

@transactions_bp.get('/sales/<int:item_id>')
@login_required
def sale_detail(item_id):
    return render_template('transactions/detail.html', title='Sale receipt', kind='sale', transaction=db.get_or_404(Sale, item_id))

@transactions_bp.get('/inventory')
@login_required
def inventory():
    q=request.args.get('q','').strip()[:100]
    query=db.select(Product).filter(Product.active.is_(True))
    if q: query=query.filter(Product.name.ilike(f'%{q}%') | Product.sku.ilike(f'%{q}%'))
    page=request.args.get('page',1,type=int)
    rows=db.paginate(query.order_by(Product.name),page=page,per_page=15,error_out=False)
    low=Product.query.filter(Product.active.is_(True),Product.stock_quantity <= Product.minimum_stock).count()
    return render_template('inventory/index.html',rows=rows,low=low,q=q)

@transactions_bp.route('/inventory/adjust/<int:product_id>', methods=['GET','POST'])
@admin_required
def adjustment(product_id):
    product=db.get_or_404(Product,product_id)
    if request.method == 'POST':
        try:
            target=request.form.get('target','')
            if not str(target).isdecimal() or int(target)>1000000000: raise StockError('Enter a nonnegative whole number.')
            target=int(target)
            reason=request.form.get('reason','').strip()
            if len(reason)<3 or len(reason)>255: raise StockError('Reason must be between 3 and 255 characters.')
            # Atomic increment from current stock; manual target is based on stock at request time.
            # Conditional WHERE guards against a concurrent update overwriting another change.
            from sqlalchemy import update
            old=product.stock_quantity
            result=db.session.execute(update(Product).where(Product.id==product_id,Product.stock_quantity==old)
                 .values(stock_quantity=target).returning(Product.stock_quantity)).scalar_one_or_none()
            if result is None: raise StockError('Stock changed. Reload and try again.')
            db.session.add(StockMovement(product_id=product_id,user_id=current_user.id,
                movement_type='adjustment',quantity=target-old,stock_before=old,stock_after=target,reason=reason))
            db.session.commit()
            flash('Stock adjustment saved.', 'success')
            return redirect(url_for('transactions.inventory'))
        except (StockError,SQLAlchemyError) as exc:
            db.session.rollback()
            flash(str(exc) if isinstance(exc,StockError) else 'Could not adjust stock.','danger')
    return render_template('inventory/adjust.html', product=product)

@transactions_bp.get('/inventory/movements')
@login_required
def movements():
    page=request.args.get('page',1,type=int)
    return render_template('inventory/movements.html',rows=db.paginate(
        db.select(StockMovement).order_by(StockMovement.id.desc()),page=page,per_page=20,error_out=False))
