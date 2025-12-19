# Multi-stage Dockerfile for MagicToolbox Django application
# Optimized for Azure Container Apps deployment

# Build arguments for version tracking
ARG BUILD_DATE
ARG VCS_REF
ARG BUILD_VERSION="unknown"

# =============================================================================
# Stage 1: Builder - Install dependencies and build assets
# =============================================================================
FROM python:3.11-slim AS builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements files
COPY requirements/base.txt requirements/production.txt /tmp/

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/production.txt

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.11-slim

# Copy build arguments to runtime
ARG BUILD_DATE
ARG VCS_REF
ARG BUILD_VERSION

# Set environment variables including build info
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=magictoolbox.settings.production \
    PATH="/opt/venv/bin:$PATH" \
    BUILD_DATE=${BUILD_DATE} \
    VCS_REF=${VCS_REF} \
    BUILD_VERSION=${BUILD_VERSION}

# Add labels for image metadata
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.title="MagicToolbox" \
      org.opencontainers.image.description="MagicToolbox Django Application"

# Install runtime system dependencies including FFmpeg for video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs /app/staticfiles /app/mediafiles && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser . /app/

# Switch to non-root user
USER appuser

# Expose port (Container Apps uses 8000 by default)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Ensure startup script is executable (already copied in line 89)
RUN chmod +x /app/scripts/startup.sh

# Run application
ENTRYPOINT ["/app/scripts/startup.sh"]
