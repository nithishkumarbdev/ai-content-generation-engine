import os
import uuid

from fastapi import UploadFile

from app.config import settings

UPLOADS_DIR = os.path.join(settings.STATIC_DIR, settings.UPLOADS_SUBDIR)
GENERATED_DIR = os.path.join(settings.STATIC_DIR, settings.GENERATED_SUBDIR)


def ensure_dirs() -> None:
    """Create the upload/generated directories if they don't exist. Called once on startup."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(GENERATED_DIR, exist_ok=True)


def save_upload(file: UploadFile) -> str:
    """Persist an uploaded reference image to disk and return its relative path."""
    extension = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4()}{extension}"
    destination = os.path.join(UPLOADS_DIR, filename)

    with open(destination, "wb") as out_file:
        out_file.write(file.file.read())

    return destination


def save_generated_bytes(image_bytes: bytes, extension: str = ".png") -> str:
    """Persist generated image bytes to disk and return the relative path."""
    filename = f"{uuid.uuid4()}{extension}"
    destination = os.path.join(GENERATED_DIR, filename)

    with open(destination, "wb") as out_file:
        out_file.write(image_bytes)

    return destination


def to_public_url(relative_path: str) -> str:
    """Turn a filesystem path under STATIC_DIR into a URL the frontend can load."""
    static_prefix = relative_path.replace(settings.STATIC_DIR, "/static", 1)
    static_prefix = static_prefix.replace(os.sep, "/")
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{static_prefix}"
    return static_prefix
