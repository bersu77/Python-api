import logging
from datetime import datetime, timedelta
from app import db
from app.models.token import TokenBlocklist
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def cleanup_expired_tokens():
    count = TokenBlocklist.cleanup_expired()
    logger.info(f"Cleaned up {count} expired tokens")
    return count


def cleanup_old_notifications(days=90):
    cutoff = datetime.utcnow() - timedelta(days=days)
    old_notifications = Notification.query.filter(
        Notification.is_read == True,
        Notification.created_at < cutoff,
    ).all()

    count = len(old_notifications)
    for notification in old_notifications:
        db.session.delete(notification)

    db.session.commit()
    logger.info(f"Cleaned up {count} old notifications")
    return count


def cleanup_inactive_users(days=365):
    cutoff = datetime.utcnow() - timedelta(days=days)
    inactive_users = db.session.query(db.func.count()).filter(
        db.and_(
            db.Column("last_seen") < cutoff,
            db.Column("is_active") == True,
        )
    ).scalar()

    logger.info(f"Found {inactive_users} inactive users (not deactivated)")
    return inactive_users


def run_all_cleanup():
    logger.info("Starting cleanup tasks...")
    tokens = cleanup_expired_tokens()
    notifications = cleanup_old_notifications()
    logger.info(f"Cleanup complete: {tokens} tokens, {notifications} notifications removed")
    return {"tokens": tokens, "notifications": notifications}
