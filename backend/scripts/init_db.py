#!/usr/bin/env python3
"""
scripts/init_db.py
Run once to create all database tables.
Usage: FLASK_ENV=development python scripts/init_db.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.extensions import db
from app.config import config

env = os.environ.get("FLASK_ENV", "development")
app = create_app(config[env])

with app.app_context():
    db.create_all()
    print("✓ All tables created successfully.")
