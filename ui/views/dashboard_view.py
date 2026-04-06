from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from models import PaymentStatus, UserRole
from services.student_service import ContractService, PaymentService, RoomService, StudentService
from ui.widgets.hover_table_widget import HoverTableWidget
from utils.formatters import contract_status_label, format_currency, format_date, room_status_label


class MetricCard(QFrame):
    def __init__(self, title, accent):
        super().__init__()
        self.setObjectName("MetricCard")
        self.setProperty("accent", accent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")
        self.value_label = QLabel("--")
        self.value_label.setObjectName("MetricValue")
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("MetricDetail")
        self.detail_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def update(self, value, detail=""):
        self.value_label.setText(str(value))
        self.detail_label.setText(detail)


class DashboardView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.student_service = StudentService()
        self.room_service = RoomService()
        self.contract_service = ContractService()
        self.payment_service = PaymentService()
        self.init_ui()
        self.refresh_stats()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(22)

        hero = QFrame()
        hero.setObjectName("HeroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(16)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(6)
        title = QLabel("Bảng điều khiển ký túc xá")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Theo dõi sức chứa, hợp đồng và công nợ tại một nơi.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        self.date_chip = QLabel(date.today().strftime("Hôm nay %d/%m/%Y"))
        self.date_chip.setObjectName("InfoChip")
        self.date_chip.setAlignment(Qt.AlignCenter)
        self.date_chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        hero_layout.addLayout(title_wrap, 1)
        hero_layout.addWidget(self.date_chip, 0)
        layout.addWidget(hero)

        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(16)
        cards_layout.setVerticalSpacing(16)

        self.card_one = MetricCard("Sinh viên", "blue")
        self.card_two = MetricCard("Phòng ở", "green")
        self.card_three = MetricCard("Hợp đồng", "amber")
        self.card_four = MetricCard("Công nợ", "rose")

        cards_layout.addWidget(self.card_one, 0, 0)
        cards_layout.addWidget(self.card_two, 0, 1)
        cards_layout.addWidget(self.card_three, 1, 0)
        cards_layout.addWidget(self.card_four, 1, 1)
        layout.addLayout(cards_layout)

        analytics_layout = QHBoxLayout()
        analytics_layout.setSpacing(18)

        occupancy_panel = QFrame()
        occupancy_panel.setObjectName("DataPanel")
        occupancy_layout = QVBoxLayout(occupancy_panel)
        occupancy_layout.setContentsMargins(20, 20, 20, 20)
        occupancy_layout.setSpacing(14)
        occupancy_title = QLabel("Tình trạng phòng")
        occupancy_title.setObjectName("SectionTitle")
        self.occupancy_summary = QLabel("")
        self.occupancy_summary.setObjectName("SectionHint")
        self.occupancy_bar = QProgressBar()
        self.occupancy_bar.setObjectName("OccupancyBar")
        self.room_table = HoverTableWidget()
        self.room_table.setColumnCount(4)
        self.room_table.setHorizontalHeaderLabels(["Phòng", "Lấp đầy", "Giá thuê", "Trạng thái"])
        self.room_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.room_table.verticalHeader().setVisible(False)
        self.room_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.room_table.setSelectionMode(QAbstractItemView.NoSelection)
        occupancy_layout.addWidget(occupancy_title)
        occupancy_layout.addWidget(self.occupancy_summary)
        occupancy_layout.addWidget(self.occupancy_bar)
        occupancy_layout.addWidget(self.room_table)

        contract_panel = QFrame()
        contract_panel.setObjectName("DataPanel")
        contract_layout = QVBoxLayout(contract_panel)
        contract_layout.setContentsMargins(20, 20, 20, 20)
        contract_layout.setSpacing(14)
        contract_title = QLabel("Hợp đồng đáng chú ý")
        contract_title.setObjectName("SectionTitle")
        self.contract_hint = QLabel("Các hợp đồng sắp hết hạn sẽ xuất hiện tại đây.")
        self.contract_hint.setObjectName("SectionHint")
        self.contract_table = HoverTableWidget()
        self.contract_table.setColumnCount(4)
        self.contract_table.setHorizontalHeaderLabels(["Sinh viên", "Phòng", "Hết hạn", "Trạng thái"])
        self.contract_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.contract_table.verticalHeader().setVisible(False)
        self.contract_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.contract_table.setSelectionMode(QAbstractItemView.NoSelection)
        contract_layout.addWidget(contract_title)
        contract_layout.addWidget(self.contract_hint)
        contract_layout.addWidget(self.contract_table)

        analytics_layout.addWidget(occupancy_panel, 1)
        analytics_layout.addWidget(contract_panel, 1)
        layout.addLayout(analytics_layout)

    def refresh_stats(self):
        self.contract_service.refresh_contract_statuses()

        students = self.student_service.get_all_students()
        rooms = self.room_service.get_all_rooms()
        contracts = self.contract_service.get_all_contracts()
        payments = self.payment_service.get_all_payments()

        if self.user and self.user.role == UserRole.STUDENT:
            self._refresh_student_dashboard(students, contracts, payments)
            return

        self.card_one.title_label.setText("Sinh viên")
        self.card_two.title_label.setText("Phòng ở")
        self.card_three.title_label.setText("Hợp đồng")
        self.card_four.title_label.setText("Công nợ")

        total_beds = sum(room.capacity for room in rooms)
        occupied_beds = sum(room.current_occupancy for room in rooms)
        active_contracts = [item for item in contracts if item.status == "active"]
        unpaid_total = sum(payment.amount for payment in payments if payment.status == PaymentStatus.UNPAID)
        expected_revenue = sum(room.current_occupancy * room.price for room in rooms)

        self.card_one.update(len(students), f"{sum(1 for item in students if item.user_id)} tài khoản đã kích hoạt")
        self.card_two.update(len(rooms), f"{occupied_beds}/{total_beds} chỗ đang được sử dụng" if total_beds else "Chưa có dữ liệu phòng")
        self.card_three.update(len(active_contracts), f"{sum(1 for item in contracts if item.status == 'expired')} hợp đồng đã hết hạn")
        self.card_four.update(format_currency(unpaid_total), f"Doanh thu dự kiến: {format_currency(expected_revenue)}")

        occupancy_percent = int((occupied_beds / total_beds) * 100) if total_beds else 0
        self.occupancy_summary.setText(f"Công suất toàn khu hiện tại đạt {occupied_beds}/{total_beds} chỗ.")
        self.occupancy_bar.setValue(occupancy_percent)
        self.populate_room_table(rooms)
        self.populate_contract_table(contracts)

    def _refresh_student_dashboard(self, students, contracts, payments):
        student_contracts = [item for item in contracts if item.student and item.student.user_id == self.user.id]
        student_payments = [item for item in payments if item.contract and item.contract.student and item.contract.student.user_id == self.user.id]
        active_contract = next((item for item in student_contracts if item.status == "active"), None)
        unpaid_total = sum(item.amount for item in student_payments if item.status == PaymentStatus.UNPAID)
        student_record = next((item for item in students if item.user_id == self.user.id), None)

        self.card_one.title_label.setText("Mã sinh viên")
        self.card_two.title_label.setText("Phòng hiện tại")
        self.card_three.title_label.setText("Hợp đồng")
        self.card_four.title_label.setText("Công nợ")

        self.card_one.update(student_record.student_id if student_record else "--", "Mã hồ sơ đang liên kết với tài khoản")
        self.card_two.update(active_contract.room.room_number if active_contract and active_contract.room else "--", "Phòng hiện tại")
        self.card_three.update(len(student_contracts), "Số hợp đồng gắn với tài khoản")
        self.card_four.update(format_currency(unpaid_total), "Tổng phí chưa thanh toán")

        self.occupancy_summary.setText("Thông tin phòng ở của bạn.")
        self.occupancy_bar.setValue(100 if active_contract else 0)
        self.populate_room_table([active_contract.room] if active_contract and active_contract.room else [])
        self.contract_hint.setText("Lịch sử hợp đồng cá nhân.")
        self.populate_contract_table(student_contracts)

    def populate_room_table(self, rooms):
        self.room_table.setRowCount(0)
        for row_index, room in enumerate(rooms[:6]):
            self.room_table.insertRow(row_index)
            ratio = f"{room.current_occupancy}/{room.capacity}"
            self.room_table.setItem(row_index, 0, QTableWidgetItem(room.room_number))
            self.room_table.setItem(row_index, 1, QTableWidgetItem(ratio))
            self.room_table.setItem(row_index, 2, QTableWidgetItem(format_currency(room.price)))
            self.room_table.setItem(row_index, 3, QTableWidgetItem(room_status_label(room.status)))

    def populate_contract_table(self, contracts):
        self.contract_table.setRowCount(0)
        sorted_contracts = sorted(contracts, key=lambda item: item.end_date)
        for row_index, contract in enumerate(sorted_contracts[:6]):
            self.contract_table.insertRow(row_index)
            student_name = contract.student.full_name if contract.student else "--"
            room_number = contract.room.room_number if contract.room else "--"
            self.contract_table.setItem(row_index, 0, QTableWidgetItem(student_name))
            self.contract_table.setItem(row_index, 1, QTableWidgetItem(room_number))
            self.contract_table.setItem(row_index, 2, QTableWidgetItem(format_date(contract.end_date)))
            self.contract_table.setItem(row_index, 3, QTableWidgetItem(contract_status_label(contract.status)))

    def _refresh_student_dashboard(self, students, contracts, payments):
        student_contracts = [item for item in contracts if item.student and item.student.user_id == self.user.id]
        student_payments = [
            item
            for item in payments
            if item.contract and item.contract.student and item.contract.student.user_id == self.user.id
        ]
        active_contract = next((item for item in student_contracts if item.status == "active"), None)
        unpaid_total = sum(item.amount for item in student_payments if item.status == PaymentStatus.UNPAID)
        student_record = next((item for item in students if item.user_id == self.user.id), None)
        current_room = active_contract.room if active_contract and active_contract.room else (student_record.room if student_record else None)

        self.card_one.title_label.setText("Mã sinh viên")
        self.card_two.title_label.setText("Phòng hiện tại")
        self.card_three.title_label.setText("Hợp đồng")
        self.card_four.title_label.setText("Công nợ")

        self.card_one.update(student_record.student_id if student_record else "--", "Mã hồ sơ đang liên kết với tài khoản")
        self.card_two.update(
            current_room.room_number if current_room else "--",
            "Phòng đang lưu trú" if active_contract else ("Phòng đã chọn" if current_room else "Chưa chọn phòng"),
        )
        self.card_three.update(
            len(student_contracts),
            "Đã có hợp đồng hiệu lực" if active_contract else "Chưa có hợp đồng lưu trú đang hiệu lực",
        )
        self.card_four.update(format_currency(unpaid_total), "Tổng phí chưa thanh toán")

        if current_room and not active_contract:
            self.occupancy_summary.setText("Bạn đã chọn phòng. Thông tin hợp đồng sẽ được cập nhật trong bước tiếp theo.")
        elif current_room:
            self.occupancy_summary.setText("Thông tin phòng ở hiện tại của bạn.")
        else:
            self.occupancy_summary.setText("Chưa có phòng lưu trú. Hãy vào mục Phòng ở để lựa chọn.")

        self.occupancy_bar.setValue(100 if current_room else 0)
        self.populate_room_table([current_room] if current_room else [])
        self.contract_hint.setText(
            "Lịch sử hợp đồng cá nhân." if student_contracts else "Chưa có hợp đồng lưu trú. Có thể chọn phòng trong mục Phòng ở."
        )
        self.populate_contract_table(student_contracts)
