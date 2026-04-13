#!/bin/bash
# Production startup script
# Run with: ./start_prod.sh

set -e

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Copy .env.example to .env and fill in your values."
    exit 1
fi

# Start Gunicorn on localhost:8000 (nginx will proxy from port 80)
echo "Starting app on localhost:8000"
exec gunicorn \
    --bind 127.0.0.1:8000 \
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
