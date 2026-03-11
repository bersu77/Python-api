from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    limiter.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.posts import posts_bp
    from app.routes.comments import comments_bp
    from app.routes.categories import categories_bp
    from app.routes.notifications import notifications_bp
    from app.routes.search import search_bp
    from app.routes.analytics import analytics_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(posts_bp, url_prefix="/api/posts")
    app.register_blueprint(comments_bp, url_prefix="/api/comments")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(search_bp, url_prefix="/api/search")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    register_error_handlers(app)
    register_cli_commands(app)

    return app


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad request", "message": str(error)}, 400

    @app.errorhandler(401)
    def unauthorized(error):
        return {"error": "Unauthorized", "message": "Authentication required"}, 401

    @app.errorhandler(403)
    def forbidden(error):
        return {"error": "Forbidden", "message": "Access denied"}, 403

    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found", "message": "Resource not found"}, 404

    @app.errorhandler(429)
    def rate_limited(error):
        return {"error": "Rate limit exceeded", "message": "Too many requests"}, 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error", "message": "Something went wrong"}, 500


def register_cli_commands(app):
    @app.cli.command("seed")
    def seed_database():
        from app.services.seeder import seed_all
        seed_all()
        print("Database seeded successfully.")

    @app.cli.command("cleanup")
    def cleanup_expired():
        from app.services.cleanup import cleanup_expired_tokens
        count = cleanup_expired_tokens()
        print(f"Removed {count} expired tokens.")
