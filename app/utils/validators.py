import re


def validate_password_strength(password):
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if len(password) > 128:
        errors.append("Password must not exceed 128 characters")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")

    common_passwords = [
        "password", "12345678", "qwerty123", "admin123", "letmein",
        "welcome1", "monkey123", "dragon12", "master12", "login123",
    ]
    if password.lower() in common_passwords:
        errors.append("Password is too common")

    return errors


def validate_username(username):
    errors = []

    if len(username) < 3:
        errors.append("Username must be at least 3 characters")

    if len(username) > 64:
        errors.append("Username must not exceed 64 characters")

    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        errors.append("Username can only contain letters, numbers, hyphens, and underscores")

    if username[0] in "-_":
        errors.append("Username must start with a letter or number")

    reserved = ["admin", "root", "system", "api", "www", "mail", "support", "help"]
    if username.lower() in reserved:
        errors.append("This username is reserved")

    return errors


def validate_url(url):
    pattern = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url))


def sanitize_html(content):
    import bleach

    allowed_tags = [
        "p", "br", "strong", "em", "u", "s", "h1", "h2", "h3", "h4",
        "ul", "ol", "li", "a", "img", "blockquote", "code", "pre",
        "table", "thead", "tbody", "tr", "th", "td", "hr", "div", "span",
    ]
    allowed_attrs = {
        "a": ["href", "title", "target", "rel"],
        "img": ["src", "alt", "width", "height"],
        "div": ["class"],
        "span": ["class"],
        "code": ["class"],
        "pre": ["class"],
    }

    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attrs, strip=True)
