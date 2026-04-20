from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from ..models.annotation import Annotation
from ..models.image import Image
from ..models.user import User
from ..extensions import db, socketio
from ..schemas.annotation_schema import (
    AnnotationCreateSchema, AnnotationUpdateSchema,
    AnnotationBulkCreateSchema, AnnotationQuerySchema
)
from ..services.annotation_service import AnnotationService

annotation_bp = Blueprint("annotations", __name__)
_create_schema = AnnotationCreateSchema()
_update_schema = AnnotationUpdateSchema()
_bulk_schema = AnnotationBulkCreateSchema()
_query_schema = AnnotationQuerySchema()


@annotation_bp.route("/image/<int:image_id>", methods=["GET"])
@jwt_required()
def list_annotations(image_id):
    Image.query.get_or_404(image_id)
    try:
        args = _query_schema.load(request.args)
    except ValidationError as e:
        return jsonify({"error": e.messages}), 400

    result = AnnotationService.list_annotations(image_id, **args)
    return jsonify(result), 200


@annotation_bp.route("/image/<int:image_id>", methods=["POST"])
@jwt_required()
def create_annotation(image_id):
    Image.query.get_or_404(image_id)
    user_id = int(get_jwt_identity())

    try:
        data = _create_schema.load(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"error": e.messages}), 400

    annotation = AnnotationService.create_annotation(image_id, user_id, data)

    # Broadcast real-time update to collaborators
    socketio.emit(
        "annotation_created",
        {"image_id": image_id, "annotation": annotation.to_dict()},
        room=f"image_{image_id}",
    )

    return jsonify(annotation.to_dict()), 201


@annotation_bp.route("/image/<int:image_id>/bulk", methods=["POST"])
@jwt_required()
def bulk_create_annotations(image_id):
    Image.query.get_or_404(image_id)
    user_id = int(get_jwt_identity())

    try:
        data = _bulk_schema.load(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"error": e.messages}), 400

    annotations = AnnotationService.bulk_create_annotations(image_id, user_id, data["annotations"])

    socketio.emit(
        "annotations_bulk_created",
        {"image_id": image_id, "count": len(annotations)},
        room=f"image_{image_id}",
    )

    return jsonify([a.to_dict() for a in annotations]), 201


@annotation_bp.route("/<int:annotation_id>", methods=["GET"])
@jwt_required()
def get_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    return jsonify(annotation.to_dict()), 200


@annotation_bp.route("/<int:annotation_id>", methods=["PUT"])
@jwt_required()
def update_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    user_id = int(get_jwt_identity())

    # Only author or reviewer/admin can update
    if annotation.user_id != user_id:
        user = User.query.get(user_id)
        if user.role not in ("reviewer", "admin"):
            return jsonify({"error": "Permission denied"}), 403

    try:
        data = _update_schema.load(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"error": e.messages}), 400

    annotation = AnnotationService.update_annotation(annotation, user_id, data)

    socketio.emit(
        "annotation_updated",
        {"image_id": annotation.image_id, "annotation": annotation.to_dict()},
        room=f"image_{annotation.image_id}",
    )

    return jsonify(annotation.to_dict()), 200


@annotation_bp.route("/<int:annotation_id>", methods=["DELETE"])
@jwt_required()
def delete_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    user_id = int(get_jwt_identity())

    if annotation.user_id != user_id:
        user = User.query.get(user_id)
        if user.role not in ("reviewer", "admin"):
            return jsonify({"error": "Permission denied"}), 403

    image_id = annotation.image_id
    db.session.delete(annotation)
    db.session.commit()

    socketio.emit(
        "annotation_deleted",
        {"image_id": image_id, "annotation_id": annotation_id},
        room=f"image_{image_id}",
    )

    return jsonify({"message": "Annotation deleted"}), 200


@annotation_bp.route("/<int:annotation_id>/review", methods=["POST"])
@jwt_required()
def review_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if user.role not in ("reviewer", "admin"):
        return jsonify({"error": "Reviewer role required"}), 403

    data = request.get_json() or {}
    if "status" not in data or data["status"] not in ("approved", "rejected", "needs_review"):
        return jsonify({"error": "Valid status required: approved, rejected, needs_review"}), 400

    from datetime import datetime
    annotation.status = data["status"]
    annotation.review_comment = data.get("comment", "")
    annotation.reviewed_by = user_id
    annotation.reviewed_at = datetime.utcnow()
    db.session.commit()

    return jsonify(annotation.to_dict()), 200


# WebSocket event handlers
@socketio.on("join_image_room")
def handle_join(data):
    from flask_socketio import join_room
    image_id = data.get("image_id")
    if image_id:
        join_room(f"image_{image_id}")


@socketio.on("leave_image_room")
def handle_leave(data):
    from flask_socketio import leave_room
    image_id = data.get("image_id")
    if image_id:
        leave_room(f"image_{image_id}")
