from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models import PaymentStatus, UserRole
from services.student_service import PaymentService
from ui.dialogs.payment_dialog import PaymentDialog
from ui.dialogs.student_payment_dialog import StudentPaymentDialog
from ui.widgets.hover_table_widget import HoverTableWidget
from ui.widgets.searchable_combo_box import style_combo_popups
from utils.formatters import (
    format_currency,
    format_date,
    payment_note_label,
    payment_status_label,
    payment_type_label,
)


class PaymentView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.payment_service = PaymentService()
        self.init_ui()
        self.load_payments()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        header = QFrame()
        header.setObjectName("HeroPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)

        title_wrap = QVBoxLayout()
        title = QLabel("Thanh toán và công nợ")
        title.setObjectName("HeroTitle")
        subtitle = QLabel(
            "Nhấn đúp vào một dòng để xem chi tiết hóa đơn và thanh toán online."
            if self.user and self.user.role == UserRole.STUDENT
            else "Nhấn đúp vào một dòng để cập nhật, xóa hoặc đánh dấu đã thanh toán."
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        self.btn_add = QPushButton("Tạo phiếu thanh toán")
        self.btn_add.setObjectName("PrimaryButton")
        self.btn_add.clicked.connect(self.add_payment_dialog)

        header_layout.addLayout(title_wrap, 1)
        header_layout.addWidget(self.btn_add, 0)
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo tên sinh viên, mã sinh viên hoặc số phòng")
        self.search_input.textChanged.connect(self.load_payments)

        self.status_filter = QComboBox()
        style_combo_popups(self.status_filter)
        self.status_filter.addItem("Tất cả", "all")
        self.status_filter.addItem("Chưa thanh toán", "unpaid")
        self.status_filter.addItem("Đã thanh toán", "paid")
        self.status_filter.currentIndexChanged.connect(self.load_payments)

        self.total_chip = QLabel()
        self.total_chip.setObjectName("InfoChip")
        self.paid_chip = QLabel()
        self.paid_chip.setObjectName("InfoChip")
        self.unpaid_chip = QLabel()
        self.unpaid_chip.setObjectName("InfoChip")
        for chip in (self.total_chip, self.paid_chip, self.unpaid_chip):
            chip.setAlignment(Qt.AlignCenter)
            chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.status_filter)
        toolbar.addWidget(self.total_chip)
        toolbar.addWidget(self.paid_chip)
        toolbar.addWidget(self.unpaid_chip)
        layout.addLayout(toolbar)

        self.table = HoverTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Hợp đồng", "Sinh viên", "Phòng", "Số tiền", "Loại phí", "Ngày", "Trạng thái", "Ghi chú"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setColumnHidden(0, True)
        self.table.cellDoubleClicked.connect(lambda *_: self.handle_payment_double_click())
        layout.addWidget(self.table)

        if self.user and self.user.role == UserRole.STUDENT:
            self.btn_add.hide()

    def load_payments(self):
        payments = self.payment_service.get_all_payments(self.search_input.text(), self.status_filter.currentData())
        if self.user and self.user.role == UserRole.STUDENT:
            payments = [
                item
                for item in payments
                if item.contract and item.contract.student and item.contract.student.user_id == self.user.id
            ]

        self.populate_table(payments)
        self.total_chip.setText(f"{len(payments)} phiếu")
        paid_total = sum(item.amount for item in payments if item.status == PaymentStatus.PAID)
        unpaid_total = sum(item.amount for item in payments if item.status == PaymentStatus.UNPAID)
        self.paid_chip.setText(f"Đã thu {format_currency(paid_total)}")
        self.unpaid_chip.setText(f"Còn nợ {format_currency(unpaid_total)}")

    def populate_table(self, payments):
        self.table.setRowCount(0)
        for row_index, payment in enumerate(payments):
            self.table.insertRow(row_index)
            contract = payment.contract
            student_name = contract.student.full_name if contract and contract.student else "--"
            room_number = contract.room.room_number if contract and contract.room else "--"
            values = [
                str(payment.id),
                f"HĐ#{payment.contract_id}",
                student_name,
                room_number,
                format_currency(payment.amount),
                payment_type_label(payment.payment_type),
                format_date(payment.payment_date),
                payment_status_label(payment.status),
                payment_note_label(payment.notes),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))

    def get_selected_payment_id(self):
        row_index = self.table.currentRow()
        if row_index < 0:
            return None
        item = self.table.item(row_index, 0)
        return int(item.text()) if item else None

    def handle_payment_double_click(self):
        if self.user and self.user.role == UserRole.STUDENT:
            self.open_student_payment_dialog()
            return
        self.edit_payment_dialog()

    def add_payment_dialog(self):
        contracts = self.payment_service.get_contract_candidates()
        if not contracts:
            QMessageBox.warning(self, "Không có dữ liệu", "Chưa có hợp đồng phù hợp để tạo phiếu thanh toán.")
            return

        dialog = PaymentDialog(self, contracts=contracts)
        if dialog.exec_() and dialog.action == "save":
            try:
                self.payment_service.create_payment(dialog.get_data())
                self.load_payments()
                QMessageBox.information(self, "Thành công", "Đã tạo phiếu thanh toán.")
            except Exception as exc:
                QMessageBox.critical(self, "Không thể lưu", str(exc))

    def open_student_payment_dialog(self):
        payment_id = self.get_selected_payment_id()
        if not payment_id:
            QMessageBox.warning(self, "Chưa chọn dữ liệu", "Vui lòng chọn một hóa đơn để xem chi tiết.")
            return

        payment = self.payment_service.get_payment_by_id(payment_id)
        if not payment:
            QMessageBox.warning(self, "Không tìm thấy dữ liệu", "Hóa đơn này không còn tồn tại.")
            self.load_payments()
            return

        dialog = StudentPaymentDialog(self, payment=payment, payment_service=self.payment_service)
        dialog.exec_()
        if dialog.state_changed:
            self.load_payments()

    def edit_payment_dialog(self):
        payment_id = self.get_selected_payment_id()
        if not payment_id:
            QMessageBox.warning(self, "Chưa chọn dữ liệu", "Vui lòng chọn một phiếu thanh toán để chỉnh sửa.")
            return

        payment = self.payment_service.get_payment_by_id(payment_id)
        contracts = self.payment_service.get_contract_candidates(include_contract_id=payment.contract_id)
        dialog = PaymentDialog(self, payment=payment, contracts=contracts)
        if not dialog.exec_():
            return

        try:
            if dialog.action == "delete":
                self.payment_service.delete_payment(payment_id)
                QMessageBox.information(self, "Thành công", "Đã xóa phiếu thanh toán.")
            elif dialog.action == "mark_paid":
                self.payment_service.mark_paid(payment_id)
                QMessageBox.information(self, "Thành công", "Phiếu đã được đánh dấu là đã thanh toán.")
            else:
                self.payment_service.update_payment(payment_id, dialog.get_data())
                QMessageBox.information(self, "Thành công", "Phiếu thanh toán đã được cập nhật.")
            self.load_payments()
        except Exception as exc:
            QMessageBox.critical(self, "Không thể xử lý", str(exc))
