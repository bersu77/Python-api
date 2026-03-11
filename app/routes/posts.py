from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from app import db
from app.models.post import Post
from app.models.user import User
from app.models.category import Category
from app.models.notification import Notification
from app.utils.pagination import paginate

posts_bp = Blueprint("posts", __name__)


class CreatePostSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=256))
    content = fields.String(required=True, validate=validate.Length(min=1))
    excerpt = fields.String(validate=validate.Length(max=512))
    cover_image = fields.String(validate=validate.Length(max=512))
    category_ids = fields.List(fields.Integer())
    status = fields.String(validate=validate.OneOf(["draft", "published"]))


class UpdatePostSchema(Schema):
    title = fields.String(validate=validate.Length(min=1, max=256))
    content = fields.String(validate=validate.Length(min=1))
    excerpt = fields.String(validate=validate.Length(max=512))
    cover_image = fields.String(validate=validate.Length(max=512))
    category_ids = fields.List(fields.Integer())
    status = fields.String(validate=validate.OneOf(["draft", "published"]))


@posts_bp.route("/", methods=["GET"])
def list_posts():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category = request.args.get("category", None)
    sort = request.args.get("sort", "latest")
    featured = request.args.get("featured", None, type=bool)

    query = Post.query.filter_by(status="published")

    if category:
        query = query.filter(Post.categories.any(Category.slug == category))

    if featured:
        query = query.filter_by(is_featured=True)

    if sort == "popular":
        query = query.order_by(Post.view_count.desc())
    elif sort == "most_liked":
        query = query.order_by(db.func.count(Post.liked_by).desc())
    else:
        query = query.order_by(Post.created_at.desc())

    result = paginate(query, page, per_page)

    return jsonify({
        "posts": [post.to_dict(include_content=False) for post in result["items"]],
        "pagination": result["pagination"],
    }), 200


@posts_bp.route("/feed", methods=["GET"])
@jwt_required()
def get_feed():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    current_user = User.query.get(int(get_jwt_identity()))
    query = current_user.get_feed()
    result = paginate(query, page, per_page)

    return jsonify({
        "posts": [post.to_dict(include_content=False) for post in result["items"]],
        "pagination": result["pagination"],
    }), 200


@posts_bp.route("/<slug>", methods=["GET"])
def get_post(slug):
    post = Post.query.filter_by(slug=slug, status="published").first_or_404()
    post.increment_views()
    return jsonify({"post": post.to_dict()}), 200


@posts_bp.route("/", methods=["POST"])
@jwt_required()
def create_post():
    schema = CreatePostSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    user = User.query.get(int(get_jwt_identity()))

    post = Post(
        title=data["title"],
        slug=Post.generate_slug(data["title"]),
        content=data["content"],
        excerpt=data.get("excerpt", data["content"][:200]),
        cover_image=data.get("cover_image"),
        reading_time=Post.calculate_reading_time(data["content"]),
        author_id=user.id,
        status=data.get("status", "draft"),
    )

    if data.get("category_ids"):
        categories = Category.query.filter(Category.id.in_(data["category_ids"])).all()
        post.categories = categories

    if post.status == "published":
        post.publish()

    db.session.add(post)
    db.session.commit()

    return jsonify({"post": post.to_dict()}), 201


@posts_bp.route("/<int:post_id>", methods=["PUT"])
@jwt_required()
def update_post(post_id):
    schema = UpdatePostSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    post = Post.query.get_or_404(post_id)
    user_id = int(get_jwt_identity())

    if post.author_id != user_id:
        return jsonify({"error": "Not authorized to edit this post"}), 403

    if "title" in data:
        post.title = data["title"]
        post.slug = Post.generate_slug(data["title"])

    if "content" in data:
        post.content = data["content"]
        post.reading_time = Post.calculate_reading_time(data["content"])

    if "excerpt" in data:
        post.excerpt = data["excerpt"]

    if "cover_image" in data:
        post.cover_image = data["cover_image"]

    if "category_ids" in data:
        categories = Category.query.filter(Category.id.in_(data["category_ids"])).all()
        post.categories = categories

    if "status" in data:
        if data["status"] == "published" and post.status != "published":
            post.publish()
        elif data["status"] == "draft":
            post.unpublish()

    db.session.commit()
    return jsonify({"post": post.to_dict()}), 200


@posts_bp.route("/<int:post_id>", methods=["DELETE"])
@jwt_required()
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if post.author_id != user_id and not user.is_admin:
        return jsonify({"error": "Not authorized to delete this post"}), 403

    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted successfully"}), 200


@posts_bp.route("/<int:post_id>/like", methods=["POST"])
@jwt_required()
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    user = User.query.get(int(get_jwt_identity()))

    if post.is_liked_by(user):
        post.liked_by.remove(user)
        db.session.commit()
        return jsonify({"message": "Post unliked", "likes_count": post.likes_count}), 200

    post.liked_by.append(user)
    db.session.commit()

    if post.author_id != user.id:
        Notification.create(
            recipient_id=post.author_id,
            notification_type="like_post",
            sender_id=user.id,
            data={"post_id": post.id, "post_title": post.title},
        )
        db.session.commit()

    return jsonify({"message": "Post liked", "likes_count": post.likes_count}), 200


@posts_bp.route("/<int:post_id>/bookmark", methods=["POST"])
@jwt_required()
def bookmark_post(post_id):
    post = Post.query.get_or_404(post_id)
    user = User.query.get(int(get_jwt_identity()))

    if post.is_bookmarked_by(user):
        post.bookmarked_by.remove(user)
        db.session.commit()
        return jsonify({"message": "Bookmark removed"}), 200

    post.bookmarked_by.append(user)
    db.session.commit()
    return jsonify({"message": "Post bookmarked"}), 200


@posts_bp.route("/bookmarks", methods=["GET"])
@jwt_required()
def get_bookmarks():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    user = User.query.get(int(get_jwt_identity()))
    query = user.bookmarked_posts
    result = paginate(query, page, per_page)

    return jsonify({
        "posts": [post.to_dict(include_content=False) for post in result["items"]],
        "pagination": result["pagination"],
    }), 200
