from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models import UserRole
from ui.widgets.chat_assistant import DormChatAssistant
from .contract_view import ContractView
from .dashboard_view import DashboardView
from .export_view import ExportView
from .payment_view import PaymentView
from .room_view import RoomView
from .student_view import StudentView


class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("DormManager | Hệ thống quản lý ký túc xá")
        self.resize(1440, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 22, 20, 22)
        sidebar_layout.setSpacing(14)

        brand_card = QFrame()
        brand_card.setObjectName("BrandCard")
        brand_layout = QVBoxLayout(brand_card)
        brand_layout.setContentsMargins(18, 18, 18, 18)
        brand_layout.setSpacing(6)
        brand_title = QLabel("DormManager")
        brand_title.setObjectName("BrandTitle")
        brand_subtitle = QLabel("Quản lý lưu trú, hợp đồng và thanh toán trên một nền tảng thống nhất.")
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_subtitle.setWordWrap(True)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)
        sidebar_layout.addWidget(brand_card)

        user_card = QFrame()
        user_card.setObjectName("UserCard")
        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(18, 18, 18, 18)
        user_layout.setSpacing(4)
        user_name = QLabel(self.user.full_name or self.user.username)
        user_name.setObjectName("UserName")
        user_role = QLabel(self.role_label(self.user.role))
        user_role.setObjectName("RoleChip")
        user_role.setAlignment(Qt.AlignCenter)
        user_role.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        user_layout.addWidget(user_name)
        user_layout.addWidget(user_role, 0, Qt.AlignLeft)
        sidebar_layout.addWidget(user_card)

        nav_title = QLabel("Điều hướng")
        nav_title.setObjectName("NavTitle")
        sidebar_layout.addWidget(nav_title)

        self.btn_dashboard = self.build_nav_button("Dashboard")
        self.btn_students = self.build_nav_button("Sinh viên")
        self.btn_rooms = self.build_nav_button("Phòng ở")
        self.btn_contracts = self.build_nav_button("Hợp đồng")
        self.btn_payments = self.build_nav_button("Thanh toán")
        self.btn_exports = self.build_nav_button("Xuất file")

        for button in [
            self.btn_dashboard,
            self.btn_students,
            self.btn_rooms,
            self.btn_contracts,
            self.btn_payments,
            self.btn_exports,
        ]:
            sidebar_layout.addWidget(button)

        if self.user.role == UserRole.STUDENT:
            self.btn_students.hide()
            self.btn_contracts.hide()
            self.btn_exports.hide()
        elif self.user.role != UserRole.ADMIN:
            self.btn_exports.hide()

        sidebar_layout.addStretch()

        self.btn_logout = QPushButton("Đăng xuất")
        self.btn_logout.setObjectName("DangerButton")
        self.btn_logout.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.btn_logout)

        content_shell = QFrame()
        content_shell.setObjectName("ContentShell")
        content_layout = QVBoxLayout(content_shell)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.content_area = QStackedWidget()
        self.content_area.setObjectName("ContentArea")

        self.dashboard_view = DashboardView(self.user)
        self.student_view = StudentView(self.user)
        self.room_view = RoomView(self.user)
        self.contract_view = ContractView()
        self.payment_view = PaymentView(self.user)
        self.export_view = ExportView(self.user)

        self.content_area.addWidget(self.dashboard_view)
        self.content_area.addWidget(self.student_view)
        self.content_area.addWidget(self.room_view)
        self.content_area.addWidget(self.contract_view)
        self.content_area.addWidget(self.payment_view)
        self.content_area.addWidget(self.export_view)
        content_layout.addWidget(self.content_area)

        self.btn_dashboard.clicked.connect(lambda: self.switch_view(0, self.btn_dashboard))
        self.btn_students.clicked.connect(lambda: self.switch_view(1, self.btn_students))
        self.btn_rooms.clicked.connect(lambda: self.switch_view(2, self.btn_rooms))
        self.btn_contracts.clicked.connect(lambda: self.switch_view(3, self.btn_contracts))
        self.btn_payments.clicked.connect(lambda: self.switch_view(4, self.btn_payments))
        self.btn_exports.clicked.connect(lambda: self.switch_view(5, self.btn_exports))

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_shell, 1)

        self.chat_assistant = DormChatAssistant(self.user, central_widget)

        self.btn_dashboard.setChecked(True)
        self.switch_view(0, self.btn_dashboard)

    def build_nav_button(self, label):
        button = QPushButton(label)
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        return button

    def switch_view(self, index, active_button):
        for button in [
            self.btn_dashboard,
            self.btn_students,
            self.btn_rooms,
            self.btn_contracts,
            self.btn_payments,
            self.btn_exports,
        ]:
            if button != active_button:
                button.setChecked(False)

        active_view = self.content_area.widget(index)
        for method_name in [
            "load_students",
            "load_rooms",
            "load_contracts",
            "load_payments",
            "refresh_stats",
            "refresh_directory_labels",
        ]:
            if hasattr(active_view, method_name):
                getattr(active_view, method_name)()

        self.content_area.setCurrentIndex(index)
        self.chat_assistant.raise_to_front()

    def role_label(self, role):
        return {
            UserRole.ADMIN: "Quản trị viên",
            UserRole.STAFF: "Nhân viên",
            UserRole.STUDENT: "Sinh viên",
        }.get(role, "Người dùng")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "chat_assistant"):
            self.chat_assistant.reposition()

    def handle_logout(self):
        self.logout_signal.emit()
        self.close()
