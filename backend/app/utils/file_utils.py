import os
from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tif", "tiff", "nc", "h5", "hdf5"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def ensure_upload_dirs(dataset_id: int) -> str:
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(dataset_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def human_readable_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
