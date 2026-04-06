import json
import os

SESSION_FILE = "session.json"

def save_session(user_id):
    """Lưu ID người dùng vào file session"""
    with open(SESSION_FILE, "w") as f:
        json.dump({"user_id": user_id}, f)

def load_session():
    """Tải ID người dùng từ file session nếu tồn tại"""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                return data.get("user_id")
        except:
            return None
    return None

def clear_session():
    """Xóa file session khi đăng xuất"""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
