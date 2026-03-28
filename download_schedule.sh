#!/bin/bash
# Auto-download schedule from Google Drive
# Add to crontab with: 0 7 * * * ~/webapp/download_schedule.sh

# Google Drive file ID
FILE_ID="1_lBSt7ZT9Cz57gPcT00gpJt_gJ9u6mbz"
DOWNLOAD_URL="https://drive.google.com/uc?export=download&id=${FILE_ID}"

# Project directories
WEBAPP_ROOT="$HOME/webapp"
PROJECT_DIR="${WEBAPP_ROOT}/project"
SOURCE_DIR="${PROJECT_DIR}/source"
OUTPUT_FILE="${SOURCE_DIR}/schedule.xlsx"
LOG_FILE="${WEBAPP_ROOT}/download.log"
VENV_PYTHON="${WEBAPP_ROOT}/venv/bin/python3"
GUNICORN="${WEBAPP_ROOT}/venv/bin/gunicorn"

# Create source directory if it doesn't exist
mkdir -p "${SOURCE_DIR}"

# Download the file
curl -L -o "${OUTPUT_FILE}" "${DOWNLOAD_URL}"

# Check if download was successful
if [ -f "${OUTPUT_FILE}" ]; then
    echo "[$(date)] ✅ Schedule downloaded successfully to ${OUTPUT_FILE}" >> "${LOG_FILE}"
    
    # Restart Gunicorn to load the new data
    echo "[$(date)] 🔄 Restarting Gunicorn..." >> "${LOG_FILE}"
    
    # Kill all gunicorn processes - be very aggressive
    killall -9 gunicorn 2>/dev/null || true
    pkill -9 -f /gunicorn 2>/dev/null || true
    rm -f /tmp/gunicorn.pid
    
    # Force release the port
    fuser -k 8000/tcp 2>/dev/null || true
    
    # Wait for everything to fully clean up
    sleep 5
    
    # Start Gunicorn in background using full paths
    cd "${PROJECT_DIR}"
    nohup "${GUNICORN}" --bind 127.0.0.1:8000 --workers 4 --worker-class sync --worker-connections 1000 --max-requests 1000 --max-requests-jitter 50 --timeout 30 --keep-alive 2 --log-level info --access-logfile - --error-logfile - wsgi:application >> "${LOG_FILE}" 2>&1 &
    
    sleep 2
    echo "[$(date)] ✅ Gunicorn restart completed" >> "${LOG_FILE}"
    exit 0
else
    echo "[$(date)] ❌ Failed to download schedule" >> "${LOG_FILE}"
    exit 1
fi
