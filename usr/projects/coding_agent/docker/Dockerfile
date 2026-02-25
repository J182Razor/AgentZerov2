# Multi-stage Dockerfile for Content Automation System
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1     PIP_NO_CACHE_DIR=1     PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y     ffmpeg     git     curl     && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt &&     pip install --no-cache-dir openai-whisper

# Copy application code
COPY content_automation/ ./content_automation/
COPY pyproject.toml .

# Create necessary directories
RUN mkdir -p /app/work /app/temp /app/output /app/logs

# Install the package
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 appuser &&     chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3     CMD python -c "import content_automation; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "content_automation.pipeline.orchestrator"]
