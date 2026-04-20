import os
import requests
from typing import List, Dict, Any, Optional
from flask import current_app


class AIService:
    """
    AI-assisted labeling service for Sentinel and climate data.
    Integrates with an external AI model endpoint (e.g., a hosted segmentation
    or classification model) and provides fallback heuristics when unavailable.
    """

    @staticmethod
    def predict(image_path: str, model_type: str = "auto", dataset_context: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        Call the configured AI model endpoint to get predictions for an image.
        Returns a list of annotation dicts compatible with AnnotationCreateSchema.
        """
        endpoint = current_app.config.get("AI_MODEL_ENDPOINT")
        api_key = current_app.config.get("AI_API_KEY", "")

        if not endpoint:
            return AIService._fallback_predictions(image_path, dataset_context)

        try:
            with open(image_path, "rb") as f:
                files = {"image": (os.path.basename(image_path), f, "application/octet-stream")}
                payload = {"model_type": model_type}
                if dataset_context:
                    payload["context"] = str(dataset_context)

                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                response = requests.post(
                    f"{endpoint}/predict",
                    files=files,
                    data=payload,
                    headers=headers,
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()
                return AIService._normalize_predictions(result)

        except requests.RequestException as e:
            current_app.logger.warning(f"AI endpoint unreachable: {e}. Using fallback.")
            return AIService._fallback_predictions(image_path, dataset_context)

    @staticmethod
    def _normalize_predictions(raw: dict) -> List[Dict[str, Any]]:
        """Normalize various AI response formats into our annotation schema."""
        annotations = []

        # Support COCO-style predictions
        if "predictions" in raw:
            for pred in raw["predictions"]:
                ann = {
                    "annotation_type": pred.get("type", "bbox"),
                    "label": pred.get("label", "unknown"),
                    "confidence": float(pred.get("score", pred.get("confidence", 0.5))),
                    "geometry": pred.get("geometry", {}),
                    "attributes": pred.get("attributes", {}),
                    "is_ai_generated": True,
                }
                annotations.append(ann)

        # Support bounding-box array format
        elif "boxes" in raw:
            for box in raw["boxes"]:
                x1, y1, x2, y2 = box.get("bbox", [0, 0, 0, 0])
                annotations.append({
                    "annotation_type": "bbox",
                    "label": box.get("class", "object"),
                    "confidence": float(box.get("score", 0.5)),
                    "geometry": {"type": "bbox", "coordinates": [x1, y1, x2, y2]},
                    "attributes": {},
                    "is_ai_generated": True,
                })

        return annotations

    @staticmethod
    def _fallback_predictions(image_path: str, context: Optional[dict]) -> List[Dict[str, Any]]:
        """
        Minimal heuristic fallback when no AI endpoint is available.
        Returns a single whole-image classification placeholder.
        """
        ext = os.path.splitext(image_path)[1].lower()
        label = "cloud" if ext in (".tif", ".tiff") else "unlabeled_region"

        return [{
            "annotation_type": "classification",
            "label": label,
            "confidence": 0.3,
            "geometry": {"type": "classification", "coordinates": []},
            "attributes": {"source": "fallback_heuristic"},
            "is_ai_generated": True,
        }]

    @staticmethod
    def get_available_models() -> List[Dict[str, str]]:
        """Return list of available AI models from the endpoint."""
        endpoint = current_app.config.get("AI_MODEL_ENDPOINT")
        if not endpoint:
            return []
        try:
            resp = requests.get(f"{endpoint}/models", timeout=10)
            resp.raise_for_status()
            return resp.json().get("models", [])
        except requests.RequestException:
            return []
