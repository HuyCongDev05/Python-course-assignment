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

from services.student_service import ContractService
from ui.dialogs.contract_dialog import ContractDialog
from ui.widgets.hover_table_widget import HoverTableWidget
from ui.widgets.searchable_combo_box import style_combo_popups
from utils.formatters import contract_status_label, format_currency, format_date


class ContractView(QWidget):
    def __init__(self):
        super().__init__()
        self.contract_service = ContractService()
        self.init_ui()
        self.load_contracts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        header = QFrame()
        header.setObjectName("HeroPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)

        title_wrap = QVBoxLayout()
        title = QLabel("Quản lý hợp đồng")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Nhấn đúp vào một dòng để sửa, kết thúc hoặc xóa hợp đồng ngay trong dialog.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        self.btn_add = QPushButton("Tạo hợp đồng")
        self.btn_add.setObjectName("PrimaryButton")
        self.btn_add.clicked.connect(self.add_contract_dialog)

        header_layout.addLayout(title_wrap, 1)
        header_layout.addWidget(self.btn_add, 0)
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo tên sinh viên, mã sinh viên hoặc số phòng")
        self.search_input.textChanged.connect(self.load_contracts)

        self.status_filter = QComboBox()
        style_combo_popups(self.status_filter)
        self.status_filter.addItem("Tất cả", "all")
        self.status_filter.addItem("Hiệu lực", "active")
        self.status_filter.addItem("Hết hạn", "expired")
        self.status_filter.addItem("Đã kết thúc", "terminated")
        self.status_filter.currentIndexChanged.connect(self.load_contracts)

        self.total_chip = QLabel()
        self.total_chip.setObjectName("InfoChip")
        self.active_chip = QLabel()
        self.active_chip.setObjectName("InfoChip")
        self.value_chip = QLabel()
        self.value_chip.setObjectName("InfoChip")
        for chip in (self.total_chip, self.active_chip, self.value_chip):
            chip.setAlignment(Qt.AlignCenter)
            chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.status_filter)
        toolbar.addWidget(self.total_chip)
        toolbar.addWidget(self.active_chip)
        toolbar.addWidget(self.value_chip)
        layout.addLayout(toolbar)

        self.table = HoverTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Sinh viên", "Mã SV", "Phòng", "Bắt đầu", "Kết thúc", "Giá trị", "Trạng thái"]
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
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_contract_dialog())
        layout.addWidget(self.table)

    def load_contracts(self):
        self.contract_service = ContractService()
        contracts = self.contract_service.get_all_contracts(self.search_input.text(), self.status_filter.currentData())
        self.populate_table(contracts)

        self.total_chip.setText(f"{len(contracts)} hợp đồng")
        self.active_chip.setText(f"{sum(1 for item in contracts if item.status == 'active')} đang hiệu lực")
        self.value_chip.setText(format_currency(sum(item.total_amount or 0 for item in contracts)))

    def populate_table(self, contracts):
        self.table.setRowCount(0)
        for row_index, contract in enumerate(contracts):
            self.table.insertRow(row_index)
            values = [
                str(contract.id),
                contract.student.full_name if contract.student else "--",
                contract.student.student_id if contract.student else "--",
                contract.room.room_number if contract.room else "--",
                format_date(contract.start_date),
                format_date(contract.end_date),
                format_currency(contract.total_amount),
                contract_status_label(contract.status),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))

    def get_selected_contract_id(self):
        row_index = self.table.currentRow()
        if row_index < 0:
            return None
        item = self.table.item(row_index, 0)
        return int(item.text()) if item else None

    def add_contract_dialog(self):
        students = self.contract_service.get_assignable_students()
        rooms = self.contract_service.get_room_candidates()
        if not students:
            QMessageBox.warning(self, "Không có dữ liệu", "Không còn sinh viên khả dụng để tạo hợp đồng.")
            return
        if not rooms:
            QMessageBox.warning(self, "Không có dữ liệu", "Không còn phòng trống khả dụng.")
            return

        dialog = ContractDialog(self, students=students, rooms=rooms)
        if dialog.exec_() and dialog.action == "save":
            try:
                self.contract_service.create_contract(dialog.get_data())
                self.load_contracts()
                QMessageBox.information(self, "Thành công", "Đã tạo hợp đồng mới.")
            except Exception as exc:
                QMessageBox.critical(self, "Không thể lưu", str(exc))

    def edit_contract_dialog(self):
        contract_id = self.get_selected_contract_id()
        if not contract_id:
            QMessageBox.warning(self, "Chưa chọn dữ liệu", "Vui lòng chọn một hợp đồng để chỉnh sửa.")
            return

        contract = self.contract_service.get_contract_by_id(contract_id)
        students = self.contract_service.get_assignable_students(include_student_id=contract.student_id)
        rooms = self.contract_service.get_room_candidates(include_room_id=contract.room_id)
        dialog = ContractDialog(self, contract=contract, students=students, rooms=rooms)
        if not dialog.exec_():
            return

        try:
            if dialog.action == "delete":
                self.contract_service.delete_contract(contract_id)
                QMessageBox.information(self, "Thành công", "Đã xóa hợp đồng.")
            elif dialog.action == "terminate":
                self.contract_service.terminate_contract(contract_id)
                QMessageBox.information(self, "Thành công", "Hợp đồng đã được kết thúc.")
            else:
                self.contract_service.update_contract(contract_id, dialog.get_data())
                QMessageBox.information(self, "Thành công", "Hợp đồng đã được cập nhật.")
            self.load_contracts()
        except Exception as exc:
            QMessageBox.critical(self, "Không thể xử lý", str(exc))
