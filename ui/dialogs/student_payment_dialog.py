import hashlib
import math
import os

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from models import PaymentStatus
from services.student_service import ONLINE_PAYMENT_PENDING_NOTE, is_online_payment_pending_note
from utils.formatters import format_currency, format_date, payment_note_label, payment_status_label, payment_type_label

MB_BANK_ACCOUNT_NAME = "Nguyễn Huy Công"
MB_BANK_NAME = "MB Bank"
PAYMENT_QR_CANDIDATES = (
    "payment_qr.png",
    "payment_qr.jpg",
    "payment_qr.jpeg",
    "payment_qr.webp",
)


def _resource_path(*parts):
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "resources", *parts))


def _draw_module(painter, module_size, border_modules, row, col, color):
    offset = border_modules * module_size
    painter.fillRect(
        offset + (col * module_size),
        offset + (row * module_size),
        module_size,
        module_size,
        color,
    )


def _draw_finder_pattern(painter, module_size, border_modules, top_row, left_col):
    black = QColor("#111111")
    white = QColor("#ffffff")
    for row in range(7):
        for col in range(7):
            is_border = row in {0, 6} or col in {0, 6}
            is_core = 2 <= row <= 4 and 2 <= col <= 4
            color = black if is_border or is_core else white
            _draw_module(painter, module_size, border_modules, top_row + row, left_col + col, color)


def _in_finder_area(module_count, row, col):
    corners = (
        (0, 0),
        (0, module_count - 7),
        (module_count - 7, 0),
    )
    for top_row, left_col in corners:
        if top_row <= row < top_row + 7 and left_col <= col < left_col + 7:
            return True
    return False


def build_qr_pixmap(payload, size=300):
    module_count = 29
    border_modules = 4
    total_modules = module_count + (border_modules * 2)
    module_size = max(6, size // total_modules)
    canvas_size = total_modules * module_size

    pixmap = QPixmap(canvas_size, canvas_size)
    pixmap.fill(QColor("#ffffff"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, False)

    black = QColor("#111111")
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    bit_index = 0

    for row in range(module_count):
        for col in range(module_count):
            if _in_finder_area(module_count, row, col):
                continue

            byte = digest[(bit_index // 8) % len(digest)]
            bit = (byte >> (bit_index % 8)) & 1
            if (row + col) % 3 == 0:
                bit ^= 1
            if bit:
                _draw_module(painter, module_size, border_modules, row, col, black)
            bit_index += 1

    _draw_finder_pattern(painter, module_size, border_modules, 0, 0)
    _draw_finder_pattern(painter, module_size, border_modules, 0, module_count - 7)
    _draw_finder_pattern(painter, module_size, border_modules, module_count - 7, 0)

    painter.end()
    return pixmap


def build_mb_bank_badge_pixmap(width=148, height=50):
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    container = QRectF(0.5, 0.5, width - 1, height - 1)
    painter.setPen(QColor("#c9d8ea"))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(container, 14, 14)

    mark_rect = QRectF(8, 8, 34, 34)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#d71920"))
    painter.drawRoundedRect(mark_rect, 9, 9)

    star = QPolygonF()
    center_x = mark_rect.center().x()
    center_y = mark_rect.center().y()
    outer_radius = 10
    inner_radius = 4.5
    for point_index in range(10):
        angle = math.radians(-90 + (point_index * 36))
        radius = outer_radius if point_index % 2 == 0 else inner_radius
        star.append(
            QPointF(
                center_x + (math.cos(angle) * radius),
                center_y + (math.sin(angle) * radius),
            )
        )

    painter.setBrush(QColor("#ffffff"))
    painter.drawPolygon(star)

    text_font = QFont()
    text_font.setBold(True)
    text_font.setPointSize(12)
    painter.setFont(text_font)
    painter.setPen(QColor("#1f4f9b"))
    painter.drawText(QRectF(50, 8, width - 58, 20), Qt.AlignLeft | Qt.AlignVCenter, "MB Bank")

    sub_font = QFont()
    sub_font.setPointSize(8)
    painter.setFont(sub_font)
    painter.setPen(QColor("#6b7e93"))
    painter.drawText(QRectF(50, 26, width - 58, 16), Qt.AlignLeft | Qt.AlignVCenter, "Military Bank")

    painter.end()
    return pixmap


def load_payment_qr_pixmap(max_width=260, max_height=260):
    for filename in PAYMENT_QR_CANDIDATES:
        candidate_path = _resource_path("images", filename)
        if not os.path.exists(candidate_path):
            continue
        pixmap = QPixmap(candidate_path)
        if pixmap.isNull():
            continue
        return pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return None


class StudentPaymentQrDialog(QDialog):
    def __init__(self, parent=None, payment=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.payment = payment
        self.confirmed = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("QR thanh toán")
        self.setFixedSize(620, 480)
        self.setObjectName("EntityDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Header ---
        header = QFrame()
        header.setObjectName("DialogHero")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)

        title_row = QHBoxLayout()
        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)
        title = QLabel("Thanh toán online")
        title.setObjectName("DialogTitle")
        subtitle = QLabel('Quét mã QR để chuyển khoản, sau đó bấm "Đã thanh toán".')
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        bank_badge = QLabel()
        bank_badge.setPixmap(build_mb_bank_badge_pixmap())

        title_row.addLayout(title_wrap, 1)
        title_row.addWidget(bank_badge, 0, Qt.AlignTop | Qt.AlignRight)
        header_layout.addLayout(title_row)
        layout.addWidget(header)

        # --- Body: QR bên trái | Thông tin bên phải ---
        body = QHBoxLayout()
        body.setSpacing(18)

        # QR image
        contract = self.payment.contract if self.payment else None
        room = contract.room if contract and contract.room else None
        student = contract.student if contract and contract.student else None
        payload = "|".join(
            [
                f"PAYMENT:{getattr(self.payment, 'id', '--')}",
                f"CONTRACT:{getattr(contract, 'id', '--')}",
                f"ROOM:{getattr(room, 'room_number', '--')}",
                f"STUDENT:{getattr(student, 'student_id', '--')}",
                f"AMOUNT:{int(getattr(self.payment, 'amount', 0) or 0)}",
            ]
        )

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setObjectName("PaymentQrImage")

        static_qr_pixmap = load_payment_qr_pixmap(max_width=240, max_height=240)
        if static_qr_pixmap is not None:
            qr_label.setPixmap(static_qr_pixmap)
            qr_label.setFixedSize(static_qr_pixmap.size())
        else:
            fallback_pixmap = build_qr_pixmap(payload, size=240)
            qr_label.setPixmap(fallback_pixmap)
            qr_label.setFixedSize(fallback_pixmap.size())

        body.addWidget(qr_label, 0, Qt.AlignTop | Qt.AlignHCenter)

        # Info panel bên phải
        info_panel = QFrame()
        info_panel.setObjectName("QrBankPanel")
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(14)

        bank_grid = QGridLayout()
        bank_grid.setHorizontalSpacing(12)
        bank_grid.setVerticalSpacing(10)
        self._add_bank_info(bank_grid, 0, "Chủ tài khoản", MB_BANK_ACCOUNT_NAME)
        self._add_bank_info(bank_grid, 1, "Ngân hàng", MB_BANK_NAME)
        self._add_bank_info(bank_grid, 2, "Nội dung CK", f"TT PAYMENT {getattr(self.payment, 'id', '--')}")
        info_layout.addLayout(bank_grid)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("Separator")
        info_layout.addWidget(sep)

        amount_label = QLabel(f"Số tiền: {format_currency(self.payment.amount if self.payment else 0)}")
        amount_label.setObjectName("SectionTitle")
        amount_label.setWordWrap(True)
        info_layout.addWidget(amount_label)

        room_label = QLabel(
            f"Phòng {getattr(room, 'room_number', '--')}  ·  {getattr(student, 'full_name', '--') or '--'}"
        )
        room_label.setObjectName("SectionHint")
        room_label.setWordWrap(True)
        info_layout.addWidget(room_label)

        scan_hint = QLabel("Quét bằng ứng dụng MB Bank hoặc bất kỳ ứng dụng ngân hàng nào hỗ trợ VietQR.")
        scan_hint.setObjectName("SectionHint")
        scan_hint.setWordWrap(True)
        info_layout.addWidget(scan_hint)

        info_layout.addStretch()
        body.addWidget(info_panel, 1)
        layout.addLayout(body)

        # --- Note & Actions ---
        note = QLabel("Nếu cần thanh toán tiền mặt, vui lòng đến văn phòng kế toán để nộp trực tiếp.")
        note.setWordWrap(True)
        note.setObjectName("SectionHint")
        layout.addWidget(note)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.reject)
        btn_confirm = QPushButton("Đã thanh toán")
        btn_confirm.setObjectName("PrimaryButton")
        btn_confirm.clicked.connect(self.handle_confirm)
        actions.addWidget(btn_close)
        actions.addWidget(btn_confirm)
        layout.addLayout(actions)

    def _add_bank_info(self, layout, row, label_text, value_text):
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        value = QLabel(value_text)
        value.setObjectName("QrBankValue")
        value.setWordWrap(True)
        layout.addWidget(label, row, 0)
        layout.addWidget(value, row, 1)

    def handle_confirm(self):
        self.confirmed = True
        self.accept()


class StudentPaymentDialog(QDialog):
    def __init__(self, parent=None, payment=None, payment_service=None):
        super().__init__(parent)
        self.payment = payment
        self.payment_service = payment_service
        self.state_changed = False
        self.init_ui()
        self.refresh_payment_state()

    def init_ui(self):
        self.setWindowTitle("Chi tiết hóa đơn")
        self.setFixedSize(620, 640)
        self.setObjectName("EntityDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QFrame()
        header.setObjectName("DialogHero")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)

        title = QLabel("Chi tiết hóa đơn")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Xem thông tin hóa đơn, hướng dẫn thanh toán tiền mặt và gửi yêu cầu thanh toán online.")
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        details = QFrame()
        details.setObjectName("DataPanel")
        self.details_layout = QGridLayout(details)
        self.details_layout.setContentsMargins(18, 18, 18, 18)
        self.details_layout.setHorizontalSpacing(24)
        self.details_layout.setVerticalSpacing(14)

        self.contract_value = QLabel()
        self.student_value = QLabel()
        self.room_value = QLabel()
        self.amount_value = QLabel()
        self.type_value = QLabel()
        self.date_value = QLabel()
        self.status_value = QLabel()
        self.note_value = QLabel()
        self.note_value.setWordWrap(True)

        self._add_info_row("Hợp đồng", self.contract_value, 0, 0)
        self._add_info_row("Sinh viên", self.student_value, 0, 1)
        self._add_info_row("Phòng", self.room_value, 1, 0)
        self._add_info_row("Số tiền", self.amount_value, 1, 1)
        self._add_info_row("Loại phí", self.type_value, 2, 0)
        self._add_info_row("Ngày lập", self.date_value, 2, 1)
        self._add_info_row("Trạng thái", self.status_value, 3, 0)
        self._add_info_row("Ghi chú", self.note_value, 3, 1)

        layout.addWidget(details)

        cash_panel = QFrame()
        cash_panel.setObjectName("DataPanel")
        cash_layout = QVBoxLayout(cash_panel)
        cash_layout.setContentsMargins(18, 18, 18, 18)
        cash_layout.setSpacing(8)

        cash_title = QLabel("Thanh toán tiền mặt")
        cash_title.setObjectName("SectionTitle")
        cash_text = QLabel("Vui lòng lên văn phòng kế toán trường để nộp tiền mặt và nhận xác nhận từ nhân viên.")
        cash_text.setObjectName("SectionHint")
        cash_text.setWordWrap(True)

        self.online_hint = QLabel()
        self.online_hint.setObjectName("SectionHint")
        self.online_hint.setWordWrap(True)

        cash_layout.addWidget(cash_title)
        cash_layout.addWidget(cash_text)
        cash_layout.addWidget(self.online_hint)
        layout.addWidget(cash_panel)

        actions = QHBoxLayout()
        actions.addStretch()

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.reject)

        self.btn_online = QPushButton("Thanh toán online")
        self.btn_online.setObjectName("PrimaryButton")
        self.btn_online.clicked.connect(self.open_qr_dialog)

        actions.addWidget(btn_close)
        actions.addWidget(self.btn_online)
        layout.addLayout(actions)

    def _add_info_row(self, label_text, value_widget, row, col):
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        self.details_layout.addWidget(label, row * 2, col, 1, 1)
        self.details_layout.addWidget(value_widget, (row * 2) + 1, col, 1, 1)

    def refresh_payment_state(self):
        contract = self.payment.contract if self.payment else None
        student = contract.student if contract and contract.student else None
        room = contract.room if contract and contract.room else None

        self.contract_value.setText(f"HĐ#{getattr(self.payment, 'contract_id', '--')}")
        self.student_value.setText(getattr(student, "full_name", "--") or "--")
        self.room_value.setText(getattr(room, "room_number", "--") or "--")
        self.amount_value.setText(format_currency(self.payment.amount if self.payment else 0))
        self.type_value.setText(payment_type_label(self.payment.payment_type) if self.payment else "--")
        self.date_value.setText(format_date(self.payment.payment_date) if self.payment else "--")
        self.status_value.setText(payment_status_label(self.payment.status) if self.payment else "--")
        self.note_value.setText(payment_note_label(self.payment.notes))

        if not self.payment or self.payment.status == PaymentStatus.PAID:
            self.online_hint.setText("Hóa đơn này đã được xác nhận thanh toán.")
            self.btn_online.hide()
            return

        self.btn_online.show()
        if is_online_payment_pending_note(self.payment.notes):
            self.online_hint.setText("Yêu cầu thanh toán online đã được gửi. Hệ thống đang chờ nhân viên xác nhận.")
            self.btn_online.setText("Đang chờ xác nhận")
            self.btn_online.setEnabled(False)
        else:
            self.online_hint.setText("Nếu chuyển khoản online, nhấn nút bên dưới để mở mã QR thanh toán.")
            self.btn_online.setText("Thanh toán online")
            self.btn_online.setEnabled(True)

    def open_qr_dialog(self):
        if not self.payment or self.payment.status == PaymentStatus.PAID:
            return
        if is_online_payment_pending_note(self.payment.notes):
            QMessageBox.information(self, "Thông báo", "Hóa đơn này đang chờ xác nhận thanh toán.")
            return

        dialog = StudentPaymentQrDialog(self, payment=self.payment)
        if not dialog.exec_() or not dialog.confirmed:
            return

        try:
            self.payment_service.submit_online_payment_request(self.payment.id)
            self.payment.notes = ONLINE_PAYMENT_PENDING_NOTE
            self.state_changed = True
            self.refresh_payment_state()
            QMessageBox.information(
                self,
                "Đã gửi yêu cầu",
                "Hệ thống đã ghi nhận yêu cầu thanh toán online và đang chờ xác nhận.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Không thể cập nhật", str(exc))
