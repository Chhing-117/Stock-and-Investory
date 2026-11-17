import pytest
from app import create_app
from app.extensions import db
from app.models import User, Category

@pytest.fixture()
def app(tmp_path):
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False,
                      'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'test.db')})
    with app.app_context():
        db.create_all()
        admin = User(username='admin', role='admin')
        admin.set_password('adminpassword123')
        staff = User(username='staff', role='staff')
        staff.set_password('staffpassword123')
        db.session.add_all([admin, staff, Category(name='Electronics')])
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

def sign_in(client, role='admin'):
    password = 'adminpassword123' if role == 'admin' else 'staffpassword123'
    return client.post('/auth/login', data={'username': role, 'password': password}, follow_redirects=True)
