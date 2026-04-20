"""
tests/test_api.py
Integration tests for GeoLabeler REST API endpoints.
Run with: pytest tests/test_api.py -v
"""
import json
import pytest
from backend.app import create_app
from backend.app.extensions import db as _db
from backend.app.config import TestingConfig


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def auth_headers(client):
    """Register and log in a test user, return JWT Authorization headers."""
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@test.com",
        "password": "testpass123",
        "full_name": "Test User",
    })
    res = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    data = json.loads(res.data)
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    """Register and log in an admin user."""
    client.post("/api/auth/register", json={
        "username": "adminuser",
        "email": "admin@test.com",
        "password": "adminpass123",
        "role": "admin",
    })
    res = client.post("/api/auth/login", json={
        "username": "adminuser",
        "password": "adminpass123",
    })
    data = json.loads(res.data)
    return {"Authorization": f"Bearer {data['access_token']}"}


# ── Auth Tests ─────────────────────────────────────────────────────────────────

class TestAuth:

    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "password123",
        })
        assert res.status_code == 201
        data = json.loads(res.data)
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"

    def test_register_duplicate_username(self, client):
        payload = {"username": "dupuser", "email": "dup@test.com", "password": "pass"}
        client.post("/api/auth/register", json=payload)
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 409

    def test_login_success(self, client):
        res = client.post("/api/auth/login", json={
            "username": "testuser", "password": "testpass123"
        })
        assert res.status_code == 200
        assert "access_token" in json.loads(res.data)

    def test_login_wrong_password(self, client):
        res = client.post("/api/auth/login", json={
            "username": "testuser", "password": "wrongpass"
        })
        assert res.status_code == 401

    def test_me_authenticated(self, client, auth_headers):
        res = client.get("/api/auth/me", headers=auth_headers)
        assert res.status_code == 200
        assert json.loads(res.data)["username"] == "testuser"

    def test_me_unauthenticated(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401


# ── Dataset Tests ──────────────────────────────────────────────────────────────

class TestDatasets:

    def test_create_dataset(self, client, auth_headers):
        res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "Test Dataset",
            "description": "A test dataset",
            "data_type": "sentinel_optical",
        })
        assert res.status_code == 201
        data = json.loads(res.data)
        assert data["name"] == "Test Dataset"
        assert data["data_type"] == "sentinel_optical"
        return data["id"]

    def test_create_dataset_missing_name(self, client, auth_headers):
        res = client.post("/api/datasets/", headers=auth_headers, json={
            "description": "No name provided",
        })
        assert res.status_code == 400

    def test_list_datasets(self, client, auth_headers):
        res = client.get("/api/datasets/", headers=auth_headers)
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "items" in data
        assert "total" in data

    def test_get_dataset(self, client, auth_headers):
        # Create first
        create_res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "Get Test Dataset",
            "data_type": "other",
        })
        ds_id = json.loads(create_res.data)["id"]

        res = client.get(f"/api/datasets/{ds_id}", headers=auth_headers)
        assert res.status_code == 200
        assert json.loads(res.data)["id"] == ds_id

    def test_get_nonexistent_dataset(self, client, auth_headers):
        res = client.get("/api/datasets/99999", headers=auth_headers)
        assert res.status_code == 404

    def test_update_dataset(self, client, auth_headers):
        create_res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "Update Me", "data_type": "other",
        })
        ds_id = json.loads(create_res.data)["id"]

        res = client.put(f"/api/datasets/{ds_id}", headers=auth_headers, json={
            "name": "Updated Name", "status": "completed",
        })
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["name"] == "Updated Name"
        assert data["status"] == "completed"

    def test_delete_dataset(self, client, auth_headers):
        create_res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "Delete Me", "data_type": "other",
        })
        ds_id = json.loads(create_res.data)["id"]

        res = client.delete(f"/api/datasets/{ds_id}", headers=auth_headers)
        assert res.status_code == 200

        get_res = client.get(f"/api/datasets/{ds_id}", headers=auth_headers)
        assert get_res.status_code == 404

    def test_dataset_stats(self, client, auth_headers):
        create_res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "Stats Dataset", "data_type": "other",
        })
        ds_id = json.loads(create_res.data)["id"]
        res = client.get(f"/api/datasets/{ds_id}/stats", headers=auth_headers)
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "total_images" in data
        assert "total_annotations" in data

    def test_dataset_export_coco(self, client, auth_headers):
        create_res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "Export Dataset", "data_type": "other",
        })
        ds_id = json.loads(create_res.data)["id"]
        res = client.get(f"/api/datasets/{ds_id}/export?format=coco", headers=auth_headers)
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "images" in data
        assert "annotations" in data
        assert "categories" in data

    def test_dataset_export_geojson(self, client, auth_headers):
        create_res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "GeoJSON Export", "data_type": "other",
        })
        ds_id = json.loads(create_res.data)["id"]
        res = client.get(f"/api/datasets/{ds_id}/export?format=geojson", headers=auth_headers)
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["type"] == "FeatureCollection"


# ── Annotation Tests ───────────────────────────────────────────────────────────

class TestAnnotations:

    @pytest.fixture(autouse=True)
    def setup_image(self, client, auth_headers):
        """Create a dataset + image record for annotation tests."""
        ds_res = client.post("/api/datasets/", headers=auth_headers, json={
            "name": "Annotation Test DS", "data_type": "other",
        })
        self.ds_id = json.loads(ds_res.data)["id"]

        # Directly insert an image into DB for testing
        from backend.app.models.image import Image
        from backend.app.extensions import db
        from flask import current_app
        with client.application.app_context():
            img = Image(
                filename="test.png",
                original_filename="test.png",
                file_path="/tmp/test.png",
                dataset_id=self.ds_id,
            )
            db.session.add(img)
            db.session.commit()
            self.image_id = img.id

    def test_create_bbox_annotation(self, client, auth_headers):
        res = client.post(f"/api/annotations/image/{self.image_id}", headers=auth_headers, json={
            "annotation_type": "bbox",
            "label": "cloud",
            "geometry": {"type": "bbox", "coordinates": [10, 10, 100, 100]},
            "confidence": 0.95,
        })
        assert res.status_code == 201
        data = json.loads(res.data)
        assert data["label"] == "cloud"
        assert data["annotation_type"] == "bbox"
        assert data["confidence"] == 0.95
        self.ann_id = data["id"]
        return data["id"]

    def test_create_polygon_annotation(self, client, auth_headers):
        res = client.post(f"/api/annotations/image/{self.image_id}", headers=auth_headers, json={
            "annotation_type": "polygon",
            "label": "water",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[10,10],[50,10],[50,50],[10,50],[10,10]]]
            },
        })
        assert res.status_code == 201

    def test_create_annotation_invalid_type(self, client, auth_headers):
        res = client.post(f"/api/annotations/image/{self.image_id}", headers=auth_headers, json={
            "annotation_type": "invalid_type",
            "label": "test",
            "geometry": {},
        })
        assert res.status_code == 400

    def test_list_annotations(self, client, auth_headers):
        # Create one first
        client.post(f"/api/annotations/image/{self.image_id}", headers=auth_headers, json={
            "annotation_type": "point",
            "label": "marker",
            "geometry": {"type": "Point", "coordinates": [50, 50]},
        })
        res = client.get(f"/api/annotations/image/{self.image_id}", headers=auth_headers)
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "items" in data
        assert data["total"] >= 1

    def test_bulk_create_annotations(self, client, auth_headers):
        res = client.post(
            f"/api/annotations/image/{self.image_id}/bulk",
            headers=auth_headers,
            json={"annotations": [
                {"annotation_type": "bbox", "label": "cloud",
                 "geometry": {"type": "bbox", "coordinates": [0,0,50,50]}},
                {"annotation_type": "bbox", "label": "water",
                 "geometry": {"type": "bbox", "coordinates": [60,60,120,120]}},
            ]},
        )
        assert res.status_code == 201
        data = json.loads(res.data)
        assert len(data) == 2

    def test_update_annotation(self, client, auth_headers):
        create_res = client.post(f"/api/annotations/image/{self.image_id}", headers=auth_headers, json={
            "annotation_type": "bbox", "label": "old_label",
            "geometry": {"type": "bbox", "coordinates": [0,0,10,10]},
        })
        ann_id = json.loads(create_res.data)["id"]

        res = client.put(f"/api/annotations/{ann_id}", headers=auth_headers, json={
            "label": "new_label", "confidence": 0.8,
        })
        assert res.status_code == 200
        assert json.loads(res.data)["label"] == "new_label"

    def test_delete_annotation(self, client, auth_headers):
        create_res = client.post(f"/api/annotations/image/{self.image_id}", headers=auth_headers, json={
            "annotation_type": "point", "label": "delete_me",
            "geometry": {"type": "Point", "coordinates": [1,1]},
        })
        ann_id = json.loads(create_res.data)["id"]

        res = client.delete(f"/api/annotations/{ann_id}", headers=auth_headers)
        assert res.status_code == 200

        get_res = client.get(f"/api/annotations/{ann_id}", headers=auth_headers)
        assert get_res.status_code == 404

    def test_filter_annotations_by_label(self, client, auth_headers):
        client.post(f"/api/annotations/image/{self.image_id}", headers=auth_headers, json={
            "annotation_type": "bbox", "label": "unique_filter_label",
            "geometry": {"type": "bbox", "coordinates": [0,0,5,5]},
        })
        res = client.get(
            f"/api/annotations/image/{self.image_id}?label=unique_filter_label",
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = json.loads(res.data)
        assert all(a["label"] == "unique_filter_label" for a in data["items"])
