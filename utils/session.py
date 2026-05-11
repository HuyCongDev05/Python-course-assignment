import json
import os

from utils.runtime_paths import app_dir, project_path, user_data_path


SESSION_FILE = user_data_path("session.json")
LEGACY_SESSION_FILES = [
    os.path.join(app_dir(), "session.json"),
    project_path("session.json"),
]


def _ensure_session_parent():
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)


def save_session(user_id):
    _ensure_session_parent()
    with open(SESSION_FILE, "w", encoding="utf-8") as session_file:
        json.dump({"user_id": user_id}, session_file)


def _load_session_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as session_file:
            data = json.load(session_file)
            return data.get("user_id")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def load_session():
    if os.path.exists(SESSION_FILE):
        return _load_session_file(SESSION_FILE)

    for legacy_file in LEGACY_SESSION_FILES:
        if os.path.exists(legacy_file):
            return _load_session_file(legacy_file)
    return None


def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
        return

    for legacy_file in LEGACY_SESSION_FILES:
        if os.path.exists(legacy_file):
            os.remove(legacy_file)
