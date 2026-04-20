from typing import Optional
from ..models.dataset import Dataset
from ..models.image import Image
from ..models.annotation import Annotation
from ..extensions import db


class DatasetService:

    @staticmethod
    def list_datasets(user_id: int, page: int = 1, per_page: int = 20,
                      data_type: Optional[str] = None, status: Optional[str] = None,
                      search: Optional[str] = None) -> dict:
        from ..models.dataset import dataset_collaborators
        from sqlalchemy import or_

        query = Dataset.query.filter(
            or_(
                Dataset.owner_id == user_id,
                Dataset.collaborators.any(id=user_id)
            )
        )

        if data_type:
            query = query.filter_by(data_type=data_type)
        if status:
            query = query.filter_by(status=status)
        if search:
            query = query.filter(Dataset.name.ilike(f"%{search}%"))

        paginated = query.order_by(Dataset.created_at.desc()).paginate(page=page, per_page=per_page)

        return {
            "items": [d.to_dict(include_stats=True) for d in paginated.items],
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": page,
            "per_page": per_page,
        }

    @staticmethod
    def create_dataset(user_id: int, data: dict) -> Dataset:
        dataset = Dataset(
            name=data["name"],
            description=data.get("description", ""),
            data_type=data.get("data_type", "other"),
            label_schema=data.get("label_schema"),
            metadata_=data.get("metadata", {}),
            owner_id=user_id,
        )
        db.session.add(dataset)
        db.session.commit()
        return dataset

    @staticmethod
    def update_dataset(dataset: Dataset, data: dict) -> Dataset:
        for field in ("name", "description", "status"):
            if field in data:
                setattr(dataset, field, data[field])
        if "label_schema" in data:
            dataset.label_schema = data["label_schema"]
        if "metadata" in data:
            dataset.metadata_ = data["metadata"]
        db.session.commit()
        return dataset

    @staticmethod
    def export_dataset(dataset: Dataset, fmt: str) -> dict:
        images = dataset.images.all()
        if fmt == "coco":
            return DatasetService._export_coco(dataset, images)
        elif fmt == "geojson":
            return DatasetService._export_geojson(dataset, images)
        elif fmt == "csv":
            return DatasetService._export_csv(dataset, images)
        else:
            return {"error": f"Unsupported format: {fmt}"}

    @staticmethod
    def _export_coco(dataset: Dataset, images: list) -> dict:
        categories = []
        if dataset.label_schema and "classes" in dataset.label_schema:
            for i, cls in enumerate(dataset.label_schema["classes"]):
                categories.append({
                    "id": i + 1,
                    "name": cls["name"],
                    "supercategory": "none",
                })

        coco_images = []
        coco_annotations = []
        ann_id = 1

        for img in images:
            coco_images.append({
                "id": img.id,
                "file_name": img.filename,
                "width": img.width or 0,
                "height": img.height or 0,
                "date_captured": img.acquisition_date.isoformat() if img.acquisition_date else "",
            })

            for ann in img.annotations.filter_by(status="approved").all():
                coco_ann = {
                    "id": ann_id,
                    "image_id": img.id,
                    "category_id": next(
                        (c["id"] for c in categories if c["name"] == ann.label), 0
                    ),
                    "confidence": ann.confidence,
                    "attributes": ann.attributes,
                }
                if ann.annotation_type == "bbox" and ann.geometry:
                    coords = ann.geometry.get("coordinates", [0, 0, 0, 0])
                    x1, y1, x2, y2 = coords
                    coco_ann["bbox"] = [x1, y1, x2 - x1, y2 - y1]
                    coco_ann["area"] = (x2 - x1) * (y2 - y1)
                coco_annotations.append(coco_ann)
                ann_id += 1

        return {
            "info": {"description": dataset.description, "version": "1.0"},
            "licenses": [],
            "images": coco_images,
            "annotations": coco_annotations,
            "categories": categories,
        }

    @staticmethod
    def _export_geojson(dataset: Dataset, images: list) -> dict:
        features = []
        for img in images:
            for ann in img.annotations.filter_by(status="approved").all():
                feature = {
                    "type": "Feature",
                    "geometry": ann.geometry,
                    "properties": {
                        "label": ann.label,
                        "confidence": ann.confidence,
                        "image_id": img.id,
                        "annotation_id": ann.id,
                        "attributes": ann.attributes,
                    },
                }
                if img.bbox:
                    feature["properties"]["image_bbox"] = img.bbox
                features.append(feature)

        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def _export_csv(dataset: Dataset, images: list) -> dict:
        rows = [["image_id", "filename", "annotation_id", "label", "type", "confidence", "geometry"]]
        for img in images:
            for ann in img.annotations.all():
                rows.append([
                    img.id, img.filename, ann.id, ann.label,
                    ann.annotation_type, ann.confidence, str(ann.geometry),
                ])
        return {"format": "csv", "headers": rows[0], "data": rows[1:]}

    @staticmethod
    def get_dataset_stats(dataset: Dataset) -> dict:
        images = dataset.images.all()
        total_images = len(images)
        annotated_images = sum(1 for img in images if img.is_annotated)

        all_annotations = []
        for img in images:
            all_annotations.extend(img.annotations.all())

        label_dist = {}
        type_dist = {}
        status_dist = {}
        for ann in all_annotations:
            label_dist[ann.label] = label_dist.get(ann.label, 0) + 1
            type_dist[ann.annotation_type] = type_dist.get(ann.annotation_type, 0) + 1
            status_dist[ann.status] = status_dist.get(ann.status, 0) + 1

        return {
            "total_images": total_images,
            "annotated_images": annotated_images,
            "completion_percentage": dataset.completion_percentage,
            "total_annotations": len(all_annotations),
            "label_distribution": label_dist,
            "type_distribution": type_dist,
            "status_distribution": status_dist,
            "collaborator_count": len(dataset.collaborators),
        }
