from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QMenu, QScrollBar,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (
    QPainter, QBrush, QColor, QFont, QShortcut, QKeySequence, QTextCursor,
)


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

        self.setGeometry(100, 100, 520, 360)

        self._dragging = False
        self._drag_pos = QPoint()

        self._setup_ui()
        self._setup_hotkeys()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Question label (collapsible)
        self.question_label = QLabel()
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet(
            "color: rgba(180, 190, 210, 200); font-size: 13px;"
            "padding: 0px;"
        )
        self.question_label.setVisible(False)

        # Answer text area with scrollbar
        self.answer_view = QTextEdit()
        self.answer_view.setReadOnly(True)
        self.answer_view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.answer_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.answer_view.setStyleSheet("""
            QTextEdit {
                color: white;
                font-size: 15px;
                background: transparent;
                border: none;
                padding: 0px;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,20);
                width: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,80);
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,140);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        font = QFont()
        font.setFamilies(["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC"])
        self.question_label.setFont(font)
        self.answer_view.setFont(font)

        layout.addWidget(self.question_label)
        layout.addWidget(self.answer_view)
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
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def wheelEvent(self, event):
        # Forward scroll to the answer view
        self.answer_view.wheelEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("隐藏", self._toggle_visible)
        menu.addAction("退出", self.close)
        menu.exec(event.globalPos())

    def show_question(self, question: str):
        self.question_label.setText(f"问题: {question}")
        self.question_label.setVisible(True)
        self.answer_view.setPlainText("")

    def on_answer_start(self):
        self.answer_view.setPlainText("AI 思考中...")
        self._scroll_to_bottom()

    def append_answer(self, token: str):
        current = self.answer_view.toPlainText()
        if current in ("", "监听中...", "AI 思考中..."):
            self.answer_view.setPlainText(token)
        else:
            cursor = self.answer_view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(token)
            self.answer_view.setTextCursor(cursor)
        self._scroll_to_bottom()

    def finalize_answer(self):
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        sb = self.answer_view.verticalScrollBar()
        sb.setValue(sb.maximum())
