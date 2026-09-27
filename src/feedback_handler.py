"""
feedback_handler.py

Handles loading and saving of feedback for all roles.
Data is stored in data/feedback.json
"""
import os
import json
from datetime import datetime

FEEDBACK_FILE = "data/feedback.json"

def load_feedback() -> list:
    """Loads all feedback from the JSON file."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_feedback(usn: str, role: str, rating: int, comment: str, subject: str = "General"):
    """Saves a new piece of feedback to the JSON file."""
    all_feedback = load_feedback()
    
    new_entry = {
        "id": f"{usn}_{datetime.now().isoformat()}",
        "usn": usn,
        "role": role,
        "rating": rating,
        "comment": comment,
        "subject": subject,
        "timestamp": datetime.now().isoformat()
    }
    
    all_feedback.append(new_entry)
    
    try:
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(all_feedback, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return False
