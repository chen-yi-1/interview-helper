"""Full-screen region selector: dim screen, drag to select capture area."""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush


class RegionSelector(QWidget):
    region_selected = Signal(tuple)  # (left, top, right, bottom) in screen coords

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
        self._aborted = False

        screen = QApplication.primaryScreen()
        self._screen_geo = screen.availableGeometry()
        self._size = screen.size()
        self.showFullScreen()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

        if self._start and self._end:
            rect = QRect(self._start, self._end).normalized()
            # Highlight selected area
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # Border
            pen = QPen(QColor(74, 158, 255), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush())
            painter.drawRect(rect)

            # Size label
            label = f"{rect.width()} x {rect.height()}"
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Microsoft YaHei", 11)
            painter.setFont(font)
            painter.drawText(rect.topLeft() + QPoint(4, -6), label)

        # Instruction
        if not self._dragging:
            painter.setPen(QColor(255, 255, 255, 200))
            font = QFont("Microsoft YaHei", 14)
            painter.setFont(font)
            text = "拖动鼠标选择截图区域  ·  Esc 取消"
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, text)

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
            min_size = 20
            if rect.width() < min_size or rect.height() < min_size:
                # Too small → treat as full screen
                rect = QRect(0, 0, self._size.width(), self._size.height())

            # Get screen-relative coordinates
            left = rect.left()
            top = rect.top()
            right = rect.right()
            bottom = rect.bottom()

            self.close()
            self.region_selected.emit((left, top, right, bottom))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._aborted = True
            self.close()
