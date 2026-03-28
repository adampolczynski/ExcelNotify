#!/bin/bash
# Auto-download schedule from Google Drive
# Add to crontab with: 0 7 * * * ~/webapp/download_schedule.sh

# Google Drive file ID
FILE_ID="1_lBSt7ZT9Cz57gPcT00gpJt_gJ9u6mbz"
DOWNLOAD_URL="https://drive.google.com/uc?export=download&id=${FILE_ID}"

# Project directories - the source folder is at webapp root, not in project/
WEBAPP_ROOT="$HOME/webapp"
SOURCE_DIR="${WEBAPP_ROOT}/source"
OUTPUT_FILE="${SOURCE_DIR}/schedule.xlsx"
LOG_FILE="${WEBAPP_ROOT}/download.log"

# Create source directory if it doesn't exist
mkdir -p "${SOURCE_DIR}"

# Remove old file before downloading
rm -f "${OUTPUT_FILE}"

# Download the file
curl -L -o "${OUTPUT_FILE}" "${DOWNLOAD_URL}"

# Check if download was successful
if [ -f "${OUTPUT_FILE}" ]; then
    echo "[$(date)] ✅ Schedule downloaded successfully to ${OUTPUT_FILE}" >> "${LOG_FILE}"
    
    # Restart the webapp service to load new data
    echo "[$(date)] 🔄 Restarting webapp service..." >> "${LOG_FILE}"
    sudo systemctl restart webapp
    
    sleep 2
    echo "[$(date)] ✅ Webapp service restarted" >> "${LOG_FILE}"
    exit 0
else
    echo "[$(date)] ❌ Failed to download schedule" >> "${LOG_FILE}"
    exit 1
fi
