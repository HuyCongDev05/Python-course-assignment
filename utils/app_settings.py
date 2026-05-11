import json
import os

from utils.runtime_paths import project_path, user_data_path


SETTINGS_FILE = user_data_path("config", "app_settings.json")
LEGACY_SETTINGS_FILE = project_path("config", "app_settings.json")


def _ensure_settings_parent():
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)


def _read_settings_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as settings_file:
            data = json.load(settings_file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_app_settings():
    if os.path.exists(SETTINGS_FILE):
        return _read_settings_file(SETTINGS_FILE)
    if os.path.exists(LEGACY_SETTINGS_FILE):
        return _read_settings_file(LEGACY_SETTINGS_FILE)
    return {}


def save_app_settings(settings):
    _ensure_settings_parent()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, ensure_ascii=False, indent=2)


def get_default_export_directory():
    documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
    if os.path.isdir(documents_dir):
        return documents_dir
    return os.getcwd()


def get_export_directory():
    settings = load_app_settings()
    export_directory = settings.get("export_directory")
    if export_directory:
        return export_directory
    return get_default_export_directory()


def set_export_directory(path):
    settings = load_app_settings()
    settings["export_directory"] = os.path.abspath(path)
    save_app_settings(settings)
