"""Orchestrator: ties hotkey → screenshot → OCR → AI → overlay."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QTimer

from .screen_monitor import ScreenCapture
from .audio_monitor import AudioMonitor
from .ai_client import AIClient
from .overlay import OverlayWindow
from .hotkey_manager import HotkeyManager


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
            # Also connect screen monitor error states
        # For streaming tokens during audio flow
        self.ai.response_token.connect(self._on_token)

    def _on_token(self, token: str):
        """Streaming token from audio-triggered AI (not used in hotkey flow)."""
        pass  # currently unused; could show live tokens

    def _on_audio_question(self, text: str):
        """Audio detected a question → send to AI."""
        from .question_detector import QuestionDetector
        if not hasattr(self, '_qd'):
            self._qd = QuestionDetector(self.config)
            self._qd.new_question.connect(self._do_ask)
        self._qd.on_audio_text(text)

    def _do_ask(self, text: str):
        self.overlay.show_question(text)
        self.ai.ask(text)

    def _setup_hotkeys(self):
        self.hotkey_mgr = HotkeyManager()
        self.hotkey_mgr.register('ctrl+shift+q', self._capture_and_ask)

    def _capture_and_ask(self):
        """Hotkey trigger: region selector → screenshot → OCR → AI → overlay."""
        from .region_selector import RegionSelector

        # Flash feedback: show that hotkey was received
        self.overlay.answer_view.setHtml(
            '<p style="color:#8af;font-size:16px;text-align:center">'
            '⏎ 热键已触发，请选择截图区域...</p>'
        )
        QApplication.processEvents()

        # Show region selector
        selector = RegionSelector()
        selector.region_selected.connect(self._on_region_selected)
        selector.show()

    def _on_region_selected(self, region: tuple):
        self.overlay.show_question("识别中...")
        QApplication.processEvents()

        text = self.screen.capture_text(region=region)

        if not text or len(text) < 5:
            self.overlay.show_structured({
                "answer": "未识别到足够文字，请重试。\n"
                          "提示：截图区域尽量只包含题目部分。",
                "thought": "", "code": "", "complexity": "",
            })
            return

        self.overlay.show_question(text)
        self.ai.ask(text)

    def run(self):
        self.overlay.show()
        self.overlay.show_structured({
            "answer": "按 Ctrl+Shift+Q 截图提问\n按住 Alt 拖拽浮窗\n右键菜单切换穿透模式",
            "thought": "", "code": "", "complexity": "",
        })
        if self.audio:
            self.audio.start()
        sys.exit(self.app.exec())

    def _cleanup(self):
        self.hotkey_mgr.unregister_all()
        self.screen.cleanup()
        if self.audio:
            self.audio.requestInterruption()
            self.audio.wait(2000)
        self.ai.abort()
        self.ai.wait(2000)
