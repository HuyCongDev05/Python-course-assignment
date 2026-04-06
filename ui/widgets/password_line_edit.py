import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QLineEdit


def _icon_path(name):
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons", name))


class PasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hidden_icon = QIcon(_icon_path("eye.svg"))
        self._visible_icon = QIcon(_icon_path("eye_off.svg"))
        self._password_visible = False

        self.setEchoMode(QLineEdit.Password)
        self._toggle_action = self.addAction(self._hidden_icon, QLineEdit.TrailingPosition)
        self._toggle_action.triggered.connect(self.toggle_password_visibility)
        self._sync_action()

    def toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        self.setEchoMode(QLineEdit.Normal if self._password_visible else QLineEdit.Password)
        self._sync_action()

    def _sync_action(self):
        self._toggle_action.setIcon(self._visible_icon if self._password_visible else self._hidden_icon)
        self._toggle_action.setToolTip("Ẩn mật khẩu" if self._password_visible else "Hiện mật khẩu")
