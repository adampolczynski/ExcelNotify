# PAM Pielęgniarstwo - Plan Zajęć

Simple schedule viewer application for displaying class schedules with optional auto-download from Google Drive.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure (optional)
- No configuration needed for basic operation
- The app reads Excel files from the `source/` directory

### 3. Run locally
```bash
python app.py
```
Visit http://localhost:5000

### 4. Deploy

**Option A: Manual deployment**
```bash
# Download Excel file manually to source/ folder
cp /path/to/schedule.xlsx ./source/schedule.xlsx

# Run with Gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

**Option B: Auto-download with Cron (Recommended)**

1. Make the download script executable:
```bash
chmod +x /home/beat/Code/web/project/download_schedule.sh
```

2. Add to crontab to run daily at 7:00 AM:
```bash
crontab -e
# Add this line:
0 7 * * * /home/beat/Code/web/project/download_schedule.sh
```

3. Verify cron job is set:
```bash
crontab -l
```

4. Check download logs:
```bash
tail -f /home/beat/Code/web/project/download.log
```

## Features

- 📅 View schedule with multiple filters
- 🔍 Filter by classes (multi-select dropdown)
- 📅 Filter by date range
- 🖱️ Calendar date picker
- ⬇️ Manual download button for testing
- ✅ Auto-download daily via cron
- 📊 Displays: Date, Class, Time, Subject, Room, Instructor, Title, Method

## File Structure

```
project/
├── app.py                 # Flask application
├── download_schedule.sh   # Cron download script
├── requirements.txt       # Python dependencies
├── source/               # Excel files (auto-read)
│   └── schedule.xlsx
├── templates/
│   ├── index.html        # Main page
│   └── login.html        # Login (auth removed)
└── static/
    └── style.css         # Styling
```

## Notes

- The app automatically detects Excel columns by keywords
- Polish language support for UI
- No authentication required
- Responsive design works on mobile/tablet
