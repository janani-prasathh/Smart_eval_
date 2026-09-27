import json, os

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def format_timestamp(ts, fmt="%Y-%m-%d %H:%M:%S"):
    """Format a datetime object or timestamp (int/float) to a string."""
    from datetime import datetime
    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts)
    elif isinstance(ts, datetime):
        dt = ts
    else:
        raise TypeError("ts must be a datetime object or a timestamp (int/float)")
    return dt.strftime(fmt)
