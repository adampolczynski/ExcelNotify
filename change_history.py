"""Change history tracking for schedule updates"""
import json
import os
from datetime import datetime
from pathlib import Path


class ScheduleChangeTracker:
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

        # Exclude rows with no group (meant for all students - not group-specific changes)
        old_df = old_df[old_df["class"].astype(str).str.strip() != ""]
        new_df = new_df[new_df["class"].astype(str).str.strip() != ""]

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
