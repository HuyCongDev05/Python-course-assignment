from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem


class HoverTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_row = -1
        self._base_color = QColor("#fffdfa")
        self._alternate_color = QColor("#fbf6f0")
        self._hover_color = QColor("#f1e3cd")
        self._selected_color = QColor("#e2bf8f")
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.cellEntered.connect(self._on_cell_entered)
        self.itemSelectionChanged.connect(self._refresh_all_rows)

    def _on_cell_entered(self, row, _column):
        self._set_hover_row(row)

    def leaveEvent(self, event):
        self._set_hover_row(-1)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        self._set_hover_row(index.row() if index.isValid() else -1)
        super().mouseMoveEvent(event)

    def _set_hover_row(self, row):
        if row == self._hover_row:
            return
        previous_row = self._hover_row
        self._hover_row = row
        self._refresh_row(previous_row)
        self._refresh_row(row)

    def _row_color(self, row):
        if row == self._hover_row:
            return self._hover_color

        for column in range(self.columnCount()):
            item = self.item(row, column)
            if item is not None and item.isSelected():
                return self._selected_color

        return self._alternate_color if row % 2 else self._base_color

    def _refresh_row(self, row):
        if row < 0:
            return
        row_color = self._row_color(row)
        for column in range(self.columnCount()):
            item = self.item(row, column)
            if item is not None:
                item.setBackground(row_color)

    def _refresh_all_rows(self):
        for row in range(self.rowCount()):
            self._refresh_row(row)

    def setRowCount(self, rows):
        super().setRowCount(rows)
        self._hover_row = -1

    def setItem(self, row, column, item):
        if not isinstance(item, QTableWidgetItem):
            super().setItem(row, column, item)
            return
        super().setItem(row, column, item)
        self._refresh_row(row)
