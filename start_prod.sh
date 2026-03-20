#!/bin/bash
# Production startup script
# Run with: ./start_prod.sh

set -e

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Copy .env.example to .env and fill in your values."
    exit 1
fi

# Check if virtual environment is active (optional but recommended)
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected. Consider activating one."
fi

# Start Gunicorn
echo "Starting production server on http://0.0.0.0:8000"
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --keep-alive 2 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    wsgi:application
