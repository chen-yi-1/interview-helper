"""Orchestrator: ties hotkey → screenshot → OCR → AI → overlay."""

import sys
import time
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QAbstractNativeEventFilter, QTimer

from .screen_monitor import ScreenCapture
from .audio_monitor import AudioMonitor
from .ai_client import AIClient
from .overlay import OverlayWindow

# WinAPI constants
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000


class _GlobalHotkeyFilter(QAbstractNativeEventFilter):
    """Intercepts WM_HOTKEY messages and routes to registered callbacks."""

    def __init__(self):
        super().__init__()
        self._callbacks = {}
        self._last_fire = {}

    def register(self, hotkey_id: int, mods: int, vk: int, callback):
        ctypes.windll.user32.RegisterHotKey(None, hotkey_id, mods, vk)
        self._callbacks[hotkey_id] = callback

    def unregister_all(self):
        for hid in list(self._callbacks):
            ctypes.windll.user32.UnregisterHotKey(None, hid)
        self._callbacks.clear()
        self._last_fire.clear()

    def nativeEventFilter(self, eventType, message):
        if eventType != "windows_generic_MSG":
            return False, 0
        msg = ctypes.wintypes.MSG.from_address(message.__int__())
        if msg.message == WM_HOTKEY and msg.wParam in self._callbacks:
            now = time.monotonic()
            if now - self._last_fire.get(msg.wParam, 0) < 0.3:
                return True, 0  # debounce rapid repeats
            self._last_fire[msg.wParam] = now
            # Defer to next event loop cycle to avoid re-entrancy issues
            QTimer.singleShot(0, self._callbacks[msg.wParam])
            return True, 0
        return False, 0


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
        self._setup_global_hotkeys()
        self.app.aboutToQuit.connect(self._cleanup)

    def _connect_signals(self):
        self.ai.response_ready.connect(self.overlay.show_structured)
        self.overlay.confirm_edit.connect(self._on_confirm_edit)
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

    def _setup_global_hotkeys(self):
        """Global hotkeys via WinAPI — work even when app is in background."""
        self._hotkey_filter = _GlobalHotkeyFilter()
        self.app.installNativeEventFilter(self._hotkey_filter)
        self._hotkey_filter.register(1, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x5A, self._capture_and_ask)  # Z
        self._hotkey_filter.register(2, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x48, QApplication.quit)    # H
        self._hotkey_filter.register(3, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x58, self.overlay.toggle_visible)  # X

    def _capture_and_ask(self):
        """Hotkey trigger: region selector → screenshot → OCR → AI → overlay."""
        from .region_selector import RegionSelector

        self._selector = RegionSelector()
        self._selector.region_selected.connect(self._on_region_selected)

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

        self.overlay.show_editable(text)

    def _on_confirm_edit(self, text: str):
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
        self._hotkey_filter.unregister_all()
        self.screen.cleanup()
        if self.audio:
            self.audio.requestInterruption()
            self.audio.wait(2000)
        self.ai.abort()
        self.ai.wait(2000)
