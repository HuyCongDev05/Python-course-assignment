from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
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

from models import UserRole
from services.data_exchange_service import DataExchangeService
from services.student_service import RoomService, StudentService
from ui.dialogs.room_dialog import RoomDialog
from ui.dialogs.student_contract_dialog import StudentContractDialog
from ui.widgets.hover_table_widget import HoverTableWidget
from ui.widgets.searchable_combo_box import style_combo_popups
from utils.formatters import format_currency, room_status_label


class RoomView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.is_student_mode = bool(user and user.role == UserRole.STUDENT)
        self.is_admin_mode = bool(user and user.role == UserRole.ADMIN)
        self.room_service = RoomService()
        self.exchange_service = DataExchangeService()
        self.student_service = StudentService() if self.is_student_mode else None
        self.current_student = None
        self.init_ui()
        self.load_rooms()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        header = QFrame()
        header.setObjectName("HeroPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)

        title_wrap = QVBoxLayout()
        title = QLabel("Danh sách phòng ở" if self.is_student_mode else "Quản lý phòng ở")
        title.setObjectName("HeroTitle")
        subtitle = QLabel(
            "Chọn một phòng phù hợp để cập nhật hồ sơ lưu trú của bạn."
            if self.is_student_mode
            else "Nhấn đúp vào một dòng để mở phòng và xử lý ngay trong dialog."
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        actions = QHBoxLayout()
        actions.setSpacing(10)

        self.btn_import = QPushButton("Nạp từ Excel")
        self.btn_import.clicked.connect(self.import_rooms_from_excel)
        self.btn_import.setVisible(self.is_admin_mode and not self.is_student_mode)

        self.btn_primary = QPushButton("Chọn phòng đã chọn" if self.is_student_mode else "Thêm phòng")
        self.btn_primary.setObjectName("PrimaryButton")
        self.btn_primary.clicked.connect(self.select_room if self.is_student_mode else self.add_room_dialog)
        if self.is_student_mode:
            self.btn_primary.setEnabled(False)

        actions.addWidget(self.btn_import)
        actions.addWidget(self.btn_primary)

        header_layout.addLayout(title_wrap, 1)
        header_layout.addLayout(actions, 0)
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo số phòng hoặc phân loại")
        self.search_input.textChanged.connect(self.load_rooms)

        self.status_filter = QComboBox()
        style_combo_popups(self.status_filter)
        self.status_filter.addItem("Tất cả trạng thái", "all")
        self.status_filter.addItem("Còn trống", "available")
        self.status_filter.addItem("Đã đầy", "occupied")
        self.status_filter.addItem("Bảo trì", "maintenance")
        self.status_filter.currentIndexChanged.connect(self.load_rooms)

        self.total_chip = QLabel()
        self.total_chip.setObjectName("InfoChip")
        self.capacity_chip = QLabel()
        self.capacity_chip.setObjectName("InfoChip")
        self.maintenance_chip = QLabel()
        self.maintenance_chip.setObjectName("InfoChip")
        for chip in (self.total_chip, self.capacity_chip, self.maintenance_chip):
            chip.setAlignment(Qt.AlignCenter)
            chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.status_filter)
        toolbar.addWidget(self.total_chip)
        toolbar.addWidget(self.capacity_chip)
        toolbar.addWidget(self.maintenance_chip)
        layout.addLayout(toolbar)

        self.table = HoverTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Số phòng", "Phân loại", "Sức chứa", "Đang ở", "Giá thuê", "Trạng thái"]
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
        self.table.cellDoubleClicked.connect(lambda *_: self.handle_row_action())
        if self.is_student_mode:
            self.table.itemSelectionChanged.connect(self.update_student_action_state)
        layout.addWidget(self.table)

    def load_rooms(self):
        if self.is_student_mode:
            self.current_student = self.student_service.get_student_by_user_id(self.user.id)

        rooms = self.room_service.get_all_rooms(self.search_input.text(), self.status_filter.currentData())
        self.populate_table(rooms)

        if self.is_student_mode:
            selectable_rooms = [
                room
                for room in rooms
                if room.status.value != "maintenance"
                and (room.current_occupancy < room.capacity or (self.current_student and self.current_student.room_id == room.id))
            ]
            available_slots = sum(
                max(0, room.capacity - room.current_occupancy)
                for room in rooms
                if room.status.value != "maintenance"
            )
            self.total_chip.setText(f"{len(selectable_rooms)} phòng khả dụng")
            self.capacity_chip.setText(f"{available_slots} chỗ trống")
            self.maintenance_chip.setText(
                f"Đã chọn: {self.current_student.room.room_number}"
                if self.current_student and self.current_student.room
                else "Chưa chọn phòng"
            )
            self.update_student_action_state()
            return

        total_capacity = sum(room.capacity for room in rooms)
        total_occupancy = sum(room.current_occupancy for room in rooms)
        self.total_chip.setText(f"{len(rooms)} phòng")
        self.capacity_chip.setText(f"{total_occupancy}/{total_capacity} chỗ sử dụng" if total_capacity else "0 chỗ sử dụng")
        self.maintenance_chip.setText(f"{sum(1 for room in rooms if room.status.value == 'maintenance')} bảo trì")

    def populate_table(self, rooms):
        self.table.setRowCount(0)
        selected_row = -1
        current_room_id = self.current_student.room_id if self.is_student_mode and self.current_student else None

        for row_index, room in enumerate(rooms):
            self.table.insertRow(row_index)
            values = [
                str(room.id),
                room.room_number,
                room.room_type or "--",
                str(room.capacity),
                str(room.current_occupancy),
                format_currency(room.price),
                room_status_label(room.status),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
            if current_room_id and room.id == current_room_id:
                selected_row = row_index

        if selected_row >= 0:
            self.table.selectRow(selected_row)

    def get_selected_room_id(self):
        row_index = self.table.currentRow()
        if row_index < 0:
            return None
        item = self.table.item(row_index, 0)
        return int(item.text()) if item else None

    def update_student_action_state(self):
        if not self.is_student_mode:
            return

        room_id = self.get_selected_room_id()
        already_selected = bool(self.current_student and self.current_student.room_id == room_id)
        self.btn_primary.setEnabled(bool(room_id) and not already_selected)
        self.btn_primary.setText("Đã chọn phòng này" if already_selected else "Chọn phòng đã chọn")

    def handle_row_action(self):
        if self.is_student_mode:
            self.select_room()
            return
        self.edit_room_dialog()

    def add_room_dialog(self):
        dialog = RoomDialog(self)
        if dialog.exec_() and dialog.action == "save":
            try:
                self.room_service.add_room(dialog.get_data())
                self.load_rooms()
                QMessageBox.information(self, "Thành công", "Đã thêm phòng mới.")
            except Exception as exc:
                QMessageBox.critical(self, "Không thể lưu", str(exc))

    def edit_room_dialog(self):
        room_id = self.get_selected_room_id()
        if not room_id:
            QMessageBox.warning(self, "Chưa chọn dữ liệu", "Vui lòng chọn một phòng để chỉnh sửa.")
            return

        room = self.room_service.get_room_by_id(room_id)
        dialog = RoomDialog(self, room=room)
        if not dialog.exec_():
            return

        try:
            if dialog.action == "delete":
                self.room_service.delete_room(room_id)
                QMessageBox.information(self, "Thành công", "Đã xóa phòng.")
            else:
                self.room_service.update_room(room_id, dialog.get_data())
                QMessageBox.information(self, "Thành công", "Thông tin phòng đã được cập nhật.")
            self.load_rooms()
        except Exception as exc:
            QMessageBox.critical(self, "Không thể xử lý", str(exc))

    def select_room(self):
        if not self.is_student_mode:
            return

        room_id = self.get_selected_room_id()
        if not room_id:
            QMessageBox.warning(self, "Chưa chọn phòng", "Vui lòng chọn một phòng trong danh sách.")
            return

        if self.current_student and self.current_student.room_id == room_id:
            QMessageBox.information(self, "Thông tin", "Phòng này đã được gắn với hồ sơ của bạn.")
            return

        room = self.room_service.get_room_by_id(room_id)
        if not room:
            QMessageBox.warning(self, "Không tìm thấy dữ liệu", "Phòng đã chọn không còn tồn tại.")
            return

        # Mở dialog nhập ngày hợp đồng — thay thế hộp xác nhận đơn giản
        dialog = StudentContractDialog(self, room=room)
        if dialog.exec_() != StudentContractDialog.Accepted:
            return

        start_date = dialog.get_start_date()
        end_date = dialog.get_end_date()

        try:
            self.room_service.select_room_for_student(self.user.id, room_id, start_date, end_date)
            self.load_rooms()
            QMessageBox.information(
                self,
                "Đăng ký thành công",
                f"Đã chọn phòng {room.room_number}.\n"
                f"Hợp đồng lưu trú và phiếu thanh toán tháng đầu đã được tạo tự động.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Không thể chọn phòng", str(exc))

    def import_rooms_from_excel(self):
        if not self.is_admin_mode or self.is_student_mode:
            QMessageBox.warning(self, "Không có quyền", "Chỉ quản trị viên mới được phép nạp dữ liệu phòng.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file Excel phòng",
            "",
            "Excel Workbook (*.xlsx)",
        )
        if not file_path:
            return

        try:
            summary = self.exchange_service.import_rooms_from_excel(file_path)
            self.load_rooms()
            self.show_import_summary(summary)
        except Exception as exc:
            QMessageBox.critical(self, "Không thể nạp dữ liệu", str(exc))

    def show_import_summary(self, summary):
        if summary.skipped_count == 0:
            QMessageBox.information(
                self,
                "Nạp dữ liệu thành công",
                f"Đã nạp thành công {summary.success_count} phòng.",
            )
            return

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning if summary.success_count == 0 else QMessageBox.Information)
        dialog.setWindowTitle("Kết quả nạp dữ liệu")
        dialog.setText(
            f"Đã nạp thành công {summary.success_count} phòng.\n"
            f"Bỏ qua {summary.skipped_count} dòng không hợp lệ hoặc bị trùng."
        )
        dialog.setInformativeText("Mở phần Chi tiết để xem từng lý do cụ thể.")
        dialog.setDetailedText("\n".join(summary.issues))
        dialog.exec_()
