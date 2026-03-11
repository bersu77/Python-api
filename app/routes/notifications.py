from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.notification import Notification
from app.utils.pagination import paginate

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/", methods=["GET"])
@jwt_required()
def list_notifications():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    unread_only = request.args.get("unread", False, type=bool)

    user_id = int(get_jwt_identity())
    query = Notification.query.filter_by(recipient_id=user_id)

    if unread_only:
        query = query.filter_by(is_read=False)

    query = query.order_by(Notification.created_at.desc())
    result = paginate(query, page, per_page)

    return jsonify({
        "notifications": [n.to_dict() for n in result["items"]],
        "pagination": result["pagination"],
        "unread_count": Notification.get_unread_count(user_id),
    }), 200


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@jwt_required()
def mark_as_read(notification_id):
    user_id = int(get_jwt_identity())
    notification = Notification.query.filter_by(id=notification_id, recipient_id=user_id).first_or_404()

    notification.mark_as_read()
    db.session.commit()

    return jsonify({"message": "Notification marked as read"}), 200


@notifications_bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_as_read():
    user_id = int(get_jwt_identity())
    Notification.mark_all_as_read(user_id)
    return jsonify({"message": "All notifications marked as read"}), 200


@notifications_bp.route("/count", methods=["GET"])
@jwt_required()
def get_unread_count():
    user_id = int(get_jwt_identity())
    count = Notification.get_unread_count(user_id)
    return jsonify({"unread_count": count}), 200


@notifications_bp.route("/<int:notification_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(notification_id):
    user_id = int(get_jwt_identity())
    notification = Notification.query.filter_by(id=notification_id, recipient_id=user_id).first_or_404()

    db.session.delete(notification)
    db.session.commit()

    return jsonify({"message": "Notification deleted"}), 200


@notifications_bp.route("/clear", methods=["DELETE"])
@jwt_required()
def clear_notifications():
    user_id = int(get_jwt_identity())
    Notification.query.filter_by(recipient_id=user_id, is_read=True).delete()
    db.session.commit()
    return jsonify({"message": "Read notifications cleared"}), 200
