"""Settings for the CV Pipeline service."""

import logging
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """All env-driven config consumed by the worker and pipeline stages."""

    # ── Broker ──────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://broker:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://broker:6379/1"

    # ── Database ────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://trafficvision:devpassword@db:5432/trafficvision"
    )

    # When running the worker on the host machine (outside Docker), swap
    # the Docker hostname 'db' for 'localhost' so the URL resolves.
    USE_HOST_DB: bool = False

    @property
    def resolved_database_url(self) -> str:
        url = self.DATABASE_URL
        if self.USE_HOST_DB and "@db:" in url:
            return url.replace("@db:", "@localhost:")
        return url

    # ── CV Inference ─────────────────────────────────────────────────
    # Set USE_REAL_MODELS=true (or in .env) to enable real model inference.
    # When false, every stage falls back to the mock outputs so the
    # pipeline remains functional without GPU / internet access.
    USE_REAL_MODELS: bool = False

    # Device for PyTorch inference.  "cuda" triggers GPU acceleration when
    # torch.cuda.is_available()==True; falls back to "cpu" automatically.
    DEVICE: str = "cuda"

    # Directory where fine-tuned model weights and cached OCR models live.
    # Pre-downloaded weights from the training phase can be placed here.
    MODEL_CACHE_DIR: str = "/app/models"

    @property
    def model_cache_path(self) -> Path:
        p = Path(self.MODEL_CACHE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def device(self) -> str:
        # Respect user's DEVICE choice only when CUDA is available.
        # Silently switch to cpu so the pipeline never crashes on a CPU-only host.
        try:
            import torch as _torch
            if self.DEVICE == "cuda" and not _torch.cuda.is_available():
                logger.warning("CUDA requested but not available; using CPU.")
                return "cpu"
        except ImportError:
            pass
        return self.DEVICE

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()