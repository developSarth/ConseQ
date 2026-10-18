#!/bin/sh
set -e

# Optional: Run graph seeder if SEED_ON_STARTUP is enabled in environment
if [ "$SEED_ON_STARTUP" = "true" ] || [ "$SEED_ON_STARTUP" = "1" ]; then
    echo "[entrypoint] SEED_ON_STARTUP is enabled. Running software graph seeder..."
    python /app/scripts/seed_software.py || echo "[entrypoint] Warning: Seeding returned non-zero (graph may already exist or DB offline)."
fi

# Determine port (Render dynamically sets $PORT, default to 8000)
APP_PORT="${PORT:-8000}"
echo "[entrypoint] Starting ECHO FastAPI server on 0.0.0.0:${APP_PORT}..."

# Start uvicorn with standard production settings
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${APP_PORT}" \
    --workers "${WORKERS:-1}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
