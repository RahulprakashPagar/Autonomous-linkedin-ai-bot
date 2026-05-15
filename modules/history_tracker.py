import json
from pathlib import Path

FILE = "post_history.json"

def load_history() -> dict:
    if Path(FILE).exists():
        with open(FILE) as f:
            return json.load(f)
    return {"posts": []}

def save_post(entry: dict):
    h = load_history()
    h["posts"].append(entry)
    with open(FILE, "w") as f:
        json.dump(h, f, indent=2)
