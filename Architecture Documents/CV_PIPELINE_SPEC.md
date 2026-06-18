# Computer Vision Pipeline Specification

## Pipeline Orchestration
The pipeline is a sequential DAG (Directed Acyclic Graph) of distinct deep learning models and deterministic algorithms. It is designed to maximize accuracy while minimizing compute on unviable images.

### Stage 1: Image Quality Assessment (IQA)
- **Goal**: Discard unusable images before wasting expensive GPU cycles.
- **Checks**:
  - Blur detection (using Laplacian variance).
  - Brightness/Contrast checks (detecting pitch black or overexposed images due to glare/weather).
- **Output**:
  ```json
  {
    "quality_pass": true,
    "metrics": { "blur_score": 120.5, "brightness": 105 }
  }
  ```

### Stage 2: Primary Object Detection
- **Model**: YOLOv11 (or equivalent object detector).
- **Goal**: Identify all vehicles, pedestrians, and traffic infrastructure.
- **Classes**: `car`, `truck`, `bus`, `motorcycle`, `auto_rickshaw`, `bicycle`, `pedestrian`, `traffic_light`.
- **Output**: Array of bounding boxes with class labels and confidence scores.

### Stage 3: Secondary Detection (Riders & Accessories)
- **Goal**: For every `motorcycle` detected in Stage 2, crop the vehicle and run a secondary, specialized model.
- **Classes**: `rider`, `helmet`, `no_helmet`.
- **Note**: Operating on cropped regions increases accuracy for small objects like helmets which might be lost in down-sampling the full image.

### Stage 4: Tracking (For Video sequences)
- **Algorithm**: ByteTrack or DeepSORT.
- **Goal**: Assign unique IDs to vehicles across multiple frames to determine speed, direction, and line-crossing behavior over time.

### Stage 5: License Plate Detection (LPD)
- **Goal**: Detect the bounding box of the license plate on vehicles involved in a violation.
- **Classes**: `license_plate`.
- **Logic**: Triggered conditionally only if a violation is detected in Stage 7, to save compute.

### Stage 6: Optical Character Recognition (OCR)
- **Model**: PaddleOCR or specialized CRNN.
- **Input**: Cropped and perspective-transformed license plate image.
- **Output**: String (e.g., "MH 12 AB 1234") and character-level confidence scores.

### Stage 7: Violation Decision Engine
- **Goal**: Aggregate all bounding boxes, tracks, and OCR results, and apply business logic rules to determine if a violation occurred. (See `VIOLATION_RULE_ENGINE.md`).
