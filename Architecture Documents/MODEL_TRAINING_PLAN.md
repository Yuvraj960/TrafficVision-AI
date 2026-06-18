# Model Training Plan

## 1. Primary Detection Model
Responsible for detecting vehicles, riders, and helmets.

### Architecture & Hyperparameters
```yaml
Model: YOLOv11m (Medium variant)
Input Image Size: 640x640
Epochs: 150
Batch Size: 32
Optimizer: AdamW
Learning Rate (Initial): 0.001

Data Augmentation: 
  - Mosaic: 1.0
  - MixUp: 0.1
  - HSV adjustments (H: 0.015, S: 0.7, V: 0.4)
  - Random Perspective/Affine transformations
```

### Hardware Requirements
- **Training**: 4x NVIDIA A100 (40GB) or equivalent setup for distributed data parallel (DDP) training.
- **Inference (Production)**: NVIDIA T4 or RTX 4000 series per edge node.

## 2. Optical Character Recognition (OCR)
Fine-tuning for localized license plate recognition.

### Architecture & Hyperparameters
```yaml
Model Framework: PaddleOCR
Detection Architecture: ResNet50_vd_DB (Differentiable Binarization)
Recognition Architecture: MobileNetV3_CRNN (Convolutional Recurrent Neural Network)
Epochs: 100
Image Size: 
  - Det: 320x320
  - Rec: 32x320
```

## 3. Evaluation Metrics
Models will be evaluated based on the following metrics:
- **mAP@0.5**: Mean Average Precision at IoU 0.5 (Target > 0.90 for vehicles, > 0.85 for helmets).
- **mAP@0.5:0.95**: Strict detection metric indicating tight bounding boxes.
- **Precision vs. Recall**: The system targets high Recall for the initial pipeline (preferring false positives over missing a violation), as human reviewers will filter FPs in the dashboard.
- **Inference Latency**: Target < 50ms per frame for the YOLO pipeline on production hardware.
