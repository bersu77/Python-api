import logging
from threading import Thread
from flask import current_app, render_template_string
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

logger = logging.getLogger(__name__)
mail = Mail()


def get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_verification_token(email):
    serializer = get_serializer()
    return serializer.dumps(email, salt="email-verification")


def verify_token(token, max_age=3600):
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt="email-verification", max_age=max_age)
        return email
    except Exception:
        return None


def generate_password_reset_token(email):
    serializer = get_serializer()
    return serializer.dumps(email, salt="password-reset")


def verify_password_reset_token(token, max_age=1800):
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt="password-reset", max_age=max_age)
        return email
    except Exception:
        return None


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            logger.error(f"Failed to send email: {e}")


def send_email(subject, recipient, html_body, text_body=None):
    app = current_app._get_current_object()
    msg = Message(
        subject=subject,
        recipients=[recipient],
        html=html_body,
        body=text_body or "",
    )
    thread = Thread(target=send_async_email, args=(app, msg))
    thread.start()
    return thread


def send_verification_email(user):
    token = generate_verification_token(user.email)
    base_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
    verification_url = f"{base_url}/verify-email?token={token}"

    html_body = render_template_string(
        """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Welcome, {{ user.username }}!</h2>
            <p>Please verify your email address by clicking the button below:</p>
            <a href="{{ url }}" style="display: inline-block; padding: 12px 24px;
               background-color: #6366f1; color: white; text-decoration: none;
               border-radius: 6px; margin: 16px 0;">Verify Email</a>
            <p>Or copy this link: {{ url }}</p>
            <p>This link expires in 1 hour.</p>
        </div>
        """,
        user=user,
        url=verification_url,
    )

    send_email("Verify Your Email", user.email, html_body)


def send_password_reset_email(user):
    token = generate_password_reset_token(user.email)
    base_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{base_url}/reset-password?token={token}"

    html_body = render_template_string(
        """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Password Reset Request</h2>
            <p>Hi {{ user.username }}, you requested a password reset.</p>
            <a href="{{ url }}" style="display: inline-block; padding: 12px 24px;
               background-color: #6366f1; color: white; text-decoration: none;
               border-radius: 6px; margin: 16px 0;">Reset Password</a>
            <p>Or copy this link: {{ url }}</p>
            <p>This link expires in 30 minutes.</p>
            <p>If you didn't request this, ignore this email.</p>
        </div>
        """,
        user=user,
        url=reset_url,
    )

    send_email("Password Reset", user.email, html_body)


def send_welcome_email(user):
    html_body = render_template_string(
        """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Welcome to the platform, {{ user.username }}!</h2>
            <p>Your account has been verified successfully.</p>
            <p>Start exploring and creating amazing content.</p>
        </div>
        """,
        user=user,
    )

    send_email("Welcome!", user.email, html_body)
