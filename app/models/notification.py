from datetime import datetime
from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    message = db.Column(db.String(512), nullable=False)
    data = db.Column(db.JSON, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    sender = db.relationship("User", foreign_keys=[sender_id])

    TYPES = {
        "follow": "{sender} started following you",
        "like_post": "{sender} liked your post \"{post_title}\"",
        "comment": "{sender} commented on your post \"{post_title}\"",
        "reply": "{sender} replied to your comment",
        "mention": "{sender} mentioned you in a comment",
        "post_featured": "Your post \"{post_title}\" has been featured",
    }

    @classmethod
    def create(cls, recipient_id, notification_type, sender_id=None, data=None):
        notification = cls(
            recipient_id=recipient_id,
            sender_id=sender_id,
            type=notification_type,
            message=cls.TYPES.get(notification_type, "You have a new notification"),
            data=data or {},
        )
        db.session.add(notification)
        return notification

    def mark_as_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()

    @classmethod
    def mark_all_as_read(cls, user_id):
        cls.query.filter_by(recipient_id=user_id, is_read=False).update(
            {"is_read": True, "read_at": datetime.utcnow()}
        )
        db.session.commit()

    @classmethod
    def get_unread_count(cls, user_id):
        return cls.query.filter_by(recipient_id=user_id, is_read=False).count()

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "message": self.message,
            "data": self.data,
            "is_read": self.is_read,
            "sender": self.sender.to_dict() if self.sender else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<Notification {self.type} for User {self.recipient_id}>"
