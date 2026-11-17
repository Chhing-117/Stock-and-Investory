from app.extensions import db
from app.models import Category, Customer, Product, Supplier, User
from .conftest import sign_in

def test_auth_and_permissions(client):
    assert client.get('/products').status_code == 302
    sign_in(client, 'staff')
    assert client.get('/products').status_code == 200
    assert client.get('/products/new').status_code == 403
    assert client.get('/users/').status_code == 403

def test_category_crud(client, app):
    sign_in(client)
    assert client.post('/categories/new', data={'name': 'Clothing', 'description': 'Fabric'}).status_code == 302
    with app.app_context():
        category = Category.query.filter_by(name='Clothing').one()
        cid = category.id
    assert client.post(f'/categories/{cid}/edit', data={'name': 'Apparel'}).status_code == 302
    assert client.post(f'/categories/{cid}/delete').status_code == 302
    with app.app_context():
        assert Category.query.filter_by(name='Apparel').first() is None

def test_product_creation_and_edit(client, app):
    sign_in(client)
    payload = {'name':'Laptop','sku':'LAP-01','barcode':'','category_id':'1',
               'supplier_id':'0','purchase_price':'0','selling_price':'120.00',
               'minimum_stock':'0','unit':'pcs','description':'','active':'y'}
    response = client.post('/products/new', data=payload, follow_redirects=True)
    assert b'Product created' in response.data
    with app.app_context():
        item = Product.query.filter_by(sku='LAP-01').one()
        pid = item.id
        assert item.stock_quantity == 0
        assert str(item.purchase_price) == '0.00'
    payload['name'] = 'Laptop Pro'
    assert client.post(f'/products/{pid}/edit', data=payload).status_code == 302
    with app.app_context():
        assert db.session.get(Product, pid).name == 'Laptop Pro'

def test_category_with_products_cannot_be_deleted(client, app):
    sign_in(client)
    payload = {'name':'Pen','sku':'P-1','category_id':'1','supplier_id':'0',
               'purchase_price':'1','selling_price':'2','minimum_stock':'5','unit':'pcs'}
    assert client.post('/products/new', data=payload).status_code == 302
    client.post('/categories/1/delete')
    with app.app_context():
        assert db.session.get(Category, 1) is not None

def test_suppliers_customers(client, app):
    sign_in(client)
    for path in ('suppliers','customers'):
        assert client.post(f'/{path}/new', data={'name':'A Company','active':'y'}).status_code == 302
    with app.app_context():
        assert Supplier.query.count() == 1
        assert Customer.query.count() == 1

def test_admin_can_create_staff(client, app):
    sign_in(client)
    assert client.post('/users/new', data={'username':'employee','password':'strongpassword123','role':'staff','active':'y'}).status_code == 302
    with app.app_context():
        user = User.query.filter_by(username='employee').one()
        assert user.role == 'staff' and user.check_password('strongpassword123')
