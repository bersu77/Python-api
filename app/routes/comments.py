from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from app import db
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User
from app.models.notification import Notification
from app.utils.pagination import paginate

comments_bp = Blueprint("comments", __name__)


class CreateCommentSchema(Schema):
    content = fields.String(required=True, validate=validate.Length(min=1, max=2000))
    post_id = fields.Integer(required=True)
    parent_id = fields.Integer()


class UpdateCommentSchema(Schema):
    content = fields.String(required=True, validate=validate.Length(min=1, max=2000))


@comments_bp.route("/", methods=["POST"])
@jwt_required()
def create_comment():
    schema = CreateCommentSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    post = Post.query.get_or_404(data["post_id"])
    user = User.query.get(int(get_jwt_identity()))

    comment = Comment(
        content=data["content"],
        author_id=user.id,
        post_id=post.id,
        parent_id=data.get("parent_id"),
    )

    db.session.add(comment)
    db.session.commit()

    if post.author_id != user.id:
        if comment.parent_id:
            parent_comment = Comment.query.get(comment.parent_id)
            if parent_comment and parent_comment.author_id != user.id:
                Notification.create(
                    recipient_id=parent_comment.author_id,
                    notification_type="reply",
                    sender_id=user.id,
                    data={"post_id": post.id, "comment_id": comment.id},
                )
        else:
            Notification.create(
                recipient_id=post.author_id,
                notification_type="comment",
                sender_id=user.id,
                data={"post_id": post.id, "post_title": post.title, "comment_id": comment.id},
            )
        db.session.commit()

    return jsonify({"comment": comment.to_dict()}), 201


@comments_bp.route("/post/<int:post_id>", methods=["GET"])
def get_post_comments(post_id):
    Post.query.get_or_404(post_id)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort = request.args.get("sort", "latest")

    query = Comment.query.filter_by(post_id=post_id, parent_id=None)

    if sort == "oldest":
        query = query.order_by(Comment.created_at.asc())
    elif sort == "popular":
        query = query.order_by(db.func.count(Comment.liked_by).desc())
    else:
        query = query.order_by(Comment.created_at.desc())

    result = paginate(query, page, per_page)

    return jsonify({
        "comments": [comment.to_dict(include_replies=True) for comment in result["items"]],
        "pagination": result["pagination"],
    }), 200


@comments_bp.route("/<int:comment_id>", methods=["PUT"])
@jwt_required()
def update_comment(comment_id):
    schema = UpdateCommentSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    comment = Comment.query.get_or_404(comment_id)
    user_id = int(get_jwt_identity())

    if comment.author_id != user_id:
        return jsonify({"error": "Not authorized to edit this comment"}), 403

    comment.content = data["content"]
    comment.is_edited = True
    db.session.commit()

    return jsonify({"comment": comment.to_dict()}), 200


@comments_bp.route("/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if comment.author_id != user_id and not user.is_admin:
        return jsonify({"error": "Not authorized to delete this comment"}), 403

    if comment.replies.count() > 0:
        comment.soft_delete()
    else:
        db.session.delete(comment)

    db.session.commit()
    return jsonify({"message": "Comment deleted"}), 200


@comments_bp.route("/<int:comment_id>/like", methods=["POST"])
@jwt_required()
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    user = User.query.get(int(get_jwt_identity()))

    if comment.is_liked_by(user):
        comment.liked_by.remove(user)
        db.session.commit()
        return jsonify({"message": "Comment unliked", "likes_count": comment.likes_count}), 200

    comment.liked_by.append(user)
    db.session.commit()

    return jsonify({"message": "Comment liked", "likes_count": comment.likes_count}), 200
