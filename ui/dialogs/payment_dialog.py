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
    QTextEdit,
    QVBoxLayout,
)

from models import PaymentStatus, PaymentType
from ui.widgets.searchable_combo_box import style_combo_popups


class PaymentDialog(QDialog):
    def __init__(self, parent=None, payment=None, contracts=None):
        super().__init__(parent)
        self.payment = payment
        self.contracts = contracts or []
        self.action = "save"
        self.init_ui()
        self.load_options()
        self.bind_data()

    def init_ui(self):
        self.setWindowTitle("Phiếu thanh toán")
        self.setFixedSize(560, 620)
        self.setObjectName("EntityDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)

        header = QFrame()
        header.setObjectName("DialogHero")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel("Phiếu thanh toán")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Theo dõi tiền phòng, điện, nước theo từng hợp đồng.")
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

        self.contract_combo = QComboBox()
        style_combo_popups(self.contract_combo)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 999999999)
        self.amount_input.setDecimals(0)
        self.amount_input.setGroupSeparatorShown(True)
        self.amount_input.setSingleStep(100000)
        self.amount_input.setSuffix(" VNĐ")
        self.amount_input.setButtonSymbols(QAbstractSpinBox.NoButtons)

        self.type_combo = QComboBox()
        style_combo_popups(self.type_combo)
        self.type_combo.addItem("Tiền phòng", PaymentType.ROOM_FEE.value)
        self.type_combo.addItem("Tiền điện", PaymentType.ELECTRICITY.value)
        self.type_combo.addItem("Tiền nước", PaymentType.WATER.value)

        self.payment_date = QDateEdit()
        self.payment_date.setCalendarPopup(True)
        self.payment_date.setDate(QDate.currentDate())

        self.status_combo = QComboBox()
        style_combo_popups(self.status_combo)
        self.status_combo.addItem("Chưa thanh toán", PaymentStatus.UNPAID.value)
        self.status_combo.addItem("Đã thanh toán", PaymentStatus.PAID.value)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Ghi chú thêm nếu cần")
        self.notes_input.setFixedHeight(90)

        form_layout.addRow("Hợp đồng", self.contract_combo)
        form_layout.addRow("Số tiền", self.amount_input)
        form_layout.addRow("Loại phí", self.type_combo)
        form_layout.addRow("Ngày thanh toán", self.payment_date)
        form_layout.addRow("Trạng thái", self.status_combo)
        form_layout.addRow("Ghi chú", self.notes_input)
        layout.addLayout(form_layout)

        actions = QHBoxLayout()
        if self.payment:
            btn_delete = QPushButton("Xóa phiếu")
            btn_delete.setObjectName("DangerButton")
            btn_delete.clicked.connect(self.handle_delete)
            actions.addWidget(btn_delete)

            if self.payment.status == PaymentStatus.UNPAID:
                btn_mark_paid = QPushButton("Đánh dấu đã thanh toán")
                btn_mark_paid.clicked.connect(self.handle_mark_paid)
                actions.addWidget(btn_mark_paid)

        actions.addStretch()
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Lưu phiếu")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_save)
        layout.addLayout(actions)

        self.contract_combo.currentIndexChanged.connect(self.sync_amount)

    def load_options(self):
        self.contract_combo.clear()
        for contract in self.contracts:
            student_name = contract.student.full_name if contract.student else "N/A"
            room_number = contract.room.room_number if contract.room else "--"
            label = f"HĐ#{contract.id} | {student_name} | Phòng {room_number}"
            self.contract_combo.addItem(label, contract.id)

    def bind_data(self):
        if self.payment:
            contract_index = self.contract_combo.findData(self.payment.contract_id)
            if contract_index >= 0:
                self.contract_combo.setCurrentIndex(contract_index)
            self.amount_input.setValue(self.payment.amount or 0)
            type_index = self.type_combo.findData(self.payment.payment_type.value)
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            self.payment_date.setDate(
                QDate(self.payment.payment_date.year, self.payment.payment_date.month, self.payment.payment_date.day)
            )
            status_index = self.status_combo.findData(self.payment.status.value)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
            self.notes_input.setPlainText(self.payment.notes or "")
        else:
            self.sync_amount()

    def sync_amount(self):
        if self.payment:
            return
        contract_id = self.contract_combo.currentData()
        contract = next((item for item in self.contracts if item.id == contract_id), None)
        if contract and contract.room:
            self.amount_input.setValue(contract.room.price or 0)

    def get_data(self):
        return {
            "contract_id": self.contract_combo.currentData(),
            "amount": self.amount_input.value(),
            "payment_type": self.type_combo.currentData(),
            "payment_date": self.payment_date.date().toPyDate(),
            "status": self.status_combo.currentData(),
            "notes": self.notes_input.toPlainText(),
        }

    def validate(self):
        if self.contract_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Bạn phải chọn hợp đồng.")
            return False
        if self.amount_input.value() <= 0:
            QMessageBox.warning(self, "Số tiền không hợp lệ", "Số tiền phải lớn hơn 0.")
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
            "Xóa phiếu thanh toán này khỏi hệ thống?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.action = "delete"
            self.done(QDialog.Accepted)

    def handle_mark_paid(self):
        reply = QMessageBox.question(
            self,
            "Đánh dấu đã thanh toán",
            "Đánh dấu phiếu này là đã thanh toán?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.action = "mark_paid"
            self.done(QDialog.Accepted)
