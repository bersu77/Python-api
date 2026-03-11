from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from app import db
from app.models.user import User
from app.models.notification import Notification
from app.utils.pagination import paginate
from app.utils.decorators import admin_required

users_bp = Blueprint("users", __name__)


class UpdateProfileSchema(Schema):
    first_name = fields.String(validate=validate.Length(max=64))
    last_name = fields.String(validate=validate.Length(max=64))
    bio = fields.String(validate=validate.Length(max=500))
    location = fields.String(validate=validate.Length(max=128))
    website = fields.String(validate=validate.Length(max=256))


@users_bp.route("/", methods=["GET"])
@jwt_required()
def list_users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("q", None)

    query = User.query.filter_by(is_active=True)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
            )
        )

    query = query.order_by(User.created_at.desc())
    result = paginate(query, page, per_page)

    return jsonify({
        "users": [user.to_dict() for user in result["items"]],
        "pagination": result["pagination"],
    }), 200


@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    current_user = User.query.get(int(get_jwt_identity()))

    data = user.to_dict()
    data["is_following"] = current_user.is_following(user) if current_user else False

    return jsonify({"user": data}), 200


@users_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    schema = UpdateProfileSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    user = User.query.get(int(get_jwt_identity()))

    for key, value in data.items():
        setattr(user, key, value)

    db.session.commit()
    return jsonify({"user": user.to_dict(include_email=True)}), 200


@users_bp.route("/<int:user_id>/follow", methods=["POST"])
@jwt_required()
def follow_user(user_id):
    current_user = User.query.get(int(get_jwt_identity()))
    target_user = User.query.get_or_404(user_id)

    if current_user.id == target_user.id:
        return jsonify({"error": "You cannot follow yourself"}), 400

    if current_user.is_following(target_user):
        return jsonify({"error": "Already following this user"}), 400

    current_user.follow(target_user)
    db.session.commit()

    Notification.create(
        recipient_id=target_user.id,
        notification_type="follow",
        sender_id=current_user.id,
    )
    db.session.commit()

    return jsonify({"message": f"Now following {target_user.username}"}), 200


@users_bp.route("/<int:user_id>/unfollow", methods=["POST"])
@jwt_required()
def unfollow_user(user_id):
    current_user = User.query.get(int(get_jwt_identity()))
    target_user = User.query.get_or_404(user_id)

    if not current_user.is_following(target_user):
        return jsonify({"error": "Not following this user"}), 400

    current_user.unfollow(target_user)
    db.session.commit()

    return jsonify({"message": f"Unfollowed {target_user.username}"}), 200


@users_bp.route("/<int:user_id>/followers", methods=["GET"])
@jwt_required()
def get_followers(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    result = paginate(user.followers, page, per_page)

    return jsonify({
        "followers": [u.to_dict() for u in result["items"]],
        "pagination": result["pagination"],
    }), 200


@users_bp.route("/<int:user_id>/following", methods=["GET"])
@jwt_required()
def get_following(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    result = paginate(user.following, page, per_page)

    return jsonify({
        "following": [u.to_dict() for u in result["items"]],
        "pagination": result["pagination"],
    }), 200


@users_bp.route("/<int:user_id>/posts", methods=["GET"])
@jwt_required()
def get_user_posts(user_id):
    from app.models.post import Post
    user = User.query.get_or_404(user_id)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = user.posts.filter_by(status="published").order_by(Post.created_at.desc())
    result = paginate(query, page, per_page)

    return jsonify({
        "posts": [post.to_dict(include_content=False) for post in result["items"]],
        "pagination": result["pagination"],
    }), 200


@users_bp.route("/<int:user_id>/deactivate", methods=["POST"])
@jwt_required()
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return jsonify({"message": f"User {user.username} deactivated"}), 200
