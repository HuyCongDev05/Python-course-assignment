from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.student_service import AuthService
from ui.widgets.password_line_edit import PasswordLineEdit


class LoginView(QWidget):
    login_success = pyqtSignal(object)
    register_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.auth_service = AuthService()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Đăng nhập | DormManager")
        self.resize(980, 620)
        self.setObjectName("AuthWindow")

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("AuthHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(32, 32, 32, 32)
        hero_layout.setSpacing(14)

        brand = QLabel("DormManager")
        brand.setObjectName("AuthBrand")
        title = QLabel("Nền tảng quản lý vận hành ký túc xá tập trung.")
        title.setObjectName("AuthTitle")
        title.setWordWrap(True)
        desc = QLabel(
            "Hỗ trợ quản trị lưu trú, hợp đồng và thanh toán trên một hệ thống thống nhất cho ban quản lý, nhân viên và sinh viên."
        )
        desc.setObjectName("AuthSubtitle")
        desc.setWordWrap(True)

        bullet_1 = QLabel("Giám sát công suất phòng và tình trạng sử dụng theo dữ liệu cập nhật.")
        bullet_2 = QLabel("Theo dõi hợp đồng lưu trú, công nợ và lịch sử thanh toán trong cùng một quy trình.")
        bullet_3 = QLabel("Chuẩn hóa thao tác vận hành hằng ngày với giao diện rõ ràng và nhất quán.")
        for bullet in [bullet_1, bullet_2, bullet_3]:
            bullet.setObjectName("AuthBullet")

        hero_layout.addWidget(brand)
        hero_layout.addStretch()
        hero_layout.addWidget(title)
        hero_layout.addWidget(desc)
        hero_layout.addSpacing(8)
        hero_layout.addWidget(bullet_1)
        hero_layout.addWidget(bullet_2)
        hero_layout.addWidget(bullet_3)
        hero_layout.addStretch()

        form_shell = QFrame()
        form_shell.setObjectName("AuthCard")
        form_layout = QVBoxLayout(form_shell)
        form_layout.setContentsMargins(34, 34, 34, 34)
        form_layout.setSpacing(16)

        welcome = QLabel("Đăng nhập")
        welcome.setObjectName("FormTitle")
        welcome_hint = QLabel("Đăng nhập để sử dụng hệ thống.")
        welcome_hint.setObjectName("FormSubtitle")
        welcome_hint.setWordWrap(True)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Tên đăng nhập")
        self.username_input.setObjectName("AuthInput")

        self.password_input = PasswordLineEdit()
        self.password_input.setPlaceholderText("Mật khẩu")
        self.password_input.setObjectName("AuthInput")
        self.password_input.returnPressed.connect(self.handle_login)

        self.login_btn = QPushButton("Đăng nhập vào hệ thống")
        self.login_btn.setObjectName("PrimaryButton")
        self.login_btn.clicked.connect(self.handle_login)

        self.register_btn = QPushButton("Chưa có tài khoản? Tạo tài khoản ngay")
        self.register_btn.setObjectName("SecondaryButton")
        self.register_btn.clicked.connect(self.register_requested.emit)

        form_layout.addWidget(welcome)
        form_layout.addWidget(welcome_hint)
        form_layout.addSpacing(8)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.login_btn)
        form_layout.addWidget(self.register_btn)
        form_layout.addStretch()

        root.addWidget(hero, 7)
        root.addWidget(form_shell, 5)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            return

        user = self.auth_service.login(username, password)
        if user:
            self.login_success.emit(user)
            return

        QMessageBox.critical(self, "Đăng nhập thất bại", "Tên đăng nhập hoặc mật khẩu không đúng.")
