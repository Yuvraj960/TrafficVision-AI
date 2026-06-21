FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

WORKDIR /app

# Install build dependencies + system libs for OpenCV & CV libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    wget \
    libbz2-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Build Python 3.12 from source (deadsnakes PPA doesn't ship 3.12 for jammy)
RUN wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz \
    && tar -xf Python-3.12.0.tgz \
    && cd Python-3.12.0 \
    && ./configure --enable-optimizations --prefix=/usr/local \
    && make -j$(nproc) \
    && make altinstall \
    && cd .. \
    && rm -rf Python-3.12.0 Python-3.12.0.tgz

# Install uv
RUN pip3.12 install --no-cache-dir uv

# Copy dependency files before installing packages
COPY requirements.txt uv.lock pyproject.toml ./

# Install Python dependencies into system Python (no venv needed)
# Everything lands in /usr/local/bin which is in PATH
RUN uv pip install --system -r requirements.txt

# Copy pre-trained model weights (placeholders; replace in production)
# COPY models/ /app/models/

# Copy application code
COPY app/ ./app/

RUN mkdir -p /app/models

# Entrypoint is overridden in docker-compose.yml to skip the nvidia-base-image
# init script. With --system install, celery is already in PATH.
CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info", "--concurrency=2"]