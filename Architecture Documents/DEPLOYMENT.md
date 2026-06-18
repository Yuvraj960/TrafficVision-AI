# Deployment Strategy

## 1. Technology Stack
- **Frontend**: React, TypeScript, Vite, TailwindCSS.
- **Backend**: Python, FastAPI, SQLAlchemy.
- **Background Workers**: Celery.
- **Database**: PostgreSQL (Relational metadata), Redis (Message Broker & API Caching).
- **AI Worker**: Python, PyTorch, YOLOv11, PaddleOCR.
- **Containerization**: Docker, Docker Compose.

## 2. Environment Configuration
Environment variables will be managed via `.env` files (not committed to source control).
```env
# Database
POSTGRES_USER=traffic_admin
POSTGRES_PASSWORD=secure_pass
POSTGRES_DB=traffic_vision

# Services
REDIS_URL=redis://redis:6379/0
API_PORT=8000
```

## 3. Deployment Architecture (Cloud/Edge Hybrid)
- **Edge Nodes**: Deployed near the physical cameras. Run lightweight ingestion services and optionally perform initial low-cost frame filtering (e.g., motion detection).
- **Cloud/Central Server**: AWS EC2 (GPU-enabled instance like g4dn.xlarge) or a local datacenter cluster. Runs the heavy Deep Learning CV pipeline, PostgreSQL database, and hosts the Web Dashboard API.

## 4. CI/CD Pipeline
- **Continuous Integration (GitHub Actions)**:
  1. Linting & Unit tests triggered on Push to `main`.
  2. Build Docker images for Frontend, Backend, and CV Worker components.
  3. Push verified images to AWS ECR or Docker Hub.
- **Continuous Deployment**:
  1. Trigger remote deployment script on the production server for rolling updates with zero downtime.

## 5. Backup Strategy
- **Database**: Nightly `pg_dump` backups automatically uploaded to AWS S3.
- **Storage**: Raw violation images stored in S3/MinIO with lifecycle policies configured to move images to cold storage (Glacier) after 90 days for compliance auditing.
