import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from db_setup import run_db_setup
from services.student_service import AuthService
from ui.views.login_view import LoginView
from ui.views.main_window import MainWindow
from ui.views.register_view import RegisterView
from utils.session import clear_session, load_session, save_session


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_stylesheet(app):
    """Tải tệp định dạng (stylesheet) chung của ứng dụng."""
    style_path = os.path.join(os.path.dirname(__file__), "ui", "resources", "style.qss")
    if not os.path.exists(style_path):
        return

    with open(style_path, "r", encoding="utf-8") as stylesheet_file:
        app.setStyleSheet(stylesheet_file.read())


class DormManagerApp:
    def __init__(self):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)
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
        """Hiển thị cửa sổ đăng ký tài khoản."""
        self.login_view.hide()
        self.register_view.show()
        self.register_view.raise_()
        self.register_view.activateWindow()

    def show_login_from_register(self):
        """Quay lại cửa sổ đăng nhập từ cửa sổ đăng ký."""
        self.register_view.hide()
        self.login_view.show()
        self.login_view.raise_()
        self.login_view.activateWindow()

    def show_main_window(self, user_or_id):
        """Mở cửa sổ chính của ứng dụng cho người dùng tương ứng."""
        user = self._resolve_user(user_or_id)
        if not user:
            QMessageBox.critical(
                self.register_view if self.register_view.isVisible() else self.login_view,
                "Không thể mở hệ thống",
                "Không tải được thông tin tài khoản sau khi đăng nhập hoặc đăng ký.",
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
        """Quay lại cửa sổ đăng nhập và xóa phiên làm việc hiện tại."""
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
    """Kiểm tra kết nối cơ sở dữ liệu trước khi ứng dụng bắt đầu."""
    try:
        from sqlalchemy import text

        from config.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"Lỗi kết nối cơ sở dữ liệu: {exc}")
        return False


if __name__ == "__main__":
    run_db_setup()

    app = DormManagerApp()

    if not check_db_connection():
        print("Cảnh báo: Không thể kết nối tới cơ sở dữ liệu.")
        print("Vui lòng chạy 'python db_setup.py' trước khi khởi chạy ứng dụng.")

    app.run()
