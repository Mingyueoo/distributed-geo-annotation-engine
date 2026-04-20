from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from ..models.user import User
from ..models.dataset import Dataset
from ..extensions import db
from ..schemas.dataset_schema import DatasetCreateSchema, DatasetUpdateSchema, DatasetQuerySchema
from ..services.dataset_service import DatasetService

dataset_bp = Blueprint("datasets", __name__)
_create_schema = DatasetCreateSchema()
_update_schema = DatasetUpdateSchema()
_query_schema = DatasetQuerySchema()


@dataset_bp.route("/", methods=["GET"])
@jwt_required()
def list_datasets():
    try:
        args = _query_schema.load(request.args)
    except ValidationError as e:
        return jsonify({"error": e.messages}), 400

    user_id = int(get_jwt_identity())
    result = DatasetService.list_datasets(user_id, **args)
    return jsonify(result), 200


@dataset_bp.route("/", methods=["POST"])
@jwt_required()
def create_dataset():
    try:
        data = _create_schema.load(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"error": e.messages}), 400

    user_id = int(get_jwt_identity())
    dataset = DatasetService.create_dataset(user_id, data)
    return jsonify(dataset.to_dict(include_stats=True)), 201


@dataset_bp.route("/<int:dataset_id>", methods=["GET"])
@jwt_required()
def get_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    return jsonify(dataset.to_dict(include_stats=True)), 200


@dataset_bp.route("/<int:dataset_id>", methods=["PUT"])
@jwt_required()
def update_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    user_id = int(get_jwt_identity())

    if dataset.owner_id != user_id:
        user = User.query.get(user_id)
        if user.role != "admin":
            return jsonify({"error": "Permission denied"}), 403

    try:
        data = _update_schema.load(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"error": e.messages}), 400

    dataset = DatasetService.update_dataset(dataset, data)
    return jsonify(dataset.to_dict(include_stats=True)), 200


@dataset_bp.route("/<int:dataset_id>", methods=["DELETE"])
@jwt_required()
def delete_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    user_id = int(get_jwt_identity())

    if dataset.owner_id != user_id:
        user = User.query.get(user_id)
        if user.role != "admin":
            return jsonify({"error": "Permission denied"}), 403

    db.session.delete(dataset)
    db.session.commit()
    return jsonify({"message": "Dataset deleted"}), 200


@dataset_bp.route("/<int:dataset_id>/collaborators", methods=["POST"])
@jwt_required()
def add_collaborator(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    user_id = int(get_jwt_identity())

    if dataset.owner_id != user_id:
        return jsonify({"error": "Only the owner can manage collaborators"}), 403

    data = request.get_json() or {}
    collab_user = User.query.filter_by(email=data.get("email")).first()
    if not collab_user:
        return jsonify({"error": "User not found"}), 404

    if collab_user not in dataset.collaborators:
        dataset.collaborators.append(collab_user)
        db.session.commit()

    return jsonify({"message": f"User {collab_user.username} added as collaborator"}), 200


@dataset_bp.route("/<int:dataset_id>/collaborators/<int:user_id>", methods=["DELETE"])
@jwt_required()
def remove_collaborator(dataset_id, user_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    current_user_id = int(get_jwt_identity())

    if dataset.owner_id != current_user_id:
        return jsonify({"error": "Only the owner can manage collaborators"}), 403

    collab_user = User.query.get_or_404(user_id)
    if collab_user in dataset.collaborators:
        dataset.collaborators.remove(collab_user)
        db.session.commit()

    return jsonify({"message": "Collaborator removed"}), 200


@dataset_bp.route("/<int:dataset_id>/export", methods=["GET"])
@jwt_required()
def export_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    fmt = request.args.get("format", "coco")  # coco, yolo, geojson, csv

    result = DatasetService.export_dataset(dataset, fmt)
    return jsonify(result), 200


@dataset_bp.route("/<int:dataset_id>/stats", methods=["GET"])
@jwt_required()
def dataset_stats(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    stats = DatasetService.get_dataset_stats(dataset)
    return jsonify(stats), 200
