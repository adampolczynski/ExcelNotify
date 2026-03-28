#!/bin/bash
# Auto-download schedule from Google Drive
# Add to crontab with: 0 7 * * * /path/to/download_schedule.sh

# Google Drive file ID
FILE_ID="1_lBSt7ZT9Cz57gPcT00gpJt_gJ9u6mbz"
DOWNLOAD_URL="https://drive.google.com/uc?export=download&id=${FILE_ID}"

# Project directory
PROJECT_DIR="/home/beat/Code/web/project"
SOURCE_DIR="${PROJECT_DIR}/source"
OUTPUT_FILE="${SOURCE_DIR}/schedule.xlsx"

# Create source directory if it doesn't exist
mkdir -p "${SOURCE_DIR}"

# Download the file
curl -L -o "${OUTPUT_FILE}" "${DOWNLOAD_URL}"

# Check if download was successful
if [ -f "${OUTPUT_FILE}" ]; then
    echo "[$(date)] ✅ Schedule downloaded successfully to ${OUTPUT_FILE}" >> "${PROJECT_DIR}/download.log"
    
    # Restart Gunicorn to load the new data
    echo "[$(date)] 🔄 Restarting Gunicorn..." >> "${PROJECT_DIR}/download.log"
    pkill -9 -f gunicorn
    rm -f /tmp/gunicorn.pid
    sleep 2
    cd "${PROJECT_DIR}" && nohup ./start_prod.sh >> "${PROJECT_DIR}/download.log" 2>&1 &
    echo "[$(date)] ✅ Gunicorn restarted" >> "${PROJECT_DIR}/download.log"
    
    exit 0
else
    echo "[$(date)] ❌ Failed to download schedule" >> "${PROJECT_DIR}/download.log"
    exit 1
fi
