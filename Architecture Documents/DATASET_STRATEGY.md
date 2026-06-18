# Dataset Strategy

To train robust Object Detection and OCR models, a diverse set of datasets is required, covering various weather conditions, lighting (day/night), and camera angles.

## 1. Dataset Sources

### Vehicle & Person Detection
- **COCO Dataset**: General baseline weights for common objects.
- **BDD100K (Berkeley DeepDrive)**: For diverse driving conditions, vehicle types, and traffic lights from dashboard/street views.
- **MIO-TCD**: Specialized dataset for traffic camera vehicle classification (car, bus, truck, etc.).

### Specialized Anomalies (Helmet/Seatbelt)
- **IDD (Indian Driving Dataset)**: Excellent for unstructured traffic, dense two-wheeler population, and complex road conditions.
- **Roboflow Universe Helmet Datasets**: Crowdsourced datasets specifically tailored for helmet vs. no-helmet classification.

### License Plates
- **CCPD (Chinese City Parking Dataset)**: High volume of license plates useful for generic OCR pre-training and bounding box detection.
- **Synthetic Plate Generation**: Python scripts utilizing PIL/OpenCV to generate localized license plate formats using standard fonts to augment training data.

## 2. Dataset Mapping & Blending
```yaml
Helmet Detection:
  Sources: [IDD, Roboflow Custom]
  Ratio: 60% Real / 40% Synthetic
  
Vehicle Classification:
  Sources: [BDD100K, MIO-TCD]
  Classes: car, truck, bus, motorcycle, bicycle
```

## 3. Annotation Format
All detection datasets will be standardized to the YOLO TXT format for seamless training:
```txt
<class_id> <x_center> <y_center> <width> <height>
```
*Note: Coordinates must be normalized between 0.0 and 1.0 relative to image dimensions.*
