from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, validate, ValidationError
from app import db
from app.models.category import Category
from app.utils.decorators import admin_required

categories_bp = Blueprint("categories", __name__)


class CategorySchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=64))
    description = fields.String(validate=validate.Length(max=256))
    color = fields.String(validate=validate.Length(max=7))
    icon = fields.String(validate=validate.Length(max=64))


@categories_bp.route("/", methods=["GET"])
def list_categories():
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order.asc()).all()
    return jsonify({
        "categories": [category.to_dict() for category in categories]
    }), 200


@categories_bp.route("/<slug>", methods=["GET"])
def get_category(slug):
    category = Category.query.filter_by(slug=slug, is_active=True).first_or_404()
    return jsonify({"category": category.to_dict()}), 200


@categories_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_category():
    schema = CategorySchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    if Category.query.filter_by(name=data["name"]).first():
        return jsonify({"error": "Category already exists"}), 409

    category = Category(
        name=data["name"],
        slug=Category.generate_slug(data["name"]),
        description=data.get("description"),
        color=data.get("color", "#6366f1"),
        icon=data.get("icon"),
    )

    db.session.add(category)
    db.session.commit()

    return jsonify({"category": category.to_dict()}), 201


@categories_bp.route("/<int:category_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_category(category_id):
    schema = CategorySchema()
    try:
        data = schema.load(request.get_json(), partial=True)
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    category = Category.query.get_or_404(category_id)

    for key, value in data.items():
        setattr(category, key, value)

    if "name" in data:
        category.slug = Category.generate_slug(data["name"])

    db.session.commit()
    return jsonify({"category": category.to_dict()}), 200


@categories_bp.route("/<int:category_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    category.is_active = False
    db.session.commit()
    return jsonify({"message": "Category deactivated"}), 200
