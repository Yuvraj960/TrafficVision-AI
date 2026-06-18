# API Contracts

All APIs follow RESTful conventions. Base URL: `/api/v1`

## 1. Ingestion API

### `POST /upload`
Receives an image payload from a camera.
**Request**:
```json
{
  "camera_id": "uuid",
  "timestamp": "2023-10-25T14:30:00Z",
  "image_base64": "data:image/jpeg;base64,...",
  "metadata": {}
}
```
**Response (202 Accepted)**:
```json
{
  "job_id": "job-123456",
  "status": "queued"
}
```

## 2. Violation Review API

### `GET /violations`
Fetches a paginated list of violations.
**Query Parameters**: `?status=pending&camera_id=uuid&page=1&limit=50`
**Response (200 OK)**:
```json
{
  "data": [
    {
      "id": "viol-uuid",
      "type": "helmet_violation",
      "plate": "MH12AB1234",
      "timestamp": "2023-10-25T14:30:00Z",
      "status": "pending",
      "image_url": "https://storage.aws.com/..."
    }
  ],
  "meta": { "total": 1500, "page": 1, "limit": 50 }
}
```

### `PATCH /violations/{id}/status`
Approve or reject a violation.
**Request**:
```json
{
  "status": "approved",
  "notes": "Plate clearly visible."
}
```
**Response (200 OK)**:
```json
{
  "id": "viol-uuid",
  "status": "approved",
  "updated_at": "2023-10-25T15:00:00Z"
}
```

## 3. Analytics API

### `GET /analytics/summary`
**Query Parameters**: `?date_from=2023-10-01&date_to=2023-10-31`
**Response (200 OK)**:
```json
{
  "total_violations": 450,
  "by_type": {
    "helmet": 300,
    "wrong_side": 150
  }
}
```
