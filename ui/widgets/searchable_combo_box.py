from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class _ComboPopupFrame(QFrame):
    hidden = pyqtSignal()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.hidden.emit()


class SearchableComboBox(QComboBox):
    def __init__(self, parent=None, search_placeholder="Tìm nhanh..."):
        super().__init__(parent)
        self._search_placeholder = search_placeholder
        self._popup_visible = False

        self._popup = _ComboPopupFrame(None, Qt.Popup | Qt.FramelessWindowHint)
        self._popup.setObjectName("ComboPopup")
        self._popup.setAttribute(Qt.WA_StyledBackground, True)

        popup_layout = QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(10, 10, 10, 10)
        popup_layout.setSpacing(8)

        self._search_input = QLineEdit(self._popup)
        self._search_input.setObjectName("ComboSearchInput")
        self._search_input.setPlaceholderText(self._search_placeholder)

        self._list_widget = QListWidget(self._popup)
        self._list_widget.setObjectName("ComboSearchList")
        self._list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        popup_layout.addWidget(self._search_input)
        popup_layout.addWidget(self._list_widget)

        self._search_input.textChanged.connect(self._rebuild_popup_items)
        self._search_input.returnPressed.connect(self._activate_current_item)
        self._search_input.installEventFilter(self)
        self._list_widget.itemClicked.connect(self._handle_item_chosen)
        self._list_widget.itemActivated.connect(self._handle_item_chosen)
        self._popup.hidden.connect(self._handle_popup_hidden)

    def setSearchPlaceholderText(self, text):
        self._search_placeholder = text
        self._search_input.setPlaceholderText(text)

    def showPopup(self):
        if self._popup_visible:
            self.hidePopup()
            return

        self._search_input.clear()
        self._rebuild_popup_items("")
        self._update_popup_geometry()
        self._popup.show()
        self._popup_visible = True
        self._search_input.setFocus()

    def hidePopup(self):
        if self._popup.isVisible():
            self._popup.hide()
        self._handle_popup_hidden()

    def eventFilter(self, watched, event):
        if watched is self._search_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Down:
                self._move_current_row(1)
                return True
            if event.key() == Qt.Key_Up:
                self._move_current_row(-1)
                return True
            if event.key() == Qt.Key_Escape:
                self.hidePopup()
                return True
        return super().eventFilter(watched, event)

    def hideEvent(self, event):
        self.hidePopup()
        super().hideEvent(event)

    def _move_current_row(self, delta):
        if self._list_widget.count() == 0:
            return

        current_row = self._list_widget.currentRow()
        if current_row < 0:
            current_row = 0
        next_row = max(0, min(self._list_widget.count() - 1, current_row + delta))
        self._list_widget.setCurrentRow(next_row)

    def _activate_current_item(self):
        item = self._list_widget.currentItem()
        if item is not None:
            self._handle_item_chosen(item)

    def _handle_item_chosen(self, item):
        if item is None or not (item.flags() & Qt.ItemIsEnabled):
            return

        combo_index = item.data(Qt.UserRole)
        if combo_index is None:
            return

        self.setCurrentIndex(combo_index)
        self.hidePopup()

    def _handle_popup_hidden(self):
        self._popup_visible = False
        self._search_input.clear()

    def _rebuild_popup_items(self, query):
        self._list_widget.clear()
        current_item = None
        needle = (query or "").strip().lower()

        for index in range(self.count()):
            label = self.itemText(index)
            if needle and needle not in label.lower():
                continue

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, index)
            self._list_widget.addItem(item)

            if index == self.currentIndex():
                current_item = item

        if self._list_widget.count() == 0:
            empty_item = QListWidgetItem("Không tìm thấy kết quả")
            empty_item.setFlags(Qt.NoItemFlags)
            self._list_widget.addItem(empty_item)
            return

        self._list_widget.setCurrentItem(current_item or self._list_widget.item(0))

    def _update_popup_geometry(self):
        item_count = max(self._list_widget.count(), 1)
        row_height = self._list_widget.sizeHintForRow(0)
        row_height = max(row_height, 34) if row_height > 0 else 34
        list_height = min(item_count, 7) * row_height + 10
        self._list_widget.setFixedHeight(list_height)

        popup_width = max(self.width(), 420)
        popup_height = self._search_input.sizeHint().height() + list_height + 28

        below = self.mapToGlobal(self.rect().bottomLeft())
        above = self.mapToGlobal(self.rect().topLeft())
        screen = QApplication.desktop().availableGeometry(self)

        x_pos = below.x()
        y_pos = below.y() + 6

        if x_pos + popup_width > screen.right() - 12:
            x_pos = max(screen.left() + 12, screen.right() - popup_width - 12)

        if y_pos + popup_height > screen.bottom() - 12:
            above_y = above.y() - popup_height - 6
            if above_y >= screen.top() + 12:
                y_pos = above_y

        self._popup.setGeometry(x_pos, y_pos, popup_width, popup_height)


def style_combo_popups(*combos):
    for combo in combos:
        if combo is None or isinstance(combo, SearchableComboBox):
            continue

        view = QListView(combo)
        view.setObjectName("ComboPopupView")
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        combo.setView(view)
