# Product Requirements Document (PRD)

## 1. Introduction
This document outlines the product requirements, user flows, and page-by-page specifications for the TrafficVision AI platform.

## 2. Core Workflows
1. **System Ingestion**: Cameras auto-upload images. AI processes them and flags violations.
2. **Human Verification**: An enforcement officer logs in, views the "Pending Review" queue, and either Approves or Rejects the AI's findings.
3. **Analytics Review**: Administrators view daily/weekly trends to make macro-level decisions regarding traffic infrastructure.

## 3. Page Specifications

### 3.1 Dashboard (Home)
- **Purpose**: High-level overview of system health and daily statistics.
- **Data Elements**:
  - Total violations detected today (vs yesterday).
  - Processing queue length / Pipeline health.
  - Overall accuracy / Confidence metrics.
- **Components**:
  - Time-series chart of violations per hour.
  - Pie/Donut chart of violation types.
  - Heatmap showing top cameras with violations.
- **States**: Loading skeleton, Error boundary for failed API calls, Auto-refreshing data (every 60s).

### 3.2 Violation Explorer
- **Purpose**: Tabular interface to search, filter, and paginate through all records.
- **Filters**: Date range, Violation Type, Camera ID, Status (Pending, Approved, Rejected).
- **Table Columns**: Job ID, Thumbnail, Timestamp, Type, Plate Number, Confidence, Status, Actions.
- **Interactions**: Clicking a row opens the Violation Detail View. Supports batch selection for bulk approval/rejection.

### 3.3 Violation Detail View
- **Purpose**: Deep dive into a specific event for human verification.
- **Components**:
  - **Main Image Viewer**: High-res image with drawn bounding boxes overlaid. Bounding boxes should be toggleable by class.
  - **Cropped Evidence**: Extracted sub-images of the license plate, driver, and the specific violating vehicle.
  - **Metadata Card**: Timestamps, exact location, AI confidence scores for each detection stage.
  - **Action Buttons**: "Approve & Issue Citation", "Reject (False Positive)".

### 3.4 Analytics & Reports
- **Purpose**: Complex reporting and data export for management.
- **Components**:
  - Custom date range reports.
  - Export to CSV/PDF buttons.
  - Top 10 repeat offenders (based on license plate aggregation).

### 3.5 Admin Panel
- **Purpose**: System configuration and administration.
- **Components**:
  - Camera Management (Add/Edit/Remove camera endpoints, configure specific rules per camera).
  - User Management (RBAC for enforcement officers vs administrators).
  - AI Threshold Settings (e.g., adjust minimum confidence score from 0.7 to 0.8).
