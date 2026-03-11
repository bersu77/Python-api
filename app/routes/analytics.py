from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from app import db
from app.models.post import Post, post_likes
from app.models.user import User
from app.models.comment import Comment
from app.utils.decorators import admin_required

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def user_dashboard():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)

    total_posts = user.posts.count()
    published_posts = user.posts.filter_by(status="published").count()
    draft_posts = user.posts.filter_by(status="draft").count()

    total_views = db.session.query(func.sum(Post.view_count)).filter(Post.author_id == user_id).scalar() or 0

    total_likes = db.session.query(func.count(post_likes.c.user_id)).join(
        Post, post_likes.c.post_id == Post.id
    ).filter(Post.author_id == user_id).scalar() or 0

    total_comments = db.session.query(func.count(Comment.id)).join(
        Post, Comment.post_id == Post.id
    ).filter(Post.author_id == user_id).scalar() or 0

    top_posts = Post.query.filter_by(
        author_id=user_id, status="published"
    ).order_by(Post.view_count.desc()).limit(5).all()

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_views = db.session.query(
        func.date(Post.updated_at).label("date"),
        func.sum(Post.view_count).label("views"),
    ).filter(
        Post.author_id == user_id,
        Post.updated_at >= thirty_days_ago,
    ).group_by(func.date(Post.updated_at)).all()

    return jsonify({
        "stats": {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "draft_posts": draft_posts,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "followers_count": user.followers_count,
            "following_count": user.following_count,
        },
        "top_posts": [p.to_dict(include_content=False) for p in top_posts],
        "views_over_time": [
            {"date": str(row.date), "views": row.views} for row in recent_views
        ],
    }), 200


@analytics_bp.route("/admin", methods=["GET"])
@jwt_required()
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_posts = Post.query.count()
    published_posts = Post.query.filter_by(status="published").count()
    total_comments = Comment.query.count()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = User.query.filter(User.created_at >= seven_days_ago).count()
    new_posts_week = Post.query.filter(Post.created_at >= seven_days_ago).count()

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    user_growth = db.session.query(
        func.date(User.created_at).label("date"),
        func.count(User.id).label("count"),
    ).filter(User.created_at >= thirty_days_ago).group_by(
        func.date(User.created_at)
    ).all()

    post_growth = db.session.query(
        func.date(Post.created_at).label("date"),
        func.count(Post.id).label("count"),
    ).filter(Post.created_at >= thirty_days_ago).group_by(
        func.date(Post.created_at)
    ).all()

    popular_categories = db.session.query(
        func.count(Post.id).label("post_count"),
    ).group_by(Post.categories).order_by(func.count(Post.id).desc()).limit(10).all()

    top_authors = db.session.query(
        User.username,
        func.count(Post.id).label("post_count"),
        func.sum(Post.view_count).label("total_views"),
    ).join(Post).group_by(User.id).order_by(
        func.sum(Post.view_count).desc()
    ).limit(10).all()

    return jsonify({
        "overview": {
            "total_users": total_users,
            "active_users": active_users,
            "total_posts": total_posts,
            "published_posts": published_posts,
            "total_comments": total_comments,
            "new_users_this_week": new_users_week,
            "new_posts_this_week": new_posts_week,
        },
        "user_growth": [{"date": str(r.date), "count": r.count} for r in user_growth],
        "post_growth": [{"date": str(r.date), "count": r.count} for r in post_growth],
        "top_authors": [
            {"username": r.username, "posts": r.post_count, "views": r.total_views}
            for r in top_authors
        ],
    }), 200
