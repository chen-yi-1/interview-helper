import sys
from PySide6.QtWidgets import QApplication
from .screen_monitor import ScreenMonitor
from .audio_monitor import AudioMonitor
from .question_detector import QuestionDetector
from .ai_client import AIClient
from .overlay import OverlayWindow


class Orchestrator:
    def __init__(self, config):
        self.config = config
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.overlay = OverlayWindow()
        self.question_detector = QuestionDetector(config)
        self.ai_client = AIClient(config)
        self.screen_monitor = ScreenMonitor(config)
        self.audio_monitor = AudioMonitor(config)

        self._connect_signals()
        self.app.aboutToQuit.connect(self._cleanup)

    def _connect_signals(self):
        self.screen_monitor.new_text.connect(self.question_detector.on_screen_text)
        self.audio_monitor.new_text.connect(self.question_detector.on_audio_text)
        self.question_detector.new_question.connect(self._on_question)
        self.ai_client.response_start.connect(self.overlay.on_answer_start)
        self.ai_client.response_token.connect(self.overlay.append_answer)

    def _on_question(self, question: str):
        self.overlay.show_question(question)
        self.ai_client.ask(question)

    def run(self):
        self.overlay.show()
        self.screen_monitor.start()
        self.audio_monitor.start()
        sys.exit(self.app.exec())

    def _cleanup(self):
        self.screen_monitor.requestInterruption()
        self.audio_monitor.requestInterruption()
        self.screen_monitor.wait(3000)
        self.audio_monitor.wait(3000)
        self.ai_client.abort()
        self.ai_client.wait(3000)
