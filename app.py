import hmac
import os
import secrets
from datetime import date
from functools import wraps

import requests as http_requests
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# --- Admin credentials (set in .env) ---
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

# --- Infobip config (set in .env) ---
INFOBIP_API_KEY = os.environ.get("INFOBIP_API_KEY", "")
INFOBIP_BASE_URL = os.environ.get("INFOBIP_BASE_URL", "")  # e.g. xxxxx.api.infobip.com
INFOBIP_SENDER = os.environ.get("INFOBIP_SENDER", "")      # registered WhatsApp sender number
TO_WHATSAPP = os.environ.get("TO_WHATSAPP", "")            # recipient number (digits only, no +)

# Global state (POC only – not safe for concurrent users)
latest_message = None


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # Constant-time comparison to prevent timing-based attacks
        user_ok = hmac.compare_digest(username, ADMIN_USERNAME)
        pass_ok = hmac.compare_digest(password, ADMIN_PASSWORD)
        if user_ok and pass_ok:
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Main routes (protected)
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    global latest_message
    preview = None
    error = None

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            error = "Please upload an Excel file."
            return render_template("index.html", error=error)

        selected_class = request.form.get("class", "").strip()
        selected_date = request.form.get("date", "").strip() or str(date.today())
        
        # Store last values in session for form persistence
        session["last_class"] = selected_class
        session["last_date"] = selected_date

        try:
            # Read all sheets and concatenate them
            all_sheets = pd.read_excel(file, sheet_name=None, header=None)
            raw = pd.concat(all_sheets.values(), ignore_index=True)
        except Exception as e:
            return render_template("index.html", error=f"Could not read Excel file: {e}")

        # Keywords used to identify each canonical column
        COLUMN_KEYWORDS = {
            "date":       ["data", "date", "datum"],
            "class":      ["grupa", "group", "class", "klasa", "oddział", "oddzial"],
            "subject":    ["przedmiot", "subject", "lekcja", "lesson", "course", "nazwa"],
            "start_time": ["godzina", "start_time", "start time", "time", "godz", "hour", "czas"],
            "room":       ["miejsce", "room", "sala", "classroom", "location"],
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
            return render_template(
                "index.html",
                error="Could not find a header row in the uploaded file. "
                      "Expected columns like: Data, Grupa, Godzina zajęć, Przedmiot, Miejsce odbywania zajęć.",
            )

        df = raw.iloc[header_row + 1:].copy()
        df.columns = [str(v).lower().strip() for v in raw.iloc[header_row]]
        df = df.reset_index(drop=True)

        # Auto-detect columns by keyword matching
        col_map = {}  # canonical → actual column name in df
        for canonical, keywords in COLUMN_KEYWORDS.items():
            for col in df.columns:
                if any(kw in col for kw in keywords):
                    col_map[canonical] = col
                    break

        missing = set(COLUMN_KEYWORDS.keys()) - set(col_map.keys())
        if missing:
            detected = ", ".join(f"{v!r}→{k}" for k, v in col_map.items()) or "none"
            return render_template(
                "index.html",
                error=(
                    f"Could not find columns: {', '.join(sorted(missing))}. "
                    f"Detected: {detected}. "
                    f"Available columns: {', '.join(df.columns.tolist())}."
                ),
            )

        # Rename to canonical names so the rest of the code stays unchanged
        df = df.rename(columns={v: k for k, v in col_map.items()})

        # Normalize date column
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
        
        # Treat empty class cells as empty strings
        df["class"] = df["class"].astype(str).fillna("").str.strip()

        # Filter by class and date
        if selected_class:
            # If a specific class is selected, filter by that class
            df_filtered = df[
                (df["class"].astype(str) == selected_class) & (df["date"] == selected_date)
            ]
        else:
            # If no class is selected, fetch all rows for the selected date
            df_filtered = df[df["date"] == selected_date]
            
            # Group by class for display
            if df_filtered.empty:
                error = f"No lessons found on {selected_date}."
                latest_message = None
                return render_template("index.html", error=error)
            
            # Build message showing all classes
            lines = [f"Schedule for {selected_date}:"]
            for class_name in df_filtered["class"].unique():
                class_data = df_filtered[df_filtered["class"] == class_name]
                if class_name:
                    lines.append(f"\nClass {class_name}:")
                else:
                    lines.append(f"\nNo class specified:")
                for _, row in class_data.iterrows():
                    lines.append(f"  {row['start_time']} - {row['subject']} (room {row['room']})")
            
            latest_message = "\n".join(lines)
            preview = latest_message
            return render_template("index.html", preview=preview, error=error)

        if df_filtered.empty:
            error = f"No lessons found for class {selected_class} on {selected_date}."
            latest_message = None
            return render_template("index.html", error=error)

        lines = [f"Schedule for class {selected_class} on {selected_date}:"]
        for _, row in df_filtered.iterrows():
            lines.append(f"{row['start_time']} - {row['subject']} (room {row['room']})")

        latest_message = "\n".join(lines)
        preview = latest_message

    return render_template("index.html", preview=preview, error=error)


@app.route("/send", methods=["POST"])
@login_required
def send():
    global latest_message
    if not latest_message:
        return "No message to send. Please generate a preview first.", 400

    url = f"https://{INFOBIP_BASE_URL}/whatsapp/1/message/text"
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "from": INFOBIP_SENDER,
        "to": TO_WHATSAPP,
        "content": {"text": latest_message},
    }

    try:
        resp = http_requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
    except http_requests.exceptions.HTTPError:
        return f"Infobip API error {resp.status_code}: {resp.text}", 500
    except Exception as e:
        return f"Failed to send message: {e}", 500

    return "Message sent successfully via WhatsApp (Infobip)!", 200


if __name__ == "__main__":
    app.run(debug=True)
