from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenu
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QBrush, QColor, QFont, QShortcut, QKeySequence


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setGeometry(100, 100, 520, 320)

        self._dragging = False
        self._drag_pos = QPoint()

        self._setup_ui()
        self._setup_hotkeys()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.question_label = QLabel()
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet(
            "color: rgba(180, 190, 210, 200); font-size: 13px;"
        )
        self.question_label.setVisible(False)

        self.answer_label = QLabel("监听中...")
        self.answer_label.setWordWrap(True)
        self.answer_label.setStyleSheet("color: white; font-size: 15px;")

        font = QFont()
        font.setFamilies(["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC"])
        self.question_label.setFont(font)
        self.answer_label.setFont(font)

        layout.addWidget(self.question_label)
        layout.addWidget(self.answer_label)
        self.setLayout(layout)

    def _setup_hotkeys(self):
        QShortcut(QKeySequence("Ctrl+Shift+H"), self, self._toggle_visible)
        QShortcut(QKeySequence("Ctrl+Shift+Q"), self, self.close)

    def _toggle_visible(self):
        self.setVisible(not self.isVisible())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(20, 20, 30, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, 0, 0), 12, 12)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("隐藏", self._toggle_visible)
        menu.addAction("退出", self.close)
        menu.exec(event.globalPos())

    def show_question(self, question: str):
        self.question_label.setText(f"问题: {question}")
        self.question_label.setVisible(True)
        self.answer_label.setText("")

    def on_answer_start(self):
        self.answer_label.setText("AI 思考中...")

    def append_answer(self, token: str):
        current = self.answer_label.text()
        if current in ("", "监听中...", "AI 思考中..."):
            self.answer_label.setText(token)
        else:
            self.answer_label.setText(current + token)
