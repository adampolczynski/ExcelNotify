#!/bin/bash
# Auto-download semester schedule files from Google Drive folder
# Crontab: 0 7 * * * ~/webapp/download_schedule.sh

FOLDER_ID="1EVbnXHgVSbMT-lh_DMGbdhkX07xDCUFQ"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/source"
LOG_FILE="${SCRIPT_DIR}/download.log"
NAMES_JSON="${SCRIPT_DIR}/semester_names.json"
STATUS_FILE="${SCRIPT_DIR}/download_status.json"

log() { echo "$1" | tee -a "${LOG_FILE}"; }

mkdir -p "${SOURCE_DIR}"
log "[$(date)] 🔄 Starting schedule download..."

PREFIXES=$(python3 -c "
import json, sys
try:
    data = json.load(open('${NAMES_JSON}'))
    print(' '.join(data.keys()))
except: sys.exit(1)
" 2>/dev/null)

if [ -z "${PREFIXES}" ]; then
    log "[$(date)] ❌ Could not read prefixes from ${NAMES_JSON}"
    exit 1
fi
log "[$(date)] 📋 Valid prefixes: ${PREFIXES}"

TMPPY=$(mktemp /tmp/dl_sched_XXXX.py)
cat > "${TMPPY}" << PYEOF
import os, sys, re, json
import requests
from html import unescape

folder_id = "${FOLDER_ID}"
output_dir = "${SOURCE_DIR}"
prefixes = "${PREFIXES}".split()

os.makedirs(output_dir, exist_ok=True)

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'

# Step 1: Fetch folder page (session carries cookies for file access)
print("Fetching folder listing...")
session = requests.Session()
session.headers['User-Agent'] = UA
resp = session.get(f"https://drive.google.com/drive/folders/{folder_id}")
text = unescape(resp.text)

# Drive HTML embeds: data-id="FILE_ID" ... data-tooltip="FILENAME.xls ..."
matches = re.findall(r'data-id="([0-9A-Za-z_-]{25,})"[^>]*data-tooltip="([^"]+\.xls[x]?)', text)
seen = {}
for fid, fname in matches:
    if fname not in seen:
        seen[fname] = fid

if not seen:
    print("[ERR] Could not parse file listing from folder page")
    sys.exit(1)

print(f"Found {len(seen)} Excel file(s) in folder")

# Step 2: Download only prefix-matched files using direct requests
def drive_download(session, file_id, out_path):
    """Download a Google Drive file via export URL, handling virus-scan confirmation."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = session.get(url, stream=True, allow_redirects=True)
    r.raise_for_status()
    # Handle large-file virus scan warning page
    ct = r.headers.get('Content-Type', '')
    if 'text/html' in ct:
        # Extract confirmation token
        token = re.search(r'confirm=([0-9A-Za-z_-]+)', r.text)
        if token:
            url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={token.group(1)}"
            r = session.get(url, stream=True)
            r.raise_for_status()
        else:
            raise Exception("Got HTML response without confirmation token")
    with open(out_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)

kept, skipped, failed = [], [], []

for filename, file_id in seen.items():
    if not any(filename.startswith(p) for p in prefixes):
        skipped.append(filename)
        continue
    out_path = os.path.join(output_dir, filename)
    print(f"Downloading: {filename}")
    try:
        drive_download(session, file_id, out_path)
        size = os.path.getsize(out_path)
        print(f"  -> {size:,} bytes")
        kept.append(filename)
    except Exception as e:
        print(f"  [WARN] {filename}: {e}")
        if os.path.exists(out_path):
            os.remove(out_path)
        failed.append(filename)

print(f"\n[OK]   Downloaded ({len(kept)}): {kept}")
print(f"[SKIP] Skipped    ({len(skipped)}): {skipped}")
if failed:
    print(f"[WARN] Failed     ({len(failed)}): {failed}")

sys.exit(0 if kept else 1)
PYEOF

python3 "${TMPPY}" 2>&1 | tee -a "${LOG_FILE}"
PYEXIT=${PIPESTATUS[0]}
rm -f "${TMPPY}"

if [ ${PYEXIT} -ne 0 ]; then
    log "[$(date)] ❌ Download failed"
    FAIL_TIME=$(date '+%H:%M')
    printf '{"success": false, "time": "%s"}\n' "${FAIL_TIME}" > "${STATUS_FILE}"
    exit 1
fi

log "[$(date)] ✅ Download complete"
SUCCESS_TIME=$(date '+%H:%M')
printf '{"success": true, "time": "%s"}\n' "${SUCCESS_TIME}" > "${STATUS_FILE}"

if systemctl list-units --type=service 2>/dev/null | grep -q "webapp.service"; then
    log "[$(date)] 🔄 Restarting webapp service..."
    systemctl restart webapp 2>/dev/null \
        && log "[$(date)] ✅ Webapp restarted" \
        || log "[$(date)] ⚠️ Restart failed (try: sudo systemctl restart webapp)"
else
    log "[$(date)] ℹ️ No systemd webapp service — restart Flask manually"
fi
