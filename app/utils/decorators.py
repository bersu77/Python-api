from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.user import User


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        return fn(*args, **kwargs)

    return wrapper


def verified_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user or not user.is_verified:
            return jsonify({"error": "Email verification required"}), 403

        return fn(*args, **kwargs)

    return wrapper


def owner_or_admin(model_class, id_param="id"):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            resource_id = kwargs.get(id_param)
            resource = model_class.query.get_or_404(resource_id)

            if hasattr(resource, "author_id"):
                owner_id = resource.author_id
            elif hasattr(resource, "user_id"):
                owner_id = resource.user_id
            else:
                owner_id = resource.id

            if owner_id != user_id and not user.is_admin:
                return jsonify({"error": "Not authorized"}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator
