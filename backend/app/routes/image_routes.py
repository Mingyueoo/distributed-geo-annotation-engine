import os
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from ..models.image import Image
from ..models.dataset import Dataset
from ..models.user import User
from ..extensions import db
from ..services.image_service import ImageService
from ..utils.file_utils import allowed_file

image_bp = Blueprint("images", __name__)


@image_bp.route("/dataset/<int:dataset_id>", methods=["GET"])
@jwt_required()
def list_images(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    is_annotated = request.args.get("is_annotated", type=lambda v: v.lower() == "true")

    query = Image.query.filter_by(dataset_id=dataset_id)
    if is_annotated is not None:
        query = query.filter_by(is_annotated=is_annotated)

    paginated = query.paginate(page=page, per_page=per_page)
    return jsonify({
        "items": [img.to_dict() for img in paginated.items],
        "total": paginated.total,
        "pages": paginated.pages,
        "current_page": page,
        "per_page": per_page,
    }), 200


@image_bp.route("/dataset/<int:dataset_id>/upload", methods=["POST"])
@jwt_required()
def upload_image(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    files = request.files.getlist("file")
    uploaded = []
    errors = []

    for f in files:
        if f.filename == "":
            continue
        if not allowed_file(f.filename):
            errors.append({"filename": f.filename, "error": "File type not allowed"})
            continue
        try:
            image = ImageService.save_image(f, dataset_id)
            uploaded.append(image.to_dict())
        except Exception as e:
            errors.append({"filename": f.filename, "error": str(e)})

    return jsonify({"uploaded": uploaded, "errors": errors}), 201 if uploaded else 400


@image_bp.route("/<int:image_id>", methods=["GET"])
@jwt_required()
def get_image(image_id):
    image = Image.query.get_or_404(image_id)
    include_annotations = request.args.get("include_annotations", "false").lower() == "true"
    return jsonify(image.to_dict(include_annotations=include_annotations)), 200


@image_bp.route("/<int:image_id>", methods=["DELETE"])
@jwt_required()
def delete_image(image_id):
    image = Image.query.get_or_404(image_id)
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    dataset = Dataset.query.get(image.dataset_id)
    if dataset.owner_id != user_id and user.role != "admin":
        return jsonify({"error": "Permission denied"}), 403

    ImageService.delete_image(image)
    return jsonify({"message": "Image deleted"}), 200


@image_bp.route("/<int:image_id>/file", methods=["GET"])
# @jwt_required()
def serve_image_file(image_id):
    image = Image.query.get_or_404(image_id)
    if not os.path.exists(image.file_path):
        return jsonify({"error": "File not found on disk"}), 404
    return send_file(image.file_path, mimetype=image.mime_type)


@image_bp.route("/<int:image_id>/thumbnail", methods=["GET"])
@jwt_required()
def serve_thumbnail(image_id):
    image = Image.query.get_or_404(image_id)
    if not image.thumbnail_path or not os.path.exists(image.thumbnail_path):
        return jsonify({"error": "Thumbnail not available"}), 404
    return send_file(image.thumbnail_path, mimetype="image/jpeg")


@image_bp.route("/<int:image_id>/lock", methods=["POST"])
@jwt_required()
def lock_image(image_id):
    """Lock an image for exclusive annotation."""
    image = Image.query.get_or_404(image_id)
    user_id = int(get_jwt_identity())

    if image.is_locked and image.locked_by != user_id:
        return jsonify({"error": "Image is locked by another user"}), 409

    from datetime import datetime
    image.is_locked = True
    image.locked_by = user_id
    image.locked_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Image locked", "image": image.to_dict()}), 200


@image_bp.route("/<int:image_id>/unlock", methods=["POST"])
@jwt_required()
def unlock_image(image_id):
    image = Image.query.get_or_404(image_id)
    user_id = int(get_jwt_identity())

    if image.locked_by != user_id:
        user = User.query.get(user_id)
        if user.role != "admin":
            return jsonify({"error": "Cannot unlock image locked by another user"}), 403

    image.is_locked = False
    image.locked_by = None
    image.locked_at = None
    db.session.commit()
    return jsonify({"message": "Image unlocked"}), 200


@image_bp.route("/<int:image_id>/ai-suggest", methods=["POST"])
@jwt_required()
def ai_suggest(image_id):
    """Trigger AI auto-labeling for an image."""
    image = Image.query.get_or_404(image_id)
    from ..tasks.ai_tasks import run_ai_labeling
    task = run_ai_labeling.delay(image_id)
    return jsonify({"task_id": task.id, "message": "AI labeling task queued"}), 202


@image_bp.route("/task/<task_id>/status", methods=["GET"])
@jwt_required()
def task_status(task_id):
    from ..tasks.ai_tasks import run_ai_labeling
    task = run_ai_labeling.AsyncResult(task_id)
    return jsonify({
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
    }), 200
