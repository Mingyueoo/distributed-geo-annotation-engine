from ..extensions import celery, db
from ..models.image import Image
from ..models.annotation import Annotation
from ..services.ai_service import AIService


@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def run_ai_labeling(self, image_id: int, model_type: str = "auto") -> dict:
    """
    Async Celery task: run AI inference on a single image and
    persist the resulting annotations to the database.
    """
    try:
        image = Image.query.get(image_id)
        if not image:
            return {"error": f"Image {image_id} not found"}

        dataset_context = {
            "satellite": image.satellite,
            "bands": image.band_names,
            "data_type": image.dataset.data_type if image.dataset else None,
        }

        predictions = AIService.predict(image.file_path, model_type, dataset_context)

        created = []
        # AI annotations are attributed to a virtual "AI system" user (id=0 sentinel)
        AI_USER_ID = 1  # Replace with actual AI system user id from DB

        for pred in predictions:
            ann = Annotation(
                image_id=image_id,
                user_id=AI_USER_ID,
                annotation_type=pred["annotation_type"],
                label=pred["label"],
                confidence=pred.get("confidence", 0.5),
                geometry=pred.get("geometry", {}),
                attributes=pred.get("attributes", {}),
                is_ai_generated=True,
                status="pending",
            )
            db.session.add(ann)
            created.append(pred["label"])

        if predictions:
            image.is_annotated = True
        db.session.commit()

        return {
            "image_id": image_id,
            "annotations_created": len(created),
            "labels": created,
        }

    except Exception as exc:
        db.session.rollback()
        raise self.retry(exc=exc)


@celery.task(bind=True)
def run_batch_ai_labeling(self, dataset_id: int, model_type: str = "auto") -> dict:
    """
    Run AI labeling on all unannotated images in a dataset.
    Dispatches individual tasks per image for parallelism.
    """
    from ..models.dataset import Dataset

    dataset = Dataset.query.get(dataset_id)
    if not dataset:
        return {"error": f"Dataset {dataset_id} not found"}

    unannotated = dataset.images.filter_by(is_annotated=False).all()
    task_ids = []
    for image in unannotated:
        task = run_ai_labeling.delay(image.id, model_type)
        task_ids.append(task.id)

    return {
        "dataset_id": dataset_id,
        "images_queued": len(task_ids),
        "task_ids": task_ids,
    }


@celery.task
def generate_thumbnails(dataset_id: int) -> dict:
    """Generate thumbnails for all images in a dataset that are missing them."""
    from ..models.dataset import Dataset
    from ..services.image_service import ImageService
    import os

    dataset = Dataset.query.get(dataset_id)
    if not dataset:
        return {"error": "Dataset not found"}

    processed = 0
    for image in dataset.images.all():
        if not image.thumbnail_path or not os.path.exists(image.thumbnail_path or ""):
            folder = os.path.dirname(image.file_path)
            thumb = ImageService._generate_thumbnail(image.file_path, folder, image.filename)
            if thumb:
                image.thumbnail_path = thumb
                processed += 1

    db.session.commit()
    return {"processed": processed}
