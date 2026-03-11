from datetime import datetime
from app import db


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    @classmethod
    def is_token_revoked(cls, jti):
        return cls.query.filter_by(jti=jti).first() is not None

    @classmethod
    def revoke_token(cls, jti, token_type, user_id, expires_at):
        blocked = cls(jti=jti, token_type=token_type, user_id=user_id, expires_at=expires_at)
        db.session.add(blocked)
        db.session.commit()

    @classmethod
    def revoke_all_user_tokens(cls, user_id):
        tokens = cls.query.filter_by(user_id=user_id).all()
        for token in tokens:
            db.session.delete(token)
        db.session.commit()

    @classmethod
    def cleanup_expired(cls):
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        count = len(expired)
        for token in expired:
            db.session.delete(token)
        db.session.commit()
        return count

    def __repr__(self):
        return f"<TokenBlocklist {self.jti}>"
