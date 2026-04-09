from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ui.widgets.searchable_combo_box import SearchableComboBox, style_combo_popups


class ContractDialog(QDialog):
    def __init__(self, parent=None, contract=None, students=None, rooms=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.contract = contract
        self.students = students or []
        self.rooms = rooms or []
        self.action = "save"
        self.init_ui()
        self.load_options()
        self.bind_data()

    def init_ui(self):
        self.setWindowTitle("Thông tin hợp đồng")
        self.setFixedSize(540, 560)
        self.setObjectName("EntityDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)

        header = QFrame()
        header.setObjectName("DialogHero")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel("Hợp đồng lưu trú")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Liên kết sinh viên với phòng ở và quản lý thời hạn hợp đồng.")
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

        self.student_combo = SearchableComboBox(search_placeholder="Tìm sinh viên theo mã hoặc tên")
        self.room_combo = SearchableComboBox(search_placeholder="Tìm phòng theo số phòng hoặc loại")

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate().addMonths(6))

        self.total_amount = QDoubleSpinBox()
        self.total_amount.setRange(0, 999999999)
        self.total_amount.setDecimals(0)
        self.total_amount.setSingleStep(500000)
        self.total_amount.setGroupSeparatorShown(True)
        self.total_amount.setSuffix(" VNĐ")
        self.total_amount.setButtonSymbols(QAbstractSpinBox.NoButtons)

        self.status_combo = QComboBox()
        style_combo_popups(self.status_combo)
        self.status_combo.addItem("Hiệu lực", "active")
        self.status_combo.addItem("Hết hạn", "expired")
        self.status_combo.addItem("Đã kết thúc", "terminated")

        form_layout.addRow("Sinh viên", self.student_combo)
        form_layout.addRow("Phòng ở", self.room_combo)
        form_layout.addRow("Ngày bắt đầu", self.start_date)
        form_layout.addRow("Ngày kết thúc", self.end_date)
        form_layout.addRow("Tổng giá trị", self.total_amount)
        form_layout.addRow("Trạng thái", self.status_combo)
        layout.addLayout(form_layout)

        actions = QHBoxLayout()
        if self.contract:
            btn_delete = QPushButton("Xóa hợp đồng")
            btn_delete.setObjectName("DangerButton")
            btn_delete.clicked.connect(self.handle_delete)
            actions.addWidget(btn_delete)

            if self.contract.status == "active":
                btn_terminate = QPushButton("Kết thúc")
                btn_terminate.clicked.connect(self.handle_terminate)
                actions.addWidget(btn_terminate)

        actions.addStretch()
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Lưu hợp đồng")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_save)
        layout.addLayout(actions)

        self.room_combo.currentIndexChanged.connect(self.sync_total_amount)
        self.start_date.dateChanged.connect(self.sync_total_amount)
        self.end_date.dateChanged.connect(self.sync_total_amount)

    def load_options(self):
        self.student_combo.clear()
        self.room_combo.clear()

        for student in self.students:
            label = f"{student.student_id} | {student.full_name}"
            self.student_combo.addItem(label, student.id)

        for room in self.rooms:
            label = f"Phòng {room.room_number} | {room.room_type} | {room.current_occupancy}/{room.capacity}"
            self.room_combo.addItem(label, room.id)

    def bind_data(self):
        if self.contract:
            student_index = self.student_combo.findData(self.contract.student_id)
            if student_index >= 0:
                self.student_combo.setCurrentIndex(student_index)

            room_index = self.room_combo.findData(self.contract.room_id)
            if room_index >= 0:
                self.room_combo.setCurrentIndex(room_index)

            self.start_date.setDate(QDate(self.contract.start_date.year, self.contract.start_date.month, self.contract.start_date.day))
            self.end_date.setDate(QDate(self.contract.end_date.year, self.contract.end_date.month, self.contract.end_date.day))
            self.total_amount.setValue(self.contract.total_amount or 0)
            status_index = self.status_combo.findData(self.contract.status)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
        else:
            self.sync_total_amount()

    def sync_total_amount(self):
        room_id = self.room_combo.currentData()
        room = next((item for item in self.rooms if item.id == room_id), None)
        if not room:
            return

        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        months = (end.year - start.year) * 12 + (end.month - start.month)
        if end.day >= start.day:
            months += 1
        months = max(months, 1)
        self.total_amount.setValue(room.price * months)

    def get_data(self):
        return {
            "student_id": self.student_combo.currentData(),
            "room_id": self.room_combo.currentData(),
            "start_date": self.start_date.date().toPyDate(),
            "end_date": self.end_date.date().toPyDate(),
            "total_amount": self.total_amount.value(),
            "status": self.status_combo.currentData(),
        }

    def validate(self):
        if self.student_combo.currentIndex() < 0 or self.room_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Bạn phải chọn sinh viên và phòng.")
            return False
        if self.start_date.date() > self.end_date.date():
            QMessageBox.warning(self, "Ngày không hợp lệ", "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu.")
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
            "Xóa hợp đồng này khỏi hệ thống?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.action = "delete"
            self.done(QDialog.Accepted)

    def handle_terminate(self):
        reply = QMessageBox.question(
            self,
            "Kết thúc hợp đồng",
            "Kết thúc hợp đồng này và giải phóng phòng ở liên quan?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.action = "terminate"
            self.done(QDialog.Accepted)
