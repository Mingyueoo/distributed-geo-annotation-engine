#!/usr/bin/env python3
"""
scripts/seed_data.py
Populate the database with demo users, datasets and sample annotations.
Usage: FLASK_ENV=development python scripts/seed_data.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.extensions import db
from app.models import User, Dataset, Image, Annotation
from app.config import config

env = os.environ.get("FLASK_ENV", "development")
app = create_app(config[env])

LABEL_SCHEMA = {
    "classes": [
        {"id": "cloud",     "name": "Cloud",     "color": "#f0c040"},
        {"id": "water",     "name": "Water",     "color": "#2ecc8f"},
        {"id": "urban",     "name": "Urban",     "color": "#e05252"},
        {"id": "vegetation","name": "Vegetation","color": "#40c040"},
        {"id": "snow_ice",  "name": "Snow/Ice",  "color": "#d0eeff"},
    ],
    "annotation_types": ["bbox", "polygon", "classification"],
}

with app.app_context():
    db.create_all()

    # ── Users ──────────────────────────────────────────────
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", email="admin@geolabeler.esa.int",
                     full_name="Admin User", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    if not User.query.filter_by(username="annotator1").first():
        ann = User(username="annotator1", email="ann1@geolabeler.esa.int",
                   full_name="Alice Annotator", role="annotator")
        ann.set_password("pass1234")
        db.session.add(ann)

    if not User.query.filter_by(username="reviewer1").first():
        rev = User(username="reviewer1", email="rev1@geolabeler.esa.int",
                   full_name="Robert Reviewer", role="reviewer")
        rev.set_password("pass1234")
        db.session.add(rev)

    db.session.commit()

    admin = User.query.filter_by(username="admin").first()

    # ── Datasets ───────────────────────────────────────────
    if not Dataset.query.filter_by(name="Sentinel-2 Europe 2023").first():
        ds = Dataset(
            name="Sentinel-2 Europe 2023",
            description="Optical multispectral imagery covering central Europe, 10 m resolution.",
            data_type="sentinel_optical",
            label_schema=LABEL_SCHEMA,
            metadata_={"bands": ["B02","B03","B04","B08"], "resolution_m": 10, "crs": "EPSG:4326"},
            owner_id=admin.id,
        )
        db.session.add(ds)

    if not Dataset.query.filter_by(name="ERA5 Climate Reanalysis").first():
        ds2 = Dataset(
            name="ERA5 Climate Reanalysis",
            description="ECMWF ERA5 hourly data on single levels — temperature & precipitation.",
            data_type="climate_simulation",
            label_schema={"classes": [
                {"id": "extreme_heat", "name": "Extreme Heat", "color": "#e05252"},
                {"id": "flood_risk",   "name": "Flood Risk",   "color": "#2ecc8f"},
            ], "annotation_types": ["bbox", "classification"]},
            owner_id=admin.id,
        )
        db.session.add(ds2)

    db.session.commit()
    print("✓ Seed data loaded. Users: admin/admin123  annotator1/pass1234  reviewer1/pass1234")
