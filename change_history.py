"""Change history tracking for schedule updates"""
import json
import os
from datetime import datetime


class ScheduleChangeTracker:
    def __init__(self, history_file="change_history.json"):
        self.history_file = history_file
        self.changes_list = self._load_changes()

    def _load_changes(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_changes(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.changes_list, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _norm(v):
        """Normalize a value to a clean string for comparison."""
        s = str(v).strip() if v is not None else ""
        return "" if s.lower() in ("nan", "none", "nat", "<na>", "nat") else s

    def compare_schedules(self, old_df, new_df):
        """Compare old and new schedules, detecting additions, removals, and field changes."""
        if old_df is None:
            return {"additions": [], "removals": [], "modifications": []}

        def make_identity(row):
            return (self._norm(row.get("date")), self._norm(row.get("class")), self._norm(row.get("subject")))

        def make_full(row):
            return (
                self._norm(row.get("start_time")),
                self._norm(row.get("room")),
                self._norm(row.get("instructor", "")),
            )

        def row_to_dict(r):
            return {
                "date": self._norm(r.get("date")),
                "class": self._norm(r.get("class")),
                "subject": self._norm(r.get("subject")),
                "room": self._norm(r.get("room")),
                "start_time": self._norm(r.get("start_time")),
            }

        old_records = old_df.to_dict('records')
        new_records = new_df.to_dict('records')

        # Build identity lookup (first occurrence wins)
        old_by_id = {}
        for r in old_records:
            ikey = make_identity(r)
            if ikey not in old_by_id:
                old_by_id[ikey] = r

        new_by_id = {}
        for r in new_records:
            ikey = make_identity(r)
            if ikey not in new_by_id:
                new_by_id[ikey] = r

        old_id_set = set(old_by_id.keys())
        new_id_set = set(new_by_id.keys())

        added_ids = new_id_set - old_id_set
        removed_ids = old_id_set - new_id_set
        common_ids = old_id_set & new_id_set

        additions = [row_to_dict(new_by_id[k]) for k in added_ids]
        removals = [row_to_dict(old_by_id[k]) for k in removed_ids]

        # Detect field-level modifications among common rows
        field_labels = [
            ("start_time", "Godzina"),
            ("room", "Sala"),
            ("instructor", "Prowadzący"),
        ]
        modifications = []
        for ikey in common_ids:
            old_r = old_by_id[ikey]
            new_r = new_by_id[ikey]
            if make_full(old_r) != make_full(new_r):
                for field, label in field_labels:
                    old_val = self._norm(old_r.get(field, ""))
                    new_val = self._norm(new_r.get(field, ""))
                    if old_val != new_val:
                        modifications.append({
                            "date": self._norm(new_r.get("date")),
                            "class": self._norm(new_r.get("class")),
                            "subject": self._norm(new_r.get("subject")),
                            "field": label,
                            "old_value": old_val,
                            "new_value": new_val,
                        })

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        change_entry = {
            "timestamp": timestamp,
            "additions_count": len(additions),
            "removals_count": len(removals),
            "modifications_count": len(modifications),
            "additions": additions[:100],
            "removals": removals[:100],
            "modifications": modifications[:100],
        }

        self.changes_list.insert(0, change_entry)
        self.changes_list = self.changes_list[:50]
        self._save_changes()
        return change_entry

    def get_recent_changes(self, limit=5):
        return self.changes_list[:limit]

    def get_changes_for_display(self):
        """Return up to 5 most recent entries that have any changes."""
        result = []
        for entry in self.changes_list:
            # Backfill keys missing from old-format entries
            entry.setdefault("modifications_count", 0)
            entry.setdefault("modifications", [])
            entry.setdefault("additions", [])
            entry.setdefault("removals", [])
            entry.setdefault("additions_count", len(entry["additions"]))
            entry.setdefault("removals_count", len(entry["removals"]))
            total = (entry["additions_count"]
                     + entry["removals_count"]
                     + entry["modifications_count"])
            if total > 0:
                result.append(entry)
                if len(result) >= 5:
                    break
        return result if result else None

    def __init__(self, history_file="change_history.json"):
        self.history_file = history_file
        self.changes_list = self._load_changes()
    
    def _load_changes(self):
        """Load existing changes from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_changes(self):
        """Save changes to file"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.changes_list, f, ensure_ascii=False, indent=2)
    
    def compare_schedules(self, old_df, new_df):
        """Compare old and new schedule dataframes and track changes"""
        if old_df is None:
            # First time - no previous data
            return {"additions": [], "removals": []}
        
        # Create comparable keys (date, class, subject)
        def make_key(row):
            return (row["date"], row["class"], row["subject"])

        old_keys = set(old_df.apply(make_key, axis=1))
        new_keys = set(new_df.apply(make_key, axis=1))
        
        # Find additions and removals
        added_keys = new_keys - old_keys
        removed_keys = old_keys - new_keys
        
        # Convert back to records
        additions = new_df[new_df.apply(make_key, axis=1).isin(added_keys)].to_dict('records')
        removals = old_df[old_df.apply(make_key, axis=1).isin(removed_keys)].to_dict('records')
        
        # Store in history
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        change_entry = {
            "timestamp": timestamp,
            "additions_count": len(additions),
            "removals_count": len(removals),
            "additions": [
                {
                    "date": str(r.get("date", "")),
                    "class": str(r.get("class", "")),
                    "subject": str(r.get("subject", "")),
                    "room": str(r.get("room", "")),
                    "start_time": str(r.get("start_time", ""))
                }
                for r in additions[:100]  # Limit to last 100 changes
            ],
            "removals": [
                {
                    "date": str(r.get("date", "")),
                    "class": str(r.get("class", "")),
                    "subject": str(r.get("subject", "")),
                    "room": str(r.get("room", "")),
                    "start_time": str(r.get("start_time", ""))
                }
                for r in removals[:100]
            ]
        }
        
        # Add to history list (keep last 50 updates)
        self.changes_list.insert(0, change_entry)
        self.changes_list = self.changes_list[:50]
        self._save_changes()
        
        return {
            "additions": additions,
            "removals": removals,
            "timestamp": timestamp
        }
    
    def get_recent_changes(self, limit=5):
        """Get recent changes"""
        return self.changes_list[:limit]
    
    def get_changes_for_display(self):
        """Get most recent change entry that actually has changes"""
        if not self.changes_list:
            return None
        
        for entry in self.changes_list:
            if entry["additions_count"] > 0 or entry["removals_count"] > 0:
                return {
                    "timestamp": entry["timestamp"],
                    "additions_count": entry["additions_count"],
                    "removals_count": entry["removals_count"],
                    "additions": entry["additions"],
                    "removals": entry["removals"]
                }
        return None
