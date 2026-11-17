from decimal import Decimal
from app.extensions import db
from app.models import Product, Supplier, Purchase, Sale, StockMovement
from tests.conftest import sign_in

def setup_records(app):
    with app.app_context():
        supplier=Supplier(name='Demo supplier')
        product=Product(name='USB Cable',sku='USB-C-001',category_id=1,selling_price=Decimal('12.00'),purchase_price=Decimal('6.00'),stock_quantity=0)
        db.session.add_all([supplier,product])
        db.session.commit()
        return supplier.id,product.id

def test_purchase_sale_and_audit(app,client):
    supplier_id,product_id=setup_records(app)
    sign_in(client)
    response=client.post('/purchases/new',data={'supplier_id':str(supplier_id),'product_id[]':[str(product_id)],'quantity[]':['10'],'unit_cost[]':['5.50']},follow_redirects=True)
    assert b'Purchase recorded' in response.data
    with app.app_context():
        assert db.session.get(Product,product_id).stock_quantity==10
        assert Purchase.query.first().total==Decimal('55.00')
    response=client.post('/sales/new',data={'customer_id':'0','product_id[]':[str(product_id)],'quantity[]':['3'],'discount':'2','tax_rate':'10','payment_method':'cash','payment_status':'paid'},follow_redirects=True)
    assert b'Sale recorded' in response.data
    with app.app_context():
        assert db.session.get(Product,product_id).stock_quantity==7
        sale=Sale.query.first()
        assert sale.total==Decimal('37.40')
        assert sale.items[0].unit_cost==Decimal('6.00')
        assert StockMovement.query.count()==2

def test_insufficient_stock_rolls_back_everything(app,client):
    supplier_id,pid=setup_records(app)
    sign_in(client)
    response=client.post('/sales/new',data={'customer_id':'0','product_id[]':[str(pid)],'quantity[]':['1'],'discount':'0','tax_rate':'0','payment_method':'cash','payment_status':'paid'},follow_redirects=True)
    assert b'Not enough stock' in response.data
    with app.app_context():
        assert Sale.query.count()==0
        assert StockMovement.query.count()==0
        assert db.session.get(Product,pid).stock_quantity==0

def test_adjustment_admin_only(app,client):
    _,pid=setup_records(app)
    sign_in(client,'staff')
    assert client.post(f'/inventory/adjust/{pid}',data={'target':'11','reason':'Counted stock'}).status_code==403
    client.post('/auth/logout')
    sign_in(client,'admin')
    response=client.post(f'/inventory/adjust/{pid}',data={'target':'11','reason':'Counted stock'},follow_redirects=True)
    assert b'Stock adjustment saved' in response.data
    with app.app_context():
        m=StockMovement.query.one()
        assert (m.stock_before,m.stock_after,m.quantity)==(0,11,11)
