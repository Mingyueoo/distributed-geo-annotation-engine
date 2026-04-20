from datetime import datetime
from ..extensions import db

# Association table for dataset collaborators
dataset_collaborators = db.Table(
    "dataset_collaborators",
    db.Column("dataset_id", db.Integer, db.ForeignKey("datasets.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role", db.String(20), default="annotator"),
    db.Column("joined_at", db.DateTime, default=datetime.utcnow),
)


class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    data_type = db.Column(db.String(50))  # sentinel_optical, sentinel_sar, climate_simulation, etc.
    status = db.Column(db.String(20), default="active")  # active, archived, completed
    label_schema = db.Column(db.JSON)  # JSON schema defining allowed labels/classes
    metadata_ = db.Column("metadata", db.JSON)  # Extra metadata (satellite params, time range, etc.)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Relationships
    images = db.relationship("Image", backref="dataset", lazy="dynamic", cascade="all, delete-orphan")
    collaborators = db.relationship("User", secondary=dataset_collaborators, lazy="subquery")

    @property
    def image_count(self) -> int:
        return self.images.count()

    @property
    def annotation_count(self) -> int:
        from .annotation import Annotation
        return (
            Annotation.query.join(Annotation.image)
            .filter_by(dataset_id=self.id)
            .count()
        )

    @property
    def completion_percentage(self) -> float:
        total = self.image_count
        if total == 0:
            return 0.0
        annotated = self.images.filter_by(is_annotated=True).count()
        return round((annotated / total) * 100, 2)

    def to_dict(self, include_stats: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type,
            "status": self.status,
            "label_schema": self.label_schema,
            "metadata": self.metadata_,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_stats:
            data.update({
                "image_count": self.image_count,
                "annotation_count": self.annotation_count,
                "completion_percentage": self.completion_percentage,
                "collaborator_count": len(self.collaborators),
            })
        return data

    def __repr__(self):
        return f"<Dataset {self.name}>"
