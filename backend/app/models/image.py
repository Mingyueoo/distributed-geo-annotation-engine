from datetime import datetime
from ..extensions import db


class Image(db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(500))
    file_path = db.Column(db.String(1000), nullable=False)
    file_size = db.Column(db.BigInteger)  # bytes
    mime_type = db.Column(db.String(100))

    # Geospatial metadata
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    bands = db.Column(db.Integer, default=1)  # number of spectral bands
    resolution = db.Column(db.Float)  # meters per pixel
    crs = db.Column(db.String(100))  # coordinate reference system, e.g. EPSG:4326
    bbox = db.Column(db.JSON)  # [min_lon, min_lat, max_lon, max_lat]
    acquisition_date = db.Column(db.DateTime)
    satellite = db.Column(db.String(100))  # Sentinel-1, Sentinel-2, etc.
    band_names = db.Column(db.JSON)  # e.g. ["B02","B03","B04","B08"]
    cloud_coverage = db.Column(db.Float)  # 0-100%

    # Status
    is_annotated = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    locked_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    locked_at = db.Column(db.DateTime)
    thumbnail_path = db.Column(db.String(1000))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False)

    # Relationships
    annotations = db.relationship("Annotation", backref="image", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self, include_annotations: bool = False) -> dict:
        data = {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "bands": self.bands,
            "resolution": self.resolution,
            "crs": self.crs,
            "bbox": self.bbox,
            "acquisition_date": self.acquisition_date.isoformat() if self.acquisition_date else None,
            "satellite": self.satellite,
            "band_names": self.band_names,
            "cloud_coverage": self.cloud_coverage,
            "is_annotated": self.is_annotated,
            "is_locked": self.is_locked,
            "locked_by": self.locked_by,
            "thumbnail_path": self.thumbnail_path,
            "dataset_id": self.dataset_id,
            "created_at": self.created_at.isoformat(),
            "annotation_count": self.annotations.count(),
        }
        if include_annotations:
            data["annotations"] = [a.to_dict() for a in self.annotations.all()]
        return data

    def __repr__(self):
        return f"<Image {self.filename}>"
