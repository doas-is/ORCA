# helper functions for env, json handling, timestamps, small text helpers
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urlparse

load_dotenv()

def get_env_var(name, default=None):
    return os.getenv(name, default)

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def current_timestamp():
    return datetime.utcnow().isoformat()

def normalize_url(url):
    # small helper to canonicalize url for dedup
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
        return f"{scheme}://{netloc}{path}"
    except:
        return url # note : we ain't implementing dedup for now 

def safe_truncate(text, length=1000):
    if not text:
        return ""
    return text if len(text) <= length else text[:length] + "..."
