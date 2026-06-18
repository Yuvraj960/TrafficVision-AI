# UI/UX Specification

## General Aesthetics
- **Theme**: Light and Dark mode support. Dark mode defaults for control room environments to reduce eye strain.
- **Color Palette**: 
  - Primary: Slate/Indigo for layout and navigation.
  - Accents: Red for Violations (Critical), Yellow for Pending/Warning, Green for Approved/Resolved.
- **Typography**: Inter or Roboto for high legibility on data-heavy tables.

## Screen Specifications

### 1. Dashboard
- **Cards (Top Row)**: 
  - Total Violations Today (Big Number, % change vs yesterday).
  - OCR Average Accuracy (Progress circle, e.g., 94%).
  - Active Cameras (e.g., 12/12 online).
- **Charts**:
  - Main Chart: Hourly Violation Volume (Bar chart).
  - Secondary Chart: Violation Distribution by Type (Donut chart).
- **Tables**:
  - Recent Critical Violations (Top 5 most confident detections).

### 2. Violation Explorer (Table View)
- **Layout**: Full-width data table.
- **Toolbar**: 
  - Date picker dropdown.
  - Multi-select dropdown for "Violation Type".
  - Search bar for License Plate.
- **Rows**: Hover states should highlight the row and show a quick preview tooltip of the image.

### 3. Violation Detail Modal
- **Layout**: Split view (60/40).
- **Left Pane (60%)**: 
  - High-resolution image viewer with pan/zoom capabilities.
  - Toggles for bounding boxes (`[x] Vehicles`, `[x] Plates`, `[x] Helmets`).
- **Right Pane (40%)**:
  - Extracted Plate Crop (enlarged for readability).
  - OCR text input field (allows human override if OCR failed).
  - Timestamps, Location map snippet.
  - Sticky footer with large "Approve" (Green) and "Reject" (Red/Ghost) buttons.
