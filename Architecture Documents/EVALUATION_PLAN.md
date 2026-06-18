# Evaluation Plan

To ensure the system meets production standards, rigorous evaluation must be conducted against an internal benchmark dataset.

## 1. Computer Vision Metrics
- **Mean Average Precision (mAP)**:
  - `mAP@0.5` > 85% for all core classes (vehicles, riders, helmets).
  - `mAP@0.5:0.95` > 60% for tight bounding box localization.
- **Precision vs. Recall**:
  - Goal: Maximize Recall (> 95%) to avoid missing actual violations. Precision can be slightly lower (> 75%) as the human-in-the-loop review process will filter out false positives.
- **OCR Accuracy**:
  - Character Error Rate (CER) < 5%.
  - Word Accuracy (Full License Plate string match) > 90%.

## 2. System Performance Metrics
- **Latency (End-to-End)**:
  - Time from image ingestion via API to database record creation < 2 seconds.
- **Throughput**:
  - Pipeline must process > 50 frames per second (FPS) per deployed GPU node.
- **API Response Time**:
  - Dashboard API queries (e.g., fetching a page of 50 violations) must return in < 200ms.

## 3. Benchmark Dataset
A held-out dataset of 10,000 diverse images (not used in model training) will be used for final validation. It must comprise:
- 30% Night-time or low-light images.
- 20% Adverse weather conditions (rain, fog, glare).
- 50% Standard daylight conditions across different camera angles.
