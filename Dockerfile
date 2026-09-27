# Multi-stage production Dockerfile for SmartEval
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies for OpenCV and image operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir email-validator

# Copy application codebase
COPY . .

# Ensure data and output directories exist
RUN mkdir -p data/uploads outputs/diagram_temp outputs/scores

# Expose ports for both FastAPI (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Default command starts the high-throughput FastAPI production backend
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
