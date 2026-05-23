"""Orchestrator: ties hotkey → screenshot → OCR → AI → overlay."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import QShortcut, QKeySequence

from .screen_monitor import ScreenCapture
from .audio_monitor import AudioMonitor
from .ai_client import AIClient
from .overlay import OverlayWindow


class Orchestrator(QObject):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.overlay = OverlayWindow()
        self.screen = ScreenCapture()
        self.ai = AIClient(config)

        # Audio is optional – continuous background monitoring
        self.audio = AudioMonitor(config) if config.get('deepseek_api_key') else None

        self._connect_signals()
        self._setup_hotkeys()
        self.app.aboutToQuit.connect(self._cleanup)

    def _connect_signals(self):
        self.ai.response_ready.connect(self.overlay.show_structured)
        if self.audio:
            self.audio.new_text.connect(self._on_audio_question)
        self.ai.response_token.connect(self._on_token)

    def _on_token(self, token: str):
        pass  # unused for hotkey flow

    def _on_audio_question(self, text: str):
        from .question_detector import QuestionDetector
        if not hasattr(self, '_qd'):
            self._qd = QuestionDetector(self.config)
            self._qd.new_question.connect(self._do_ask)
        self._qd.on_audio_text(text)

    def _do_ask(self, text: str):
        self.overlay.show_question(text)
        self.ai.ask(text)

    def _setup_hotkeys(self):
        # QShortcut works even when overlay is click-through (ApplicationShortcut context)
        s = QShortcut(QKeySequence("Ctrl+Shift+Z"), self.overlay, self._capture_and_ask)
        s.setContext(Qt.ShortcutContext.ApplicationShortcut)

    def _capture_and_ask(self):
        """Hotkey trigger: region selector → screenshot → OCR → AI → overlay."""
        from .region_selector import RegionSelector

        self.overlay.answer_view.setHtml(
            '<p style="color:#8af;font-size:16px;text-align:center">'
            '点击选择截图区域 (Esc 取消)</p>'
        )
        QApplication.processEvents()

        selector = RegionSelector()
        selector.region_selected.connect(self._on_region_selected)

    def _on_region_selected(self, region: tuple):
        self.overlay.show_question("识别中...")
        QApplication.processEvents()

        text = self.screen.capture_text(region=region)

        if not text or len(text) < 5:
            self.overlay.show_structured({
                "answer": "未识别到足够文字，请重试。\n"
                          "提示：尽量只框选题目部分。",
                "thought": "", "code": "", "complexity": "",
            })
            return

        self.overlay.show_question(text)
        self.ai.ask(text)

    def run(self):
        self.overlay.show()
        self.overlay.show_structured({
            "answer": "按 Ctrl+Shift+Z 框选截图提问\n"
                      "按住 Alt 拖拽浮窗 | 右键菜单切换穿透",
            "thought": "", "code": "", "complexity": "",
        })
        if self.audio:
            self.audio.start()
        sys.exit(self.app.exec())

    def _cleanup(self):
        self.screen.cleanup()
        if self.audio:
            self.audio.requestInterruption()
            self.audio.wait(2000)
        self.ai.abort()
        self.ai.wait(2000)
