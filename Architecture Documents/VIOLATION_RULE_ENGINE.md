# Violation Rule Engine

This document defines the deterministic mathematical and logical rules used to classify AI outputs into specific legal violations.

## 1. Helmet Violation
**Condition**: A motorcycle is carrying riders without helmets.
**Logic**:
```text
FOR EACH detected `motorcycle`:
  FIND intersecting `rider` bounding boxes (IoU > 0.3 or geometrically inside)
  FOR EACH `rider`:
    IF NO `helmet` detected intersecting rider's head region (top 20% of bbox)
    OR `no_helmet` class detected:
      TRIGGER Helmet_Violation
```

## 2. Triple Riding
**Condition**: More than two persons on a single two-wheeler.
**Logic**:
```text
FOR EACH detected `motorcycle`:
  COUNT intersecting `rider` bounding boxes
  IF COUNT >= 3:
    TRIGGER Triple_Riding_Violation
```

## 3. Wrong Side Driving
**Condition**: Vehicle is moving against the designated lane direction.
**Prerequisites**: Requires sequential frames (tracking) and predefined camera-specific lane vectors.
**Logic**:
```text
Vector V = Calculate trajectory vector from Track ID history over last N frames.
Vector L = Predefined legal flow vector for the lane polygon the vehicle occupies.
IF AngleBetween(V, L) > 120 degrees:
  TRIGGER Wrong_Side_Violation
```

## 4. Stop Line Violation
**Condition**: Vehicle crosses the solid white stop line at an intersection while the signal is Red.
**Prerequisites**: Predefined virtual polygon representing the Stop Line and Pedestrian Crossing for each camera view.
**Logic**:
```text
IF `traffic_light` state == RED:
  FOR EACH `vehicle`:
    IF vehicle front-bottom edge INTERSECTS Stop_Line_Polygon:
      TRIGGER Stop_Line_Violation
```

## 5. Overloading / Protruding Cargo
**Condition**: Goods extending significantly beyond the vehicle's body.
**Logic**:
```text
FOR EACH `truck` or `auto_rickshaw`:
  FIND intersecting `cargo` bounding boxes
  IF cargo_width > (vehicle_width * 1.2) OR cargo_height > (vehicle_height * 1.5):
    TRIGGER Overloading_Violation
```
