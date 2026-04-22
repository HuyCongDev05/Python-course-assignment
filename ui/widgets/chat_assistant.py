import html
import threading

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.chatbot_service import DormChatService


class ChatInput(QTextEdit):
    send_requested = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            event.accept()
            self.send_requested.emit()
            return
        super().keyPressEvent(event)


class ChatReplyEmitter(QObject):
    finished = pyqtSignal(int, str)
    failed = pyqtSignal(int, str)


class DormChatAssistant(QObject):
    PANEL_WIDTH = 400
    PANEL_HEIGHT = 560
    BUTTON_SIZE = 66
    EDGE_MARGIN = 24

    def __init__(self, user, parent_widget: QWidget):
        super().__init__(parent_widget)
        self.user = user
        self.parent_widget = parent_widget
        self._active_request_id = 0
        self._discard_pending_reply = False
        self._busy = False
        self._reply_emitter = ChatReplyEmitter()
        self._reply_emitter.finished.connect(self._handle_success)
        self._reply_emitter.failed.connect(self._handle_error)

        self._build_launcher_button()
        self._build_chat_panel()
        self.reset_conversation()
        self.reposition()

    def _build_launcher_button(self):
        self.launcher_button = QPushButton("AI", self.parent_widget)
        self.launcher_button.setObjectName("ChatLauncherButton")
        self.launcher_button.setCursor(Qt.PointingHandCursor)
        self.launcher_button.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self.launcher_button.clicked.connect(self.open_panel)
        self._apply_shadow(self.launcher_button, blur=32, y_offset=10)

    def _build_chat_panel(self):
        self.panel = QFrame(self.parent_widget)
        self.panel.setObjectName("ChatPanel")
        self.panel.setFixedSize(self.PANEL_WIDTH, self.PANEL_HEIGHT)
        self.panel.hide()
        self._apply_shadow(self.panel, blur=40, y_offset=14)

        root_layout = QVBoxLayout(self.panel)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)
        title = QLabel("Trợ lý ký túc xá")
        title.setObjectName("ChatTitle")
        header_text_layout.addWidget(title)

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("ChatCloseButton")
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setFixedSize(34, 34)
        self.close_button.clicked.connect(self.close_panel)

        header_layout.addLayout(header_text_layout, 1)
        header_layout.addWidget(self.close_button, 0, Qt.AlignTop)
        root_layout.addLayout(header_layout)

        self.status_label = QLabel("")
        self.status_label.setObjectName("ChatStatus")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        root_layout.addWidget(self.status_label)

        self.chat_log = QTextBrowser()
        self.chat_log.setObjectName("ChatLog")
        self.chat_log.setOpenExternalLinks(False)
        self.chat_log.setReadOnly(True)
        root_layout.addWidget(self.chat_log, 1)

        self.chat_input = ChatInput()
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.setPlaceholderText("Nhập câu hỏi về phòng ở, hợp đồng, điện, nước, hóa đơn...")
        self.chat_input.setFixedHeight(90)
        self.chat_input.send_requested.connect(self.submit_question)
        root_layout.addWidget(self.chat_input)

        input_footer = QHBoxLayout()
        input_footer.setSpacing(12)

        hint = QLabel("Enter để gửi, Shift+Enter để xuống dòng")
        hint.setObjectName("ChatHint")
        self.send_button = QPushButton("Gửi")
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.submit_question)

        input_footer.addWidget(hint, 1)
        input_footer.addWidget(self.send_button)
        root_layout.addLayout(input_footer)

    def _apply_shadow(self, widget, blur, y_offset):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, y_offset)
        shadow.setColor(QColor(14, 24, 34, 70))
        widget.setGraphicsEffect(shadow)

    def reposition(self):
        width = max(self.parent_widget.width() - self.EDGE_MARGIN * 2, 300)
        height = max(self.parent_widget.height() - self.EDGE_MARGIN * 2, 380)
        panel_width = min(self.PANEL_WIDTH, width)
        panel_height = min(self.PANEL_HEIGHT, height)

        panel_x = max(self.parent_widget.width() - panel_width - self.EDGE_MARGIN, self.EDGE_MARGIN)
        panel_y = max(self.parent_widget.height() - panel_height - self.EDGE_MARGIN, self.EDGE_MARGIN)
        button_x = max(self.parent_widget.width() - self.BUTTON_SIZE - self.EDGE_MARGIN, self.EDGE_MARGIN)
        button_y = max(self.parent_widget.height() - self.BUTTON_SIZE - self.EDGE_MARGIN, self.EDGE_MARGIN)

        self.panel.setFixedSize(panel_width, panel_height)
        self.panel.move(panel_x, panel_y)
        self.launcher_button.move(button_x, button_y)
        self.raise_to_front()

    def raise_to_front(self):
        if self.panel.isVisible():
            self.panel.raise_()
        self.launcher_button.raise_()

    def open_panel(self):
        self.launcher_button.hide()
        self.panel.show()
        self.raise_to_front()
        self.chat_input.setFocus()

    def close_panel(self):
        if self._busy:
            self._discard_pending_reply = True
        self.chat_input.clear()
        self.reset_conversation()
        self.panel.hide()
        self.launcher_button.show()
        self.raise_to_front()

    def reset_conversation(self):
        self.chat_log.clear()
        if not self._busy:
            self.status_label.clear()
            self.status_label.hide()

    def submit_question(self):
        question = self.chat_input.toPlainText().strip()
        if self._busy or not question:
            return

        self.append_message("Bạn", question)
        self.chat_input.clear()
        self._discard_pending_reply = False
        self._active_request_id += 1
        request_id = self._active_request_id

        worker_thread = threading.Thread(
            target=self._run_request,
            args=(request_id, question),
            daemon=True,
        )
        worker_thread.start()

    def append_message(self, author, message):
        safe_message = html.escape(message).replace("\n", "<br>")
        self.chat_log.append(
            f"<p><span style='color:#8a6b4d; font-weight:700;'>{html.escape(author)}</span><br>{safe_message}</p>"
        )
        scrollbar = self.chat_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _run_request(self, request_id, question):
        try:
            answer = DormChatService().ask(self.user.id, question)
        except Exception as exc:
            self._reply_emitter.failed.emit(request_id, str(exc))
            return
        self._reply_emitter.finished.emit(request_id, answer)

    def _handle_success(self, request_id, answer):
        if request_id != self._active_request_id:
            return
        self._set_busy(False, "Đã nạp dữ liệu mới nhất từ hệ thống.")
        if self._discard_pending_reply:
            self.reset_conversation()
        else:
            self.append_message("Ban quản lý ký túc xá", answer)
        self._discard_pending_reply = False

    def _handle_error(self, request_id, error_message):
        if request_id != self._active_request_id:
            return
        self._set_busy(False, "Không thể lấy câu trả lời từ trợ lý AI.")
        if self._discard_pending_reply:
            self.reset_conversation()
        else:
            self.append_message("Hệ thống", error_message)
        self._discard_pending_reply = False

    def _set_busy(self, busy, status_message):
        self._busy = busy
        self.send_button.setDisabled(busy)
        self.chat_input.setDisabled(busy)
        self.close_button.setDisabled(False)
        if busy and status_message:
            self.status_label.setText(status_message)
            self.status_label.show()
        else:
            self.status_label.clear()
            self.status_label.hide()
