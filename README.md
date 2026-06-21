# TrafficVision AI

> Real-time automated traffic violation detection and enforcement platform

TrafficVision AI automates traffic violation detection at scale — ingesting camera images through a 7-stage computer vision pipeline, flagging helmetless riding, triple riding, wrong-way driving, stop-line violations, and overloading, then surfacing them in a web dashboard for officer review.

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│    Redis     │
│  React+Vite  │     │   FastAPI    │     │  Celery MQ   │
│   :3000      │     │    :8000     │     │    :6379     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                                       ┌────────▼───────┐
                                       │ CV Pipeline    │
                                       │ Celery Worker  │
                                       │ (YOLO/EasyOCR) │
                                       └────────────────┘
                                                │
                                         ┌──────▼───────┐
                                         │  PostgreSQL  │
                                         │    :5432     │
                                         └──────────────┘
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | React SPA (nginx) — Login, Dashboard, Violations Explorer, Analytics |
| `backend` | 8000 | FastAPI REST API — auth, ingestion, violations CRUD, analytics |
| `cv-pipeline` | — | Celery worker — 7-stage CV pipeline (mock or real inference) |
| `db` | 5432 | PostgreSQL 16 — violations, jobs, users |
| `broker` | 6379 | Redis 7 — Celery broker + result backend |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose
- (Optional for real CV) NVIDIA GPU with [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

### 1. Clone & configure

```bash
git clone <repo-url>
cd GridLock/prototype

# Create .env from the example
cp .env.example .env
```

### 2. Generate dependency lockfiles

Before the first `docker compose build`, generate lockfiles on your host to avoid file-locking issues:

```bash
# Backend
cd backend && uv sync

# CV Pipeline
cd cv-pipeline && uv sync

# Frontend
cd frontend && pnpm install

# Commit lockfiles so CI is reproducible
cd .. && git add backend/uv.lock cv-pipeline/uv.lock frontend/pnpm-lock.yaml
```

> **Windows users:** If `uv sync` fails with "Access is denied" on a `.pyd` file, close all IDE/terminal processes and retry. Use `taskkill /F /IM python.exe` to be sure no Python process is holding the file.

### 3. Start all services

```bash
docker compose up -d
```

Wait ~10 seconds for all services to become healthy, then open **http://localhost:3000**.

### 4. Create an admin user

The default admin account is seeded automatically on first startup:

| Username | Password |
|----------|----------|
| `admin` | `trafficvision` |

Login at **http://localhost:3000**.

---

## Modes of Operation

### Mock mode (default — no GPU required)

The CV pipeline returns realistic static outputs without any ML models:

```bash
# Already the default
USE_REAL_MODELS=false docker compose up -d
```

All 7 pipeline stages still execute; only the inference results are faked. This lets you test the full stack — ingestion, worker, DB write, and frontend — on any machine.

### Real inference mode (GPU required)

```bash
USE_REAL_MODELS=true docker compose up -d
```

The worker auto-detects CUDA. If a GPU is present it runs YOLOv8, EasyOCR, and ByteTrack for real detection and OCR. If no GPU is found it logs a warning and falls back to mock outputs.

---

## Development Workflows

### Run locally without Docker

**Backend:**
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**CV Worker (mock):**
```bash
cd cv-pipeline
uv sync
# Start Redis first:
redis-server
uv run celery -A app.worker worker --loglevel=info
```

**Frontend:**
```bash
cd frontend
pnpm install
pnpm dev
```

**Running tests:**
```bash
# Backend
cd backend && uv run pytest -q

# CV Pipeline
cd cv-pipeline && uv run pytest -q

# Frontend
cd frontend && pnpm test:run
```

### Hot-reload with Docker bind mounts

All service directories are bind-mounted into their containers, so code changes on your host are reflected immediately without rebuilding images:

```bash
docker compose up -d        # already bind-mounted
docker compose restart <svc> # after changing Dockerfile or package.json
```

---

## API Reference

All endpoints require a JWT bearer token unless noted. Login at `POST /api/v1/auth/login` to obtain one.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v1/auth/login` | Login — returns JWT | No |
| `GET` | `/api/v1/auth/me` | Current user info | Yes |
| `POST` | `/api/v1/upload` | Upload camera image for processing | Yes |
| `GET` | `/api/v1/violations` | List violations (paginated, filterable) | Yes |
| `GET` | `/api/v1/violations/{id}` | Violation detail with evidence | Yes |
| `PATCH` | `/api/v1/violations/{id}` | Update status (`approved`/`rejected`) | Yes |
| `GET` | `/api/v1/analytics/summary` | Aggregate violation counts | Yes |
| `GET` | `/health` | Health check | No |

### Upload an image

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@image.jpg" \
  -F "camera_id=<uuid>"
```

Processing is asynchronous — the endpoint returns `202 Accepted` immediately with a `job_id`. The Celery worker picks up the job, runs all 7 pipeline stages, and writes the result to the database.

---

## The 7-Stage CV Pipeline

Each stage is independently selectable as real or mock via `USE_REAL_MODELS`:

| Stage | Name | Real Approach | Mock Returns |
|-------|------|---------------|--------------|
| 1 | **IQA** | OpenCV Laplacian blur + brightness | `quality_pass: true` |
| 2 | **Detection** | YOLOv8n (COCO classes) | Static vehicle bboxes |
| 3 | **Secondary** | YOLOv8n on cropped motorcycles | `helmet`/`no_helmet` labels |
| 4 | **Tracking** | ByteTrack via supervision | Track IDs + trajectories |
| 5 | **LPD** | YOLOv8 fine-tuned on plates | Static plate bboxes |
| 6 | **OCR** | EasyOCR (`english_g2` model) | `"MH 12 AB 1234"` |
| 7 | **Rules** | Geometric IoU + point-in-polygon | Violation classification |

Stage 7 (rule engine) is always real — it evaluates helmet detection, triple riding, wrong-side driving, stop-line crossing, and overloading using the geometric relationships between stage 2/3/4/5 detections and configured road geometry.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...@db:5432/trafficvision` | PostgreSQL connection string |
| `REDIS_URL` | `redis://broker:6379/0` | Redis broker URL |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT TTL |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `USE_REAL_MODELS` | `false` | `true` = real inference, `false` = mock outputs |
| `DEVICE` | `cuda` | `cuda` or `cpu` (auto-detected if CUDA available) |
| `MODEL_CACHE_DIR` | `/app/models` | Where EasyOCR/YOLO weights are cached |

---

## Project Structure

```
prototype/
├── docker-compose.yml        # All 5 services + networking
├── .env.example              # Template for .env
├── .github/workflows/
│   ├── ci.yml               # Lint + test on push/PR
│   └── build-push.yml        # Build & push images to GHCR on release
│
├── backend/                  # FastAPI REST API
│   ├── app/
│   │   ├── main.py          # FastAPI app + /health endpoint
│   │   ├── config.py         # Settings from env vars
│   │   ├── database.py       # Async SQLAlchemy engine + session
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── api/v1/
│   │       ├── auth.py       # /auth endpoints
│   │       ├── ingestion.py  # /upload endpoint
│   │       ├── violations.py # /violations CRUD
│   │       └── analytics.py  # /analytics/summary
│   └── tests/               # pytest + AsyncClient integration tests
│
├── cv-pipeline/              # Celery worker + 7-stage CV pipeline
│   ├── app/
│   │   ├── worker.py         # Celery app + process_image task
│   │   ├── config.py         # USE_REAL_MODELS, DEVICE settings
│   │   ├── models/           # YOLO, EasyOCR, IQA, ByteTrack loaders
│   │   ├── mock/            # MOCK_STAGE_* constants
│   │   └── pipeline/
│   │       ├── orchestrator.py  # Stage runner + violation record deriver
│   │       └── stage_*.py   # One file per pipeline stage
│   └── tests/               # Rule engine unit + orchestrator tests
│
└── frontend/                 # React + Vite + TypeScript SPA
    ├── src/
    │   ├── pages/
    │   │   ├── Login.tsx
    │   │   ├── Dashboard.tsx
    │   │   ├── Violations.tsx  # List + detail + ImageViewer
    │   │   └── Analytics.tsx
    │   ├── services/api.ts   # All API call helpers
    │   └── tests/            # Vitest + React Testing Library
    ├── nginx.conf            # SPA fallback + /api proxy to backend
    └── Dockerfile            # Multi-stage: node:22-alpine → nginx:alpine
```

---

## CI / CD

Push to `main` or open a PR → GitHub Actions runs:

- Backend: `uv sync && uv run pytest -q && uv run ruff check .`
- CV Pipeline: `uv sync && uv run pytest -q`
- Frontend: `pnpm install && pnpm test:run && pnpm lint`

On version tags (`v*`) or pushes to `main`, the `build-push` workflow builds and pushes all three images to GitHub Container Registry (`ghcr.io`).

---

## Production Deployment

> See `Architecture Documents/DEPLOYMENT.md` for full production guidance.

Key production considerations:

- **GPU nodes**: Use `USE_REAL_MODELS=true` and ensure [`nvidia-docker`](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) is installed on the host.
- **Secret key**: Set `SECRET_KEY` to a randomly generated value — the JWT tokens depend on it.
- **Database migrations**: Backend auto-creates tables on startup (`Base.metadata.create_all`). For schema changes, use Alembic: `uv run alembic revision --autogenerate -m "description"`.
- **Object storage**: The system works without S3. To add it, uncomment the MinIO section in `docker-compose.yml` and set the env vars in `.env`.
- **HTTPS**: Put nginx behind a reverse proxy (Traefik, nginx, Cloudflare) for TLS termination — the containers themselves listen on HTTP.

---

## Troubleshooting

**`uv sync` fails with "Access is denied"**  
A Python process (VS Code debug, background terminal) is holding a file in the venv. Run `taskkill /F /IM python.exe` and retry.

**Worker never picks up jobs**  
Check Redis is healthy: `docker compose ps broker`. Verify the worker is connected: look for `Connected to redis://localhost:6379/0` in the worker logs (`docker compose logs cv-pipeline`).

**`/api/v1/health` returns 404**  
The `/health` endpoint is at the root level: `GET /health`, not `/api/v1/health`. The API v1 prefix only applies to `v1_router`.

**Frontend shows "Network Error"**  
Ensure CORS is configured correctly in `.env`: `CORS_ORIGINS=http://localhost:3000`. Also check the backend is reachable from the frontend container — use `docker compose exec frontend curl http://backend:8000/health`.

**No violations appear after upload**  
The upload returns `202 Accepted` immediately. Processing is async — wait a few seconds and refresh the Violations page. Check worker logs for the `pipeline complete` log line and any `No DB row found` warnings (a missing `job_id` means the upload and worker can't be linked).

**`USE_REAL_MODELS=true` but worker still uses mocks**  
Worker logs `No GPU detected` when CUDA is absent. Run `nvidia-smi` in the cv-pipeline container to verify: `docker compose exec cv-pipeline nvidia-smi`. If absent, install nvidia-docker or accept that the worker falls back to mock on that machine.