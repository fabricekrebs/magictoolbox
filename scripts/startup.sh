#!/bin/bash
# Startup script for MagicToolbox Django application in Azure Container Apps
# This script runs migrations and starts the application server

set -e  # Exit on error

echo "=== MagicToolbox Startup ==="
echo "Starting at $(date)"

# Wait for database to be ready (with timeout)
echo "Checking database connectivity..."
MAX_RETRIES=30
RETRY_COUNT=0

until python manage.py check --database default 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: Database not available after $MAX_RETRIES attempts"
        echo "Last error output is shown above"
        exit 1
    fi
    echo "Waiting for database... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo "Database is ready!"

# Run comprehensive startup health checks
echo ""
echo "=== Running Startup Health Checks ==="
python /app/scripts/startup_health_checks.py
HEALTH_CHECK_EXIT=$?

if [ $HEALTH_CHECK_EXIT -ne 0 ]; then
    echo "WARNING: Some health checks failed (exit code: $HEALTH_CHECK_EXIT)"
    echo "Continuing with startup..."
fi
echo ""

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create cache table if it doesn't exist
echo "Setting up cache..."
python manage.py createcachetable || true

# Collect static files (if not already done in Dockerfile)
if [ ! -d "/app/staticfiles" ] || [ -z "$(ls -A /app/staticfiles)" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

# Check for any issues (skip deploy checks to avoid non-critical warnings blocking startup)
echo "Running system checks..."
python manage.py check

echo "=== Starting Application Server ==="
echo "Workers: ${GUNICORN_WORKERS:-2}"
echo "Threads: ${GUNICORN_THREADS:-4}"
echo "Timeout: ${GUNICORN_TIMEOUT:-120}s"

# Start Gunicorn with configuration optimized for Container Apps
exec gunicorn magictoolbox.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-2} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL:-info} \
    --capture-output \
    --enable-stdio-inheritance
