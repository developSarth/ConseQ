# =============================================================================
# ECHO — AI-Powered Software Architecture & Failure Simulator
# Production Dockerfile for Render Web Service Deployment
# =============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8000

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application source and scripts
COPY backend /app/backend
COPY scripts /app/scripts

# Make entrypoint script executable
RUN chmod +x /app/scripts/entrypoint.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser
WORKDIR /app/backend

# Expose default port (Render will bind to dynamic $PORT at runtime)
EXPOSE 8000

# Container healthcheck using ECHO's zero-dependency liveness route
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Launch application via entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
