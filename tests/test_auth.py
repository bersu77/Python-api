import pytest
from app import create_app, db
from app.config import TestingConfig
from app.models.user import User


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_user(app):
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("Test@1234")
        db.session.add(user)
        db.session.commit()
        return user


class TestRegister:
    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Strong@Pass1",
        })
        assert response.status_code == 201
        data = response.get_json()
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"

    def test_register_duplicate_email(self, client, sample_user):
        response = client.post("/api/auth/register", json={
            "username": "another",
            "email": "test@example.com",
            "password": "Strong@Pass1",
        })
        assert response.status_code == 409

    def test_register_duplicate_username(self, client, sample_user):
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "another@example.com",
            "password": "Strong@Pass1",
        })
        assert response.status_code == 409

    def test_register_weak_password(self, client):
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "weak",
        })
        assert response.status_code == 400

    def test_register_invalid_email(self, client):
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "not-an-email",
            "password": "Strong@Pass1",
        })
        assert response.status_code == 400


class TestLogin:
    def test_login_success(self, client, sample_user):
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test@1234",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client, sample_user):
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client, sample_user):
        login_response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test@1234",
        })
        token = login_response.get_json()["access_token"]

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_logout_without_token(self, client):
        response = client.post("/api/auth/logout")
        assert response.status_code == 401


class TestCurrentUser:
    def test_get_current_user(self, client, sample_user):
        login_response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test@1234",
        })
        token = login_response.get_json()["access_token"]

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"
