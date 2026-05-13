from PyQt5.QtCore import QEvent, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QGraphicsBlurEffect, QLabel, QVBoxLayout, QWidget


class SpinnerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._advance)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def sizeHint(self):
        return QSize(64, 64)

    def start(self):
        self._angle = 0
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def stop(self):
        self._timer.stop()
        self._angle = 0
        self.update()

    def _advance(self):
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(7, 7, -7, -7)

        track_pen = QPen(QColor(255, 255, 255, 50), 6)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        arc_pen = QPen(QColor("#d08c2d"), 6)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(rect, (-self._angle + 35) * 16, -235 * 16)


class LoadingOverlay(QWidget):
    def __init__(self, parent, blur_target=None):
        super().__init__(parent)
        self._blur_target = blur_target or parent
        self._blur_effect = None

        self.setObjectName("LoadingOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        panel = QFrame(self)
        panel.setObjectName("LoadingPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(26, 24, 26, 24)
        panel_layout.setSpacing(14)
        panel_layout.setAlignment(Qt.AlignCenter)

        self.spinner = SpinnerWidget(panel)
        self.message_label = QLabel("Đang tải dữ liệu...", panel)
        self.message_label.setObjectName("LoadingMessage")
        self.message_label.setAlignment(Qt.AlignCenter)

        panel_layout.addWidget(self.spinner, 0, Qt.AlignCenter)
        panel_layout.addWidget(self.message_label, 0, Qt.AlignCenter)
        layout.addWidget(panel, 0, Qt.AlignCenter)

        parent.installEventFilter(self)
        self._sync_geometry()

    def show_overlay(self, message="Đang tải dữ liệu..."):
        self.message_label.setText(message)
        self._sync_geometry()
        self._apply_blur(True)
        self.spinner.start()
        self.show()
        self.raise_()

    def hide_overlay(self):
        self.spinner.stop()
        self.hide()
        self._apply_blur(False)

    def eventFilter(self, watched, event):
        if watched == self.parentWidget() and event.type() in {QEvent.Resize, QEvent.Move, QEvent.Show}:
            self._sync_geometry()
        return super().eventFilter(watched, event)

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(18, 27, 34, 118))

    def _sync_geometry(self):
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def _apply_blur(self, enabled):
        if self._blur_target is None:
            return

        if enabled:
            if self._blur_effect is None:
                self._blur_effect = QGraphicsBlurEffect(self._blur_target)
                self._blur_effect.setBlurRadius(7)
            self._blur_target.setGraphicsEffect(self._blur_effect)
            return

        self._blur_target.setGraphicsEffect(None)
