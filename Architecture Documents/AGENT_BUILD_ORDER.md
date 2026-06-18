# Agent Build Order

This document defines the strict, phased approach for AI coding agents (e.g., Claude Code, Cursor) to autonomously build the TrafficVision AI system. 

### PHASE 1: Project Setup & Infrastructure
- Initialize Git repository.
- Setup `docker-compose.yml` with placeholder services for frontend, backend, and db.
- Configure Linting, Prettier, and project base configs.

### PHASE 2: Database Layer
- Setup PostgreSQL in Docker.
- Implement SQLAlchemy/Prisma schemas based on `DATABASE_SCHEMA.md`.
- Write and execute initial migration scripts.

### PHASE 3: Backend API Foundations
- Setup FastAPI structure (routers, controllers, dependencies).
- Implement the Ingestion API endpoint (`/upload`).
- Setup message broker (Redis/RabbitMQ) connection for background processing.

### PHASE 4: Computer Vision Pipeline (Mock)
- Create the Python Celery worker service.
- Implement the 7-stage pipeline structure with dummy/mock outputs (returning static bounding boxes and confidence scores) to establish the internal data contract.

### PHASE 5: Rule Engine Integration
- Implement the mathematical logic defined in `VIOLATION_RULE_ENGINE.md`.
- Connect the mock CV outputs to the rule engine to successfully generate violation records in the database.

### PHASE 6: Frontend Dashboard (React/Vite)
- Scaffold React app with TailwindCSS and TypeScript.
- Build the Dashboard layout (Sidebar, Header, Metrics Cards).
- Connect Dashboard to Backend Analytics APIs.

### PHASE 7: Violation Explorer & Detail View
- Build the data table with pagination and filtering for the `/violations` route.
- Implement the Detail View modal with image viewing, bounding box overlays (HTML Canvas/SVG), and Approve/Reject buttons.

### PHASE 8: Real CV Integration
- Replace the mock CV pipeline with actual PyTorch/ONNX model inference code.
- Ensure GPU acceleration is configured in the worker container.

### PHASE 9: End-to-End Testing
- Write integration tests simulating camera uploads.
- Verify end-to-end data flow from API ingestion to frontend state updates.

### PHASE 10: Deployment Prep
- Finalize multi-stage Dockerfiles for production.
- Setup CI/CD pipeline configuration (e.g., GitHub Actions).
