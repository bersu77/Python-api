from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.post import Post
from app.models.user import User
from app.models.category import Category
from app.utils.pagination import paginate

search_bp = Blueprint("search", __name__)


@search_bp.route("/", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "all")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    if not query or len(query) < 2:
        return jsonify({"error": "Search query must be at least 2 characters"}), 400

    search_term = f"%{query}%"
    results = {}

    if search_type in ("all", "posts"):
        post_query = Post.query.filter(
            Post.status == "published",
            db.or_(
                Post.title.ilike(search_term),
                Post.content.ilike(search_term),
                Post.excerpt.ilike(search_term),
            ),
        ).order_by(Post.created_at.desc())

        if search_type == "posts":
            result = paginate(post_query, page, per_page)
            return jsonify({
                "posts": [p.to_dict(include_content=False) for p in result["items"]],
                "pagination": result["pagination"],
            }), 200

        results["posts"] = [p.to_dict(include_content=False) for p in post_query.limit(5).all()]

    if search_type in ("all", "users"):
        user_query = User.query.filter(
            User.is_active == True,
            db.or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.bio.ilike(search_term),
            ),
        ).order_by(User.created_at.desc())

        if search_type == "users":
            result = paginate(user_query, page, per_page)
            return jsonify({
                "users": [u.to_dict() for u in result["items"]],
                "pagination": result["pagination"],
            }), 200

        results["users"] = [u.to_dict() for u in user_query.limit(5).all()]

    if search_type in ("all", "categories"):
        cat_query = Category.query.filter(
            Category.is_active == True,
            db.or_(
                Category.name.ilike(search_term),
                Category.description.ilike(search_term),
            ),
        )

        if search_type == "categories":
            result = paginate(cat_query, page, per_page)
            return jsonify({
                "categories": [c.to_dict() for c in result["items"]],
                "pagination": result["pagination"],
            }), 200

        results["categories"] = [c.to_dict() for c in cat_query.limit(5).all()]

    return jsonify({"query": query, "results": results}), 200


@search_bp.route("/suggest", methods=["GET"])
def search_suggestions():
    query = request.args.get("q", "").strip()

    if not query or len(query) < 2:
        return jsonify({"suggestions": []}), 200

    search_term = f"{query}%"
    suggestions = []

    posts = Post.query.filter(
        Post.status == "published",
        Post.title.ilike(search_term),
    ).limit(5).all()
    suggestions.extend([{"type": "post", "text": p.title, "slug": p.slug} for p in posts])

    users = User.query.filter(
        User.is_active == True,
        User.username.ilike(search_term),
    ).limit(3).all()
    suggestions.extend([{"type": "user", "text": u.username, "id": u.id} for u in users])

    categories = Category.query.filter(
        Category.is_active == True,
        Category.name.ilike(search_term),
    ).limit(3).all()
    suggestions.extend([{"type": "category", "text": c.name, "slug": c.slug} for c in categories])

    return jsonify({"suggestions": suggestions}), 200
