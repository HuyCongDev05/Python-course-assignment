from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ui.widgets.searchable_combo_box import style_combo_popups


class StudentDialog(QDialog):
    def __init__(self, parent=None, student=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.student = student
        self.action = "save"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Thông tin sinh viên")
        self.setFixedSize(500, 520)
        self.setObjectName("EntityDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)

        header = QFrame()
        header.setObjectName("DialogHero")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        header_layout.setSpacing(4)
        title = QLabel("Hồ sơ sinh viên")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Quản lý thông tin cá nhân, liên hệ và quê quán.")
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 4, 0, 4)
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(22)
        form_layout.setFormAlignment(Qt.AlignTop)

        self.sid_input = QLineEdit()
        self.sid_input.setPlaceholderText("Ví dụ: SV20345")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập họ và tên")

        self.gender_combo = QComboBox()
        style_combo_popups(self.gender_combo)
        self.gender_combo.addItems(["Nam", "Nữ", "Khác"])

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Số điện thoại")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email sinh viên")

        self.hometown_input = QLineEdit()
        self.hometown_input.setPlaceholderText("Quê quán")

        form_layout.addRow("Mã sinh viên", self.sid_input)
        form_layout.addRow("Họ và tên", self.name_input)
        form_layout.addRow("Giới tính", self.gender_combo)
        form_layout.addRow("Số điện thoại", self.phone_input)
        form_layout.addRow("Email", self.email_input)
        form_layout.addRow("Quê quán", self.hometown_input)
        layout.addLayout(form_layout)

        actions = QHBoxLayout()
        if self.student:
            btn_delete = QPushButton("Xóa hồ sơ")
            btn_delete.setObjectName("DangerButton")
            btn_delete.clicked.connect(self.handle_delete)
            actions.addWidget(btn_delete)
        actions.addStretch()

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Lưu thông tin")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_save)
        layout.addLayout(actions)

        if self.student:
            self.sid_input.setText(self.student.student_id)
            self.name_input.setText(self.student.full_name)
            self.phone_input.setText(self.student.phone or "")
            self.email_input.setText(self.student.email or "")
            self.hometown_input.setText(self.student.hometown or "")
            index = self.gender_combo.findText(self.student.gender or "Nam")
            if index >= 0:
                self.gender_combo.setCurrentIndex(index)

    def get_data(self):
        return {
            "student_id": self.sid_input.text(),
            "full_name": self.name_input.text(),
            "gender": self.gender_combo.currentText(),
            "phone": self.phone_input.text(),
            "email": self.email_input.text(),
            "hometown": self.hometown_input.text(),
        }

    def validate(self):
        if not self.sid_input.text().strip() or not self.name_input.text().strip():
            QMessageBox.warning(self, "Thiếu dữ liệu", "Mã sinh viên và họ tên không được để trống.")
            return False
        return True

    def accept(self):
        if self.validate():
            self.action = "save"
            super().accept()

    def handle_delete(self):
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            "Xóa sinh viên này khỏi hệ thống?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.action = "delete"
            self.done(QDialog.Accepted)
