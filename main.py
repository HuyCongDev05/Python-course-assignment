import os
import sys

# Monkey patch sua loi "is not a generic class" tren Python 3.11 Beta
try:
    import typing_extensions

    orig_check_generic = typing_extensions._check_generic

    def patched_check_generic(cls, params, elen):
        try:
            return orig_check_generic(cls, params, elen)
        except TypeError as exc:
            if "is not a generic class" in str(exc):
                return
            raise

    typing_extensions._check_generic = patched_check_generic
except ImportError:
    pass


if sys.platform == "win32":
    import ctypes

    myappid = "dormmanager.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from db_setup import run_db_setup
from services.student_service import AuthService
from ui.views.login_view import LoginView
from ui.views.main_window import MainWindow
from ui.views.register_view import RegisterView
from utils.runtime_paths import load_app_env, resource_path
from utils.session import clear_session, load_session, save_session


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_app_env()


def load_stylesheet(app):
    style_path = resource_path("ui", "resources", "style.qss")
    if not os.path.exists(style_path):
        return

    with open(style_path, "r", encoding="utf-8") as stylesheet_file:
        app.setStyleSheet(stylesheet_file.read())


class DormManagerApp:
    def __init__(self):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)

        icon_path = resource_path("ui", "resources", "icons", "logo.jpg")
        self.app.setWindowIcon(QIcon(icon_path))

        self.app.setStyle("Fusion")
        load_stylesheet(self.app)

        self.login_view = LoginView()
        self.register_view = RegisterView()
        self.auth_service = AuthService()
        self.main_window = None

        self.login_view.login_success.connect(self.show_main_window)
        self.login_view.register_requested.connect(self.show_register_view)
        self.register_view.register_success.connect(self.show_main_window)
        self.register_view.back_to_login.connect(self.show_login_from_register)

        user_id = load_session()
        if user_id and self._resolve_user(user_id):
            self.show_main_window(user_id)
            return

        self.login_view.show()

    def _resolve_user(self, user_or_id):
        user_id = getattr(user_or_id, "id", user_or_id)
        if user_id is None:
            return None
        return self.auth_service.get_user_by_id(user_id)

    def show_register_view(self):
        self.login_view.hide()
        self.register_view.show()
        self.register_view.raise_()
        self.register_view.activateWindow()

    def show_login_from_register(self):
        self.register_view.hide()
        self.login_view.show()
        self.login_view.raise_()
        self.login_view.activateWindow()

    def show_main_window(self, user_or_id):
        from models import User as UserModel

        if isinstance(user_or_id, UserModel):
            user = user_or_id
        else:
            user = self._resolve_user(user_or_id)

        if not user:
            QMessageBox.critical(
                self.register_view if self.register_view.isVisible() else self.login_view,
                "Khong the mo he thong",
                "Khong tai duoc thong tin tai khoan sau khi dang nhap hoac dang ky.",
            )
            return

        save_session(user.id)

        if self.main_window:
            self.main_window.close()

        self.main_window = MainWindow(user)
        self.main_window.logout_signal.connect(self.show_login_view)

        self.login_view.hide()
        self.register_view.hide()
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def show_login_view(self):
        clear_session()

        if self.main_window:
            self.main_window.hide()
            self.main_window = None

        self.login_view.show()
        self.login_view.raise_()
        self.login_view.activateWindow()

    def run(self):
        sys.exit(self.app.exec_())


def check_db_connection():
    try:
        from sqlalchemy import text

        from config.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"Loi ket noi co so du lieu: {exc}")
        return False


if __name__ == "__main__":
    if not check_db_connection():
        run_db_setup()

    app = DormManagerApp()

    if not check_db_connection():
        print("Canh bao: Khong the ket noi toi co so du lieu.")
        print("Vui long chay 'python db_setup.py' truoc khi khoi chay ung dung.")

    app.run()
