"""Deployment checks. These tests use the isolated SQLite test fixture."""
import pytest


def test_health_with_sqlite(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}


def test_missing_database_fails_health(app, client, monkeypatch):
    from app.extensions import db
    from sqlalchemy.exc import OperationalError
    with monkeypatch.context() as patch:
        patch.setattr(db.session, 'execute', lambda *a, **kw: (_ for _ in ()).throw(OperationalError('select', {}, Exception('offline'))))
        response = client.get('/health')
    assert response.status_code == 503
    assert response.json == {'status': 'unavailable'}


def test_production_requires_database_url(monkeypatch):
    from app import create_app
    monkeypatch.setenv('APP_ENV', 'production')
    with pytest.raises(RuntimeError, match='Production requires DATABASE_URL'):
        create_app({'SECRET_KEY': 'a' * 48, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})


def test_production_rejects_default_secret(monkeypatch):
    from app import create_app
    monkeypatch.setenv('APP_ENV', 'production')
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app({'SECRET_KEY': 'local-only-change-me'})
