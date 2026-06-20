"""ByteTrack-based multi-object tracker using the supervision library.

ByteTrack is a multi-object tracker that assigns persistent IDs across frames
and computes speed / direction from trajectory history.

For single-frame inference (current pipeline) the tracker cannot accumulate
trajectories — we instead create a single-frame "track" that uses the detection
centroid and velocity direction heuristic.  When the pipeline is extended to
video clips (multiple frames per job), full ByteTrack can be enabled.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# Supervision's ByteTrack accepts detections in its own Detections format
try:
    import supervision as sv

    BYTETRACK_AVAILABLE = True
except ImportError:
    BYTETRACK_AVAILABLE = False
    logger.warning("supervision not installed — tracking will return identity tracks")


class ByteTrackModel:
    """Wrapper around supervision.ByteTrack for video-frame tracking.

    When only a single frame is available (image ingestion pipeline),
    we return "identity tracks" — one track per detection with no history.
    """

    def __init__(
        self,
        track_thresh: float = 0.25,
        track_buffer: int = 30,
        match_thresh: float = 0.80,
        min_box_area: float = 10.0,
        max_time_since_registration: int = 30,
    ):
        self._track_thresh = track_thresh
        self._track_buffer = track_buffer
        self._match_thresh = match_thresh
        self._min_box_area = min_box_area
        self._max_time_since_registration = max_time_since_registration

        self._tracker: "sv.ByteTrack | None" = None
        self._track_history: dict[int, list[tuple[float, float]]] = defaultdict(list)

    def _get_tracker(self) -> "sv.ByteTrack | None":
        if not BYTETRACK_AVAILABLE:
            return None
        if self._tracker is None:
            import supervision as sv

            self._tracker = sv.ByteTrack(
                track_thresh=self._track_thresh,
                track_buffer=self._track_buffer,
                match_thresh=self._match_thresh,
                min_box_area=self._min_box_area,
                max_time_since_registration=self._max_time_since_registration,
            )
        return self._tracker

    @property
    def is_available(self) -> bool:
        return BYTETRACK_AVAILABLE

    def reset(self) -> None:
        """Clear all track state — call when starting a new video."""
        self._track_history.clear()

    def update(
        self,
        detections: list[dict],
        frame_size: tuple[int, int] | None = None,
    ) -> list[dict]:
        """Update tracks with current frame detections.

        Args:
            detections: List of stage-2 detections, each with 'class', 'confidence',
                'bbox' (xyxy), and optionally 'track_id' (from prior frames).
            frame_size: (width, height) of the current frame. Used for normalization.

        Returns:
            List of tracks, each with track_id, class, trajectory (list of [x,y]
            centroid points from oldest to newest), speed_kmph, and direction.
        """
        if not detections:
            return []

        tracker = self._get_tracker()

        if tracker is None or frame_size is None:
            # Fallback: create identity tracks from detections (no history)
            return self._identity_tracks(detections)

        # Convert to supervision Detections format
        import supervision as sv

        bboxes = np.array([d["bbox"] for d in detections], dtype=np.float32)
        scores = np.array([d["confidence"] for d in detections], dtype=np.float32)
        class_ids = np.array([
            {"car": 0, "truck": 1, "bus": 2, "motorcycle": 3, "bicycle": 4,
             "person": 5, "pedestrian": 5, "traffic_light": 6}.get(d.get("class", ""), -1)
            for d in detections
        ], dtype=np.int32)

        sv_dets = sv.Detections(
            xyxy=bboxes,
            confidence=scores,
            class_id=class_ids,
        )

        # Update tracker
        sv_dets = tracker.update_with_detections(sv_dets)

        tracks = []
        for i, (track_id, cls_id) in enumerate(zip(sv_dets.tracker_id or [], sv_dets.class_id or [])):
            bbox = sv_dets.xyxy[i]
            xc, yc = float((bbox[0] + bbox[2]) / 2), float((bbox[1] + bbox[3]) / 2)

            # Update trajectory history
            self._track_history[int(track_id)].append((xc, yc))
            trail = self._track_history[int(track_id)][-10:]   # keep last 10 points

            # Compute speed and direction from trajectory
            speed_kmph, direction = self._speed_and_direction(trail, fps=30)

            cls_name = ["car", "truck", "bus", "motorcycle", "bicycle",
                        "person", "traffic_light"][cls_id] if 0 <= cls_id < 7 else "unknown"

            tracks.append({
                "track_id": int(track_id),
                "class": cls_name,
                "trajectory": [[float(x), float(y)] for x, y in trail],
                "speed_kmph": speed_kmph,
                "direction": direction,
            })

        return tracks

    def _identity_tracks(self, detections: list[dict]) -> list[dict]:
        """Generate identity tracks when per-frame tracking only."""
        tracks = []
        for i, det in enumerate(detections):
            bbox = det.get("bbox", [0, 0, 0, 0])
            xc = float((bbox[0] + bbox[2]) / 2)
            yc = float((bbox[1] + bbox[3]) / 2)
            tracks.append({
                "track_id": i + 1,
                "class": det.get("class", "unknown"),
                "trajectory": [[xc, yc]],
                "speed_kmph": 0.0,
                "direction": "unknown",
            })
        return tracks

    @staticmethod
    def _speed_and_direction(
        trail: list[tuple[float, float]],
        fps: int = 30,
        px_per_meter: float = 100.0,
    ) -> tuple[float, str]:
        """Estimate speed (km/h) and cardinal direction from centroid trail.

        Args:
            trail: List of (x, y) pixel centroids, oldest first.
            fps: Assumed frames per second for the video source.
            px_per_meter: Scale factor from pixels to metres (calibrated per camera).

        Returns:
            (speed_kmph: float, direction: str)
        """
        if len(trail) < 2:
            return 0.0, "unknown"

        # Use the last few points to compute instantaneous velocity
        recent = trail[-3:] if len(trail) >= 3 else trail
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]

        # Physical velocity
        meter_per_frame = ((dx ** 2 + dy ** 2) ** 0.5) / px_per_meter
        meter_per_sec = meter_per_frame * fps
        speed_kmph = round(meter_per_sec * 3.6, 1)

        # Cardinal direction from delta
        import math
        angle = math.degrees(math.atan2(-dy, dx))  # screen-y is inverted
        if -22.5 <= angle < 22.5:
            direction = "east"
        elif 22.5 <= angle < 67.5:
            direction = "north-east"
        elif 67.5 <= angle < 112.5:
            direction = "north"
        elif 112.5 <= angle < 157.5:
            direction = "north-west"
        elif -67.5 <= angle < -22.5:
            direction = "south-east"
        elif -112.5 <= angle < -67.5:
            direction = "south"
        elif -157.5 <= angle < -112.5:
            direction = "south-west"
        else:
            direction = "west"

        return speed_kmph, direction