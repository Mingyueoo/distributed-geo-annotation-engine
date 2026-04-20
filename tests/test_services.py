"""
tests/test_services.py
Unit tests for GeoLabeler service layer.
Run with: pytest tests/test_services.py -v
"""
import pytest
from unittest.mock import MagicMock, patch
from backend.app import create_app
from backend.app.extensions import db as _db
from backend.app.config import TestingConfig


@pytest.fixture(scope="module")
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="module")
def test_user(app):
    from backend.app.models.user import User
    user = User(username="svc_user", email="svc@test.com", role="admin")
    user.set_password("pass")
    _db.session.add(user)
    _db.session.commit()
    return user


# ── DatasetService ──────────────────────────────────────────────────────────────

class TestDatasetService:

    def test_create_dataset(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        ds = DatasetService.create_dataset(test_user.id, {
            "name": "Service Test DS",
            "description": "Created by service",
            "data_type": "sentinel_optical",
            "metadata": {"resolution": 10},
        })
        assert ds.id is not None
        assert ds.name == "Service Test DS"
        assert ds.owner_id == test_user.id

    def test_list_datasets_filters(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        DatasetService.create_dataset(test_user.id, {"name": "DS Alpha", "data_type": "sentinel_sar"})
        DatasetService.create_dataset(test_user.id, {"name": "DS Beta",  "data_type": "climate_simulation"})

        result = DatasetService.list_datasets(test_user.id, data_type="sentinel_sar")
        types = {d["data_type"] for d in result["items"]}
        assert types == {"sentinel_sar"}

    def test_list_datasets_search(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        DatasetService.create_dataset(test_user.id, {"name": "Searchable Unique XYZ"})
        result = DatasetService.list_datasets(test_user.id, search="Unique XYZ")
        names = [d["name"] for d in result["items"]]
        assert any("Unique XYZ" in n for n in names)

    def test_update_dataset(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        from backend.app.models.dataset import Dataset
        ds = DatasetService.create_dataset(test_user.id, {"name": "Before Update"})
        updated = DatasetService.update_dataset(ds, {"name": "After Update", "status": "completed"})
        assert updated.name == "After Update"
        assert updated.status == "completed"

    def test_export_coco_structure(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        ds = DatasetService.create_dataset(test_user.id, {
            "name": "COCO Export DS",
            "label_schema": {
                "classes": [{"id": "cls1", "name": "Object", "color": "#ff0000"}],
                "annotation_types": ["bbox"],
            },
        })
        result = DatasetService.export_dataset(ds, "coco")
        assert "images" in result
        assert "annotations" in result
        assert "categories" in result
        assert result["categories"][0]["name"] == "Object"

    def test_export_geojson_structure(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        ds = DatasetService.create_dataset(test_user.id, {"name": "GeoJSON DS"})
        result = DatasetService.export_dataset(ds, "geojson")
        assert result["type"] == "FeatureCollection"
        assert "features" in result

    def test_export_csv_structure(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        ds = DatasetService.create_dataset(test_user.id, {"name": "CSV DS"})
        result = DatasetService.export_dataset(ds, "csv")
        assert result["format"] == "csv"
        assert "headers" in result
        assert "data" in result

    def test_get_dataset_stats_empty(self, app, test_user):
        from backend.app.services.dataset_service import DatasetService
        ds = DatasetService.create_dataset(test_user.id, {"name": "Stats DS"})
        stats = DatasetService.get_dataset_stats(ds)
        assert stats["total_images"] == 0
        assert stats["total_annotations"] == 0
        assert stats["completion_percentage"] == 0.0


# ── AnnotationService ───────────────────────────────────────────────────────────

class TestAnnotationService:

    @pytest.fixture(autouse=True)
    def setup(self, app, test_user):
        from backend.app.models.dataset import Dataset
        from backend.app.models.image import Image
        ds = Dataset(name="Ann Svc DS", owner_id=test_user.id)
        _db.session.add(ds)
        _db.session.flush()
        img = Image(filename="test.png", file_path="/tmp/test.png", dataset_id=ds.id)
        _db.session.add(img)
        _db.session.commit()
        self.image_id = img.id
        self.user_id  = test_user.id

    def test_create_annotation(self, app):
        from backend.app.services.annotation_service import AnnotationService
        ann = AnnotationService.create_annotation(self.image_id, self.user_id, {
            "annotation_type": "bbox",
            "label": "cloud",
            "geometry": {"type": "bbox", "coordinates": [0, 0, 50, 50]},
            "confidence": 0.9,
            "attributes": {"season": "winter"},
        })
        assert ann.id is not None
        assert ann.label == "cloud"
        assert ann.confidence == 0.9
        assert ann.attributes["season"] == "winter"
        assert ann.is_ai_generated is False

    def test_bulk_create_annotations(self, app):
        from backend.app.services.annotation_service import AnnotationService
        annotations = AnnotationService.bulk_create_annotations(self.image_id, self.user_id, [
            {"annotation_type": "bbox",  "label": "water",
             "geometry": {"type": "bbox", "coordinates": [10,10,40,40]}},
            {"annotation_type": "point", "label": "marker",
             "geometry": {"type": "Point", "coordinates": [25, 25]}},
        ])
        assert len(annotations) == 2
        labels = {a.label for a in annotations}
        assert labels == {"water", "marker"}

    def test_update_annotation_label(self, app):
        from backend.app.services.annotation_service import AnnotationService
        ann = AnnotationService.create_annotation(self.image_id, self.user_id, {
            "annotation_type": "bbox", "label": "original",
            "geometry": {"type": "bbox", "coordinates": [0,0,10,10]},
        })
        updated = AnnotationService.update_annotation(ann, self.user_id, {"label": "updated"})
        assert updated.label == "updated"

    def test_update_annotation_review_status(self, app):
        from backend.app.services.annotation_service import AnnotationService
        ann = AnnotationService.create_annotation(self.image_id, self.user_id, {
            "annotation_type": "point", "label": "review_me",
            "geometry": {"type": "Point", "coordinates": [5,5]},
        })
        updated = AnnotationService.update_annotation(ann, self.user_id, {
            "status": "approved", "review_comment": "Looks good",
        })
        assert updated.status == "approved"
        assert updated.review_comment == "Looks good"
        assert updated.reviewed_by == self.user_id

    def test_list_annotations_filter_by_label(self, app):
        from backend.app.services.annotation_service import AnnotationService
        for lbl in ("alpha", "beta", "alpha"):
            AnnotationService.create_annotation(self.image_id, self.user_id, {
                "annotation_type": "point", "label": lbl,
                "geometry": {"type": "Point", "coordinates": [1,1]},
            })
        result = AnnotationService.list_annotations(self.image_id, label="alpha")
        assert all(a["label"] == "alpha" for a in result["items"])

    def test_list_annotations_filter_by_type(self, app):
        from backend.app.services.annotation_service import AnnotationService
        result = AnnotationService.list_annotations(
            self.image_id, annotation_type="point"
        )
        assert all(a["annotation_type"] == "point" for a in result["items"])


# ── AIService ───────────────────────────────────────────────────────────────────

class TestAIService:

    def test_fallback_predictions_returns_list(self, app):
        with app.app_context():
            from backend.app.services.ai_service import AIService
            preds = AIService._fallback_predictions("/tmp/fake.tif", None)
            assert isinstance(preds, list)
            assert len(preds) > 0
            assert "label" in preds[0]
            assert preds[0]["is_ai_generated"] is True

    def test_normalize_predictions_coco_style(self, app):
        with app.app_context():
            from backend.app.services.ai_service import AIService
            raw = {"predictions": [
                {"type": "bbox", "label": "cloud", "score": 0.9,
                 "geometry": {"type": "bbox", "coordinates": [0,0,100,100]}},
            ]}
            result = AIService._normalize_predictions(raw)
            assert len(result) == 1
            assert result[0]["label"] == "cloud"
            assert result[0]["confidence"] == 0.9

    def test_normalize_predictions_box_format(self, app):
        with app.app_context():
            from backend.app.services.ai_service import AIService
            raw = {"boxes": [
                {"bbox": [10, 20, 80, 90], "class": "water", "score": 0.75},
                {"bbox": [5,  5,  30, 30], "class": "urban", "score": 0.6},
            ]}
            result = AIService._normalize_predictions(raw)
            assert len(result) == 2
            labels = {r["label"] for r in result}
            assert labels == {"water", "urban"}

    @patch("backend.app.services.ai_service.requests.post")
    def test_predict_calls_endpoint(self, mock_post, app):
        import tempfile, os
        with app.app_context():
            app.config["AI_MODEL_ENDPOINT"] = "http://fake-ai:8001"
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "predictions": [
                    {"type": "bbox", "label": "test", "score": 0.8,
                     "geometry": {"type": "bbox", "coordinates": [0,0,10,10]}}
                ]
            }
            mock_post.return_value.raise_for_status = MagicMock()

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(b"\x89PNG\r\n")
                tmp_path = f.name
            try:
                from backend.app.services.ai_service import AIService
                result = AIService.predict(tmp_path)
                assert mock_post.called
                assert len(result) == 1
                assert result[0]["label"] == "test"
            finally:
                os.unlink(tmp_path)


# ── User Model ──────────────────────────────────────────────────────────────────

class TestUserModel:

    def test_password_hashing(self, app):
        from backend.app.models.user import User
        user = User(username="hashtest", email="hash@test.com")
        user.set_password("secret")
        assert user.check_password("secret") is True
        assert user.check_password("wrong")  is False
        assert user.password_hash != "secret"

    def test_to_dict_excludes_password(self, app):
        from backend.app.models.user import User
        user = User(username="dicttest", email="dict@test.com")
        user.set_password("pass")
        d = user.to_dict()
        assert "password_hash" not in d
        assert "username" in d
        assert "email" in d
