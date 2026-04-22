from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from models import UserRole
from services.data_exchange_service import DataExchangeService
from ui.widgets.searchable_combo_box import style_combo_popups
from utils.app_settings import get_export_directory, set_export_directory


class ExportView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.is_admin_mode = bool(user and user.role == UserRole.ADMIN)
        self.exchange_service = DataExchangeService()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        header = QFrame()
        header.setObjectName("HeroPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)

        title_wrap = QVBoxLayout()
        title = QLabel("Xuất file dữ liệu")
        title.setObjectName("HeroTitle")
        subtitle = QLabel(
            "Xuất nhanh dữ liệu sinh viên hoặc phòng ra file Excel. Thư mục lưu sẽ được ghi nhớ cho tới khi bạn đổi lại."
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        self.btn_export = QPushButton("Xuất file")
        self.btn_export.setObjectName("PrimaryButton")
        self.btn_export.clicked.connect(self.export_data)

        header_layout.addLayout(title_wrap, 1)
        header_layout.addWidget(self.btn_export, 0)
        layout.addWidget(header)

        if not self.is_admin_mode:
            notice = QLabel("Chức năng này chỉ dành cho quản trị viên.")
            notice.setAlignment(Qt.AlignCenter)
            notice.setObjectName("HeroSubtitle")
            layout.addWidget(notice)
            layout.addStretch()
            self.btn_export.hide()
            return

        form_card = QFrame()
        form_card.setObjectName("HeroPanel")
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(20)

        self.export_type = QComboBox()
        style_combo_popups(self.export_type)
        self.export_type.addItem("Sinh viên", "students")
        self.export_type.addItem("Phòng", "rooms")

        self.directory_label = QLabel()
        self.directory_label.setWordWrap(True)
        self.directory_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.btn_change_directory = QPushButton("Đổi vị trí lưu")
        self.btn_change_directory.clicked.connect(self.change_export_directory)

        form_layout.addRow("Loại dữ liệu", self.export_type)
        form_layout.addRow("Thư mục hiện tại", self.directory_label)
        form_layout.addRow("", self.btn_change_directory)
        layout.addWidget(form_card)

        tips_card = QFrame()
        tips_card.setObjectName("HeroPanel")
        tips_layout = QVBoxLayout(tips_card)
        tips_layout.setContentsMargins(24, 24, 24, 24)
        tips_layout.setSpacing(12)

        tips_title = QLabel("Định dạng file dùng để nhập lại")
        tips_title.setObjectName("DialogTitle")
        tips_layout.addWidget(tips_title)

        student_tip = QLabel("Sinh viên: Mã sinh viên, Họ và tên, Giới tính, Số điện thoại, Email, Quê quán.")
        room_tip = QLabel("Phòng: Số phòng, Phân loại, Sức chứa, Đang ở, Giá thuê/tháng, Trạng thái.")
        for label in (student_tip, room_tip):
            label.setWordWrap(True)
            label.setObjectName("HeroSubtitle")
            tips_layout.addWidget(label)

        self.path_chip = QLabel()
        self.path_chip.setObjectName("InfoChip")
        self.path_chip.setAlignment(Qt.AlignCenter)
        self.path_chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        tips_layout.addWidget(self.path_chip, 0, Qt.AlignLeft)

        layout.addWidget(tips_card)
        layout.addStretch()
        self.refresh_directory_labels()

    def refresh_directory_labels(self):
        if not self.is_admin_mode or not hasattr(self, "directory_label"):
            return
        current_directory = get_export_directory()
        self.directory_label.setText(current_directory)
        self.path_chip.setText("Đã ghi nhớ vị trí lưu")

    def change_export_directory(self):
        current_directory = get_export_directory()
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file xuất", current_directory)
        if not directory:
            return
        set_export_directory(directory)
        self.refresh_directory_labels()

    def export_data(self):
        if not self.is_admin_mode:
            QMessageBox.warning(self, "Không có quyền", "Chỉ quản trị viên mới được phép xuất dữ liệu.")
            return

        current_directory = get_export_directory()
        if not current_directory:
            self.change_export_directory()
            current_directory = get_export_directory()

        try:
            export_type = self.export_type.currentData()
            if export_type == "students":
                file_path = self.exchange_service.export_students_to_excel(current_directory)
            else:
                file_path = self.exchange_service.export_rooms_to_excel(current_directory)

            self.refresh_directory_labels()
            QMessageBox.information(
                self,
                "Xuất file thành công",
                f"Đã xuất dữ liệu vào:\n{file_path}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Không thể xuất file", str(exc))
