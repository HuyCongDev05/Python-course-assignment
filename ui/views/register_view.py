from PyQt5.QtCore import pyqtSignal
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

from services.student_service import StudentService
from ui.widgets.password_line_edit import PasswordLineEdit


class RegisterView(QWidget):
    register_success = pyqtSignal(object)
    back_to_login = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.student_service = StudentService()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Đăng ký tài khoản sinh viên | DormManager")
        self.resize(1040, 680)
        self.setObjectName("AuthWindow")

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("AuthHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(32, 32, 32, 32)
        hero_layout.setSpacing(14)

        brand = QLabel("Cổng kích hoạt tài khoản")
        brand.setObjectName("AuthBrand")
        title = QLabel("Tạo tài khoản và bắt đầu sử dụng hệ thống.")
        title.setObjectName("AuthTitle")
        title.setWordWrap(True)
        desc = QLabel(
            "Sau khi hoàn tất đăng ký, tài khoản sẽ được liên kết với hồ sơ sinh viên và chuyển thẳng vào không gian làm việc cá nhân."
        )
        desc.setObjectName("AuthSubtitle")
        desc.setWordWrap(True)

        info_1 = QLabel("Mã sinh viên cần thuộc danh mục hồ sơ hợp lệ trong hệ thống.")
        info_2 = QLabel("Phòng ở được lựa chọn sau khi đăng nhập, ngay trong ứng dụng.")
        info_3 = QLabel("Thông tin lưu trú và thanh toán sẽ hiển thị theo tài khoản đã kích hoạt.")
        for item in (info_1, info_2, info_3):
            item.setObjectName("AuthBullet")

        hero_layout.addWidget(brand)
        hero_layout.addStretch()
        hero_layout.addWidget(title)
        hero_layout.addWidget(desc)
        hero_layout.addSpacing(8)
        hero_layout.addWidget(info_1)
        hero_layout.addWidget(info_2)
        hero_layout.addWidget(info_3)
        hero_layout.addStretch()

        form_shell = QFrame()
        form_shell.setObjectName("AuthCard")
        form_layout = QVBoxLayout(form_shell)
        form_layout.setContentsMargins(34, 34, 34, 34)
        form_layout.setSpacing(16)

        title_form = QLabel("Tạo tài khoản sinh viên")
        title_form.setObjectName("FormTitle")
        subtitle_form = QLabel("Nhập thông tin tài khoản để kích hoạt hồ sơ và truy cập hệ thống.")
        subtitle_form.setObjectName("FormSubtitle")
        subtitle_form.setWordWrap(True)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Tên đăng nhập mới, 4-24 ký tự")

        self.password_input = PasswordLineEdit()
        self.password_input.setPlaceholderText("Mật khẩu tối thiểu 8 ký tự")

        self.student_id_input = QLineEdit()
        self.student_id_input.setPlaceholderText("Mã sinh viên, ví dụ SV001")
        self.student_id_input.returnPressed.connect(self.handle_register)

        self.register_btn = QPushButton("Hoàn tất đăng ký")
        self.register_btn.setObjectName("PrimaryButton")
        self.register_btn.clicked.connect(self.handle_register)

        self.back_btn = QPushButton("Quay lại đăng nhập")
        self.back_btn.setObjectName("SecondaryButton")
        self.back_btn.clicked.connect(self.back_to_login.emit)

        form_layout.addWidget(title_form)
        form_layout.addWidget(subtitle_form)
        form_layout.addSpacing(8)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.student_id_input)
        form_layout.addSpacing(8)
        form_layout.addWidget(self.register_btn)
        form_layout.addWidget(self.back_btn)
        form_layout.addStretch()

        root.addWidget(hero, 7)
        root.addWidget(form_shell, 5)

    def handle_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        student_code = self.student_id_input.text().strip()

        success, message, user = self.student_service.register_student(username, password, student_code)
        if success and user:
            QMessageBox.information(self, "Đăng ký thành công", message)
            self.username_input.clear()
            self.password_input.clear()
            self.student_id_input.clear()
            self.register_success.emit(user)  # emit toàn bộ user object, không dùng user.id
            return

        if message.startswith("Lỗi:"):
            QMessageBox.critical(self, "Đăng ký thất bại", message)
        else:
            QMessageBox.warning(self, "Thông tin chưa hợp lệ", message)
