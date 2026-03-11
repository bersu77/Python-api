import pytest
from app import create_app, db
from app.config import TestingConfig
from app.models.user import User
from app.models.post import Post
from app.models.category import Category


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
def auth_headers(client, app):
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("Test@1234")
        db.session.add(user)
        db.session.commit()

    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "Test@1234",
    })
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_category(app):
    with app.app_context():
        category = Category(
            name="Technology",
            slug="technology",
            description="Tech articles",
        )
        db.session.add(category)
        db.session.commit()
        return category


class TestCreatePost:
    def test_create_draft(self, client, auth_headers):
        response = client.post("/api/posts/", json={
            "title": "My First Post",
            "content": "This is the content of my first post.",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data["post"]["title"] == "My First Post"
        assert data["post"]["status"] == "draft"

    def test_create_published(self, client, auth_headers):
        response = client.post("/api/posts/", json={
            "title": "Published Post",
            "content": "This post is published right away.",
            "status": "published",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data["post"]["status"] == "published"
        assert data["post"]["published_at"] is not None

    def test_create_with_categories(self, client, auth_headers, sample_category):
        response = client.post("/api/posts/", json={
            "title": "Tech Post",
            "content": "A post about technology.",
            "category_ids": [sample_category.id],
        }, headers=auth_headers)
        assert response.status_code == 201

    def test_create_without_auth(self, client):
        response = client.post("/api/posts/", json={
            "title": "Unauthorized Post",
            "content": "Should fail.",
        })
        assert response.status_code == 401

    def test_create_missing_title(self, client, auth_headers):
        response = client.post("/api/posts/", json={
            "content": "No title provided.",
        }, headers=auth_headers)
        assert response.status_code == 400


class TestGetPosts:
    def test_list_posts_empty(self, client):
        response = client.get("/api/posts/")
        assert response.status_code == 200
        data = response.get_json()
        assert data["posts"] == []
        assert data["pagination"]["total_items"] == 0

    def test_get_post_not_found(self, client):
        response = client.get("/api/posts/nonexistent-slug")
        assert response.status_code == 404


class TestPostInteractions:
    def test_like_post(self, client, auth_headers, app):
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            post = Post(
                title="Likeable Post",
                slug="likeable-post",
                content="Like this post.",
                author_id=user.id,
                status="published",
            )
            post.publish()
            db.session.add(post)
            db.session.commit()
            post_id = post.id

        response = client.post(f"/api/posts/{post_id}/like", headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()["likes_count"] == 1

        response = client.post(f"/api/posts/{post_id}/like", headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()["likes_count"] == 0

    def test_bookmark_post(self, client, auth_headers, app):
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            post = Post(
                title="Bookmarkable Post",
                slug="bookmarkable-post",
                content="Bookmark this post.",
                author_id=user.id,
                status="published",
            )
            post.publish()
            db.session.add(post)
            db.session.commit()
            post_id = post.id

        response = client.post(f"/api/posts/{post_id}/bookmark", headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()["message"] == "Post bookmarked"

        response = client.post(f"/api/posts/{post_id}/bookmark", headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()["message"] == "Bookmark removed"
