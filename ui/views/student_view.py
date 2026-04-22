from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
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
from services.student_service import StudentService
from ui.dialogs.student_dialog import StudentDialog
from ui.widgets.hover_table_widget import HoverTableWidget


class StudentView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.is_admin_mode = bool(user and user.role == UserRole.ADMIN)
        self.student_service = StudentService()
        self.exchange_service = DataExchangeService()
        self.init_ui()
        self.load_students()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        header = QFrame()
        header.setObjectName("HeroPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)

        title_wrap = QVBoxLayout()
        title = QLabel("Quản lý sinh viên")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Nhấn đúp vào một dòng để mở hồ sơ và chỉnh sửa thông tin.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        actions = QHBoxLayout()
        actions.setSpacing(10)

        self.btn_import = QPushButton("Nạp từ Excel")
        self.btn_import.clicked.connect(self.import_students_from_excel)
        self.btn_import.setVisible(self.is_admin_mode)

        self.btn_add = QPushButton("Thêm sinh viên")
        self.btn_add.setObjectName("PrimaryButton")
        self.btn_add.clicked.connect(self.add_student_dialog)

        actions.addWidget(self.btn_import)
        actions.addWidget(self.btn_add)

        header_layout.addLayout(title_wrap, 1)
        header_layout.addLayout(actions, 0)
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo mã sinh viên, tên, số điện thoại hoặc email")
        self.search_input.textChanged.connect(self.load_students)
        toolbar.addWidget(self.search_input, 1)

        self.total_chip = QLabel()
        self.total_chip.setObjectName("InfoChip")
        self.account_chip = QLabel()
        self.account_chip.setObjectName("InfoChip")
        self.room_chip = QLabel()
        self.room_chip.setObjectName("InfoChip")
        for chip in (self.total_chip, self.account_chip, self.room_chip):
            chip.setAlignment(Qt.AlignCenter)
            chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        toolbar.addWidget(self.total_chip)
        toolbar.addWidget(self.account_chip)
        toolbar.addWidget(self.room_chip)
        layout.addLayout(toolbar)

        self.table = HoverTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Mã SV", "Họ tên", "Giới tính", "Điện thoại", "Email", "Phòng", "Tài khoản"]
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
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_student_dialog())
        layout.addWidget(self.table)

    def load_students(self):
        students = self.student_service.get_all_students(self.search_input.text())
        self.populate_table(students)

        self.total_chip.setText(f"{len(students)} hồ sơ")
        self.account_chip.setText(f"{sum(1 for item in students if item.user_id)} đã có tài khoản")
        self.room_chip.setText(f"{sum(1 for item in students if item.room_id)} đã gán phòng")

    def populate_table(self, students):
        self.table.setRowCount(0)
        for row_index, student in enumerate(students):
            self.table.insertRow(row_index)
            room_label = student.room.room_number if student.room else "--"
            account_label = "Đã kích hoạt" if student.user_id else "Chưa có"
            values = [
                str(student.id),
                student.student_id,
                student.full_name,
                student.gender or "--",
                student.phone or "--",
                student.email or "--",
                room_label,
                account_label,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))

    def get_selected_student_id(self):
        row_index = self.table.currentRow()
        if row_index < 0:
            return None
        item = self.table.item(row_index, 0)
        return int(item.text()) if item else None

    def add_student_dialog(self):
        dialog = StudentDialog(self)
        if dialog.exec_() and dialog.action == "save":
            try:
                self.student_service.add_student(dialog.get_data())
                self.load_students()
                QMessageBox.information(self, "Thành công", "Đã thêm sinh viên mới.")
            except Exception as exc:
                QMessageBox.critical(self, "Không thể lưu", str(exc))

    def edit_student_dialog(self):
        student_id = self.get_selected_student_id()
        if not student_id:
            QMessageBox.warning(self, "Chưa chọn dữ liệu", "Vui lòng chọn một sinh viên để chỉnh sửa.")
            return

        student = self.student_service.get_student_by_id(student_id)
        dialog = StudentDialog(self, student=student)
        if not dialog.exec_():
            return

        try:
            if dialog.action == "delete":
                self.student_service.delete_student(student_id)
                QMessageBox.information(self, "Thành công", "Đã xóa sinh viên.")
            else:
                self.student_service.update_student(student_id, dialog.get_data())
                QMessageBox.information(self, "Thành công", "Thông tin sinh viên đã được cập nhật.")
            self.load_students()
        except Exception as exc:
            QMessageBox.critical(self, "Không thể xử lý", str(exc))

    def import_students_from_excel(self):
        if not self.is_admin_mode:
            QMessageBox.warning(self, "Không có quyền", "Chỉ quản trị viên mới được phép nạp dữ liệu sinh viên.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file Excel sinh viên",
            "",
            "Excel Workbook (*.xlsx)",
        )
        if not file_path:
            return

        try:
            summary = self.exchange_service.import_students_from_excel(file_path)
            self.load_students()
            self.show_import_summary("sinh viên", summary)
        except Exception as exc:
            QMessageBox.critical(self, "Không thể nạp dữ liệu", str(exc))

    def show_import_summary(self, entity_label, summary):
        if summary.skipped_count == 0:
            QMessageBox.information(
                self,
                "Nạp dữ liệu thành công",
                f"Đã nạp thành công {summary.success_count} {entity_label}.",
            )
            return

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning if summary.success_count == 0 else QMessageBox.Information)
        dialog.setWindowTitle("Kết quả nạp dữ liệu")
        dialog.setText(
            f"Đã nạp thành công {summary.success_count} {entity_label}.\n"
            f"Bỏ qua {summary.skipped_count} dòng không hợp lệ hoặc bị trùng."
        )
        dialog.setInformativeText("Mở phần Chi tiết để xem từng lý do cụ thể.")
        dialog.setDetailedText("\n".join(summary.issues))
        dialog.exec_()
