# Database Schema

The core database uses PostgreSQL. Below is the schema layout for the critical tables.

## 1. Cameras Table
Stores metadata for registered edge devices.
```sql
CREATE TABLE cameras (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    rtsp_url TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 2. Violations Table
The central table storing all AI-flagged infractions.
```sql
CREATE TABLE violations (
    id UUID PRIMARY KEY,
    camera_id UUID REFERENCES cameras(id),
    job_id VARCHAR(255),
    violation_type VARCHAR(100) NOT NULL, -- 'helmet', 'wrong_side', etc.
    vehicle_type VARCHAR(50),
    plate_number VARCHAR(50),
    confidence_score DECIMAL(5, 4),
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    image_url TEXT NOT NULL,
    plate_image_url TEXT,
    timestamp TIMESTAMP NOT NULL,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP
);
```

## 3. Users Table (Officers & Admins)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'officer', 'admin'
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 4. Audit Log Table
Tracks all actions taken by human reviewers for compliance.
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    violation_id UUID REFERENCES violations(id),
    action VARCHAR(50) NOT NULL, -- 'approved', 'rejected'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
