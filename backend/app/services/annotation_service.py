from datetime import datetime
from typing import List, Optional
from ..models.annotation import Annotation
from ..models.image import Image
from ..extensions import db


class AnnotationService:

    @staticmethod
    def list_annotations(image_id: int, page: int = 1, per_page: int = 50,
                         label: Optional[str] = None,
                         annotation_type: Optional[str] = None,
                         status: Optional[str] = None,
                         is_ai_generated: Optional[bool] = None,
                         user_id: Optional[int] = None) -> dict:
        query = Annotation.query.filter_by(image_id=image_id)

        if label:
            query = query.filter_by(label=label)
        if annotation_type:
            query = query.filter_by(annotation_type=annotation_type)
        if status:
            query = query.filter_by(status=status)
        if is_ai_generated is not None:
            query = query.filter_by(is_ai_generated=is_ai_generated)
        if user_id:
            query = query.filter_by(user_id=user_id)

        paginated = query.order_by(Annotation.created_at.desc()).paginate(page=page, per_page=per_page)

        return {
            "items": [a.to_dict() for a in paginated.items],
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": page,
        }

    @staticmethod
    def create_annotation(image_id: int, user_id: int, data: dict) -> Annotation:
        annotation = Annotation(
            image_id=image_id,
            user_id=user_id,
            annotation_type=data["annotation_type"],
            label=data["label"],
            label_id=data.get("label_id"),
            confidence=data.get("confidence", 1.0),
            geometry=data["geometry"],
            attributes=data.get("attributes", {}),
            band_specific=data.get("band_specific", False),
            band_index=data.get("band_index"),
            time_step=data.get("time_step"),
        )
        db.session.add(annotation)

        # Mark image as annotated
        image = Image.query.get(image_id)
        image.is_annotated = True
        image.updated_at = datetime.utcnow()

        db.session.commit()
        return annotation

    @staticmethod
    def bulk_create_annotations(image_id: int, user_id: int, annotations_data: list) -> List[Annotation]:
        annotations = []
        for data in annotations_data:
            ann = Annotation(
                image_id=image_id,
                user_id=user_id,
                annotation_type=data["annotation_type"],
                label=data["label"],
                label_id=data.get("label_id"),
                confidence=data.get("confidence", 1.0),
                geometry=data["geometry"],
                attributes=data.get("attributes", {}),
                band_specific=data.get("band_specific", False),
                band_index=data.get("band_index"),
                time_step=data.get("time_step"),
            )
            annotations.append(ann)
            db.session.add(ann)

        image = Image.query.get(image_id)
        image.is_annotated = True
        image.updated_at = datetime.utcnow()

        db.session.commit()
        return annotations

    @staticmethod
    def update_annotation(annotation: Annotation, user_id: int, data: dict) -> Annotation:
        updatable = ("label", "confidence", "geometry", "attributes")
        for field in updatable:
            if field in data:
                setattr(annotation, field, data[field])

        # Review fields
        if "status" in data:
            annotation.status = data["status"]
            annotation.reviewed_by = user_id
            annotation.reviewed_at = datetime.utcnow()
        if "review_comment" in data:
            annotation.review_comment = data["review_comment"]

        annotation.updated_at = datetime.utcnow()
        db.session.commit()
        return annotation
