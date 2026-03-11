import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGE_SIZE = (1920, 1080)
THUMBNAIL_SIZE = (300, 300)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_filename(original_filename):
    ext = original_filename.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"


def save_upload(file, subfolder="images"):
    if not file or not allowed_file(file.filename):
        return None, "Invalid file type"

    filename = generate_filename(secure_filename(file.filename))
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    optimize_image(filepath)

    thumbnail_path = create_thumbnail(filepath, subfolder)

    return {
        "filename": filename,
        "path": filepath,
        "url": f"/uploads/{subfolder}/{filename}",
        "thumbnail_url": f"/uploads/{subfolder}/thumbnails/{filename}" if thumbnail_path else None,
    }, None


def optimize_image(filepath, max_size=MAX_IMAGE_SIZE, quality=85):
    try:
        with Image.open(filepath) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(filepath, optimize=True, quality=quality)
    except Exception:
        pass


def create_thumbnail(filepath, subfolder, size=THUMBNAIL_SIZE):
    try:
        thumbnail_dir = os.path.join(
            current_app.config["UPLOAD_FOLDER"], subfolder, "thumbnails"
        )
        os.makedirs(thumbnail_dir, exist_ok=True)

        filename = os.path.basename(filepath)
        thumbnail_path = os.path.join(thumbnail_dir, filename)

        with Image.open(filepath) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, optimize=True, quality=80)

        return thumbnail_path
    except Exception:
        return None


def delete_upload(filename, subfolder="images"):
    try:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder, filename)
        thumbnail_path = os.path.join(
            current_app.config["UPLOAD_FOLDER"], subfolder, "thumbnails", filename
        )

        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

        return True
    except Exception:
        return False
