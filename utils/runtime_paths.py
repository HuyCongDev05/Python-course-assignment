import os
import sys

from dotenv import load_dotenv


APP_NAME = "DormManager"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_frozen_app():
    return bool(getattr(sys, "frozen", False))


def bundle_dir():
    return getattr(sys, "_MEIPASS", PROJECT_ROOT)


def app_dir():
    if is_frozen_app():
        return os.path.dirname(os.path.abspath(sys.executable))
    return PROJECT_ROOT


def resource_path(*parts):
    return os.path.join(bundle_dir(), *parts)


def project_path(*parts):
    return os.path.join(PROJECT_ROOT, *parts)


def user_data_dir():
    root_dir = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if root_dir:
        return os.path.join(root_dir, APP_NAME)
    return os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")


def user_data_path(*parts):
    return os.path.join(user_data_dir(), *parts)


def _existing_unique_paths(paths):
    seen = set()
    unique_paths = []
    for path in paths:
        normalized_path = os.path.abspath(path)
        if normalized_path in seen or not os.path.isfile(normalized_path):
            continue
        seen.add(normalized_path)
        unique_paths.append(normalized_path)
    return unique_paths


def load_app_env():
    candidates = _existing_unique_paths(
        [
            os.path.join(app_dir(), ".env"),
            project_path(".env"),
            os.path.join(os.getcwd(), ".env"),
            resource_path(".env"),
        ]
    )
    for env_file in candidates:
        load_dotenv(env_file, override=False)
    return candidates
