"""Floating overlay: click-through by default, structured answer rendering."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QMenu, QApplication
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPainter, QBrush, QColor, QFont

MIN_HEIGHT = 60
MAX_HEIGHT_RATIO = 0.75
WIDTH = 520

HTML_TPL = """<style>
body {{ color: #ccc; font-family: {font}; font-size: 15px; }}
.thought {{ color: #999; font-size: 13px; margin: 4px 0; }}
.thought:before {{ content: "💡 思路: "; }}
.answer {{ color: #fff; font-size: 15px; margin: 8px 0; }}
.code {{
    background: rgba(255,255,255,0.06);
    border-left: 3px solid #4a9eff;
    padding: 10px 14px;
    margin: 8px 0;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
    white-space: pre-wrap;
    color: #e0e0e0;
    border-radius: 0 6px 6px 0;
}}
.complexity {{ color: #6af; font-size: 12px; margin: 6px 0; }}
.label {{ color: #888; font-size: 12px; margin: 0; }}
</style>
{body}"""


class OverlayWindow(QWidget):
    confirm_edit = Signal(str)
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._interactive = False
        self._max_height = self._calc_max_height()
        self.resize(WIDTH, MIN_HEIGHT)

        self._setup_ui()

    def _calc_max_height(self):
        screen = QApplication.primaryScreen()
        if screen:
            return int(screen.availableGeometry().height() * MAX_HEIGHT_RATIO)
        return 600

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)

        self.answer_view = QTextEdit()
        self.answer_view.setReadOnly(True)
        self.answer_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.answer_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.answer_view.setStyleSheet("""
            QTextEdit {
                background: transparent; border: none; padding: 0px;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,15); width: 8px;
                border-radius: 4px; margin: 2px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,70);
                border-radius: 4px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,120);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)

        font = QFont()
        font.setFamilies(["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC"])
        self.answer_view.setFont(font)

        layout.addWidget(self.answer_view)
        self.setLayout(layout)

    def toggle_visible(self):
        """Toggle visibility via opacity to avoid window-manager hide/show glitches."""
        if self.windowOpacity() > 0:
            self.setWindowOpacity(0)
        else:
            self.setWindowOpacity(1)

    # ── Click-through / Interactive mode ──

    def set_interactive(self, on: bool):
        self._interactive = on
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not on)
        if on:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.BlankCursor)

    def toggle_interactive(self):
        self.set_interactive(not self._interactive)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            self.set_interactive(True)
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.ControlModifier:
            if not self.answer_view.isReadOnly():
                text = self.answer_view.toPlainText()
                self.answer_view.setReadOnly(True)
                self.confirm_edit.emit(text)
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            self.set_interactive(False)
        super().keyReleaseEvent(event)

    # ── Painting ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(20, 20, 30, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, 0, 0), 12, 12)

    def wheelEvent(self, event):
        self.answer_view.wheelEvent(event)

    def mousePressEvent(self, event):
        if self._interactive and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, '_dragging', False):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_dragging', False) and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("点击穿透" if not self._interactive else "退出穿透", self.toggle_interactive)
        menu.addAction("隐藏/显示 (Ctrl+Shift+X)", self.toggle_visible)
        menu.addAction("退出程序 (Ctrl+Shift+H)", QApplication.quit)
        menu.exec(event.globalPos())

    # ── Public API ──

    def show_editable(self, text: str):
        """Show OCR text as editable for user review before sending to AI."""
        self.answer_view.setReadOnly(False)
        self.answer_view.setPlainText(text)
        self.answer_view.setStyleSheet("""
            QTextEdit {
                background: rgba(74,158,255,20); border: 1px solid #4a9eff;
                border-radius: 6px; padding: 8px; color: #fff; font-size: 14px;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,15); width: 8px;
                border-radius: 4px; margin: 2px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,70);
                border-radius: 4px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,120);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.answer_view.selectAll()
        QApplication.processEvents()
        self._adjust_size()

    def show_question(self, question: str):
        self.answer_view.setReadOnly(True)
        self._reset_stylesheet()
        self.answer_view.setHtml(
            HTML_TPL.format(font="sans-serif",
                            body=f'<p style="color:#999;font-size:13px">问题: {self._escape(question)}</p>'
                                 f'<p style="color:#888">AI 分析中...</p>')
        )
        QApplication.processEvents()
        self._adjust_size()

    def show_structured(self, data: dict):
        """Render structured JSON answer."""
        self.answer_view.setReadOnly(True)
        self._reset_stylesheet()
        parts = []
        font_family = "'Microsoft YaHei','PingFang SC',sans-serif"
        mono = "'Cascadia Code','Fira Code','Consolas',monospace"

        if data.get("thought"):
            parts.append(
                f'<div class="label">思路</div>'
                f'<div class="thought">{self._escape(data["thought"])}</div>'
            )
        if data.get("answer"):
            parts.append(
                f'<div class="label">答案</div>'
                f'<div class="answer">{self._escape(data["answer"])}</div>'
            )
        if data.get("code"):
            parts.append(
                f'<div class="label">代码</div>'
                f'<div class="code">{self._escape(data["code"])}</div>'
            )
        if data.get("complexity"):
            parts.append(
                f'<div class="complexity">复杂度: {self._escape(data["complexity"])}</div>'
            )

        body = "\n".join(parts)
        self.answer_view.setHtml(HTML_TPL.format(font=font_family, body=body))
        QApplication.processEvents()
        self._adjust_size()
        self._scroll_to_bottom()

    def _reset_stylesheet(self):
        self.answer_view.setStyleSheet("""
            QTextEdit {
                background: transparent; border: none; padding: 0px;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,15); width: 8px;
                border-radius: 4px; margin: 2px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,70);
                border-radius: 4px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,120);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)

    # ── Sizing ──

    def _adjust_size(self):
        self.answer_view.document().adjustSize()
        doc_h = self.answer_view.document().size().height()
        margins = self.layout().contentsMargins()
        total = int(margins.top() + margins.bottom() + doc_h + 10)
        new_h = max(MIN_HEIGHT, min(total, self._max_height))
        if abs(self.height() - new_h) > 5:
            self.resize(self.width(), new_h)

    def _scroll_to_bottom(self):
        sb = self.answer_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
