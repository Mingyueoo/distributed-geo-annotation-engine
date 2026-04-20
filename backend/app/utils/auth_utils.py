from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from ..models.user import User


def role_required(*roles):
    """Decorator that restricts an endpoint to users with one of the given roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or user.role not in roles:
                return jsonify({"error": f"One of {roles} role required"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user() -> User:
    user_id = get_jwt_identity()
    return User.query.get(user_id)


def is_dataset_member(dataset, user_id: int) -> bool:
    """Check if user is owner or collaborator of a dataset."""
    if dataset.owner_id == user_id:
        return True
    return any(c.id == user_id for c in dataset.collaborators)
