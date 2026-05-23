"""Full-screen region selector with drag-to-select."""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont


class RegionSelector(QWidget):
    region_selected = Signal(tuple)  # (left, top, right, bottom)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start = None
        self._end = None
        self._dragging = False

        screen = QApplication.primaryScreen()
        self._size = screen.size()
        self.setGeometry(0, 0, self._size.width(), self._size.height())
        self.showFullScreen()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

        if self._start and self._end:
            rect = QRect(self._start, self._end).normalized()

            # Clear the selected area (make it fully transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.eraseRect(rect)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # Border
            painter.setPen(QPen(QColor(74, 158, 255), 2))
            painter.setBrush(QColor(255, 255, 255, 0))
            painter.drawRect(rect)

            # Size label
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(rect.topLeft() + QPoint(4, -8),
                             f"{rect.width()} x {rect.height()}px")

        if not self._dragging:
            painter.setPen(QColor(255, 255, 255, 200))
            painter.setFont(QFont("Microsoft YaHei", 14))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
                             "拖动鼠标选择截图区域  ·  Esc 取消")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._end = event.position().toPoint()
            rect = QRect(self._start, self._end).normalized()

            if rect.width() < 20 or rect.height() < 20:
                rect = QRect(0, 0, self._size.width(), self._size.height())

            self._done((rect.left(), rect.top(), rect.right(), rect.bottom()))

    def _done(self, region):
        self.hide()
        self.region_selected.emit(region)
        self.deleteLater()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.deleteLater()
