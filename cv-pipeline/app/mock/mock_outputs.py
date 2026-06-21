"""Comprehensive mock data for all 7 CV pipeline stages.

These static payloads match the shapes defined in CV_PIPELINE_SPEC.md
and allow the pipeline to run end-to-end without any real models.
Replace each constant with actual model inference when ready.
"""


# ── Stage 1: Image Quality Assessment ──────────────────────────────────
MOCK_STAGE_1_IQA: dict = {
    "quality_pass": True,
    "metrics": {
        "blur_score": 120.5,
        "brightness": 105,
    },
}


# ── Stage 2: Primary Object Detection ─────────────────────────────────
MOCK_STAGE_2_DETECTION: dict = {
    "detections": [
        {
            "class": "car",
            "confidence": 0.92,
            "bbox": [120, 60, 380, 280],
        },
        {
            "class": "motorcycle",
            "confidence": 0.88,
            "bbox": [450, 180, 580, 350],
        },
        {
            "class": "motorcycle",
            "confidence": 0.85,
            "bbox": [610, 200, 720, 370],
        },
        {
            "class": "truck",
            "confidence": 0.79,
            "bbox": [50, 100, 300, 400],
        },
        {
            "class": "bus",
            "confidence": 0.82,
            "bbox": [800, 90, 1050, 380],
        },
        {
            "class": "auto_rickshaw",
            "confidence": 0.76,
            "bbox": [740, 220, 830, 360],
        },
        {
            "class": "bicycle",
            "confidence": 0.71,
            "bbox": [1100, 250, 1180, 380],
        },
        {
            "class": "pedestrian",
            "confidence": 0.90,
            "bbox": [950, 150, 990, 310],
        },
        {
            "class": "traffic_light",
            "confidence": 0.94,
            "bbox": [540, 10, 570, 60],
        },
    ],
}


# ── Stage 3: Secondary Detection (Riders & Accessories) ───────────────
MOCK_STAGE_3_SECONDARY: dict = {
    "secondary_detections": [
        {
            "motorcycle_bbox": [450, 180, 580, 350],
            "detections": [
                {"class": "rider", "confidence": 0.91, "bbox": [470, 150, 560, 280]},
                {"class": "no_helmet", "confidence": 0.87, "bbox": [490, 130, 530, 170]},
            ],
        },
        {
            "motorcycle_bbox": [610, 200, 720, 370],
            "detections": [
                {"class": "rider", "confidence": 0.89, "bbox": [625, 165, 705, 300]},
                {"class": "helmet", "confidence": 0.93, "bbox": [645, 140, 685, 180]},
            ],
        },
    ],
}


# ── Stage 4: Tracking ─────────────────────────────────────────────────
MOCK_STAGE_4_TRACKING: dict = {
    "tracks": [
        {
            "track_id": 1,
            "class": "car",
            "trajectory": [
                [120, 170],
                [135, 168],
                [150, 166],
            ],
            "speed_kmph": 42.0,
            "direction": "south",
        },
        {
            "track_id": 2,
            "class": "motorcycle",
            "trajectory": [
                [450, 265],
                [458, 263],
                [466, 260],
            ],
            "speed_kmph": 35.0,
            "direction": "south",
        },
        {
            "track_id": 3,
            "class": "motorcycle",
            "trajectory": [
                [610, 285],
                [618, 283],
                [626, 281],
            ],
            "speed_kmph": 33.0,
            "direction": "south",
        },
        {
            "track_id": 4,
            "class": "truck",
            "trajectory": [
                [50, 250],
                [55, 248],
                [60, 246],
            ],
            "speed_kmph": 28.0,
            "direction": "south",
        },
    ],
}


# ── Stage 5: License Plate Detection ──────────────────────────────────
MOCK_STAGE_5_LPD: dict = {
    "plates": [
        {
            "vehicle_track_id": 2,
            "class": "license_plate",
            "confidence": 0.91,
            "bbox": [495, 310, 545, 335],
        },
    ],
}


# ── Stage 6: Optical Character Recognition ────────────────────────────
MOCK_STAGE_6_OCR: dict = {
    "plate_text": "MH 12 AB 1234",
    "char_confidence": 0.95,
}


# ── Stage 7: Violation Decision Engine ─────────────────────────────────
MOCK_STAGE_7_RULES: dict = {
    "violations_detected": [
        {
            "track_id": 2,
            "vehicle_class": "motorcycle",
            "violation_type": "helmet",
            "confidence": 0.87,
            "plate_text": "MH 12 AB 1234",
            "plate_bbox": [495, 310, 545, 335],
            "evidence": {
                "rider_bbox": [470, 150, 560, 280],
                "no_helmet_bbox": [490, 130, 530, 170],
            },
        },
    ],
    "violation_types": ["helmet"],
}
