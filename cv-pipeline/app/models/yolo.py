"""YOLOv8 model loaders for primary vehicle detection and LPD.

Each loader is lazy — weights are downloaded on first inference call and
cached under ~/.ultralytics/ (or MODEL_CACHE_DIR if set).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# COCO object classes that map to traffic vehicles / infrastructure
PRIMARY_CLASSES: dict[int, str] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    1: "bicycle",
    3: "motorcycle",      # deliberate duplicate — see note below
    14: "bird",           # not used; filtered out
    0: "person",          # mapped to pedestrian
}

# Class names that YOLOv8 COCO defines that we care about
# (Ultralytics YOLOv8n pretrained on COCO maps class IDs to these names)
_WANTED_PRIMARY = {"car", "motorcycle", "bus", "truck", "bicycle", "person", "traffic light"}

# Secondary (rider/helmet) classes — in a real deployment these would come
# from a fine-tuned model.  We use the COCO person class as a proxy for
# rider detection in Phase 8; the fine-tuned model replaces this in Phase 9.
SECONDARY_CLASSES = {"person"}


def _to_xyxy(box: np.ndarray) -> list[float]:
    """Convert YOLO [x_center, y_center, w, h] → [x1, y1, x2, y2]."""
    xc, yc, w, h = box
    return [float(xc - w / 2), float(yc - h / 2), float(xc + w / 2), float(yc + h / 2)]


class YOLOModel:
    """Primary YOLOv8n detector for vehicles / pedestrians / traffic lights."""

    def __init__(
        self,
        weights: str = "yolov8n.pt",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ):
        import torch
        from ultralytics import YOLO

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        logger.info("Loading YOLOv8 primary detector (%s) on %s", weights, device)
        self._model = YOLO(weights)
        self._model.to(device)
        self._conf = conf_threshold
        self._iou = iou_threshold

    # ── Primary detection ─────────────────────────────────────────────────────

    def detect_vehicles(self, image_path: str | None = None, image_bytes: bytes | None = None) -> list[dict]:
        """Run primary object detection on a full frame.

        Returns:
            List of detections, each with keys: class, confidence, bbox (xyxy).
            Only classes in _WANTED_PRIMARY are returned.
        """
        results = self._model.predict(
            source=image_path or image_bytes,
            conf=self._conf,
            iou=self._iou,
            verbose=False,
            device=self.device,
        )
        detections = []
        for r in results or []:
            if r.masks is None:
                continue
            cls_ids = r.boxes.cls.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()
            boxes = r.boxes.xyxy.cpu().numpy()

            for cid, conf, box in zip(cls_ids, confs, boxes):
                # Map class ID to YOLO COCO name
                name = r.names.get(cid, "")
                if name not in _WANTED_PRIMARY:
                    continue
                # Remap for our naming convention
                label = {"person": "pedestrian", "traffic light": "traffic_light"}.get(name, name)
                detections.append({
                    "class": label,
                    "confidence": float(conf),
                    "bbox": [float(x) for x in box],
                })
        return detections

    # ── Secondary detection on crop ──────────────────────────────────────────

    def detect_on_crop(
        self, crop: np.ndarray, classes: set[str], conf: float = 0.30
    ) -> list[dict]:
        """Run detection on a single cropped image region.

        Args:
            crop: BGR numpy array (OpenCV style).
            classes: Set of class names to keep (from r.names).
            conf: Confidence threshold for this model.

        Returns:
            List of detections with class / confidence / bbox (xyxy).
        """
        results = self._model.predict(
            source=crop,
            conf=conf,
            iou=self._iou,
            verbose=False,
            device=self.device,
        )
        detections = []
        for r in results or []:
            if r.masks is None:
                continue
            cls_ids = r.boxes.cls.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()
            boxes = r.boxes.xyxy.cpu().numpy()
            for cid, cf, box in zip(cls_ids, confs, boxes):
                name = r.names.get(cid, "")
                if name not in classes:
                    continue
                detections.append({
                    "class": name,
                    "confidence": float(cf),
                    "bbox": [float(x) for x in box],
                })
        return detections


# ── License Plate Detector ────────────────────────────────────────────────────
# Loads a YOLOv8 fine-tuned on license plates (lpd_yolov8.pt).
# If the file is absent we return an empty list (Stage 5 then uses mock data).
# In Phase 9 you replace the placeholder below with:
#   LPD_WEIGHTS = str(Path(settings.MODEL_CACHE_DIR) / "lpd_yolov8.pt")


class LPDModel:
    """YOLOv8-based License Plate Detector."""

    def __init__(
        self,
        weights: str = "yolov8n.pt",     # placeholder; swap for fine-tuned lpd_yolov8n.pt
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
    ):
        import torch
        from ultralytics import YOLO

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        logger.info("Loading LPD model (%s) on %s", weights, device)
        self._model = YOLO(weights)
        self._model.to(device)
        self._conf = conf_threshold
        self._iou = iou_threshold

    def detect_plates(
        self, image_path: str | None = None, image_bytes: bytes | None = None
    ) -> list[dict]:
        """Detect license plate bounding boxes in a full frame.

        Returns:
            List of plates with confidence and bbox (xyxy).
            The placeholder model uses any large rectangular detection;
            fine-tuned model returns license_plate class specifically.
        """
        try:
            results = self._model.predict(
                source=image_path or image_bytes,
                conf=self._conf,
                iou=self._iou,
                verbose=False,
                device=self.device,
            )
        except Exception as exc:
            logger.warning("LPD inference failed: %s — returning empty list", exc)
            return []

        plates = []
        for r in results or []:
            if r.masks is None:
                continue
            cls_ids = r.boxes.cls.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()
            boxes = r.boxes.xyxy.cpu().numpy()
            for cid, conf, box in zip(cls_ids, confs, boxes):
                name = r.names.get(cid, "")
                # In a real fine-tuned model the class would be "license_plate".
                # The COCO-pretrained model may fires on rectangular objects — filter
                # by aspect ratio heuristic: license plates are roughly 2:1 → 5:1.
                x1, y1, x2, y2 = box
                w, h = x2 - x1, y2 - y1
                if h <= 0 or w <= 0:
                    continue
                aspect = w / h
                if not (1.2 <= aspect <= 6.0):
                    continue   # not a plausible plate aspect ratio
                plates.append({
                    "class": "license_plate",
                    "confidence": float(conf),
                    "bbox": [float(x) for x in box],
                })
        return plates