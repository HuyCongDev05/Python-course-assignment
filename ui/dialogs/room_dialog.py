from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from models import RoomStatus
from ui.widgets.searchable_combo_box import style_combo_popups


class RoomDialog(QDialog):
    def __init__(self, parent=None, room=None):
        super().__init__(parent)
        self.room = room
        self.action = "save"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Thông tin phòng")
        self.setFixedSize(480, 490)
        self.setObjectName("EntityDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)

        header = QFrame()
        header.setObjectName("DialogHero")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel("Thiết lập phòng ở")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Cập nhật sức chứa, phân loại và đơn giá thuê hàng tháng.")
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

        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("Ví dụ: B-203")

        self.type_input = QComboBox()
        style_combo_popups(self.type_input)
        self.type_input.setEditable(True)
        self.type_input.addItems(["Tiêu chuẩn", "Thường", "VIP", "Gia đình"])

        self.capacity_input = QSpinBox()
        self.capacity_input.setRange(1, 12)
        self.capacity_input.setValue(4)
        self.capacity_input.setButtonSymbols(QAbstractSpinBox.NoButtons)

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 100000000)
        self.price_input.setSingleStep(100000)
        self.price_input.setDecimals(0)
        self.price_input.setGroupSeparatorShown(True)
        self.price_input.setSuffix(" VNĐ")
        self.price_input.setValue(500000)
        self.price_input.setButtonSymbols(QAbstractSpinBox.NoButtons)

        self.status_input = QComboBox()
        style_combo_popups(self.status_input)
        self.status_input.addItem("Còn trống", RoomStatus.AVAILABLE.value)
        self.status_input.addItem("Đã đầy", RoomStatus.OCCUPIED.value)
        self.status_input.addItem("Bảo trì", RoomStatus.MAINTENANCE.value)

        form_layout.addRow("Số phòng", self.number_input)
        form_layout.addRow("Phân loại", self.type_input)
        form_layout.addRow("Sức chứa", self.capacity_input)
        form_layout.addRow("Giá thuê/tháng", self.price_input)
        form_layout.addRow("Trạng thái", self.status_input)
        layout.addLayout(form_layout)

        actions = QHBoxLayout()
        if self.room:
            btn_delete = QPushButton("Xóa phòng")
            btn_delete.setObjectName("DangerButton")
            btn_delete.clicked.connect(self.handle_delete)
            actions.addWidget(btn_delete)
        actions.addStretch()

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Lưu phòng")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_save)
        layout.addLayout(actions)

        if self.room:
            self.number_input.setText(self.room.room_number)
            self.type_input.setCurrentText(self.room.room_type or "Tiêu chuẩn")
            self.capacity_input.setValue(self.room.capacity)
            self.price_input.setValue(self.room.price or 0)
            index = self.status_input.findData(self.room.status.value)
            if index >= 0:
                self.status_input.setCurrentIndex(index)

    def get_data(self):
        return {
            "room_number": self.number_input.text(),
            "room_type": self.type_input.currentText(),
            "capacity": self.capacity_input.value(),
            "price": self.price_input.value(),
            "status": self.status_input.currentData(),
        }

    def validate(self):
        if not self.number_input.text().strip():
            QMessageBox.warning(self, "Thiếu dữ liệu", "Số phòng không được để trống.")
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
            "Xóa phòng này khỏi hệ thống?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.action = "delete"
            self.done(QDialog.Accepted)
