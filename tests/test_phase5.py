from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Product, Supplier, Sale, StockMovement
from tests.conftest import sign_in


def test_staff_cannot_edit_products_or_view_reports(client):
    sign_in(client, 'staff')
    assert client.get('/products/new').status_code == 403
    assert client.get('/users/').status_code == 403
    assert client.get('/reports/').status_code == 403
    assert client.get('/sales/new').status_code == 200


def test_deactivated_user_is_logged_out_on_next_request(app, client):
    sign_in(client, 'staff')
    with app.app_context():
        user = User.query.filter_by(username='staff').one()
        user.active = False
        db.session.commit()
    response = client.get('/products', follow_redirects=False)
    assert response.status_code == 302
    assert '/auth/login' in response.location
    assert client.get('/products').status_code == 302


def test_csrf_missing_is_rejected(tmp_path):
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': True,
                      'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path/'csrf.db')})
    with app.app_context():
        db.create_all()
        admin = User(username='admin', role='admin')
        admin.set_password('adminpassword123')
        db.session.add(admin)
        db.session.commit()
    client = app.test_client()
    response = client.post('/auth/login', data={'username':'admin','password':'adminpassword123'})
    assert response.status_code == 400
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_security_headers_and_no_cache(client):
    response = client.get('/auth/login')
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['Cache-Control'] == 'no-store'


def test_payload_limit(client):
    response = client.post('/auth/login', data={'username':'a'*(1024*1024), 'password':'x'})
    assert response.status_code == 413


def test_stock_negative_sale_rollback(app, client):
    with app.app_context():
        s = Supplier(name='Test')
        p = Product(name='Unit', sku='PH5-001', category_id=1,
                    selling_price=Decimal('10'), purchase_price=Decimal('4'), stock_quantity=0)
        db.session.add_all([s,p])
        db.session.commit()
        pid = p.id
    sign_in(client)
    res = client.post('/sales/new', data={
        'customer_id': '0', 'product_id[]': [str(pid)], 'quantity[]': ['2'],
        'discount':'0', 'tax_rate':'0', 'payment_method':'cash', 'payment_status':'paid'
    }, follow_redirects=True)
    assert b'Not enough stock' in res.data
    with app.app_context():
        assert db.session.get(Product, pid).stock_quantity == 0
        assert Sale.query.count() == 0
        assert StockMovement.query.count() == 0


def test_last_active_admin_must_remain(app, client):
    sign_in(client)
    with app.app_context():
        admin_id = User.query.filter_by(username='admin').one().id
    res = client.post(f'/users/{admin_id}/edit', data={
        'username':'admin','password':'','role':'staff'
    }, follow_redirects=True)
    with app.app_context():
        assert User.query.get(admin_id).role == 'admin'
