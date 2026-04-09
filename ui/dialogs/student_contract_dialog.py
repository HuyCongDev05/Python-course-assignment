import calendar
from datetime import date, timedelta

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from utils.formatters import format_currency


def _months_between(start: date, end: date) -> int:
    """Tính số tháng (tối thiểu 1) giữa hai ngày."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day >= start.day:
        months += 1
    return max(months, 1)


def _default_end_date(start: date) -> date:
    """Ngày kết thúc mặc định = 6 tháng sau ngày bắt đầu."""
    month = start.month + 6
    year = start.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class StudentContractDialog(QDialog):
    """Dialog nhập ngày hợp đồng khi sinh viên chọn phòng lưu trú."""

    def __init__(self, parent=None, room=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.room = room
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Thông tin hợp đồng")
        self.setFixedSize(480, 420)
        self.setObjectName("EntityDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)

        # --- Header ---
        header = QFrame()
        header.setObjectName("DialogHero")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        header_layout.setSpacing(4)
        title = QLabel("Đăng ký hợp đồng lưu trú")
        title.setObjectName("DialogTitle")
        room_name = self.room.room_number if self.room else "---"
        room_price = format_currency(self.room.price) if self.room else "---"
        subtitle = QLabel(
            f"Phòng {room_name}  ·  {room_price} / tháng  ·  "
            "Chọn thời hạn để tạo hợp đồng và phiếu thanh toán tháng đầu."
        )
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        # --- Form ---
        today = date.today()
        default_end = _default_end_date(today)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 4)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(22)
        form.setFormAlignment(Qt.AlignTop)

        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("dd/MM/yyyy")
        self.start_edit.setDate(QDate(today.year, today.month, today.day))
        self.start_edit.dateChanged.connect(self._refresh_summary)

        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("dd/MM/yyyy")
        self.end_edit.setDate(QDate(default_end.year, default_end.month, default_end.day))
        self.end_edit.dateChanged.connect(self._refresh_summary)

        form.addRow("Ngày bắt đầu", self.start_edit)
        form.addRow("Ngày kết thúc", self.end_edit)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("DialogSubtitle")
        self.summary_label.setWordWrap(True)
        form.addRow("Tóm tắt", self.summary_label)

        layout.addLayout(form)
        layout.addStretch()

        # --- Actions ---
        actions = QHBoxLayout()
        actions.addStretch()

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QPushButton("Xác nhận & Tạo hợp đồng")
        btn_confirm.setObjectName("PrimaryButton")
        btn_confirm.clicked.connect(self.accept)

        actions.addWidget(btn_cancel)
        actions.addWidget(btn_confirm)
        layout.addLayout(actions)

        self._refresh_summary()

    # ------------------------------------------------------------------

    def _refresh_summary(self):
        start = self.get_start_date()
        end = self.get_end_date()

        if not start or not end or end <= start:
            self.summary_label.setText("⚠ Ngày kết thúc phải sau ngày bắt đầu.")
            return

        months = _months_between(start, end)
        price = float(self.room.price) if self.room else 0.0
        total = price * months
        self.summary_label.setText(
            f"{months} tháng  ·  Tổng hợp đồng: {format_currency(total)}\n"
            f"Phiếu thanh toán tháng đầu: {format_currency(price)}"
        )

    def validate(self):
        start = self.get_start_date()
        end = self.get_end_date()
        if not start or not end or end <= start:
            QMessageBox.warning(self, "Ngày không hợp lệ", "Ngày kết thúc phải sau ngày bắt đầu.")
            return False
        return True

    def accept(self):
        if self.validate():
            super().accept()

    def get_start_date(self) -> date:
        qd = self.start_edit.date()
        return date(qd.year(), qd.month(), qd.day())

    def get_end_date(self) -> date:
        qd = self.end_edit.date()
        return date(qd.year(), qd.month(), qd.day())
