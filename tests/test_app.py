from app import create_app

def test_homepage():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Smarter inventory" in response.data

def test_health():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        assert client.get("/health").json == {"status": "ok"}
