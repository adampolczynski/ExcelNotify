import os
import glob
import re
from datetime import date, datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

from change_history import ScheduleChangeTracker

load_dotenv()

app = Flask(__name__)

# Source directory for Excel files
# Try webapp/source first (VPS), fall back to project/source (local)
WEBAPP_SOURCE = os.path.join(os.path.dirname(__file__), "..", "source")
PROJECT_SOURCE = os.path.join(os.path.dirname(__file__), "source")

if os.path.exists(WEBAPP_SOURCE):
    SOURCE_DIR = WEBAPP_SOURCE
else:
    SOURCE_DIR = PROJECT_SOURCE

os.makedirs(SOURCE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def extract_primary_group(group_str):
    """Extract primary group number, removing letter suffixes.
    E.g., '9a' -> '9', '9 a' -> '9', '9b' -> '9', '9' -> '9', '10a' -> '10'
    """
    # Remove trailing letters (a, b, c, etc.)
    for i, char in enumerate(group_str):
        if char.isalpha():
            return group_str[:i].strip()
    return group_str.strip()


def extract_individual_groups(combined_class_str):
    """Extract individual group numbers from combined class strings.
    Handles comma-separated (8,9), dash-separated (14-15), or mixed formats.
    E.g., '8,9' -> ['8', '9'], '14-15' -> ['14', '15'], '8' -> ['8']
    """
    # Replace dashes with commas first, then split
    normalized = combined_class_str.replace('-', ',')
    parts = [p.strip() for p in normalized.split(',')]
    return parts


def get_unique_groups(all_classes):
    """Get unique primary group numbers from all class strings.
    Input: ['8', '9', '8,9', '9a', '9b', '9c', '8a,9a', '8,16']
    Output: ['8', '9', '16']
    """
    unique_primary_groups = set()
    for class_str in all_classes:
        groups = extract_individual_groups(class_str)
        for group in groups:
            primary = extract_primary_group(group)
            unique_primary_groups.add(primary)
    return sorted(unique_primary_groups, key=lambda x: (len(x), x))


def get_excel_file():
    """Find and return the newest .xlsx or .xls file in source/ directory."""
    files = glob.glob(os.path.join(SOURCE_DIR, "*.xlsx")) + glob.glob(os.path.join(SOURCE_DIR, "*.xls"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)  # Return the most recently modified file


def load_schedule_data():
    """Load schedule data from source/ Excel file."""
    excel_file = get_excel_file()
    if not excel_file:
        return None, "❌ Nie znaleziono pliku Excel w katalogu source/"

    try:
        # Read all sheets and concatenate them
        all_sheets = pd.read_excel(excel_file, sheet_name=None, header=None)
        raw = pd.concat(all_sheets.values(), ignore_index=True)
    except Exception as e:
        return None, f"❌ Nie można odczytać pliku Excel: {e}"

    # Keywords used to identify each canonical column
    COLUMN_KEYWORDS = {
        "date":       ["data", "date", "datum"],
        "class":      ["grupa", "group", "class", "klasa", "oddział", "oddzial"],
        "subject":    ["przedmiot", "subject", "lekcja", "lesson", "course", "nazwa"],
        "start_time": ["godzina", "start_time", "start time", "time", "godz", "hour", "czas"],
        "room":       ["miejsce", "room", "sala", "classroom", "location"],
        "instructor": ["imię", "imie", "instructor", "prowadzący", "prowadzacy", "person", "name"],
        "title":      ["tytuł", "tytul", "title", "degree", "qualification"],
        "method":     ["metody", "method", "type", "forma", "way", "online", "offline"],
    }
    all_keywords = [kw for kws in COLUMN_KEYWORDS.values() for kw in kws]

    # Find the first row that contains at least 3 of the expected keywords
    header_row = None
    for i, row in raw.iterrows():
        row_text = " ".join(str(v).lower() for v in row)
        if sum(kw in row_text for kw in all_keywords) >= 3:
            header_row = i
            break

    if header_row is None:
        return None, "❌ Nie znaleziono wiersza nagłówka w pliku."

    df = raw.iloc[header_row + 1:].copy()
    df.columns = [str(v).lower().strip() for v in raw.iloc[header_row]]
    df = df.reset_index(drop=True)

    # Auto-detect columns by keyword matching
    col_map = {}
    for canonical, keywords in COLUMN_KEYWORDS.items():
        for col in df.columns:
            if any(kw in col for kw in keywords):
                col_map[canonical] = col
                break

    missing = set(COLUMN_KEYWORDS.keys()) - set(col_map.keys())
    # Only require the core columns
    required_columns = {"date", "class", "subject", "start_time", "room"}
    missing_required = required_columns - set(col_map.keys())
    if missing_required:
        return None, f"❌ Nie znaleziono kolumn: {', '.join(sorted(missing_required))}"

    # Rename to canonical names
    df = df.rename(columns={v: k for k, v in col_map.items()})

    # Normalize date column - handle both dots and dashes (YYYY.MM.DD or YYYY-MM-DD format)
    df["date"] = df["date"].astype(str).str.replace('.', '-', regex=False)
    # Format is YYYY-MM-DD, so don't use dayfirst=True (it would swap month/day)
    df["date"] = pd.to_datetime(df["date"], format='%Y-%m-%d', errors='coerce')
    df = df.dropna(subset=['date'])
    df["date"] = df["date"].dt.date.astype(str)

    # Normalize class column
    df["class"] = df["class"].astype(str).fillna("").str.strip()
    
    # Clean up required columns
    df["subject"] = df["subject"].astype(str).fillna("").str.strip()
    df["start_time"] = df["start_time"].astype(str).fillna("").str.strip()
    df["room"] = df["room"].astype(str).fillna("").str.strip()
    
    # Clean up optional columns if they exist
    if "instructor" in df.columns:
        df["instructor"] = df["instructor"].astype(str).fillna("").str.strip()
    if "title" in df.columns:
        df["title"] = df["title"].astype(str).fillna("").str.strip()
    if "method" in df.columns:
        df["method"] = df["method"].astype(str).fillna("").str.strip()
    
    # Remove rows with empty class or date
    df = df[df["class"] != ""]
    df = df[df["date"] != ""]

    return df, None


def get_last_update_time():
    """Get the last modification time of the schedule file.
    Returns formatted string like '26.03 7:00' or None if file doesn't exist.
    """
    excel_file = get_excel_file()
    if not excel_file or not os.path.exists(excel_file):
        return None
    
    try:
        mtime = os.path.getmtime(excel_file)
        from datetime import datetime as dt
        update_dt = dt.fromtimestamp(mtime)
        return update_dt.strftime('%d.%m %H:%M')
    except Exception:
        return None


def save_previous_schedule(df):
    """Save current schedule for comparison next time"""
    try:
        prev_file = os.path.join(SOURCE_DIR, "schedule_previous.csv")
        df.to_csv(prev_file, index=False)
    except:
        pass  # Silently fail if can't save


def load_previous_schedule():
    """Load previously saved schedule for comparison"""
    try:
        prev_file = os.path.join(SOURCE_DIR, "schedule_previous.csv")
        if os.path.exists(prev_file):
            return pd.read_csv(prev_file)
    except:
        pass
    return None


def download_schedule_file():
    """Download schedule file from Google Drive."""
    import subprocess
    import sys
    
    # Google Drive direct download URL
    # File ID: 1_lBSt7ZT9Cz57gPcT00gpJt_gJ9u6mbz
    drive_url = "https://drive.google.com/uc?export=download&id=1_lBSt7ZT9Cz57gPcT00gpJt_gJ9u6mbz"
    
    # Output file path
    output_file = os.path.join(SOURCE_DIR, "schedule.xlsx")
    
    try:
        # Use curl to download (simpler than urllib)
        cmd = ["curl", "-L", "-o", output_file, drive_url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_file):
            return True, f"✅ File downloaded successfully to {output_file}"
        else:
            return False, f"❌ Download failed: {result.stderr}"
    except Exception as e:
        return False, f"❌ Error downloading file: {str(e)}"


# ---------------------------------------------------------------------------
# Main routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    df, error = load_schedule_data()
    
    if error:
        return render_template("index.html", error=error, classes=[], table_data=[])
    
    # Get all unique classes, sorted
    all_classes = sorted(df["class"].unique().tolist())
    
    # Get unique individual groups for the filter dropdown
    unique_groups = get_unique_groups(all_classes)
    
    # Get selected groups from query params (default: empty/none)
    selected_groups_param = request.args.get("groups", "")
    if selected_groups_param:
        selected_groups = [g.strip() for g in selected_groups_param.split(",") if g.strip()]
    else:
        selected_groups = []  # Default: empty - user must select

    # Get date range from query params (default: today to today+2 days)
    default_from = date.today()
    default_to = date.today() + timedelta(days=2)
    date_from_param = request.args.get("date_from", str(default_from))
    date_to_param = request.args.get("date_to", str(default_to))

    try:
        date_from = datetime.strptime(date_from_param, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to_param, "%Y-%m-%d").date()
    except ValueError:
        date_from = default_from
        date_to = default_to

    # Filter data - if groups are selected, show classes that contain any of those groups
    if selected_groups:
        # Find all classes where any group matches the selected primary groups
        matching_classes = []
        for class_str in all_classes:
            class_groups = extract_individual_groups(class_str)
            for class_group in class_groups:
                if extract_primary_group(class_group) in selected_groups:
                    matching_classes.append(class_str)
                    break  # Don't add the same class twice
        df_filtered = df[
            (df["class"].isin(matching_classes)) &
            (df["date"] >= str(date_from)) &
            (df["date"] <= str(date_to))
        ]
    else:
        # No groups selected - show empty
        df_filtered = df[df["class"].isin([])]
    
    # Sort by date and start_time
    df_filtered = df_filtered.sort_values(by=["date", "start_time"])
    
    # Convert to table rows (list of dicts)
    table_data = df_filtered.to_dict(orient="records")

    # Track changes from previous schedule (only when Excel file has changed)
    tracker = ScheduleChangeTracker(os.path.join(SOURCE_DIR, "change_history.json"))
    excel_file = os.path.join(SOURCE_DIR, "schedule.xlsx")
    mtime_file = os.path.join(SOURCE_DIR, "last_compared.txt")
    excel_mtime = os.path.getmtime(excel_file) if os.path.exists(excel_file) else 0
    try:
        last_compared = float(open(mtime_file).read().strip())
    except:
        last_compared = 0
    if excel_mtime > last_compared:
        previous_df = load_previous_schedule()
        tracker.compare_schedules(previous_df, df)
        save_previous_schedule(df)
        with open(mtime_file, 'w') as f:
            f.write(str(excel_mtime))
    
    # Get changes for display
    latest_changes = tracker.get_changes_for_display()

    return render_template(
        "index.html",
        classes=unique_groups,
        selected_classes=selected_groups,
        date_from=date_from_param,
        date_to=date_to_param,
        table_data=table_data,
        last_update_time=get_last_update_time(),
        latest_changes=latest_changes,
    )


@app.route("/api/classes")
def api_classes():
    """API endpoint to get all available individual groups."""
    df, error = load_schedule_data()
    if error:
        return jsonify({"error": error}), 400
    
    all_classes = sorted(df["class"].unique().tolist())
    unique_groups = get_unique_groups(all_classes)
    return jsonify({"groups": unique_groups})


@app.route("/api/schedule")
def api_schedule():
    """API endpoint to get filtered schedule."""
    df, error = load_schedule_data()
    if error:
        return jsonify({"error": error}), 400
    
    # Get all classes and unique groups
    all_classes = sorted(df["class"].unique().tolist())
    
    # Get filters
    groups_param = request.args.get("groups", "")
    date_from_param = request.args.get("date_from", str(date.today()))
    date_to_param = request.args.get("date_to", str(date.today()))
    
    # Parse selected groups
    if groups_param:
        selected_groups = [g.strip() for g in groups_param.split(",") if g.strip()]
        # Find all classes where any group matches the selected primary groups
        matching_classes = []
        for class_str in all_classes:
            class_groups = extract_individual_groups(class_str)
            for class_group in class_groups:
                if extract_primary_group(class_group) in selected_groups:
                    matching_classes.append(class_str)
                    break  # Don't add the same class twice
    else:
        matching_classes = []
    
    # Parse dates
    try:
        date_from = datetime.strptime(date_from_param, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to_param, "%Y-%m-%d").date()
    except ValueError:
        date_from = date.today()
        date_to = date.today()
    
    # Filter
    df_filtered = df[
        (df["class"].isin(matching_classes)) &
        (df["date"] >= str(date_from)) &
        (df["date"] <= str(date_to))
    ]
    
    df_filtered = df_filtered.sort_values(by=["date", "start_time"])
    table_data = df_filtered.to_dict(orient="records")
    
    return jsonify({"data": table_data})


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
