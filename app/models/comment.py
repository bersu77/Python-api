from datetime import datetime
from app import db


comment_likes = db.Table(
    "comment_likes",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("comment_id", db.Integer, db.ForeignKey("comments.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)

    replies = db.relationship("Comment", backref=db.backref("parent", remote_side=[id]), lazy="dynamic")
    liked_by = db.relationship("User", secondary=comment_likes, backref=db.backref("liked_comments", lazy="dynamic"))

    @property
    def likes_count(self):
        return len(self.liked_by)

    @property
    def replies_count(self):
        return self.replies.count()

    def is_liked_by(self, user):
        return user in self.liked_by

    def soft_delete(self):
        self.is_deleted = True
        self.content = "[This comment has been deleted]"

    def to_dict(self, include_replies=False):
        data = {
            "id": self.id,
            "content": self.content,
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "likes_count": self.likes_count,
            "replies_count": self.replies_count,
            "author": self.author.to_dict(),
            "post_id": self.post_id,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_replies:
            data["replies"] = [reply.to_dict() for reply in self.replies.order_by(Comment.created_at.asc()).all()]
        return data

    def __repr__(self):
        return f"<Comment {self.id} by {self.author.username}>"
