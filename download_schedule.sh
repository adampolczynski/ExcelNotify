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

# Create source directory if it doesn't exist
mkdir -p "${SOURCE_DIR}"

# Download the file
curl -L -o "${OUTPUT_FILE}" "${DOWNLOAD_URL}"

# Check if download was successful
if [ -f "${OUTPUT_FILE}" ]; then
    echo "[$(date)] ✅ Schedule downloaded successfully to ${OUTPUT_FILE}" >> "${LOG_FILE}"
    echo "[$(date)] ℹ️ Manual restart required: cd ~/webapp/project && pkill -9 gunicorn; sleep 3; ./start_prod.sh" >> "${LOG_FILE}"
    exit 0
else
    echo "[$(date)] ❌ Failed to download schedule" >> "${LOG_FILE}"
    exit 1
fi
