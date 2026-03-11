from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt,
    jwt_required,
)
from marshmallow import Schema, fields, validate, ValidationError
from app import db, limiter
from app.models.user import User
from app.models.token import TokenBlocklist
from app.services.email_service import send_verification_email, send_password_reset_email
from app.utils.validators import validate_password_strength
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__)


class RegisterSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=3, max=64))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    first_name = fields.String(validate=validate.Length(max=64))
    last_name = fields.String(validate=validate.Length(max=64))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


class PasswordResetRequestSchema(Schema):
    email = fields.Email(required=True)


class PasswordResetSchema(Schema):
    token = fields.String(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))


class ChangePasswordSchema(Schema):
    current_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=validate.Length(min=8, max=128))


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour")
def register():
    schema = RegisterSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    password_errors = validate_password_strength(data["password"])
    if password_errors:
        return jsonify({"error": "Weak password", "details": password_errors}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 409

    user = User(
        username=data["username"],
        email=data["email"],
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    send_verification_email(user)

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "Registration successful",
        "user": user.to_dict(include_email=True),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    schema = LoginSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    user = User.query.filter_by(email=data["email"]).first()

    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    if not user.is_active:
        return jsonify({"error": "Account has been deactivated"}), 403

    user.last_seen = datetime.utcnow()
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(include_email=True),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({"access_token": access_token}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    token_type = jwt_data["type"]
    user_id = get_jwt_identity()
    expires_at = datetime.fromtimestamp(jwt_data["exp"])

    TokenBlocklist.revoke_token(jti, token_type, int(user_id), expires_at)

    return jsonify({"message": "Successfully logged out"}), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    schema = ChangePasswordSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    user = User.query.get(int(get_jwt_identity()))

    if not user.check_password(data["current_password"]):
        return jsonify({"error": "Current password is incorrect"}), 400

    password_errors = validate_password_strength(data["new_password"])
    if password_errors:
        return jsonify({"error": "Weak password", "details": password_errors}), 400

    user.set_password(data["new_password"])
    db.session.commit()

    TokenBlocklist.revoke_all_user_tokens(user.id)

    return jsonify({"message": "Password changed successfully"}), 200


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3 per hour")
def forgot_password():
    schema = PasswordResetRequestSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if user:
        send_password_reset_email(user)

    return jsonify({"message": "If the email exists, a password reset link has been sent"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict(include_email=True)}), 200
