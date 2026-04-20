from datetime import datetime
from ..extensions import db


class Annotation(db.Model):
    __tablename__ = "annotations"

    id = db.Column(db.Integer, primary_key=True)

    # Annotation type
    annotation_type = db.Column(db.String(50), nullable=False)
    # bbox, polygon, point, polyline, classification, segmentation_mask, bounding_box_3d

    # Label / class
    label = db.Column(db.String(200), nullable=False)
    label_id = db.Column(db.String(100))  # ID from label schema
    confidence = db.Column(db.Float, default=1.0)  # 0.0 - 1.0
    is_ai_generated = db.Column(db.Boolean, default=False)

    # Geometry (GeoJSON format)
    geometry = db.Column(db.JSON)
    # For bbox: {"type":"bbox","coordinates":[x1,y1,x2,y2]}
    # For polygon: {"type":"Polygon","coordinates":[[[lon,lat],...]]}
    # For point: {"type":"Point","coordinates":[lon,lat]}
    # For segmentation mask: {"type":"mask","rle":...} or {"type":"mask","bitmap":...}

    # Attributes / properties (custom key-value pairs from label schema)
    attributes = db.Column(db.JSON, default={})

    # Multispectral / temporal context
    band_specific = db.Column(db.Boolean, default=False)
    band_index = db.Column(db.Integer)  # which spectral band this annotation applies to
    time_step = db.Column(db.Integer)  # for temporal/climate data (netCDF dimension)

    # Review workflow
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected, needs_review
    review_comment = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "annotation_type": self.annotation_type,
            "label": self.label,
            "label_id": self.label_id,
            "confidence": self.confidence,
            "is_ai_generated": self.is_ai_generated,
            "geometry": self.geometry,
            "attributes": self.attributes,
            "band_specific": self.band_specific,
            "band_index": self.band_index,
            "time_step": self.time_step,
            "status": self.status,
            "review_comment": self.review_comment,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "image_id": self.image_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f"<Annotation {self.annotation_type}:{self.label} on image {self.image_id}>"
