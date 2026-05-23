import re
import hashlib
import time
from PySide6.QtCore import QObject, Signal


class QuestionDetector(QObject):
    new_question = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.cooldown = config.get('cooldown_seconds', 10)
        self.last_question_time = 0
        self.recent_questions = set()
        self.screen_candidates = []
        self.audio_candidates = []

    def on_screen_text(self, text: str):
        if self._looks_like_question(text):
            self.screen_candidates.append((time.time(), text))
            self._try_emit()

    def on_audio_text(self, text: str):
        if self._looks_like_question(text):
            self.audio_candidates.append((time.time(), text))
            self._try_emit()

    def _try_emit(self):
        if not self._can_trigger():
            return

        now = time.time()
        self.screen_candidates = [(t, s) for t, s in self.screen_candidates if now - t < 3]
        self.audio_candidates = [(t, s) for t, s in self.audio_candidates if now - t < 3]

        best = ""
        for _ts, text in self.screen_candidates + self.audio_candidates:
            if len(text) > len(best):
                best = text

        if best and not self._is_duplicate(best):
            self.last_question_time = now
            self.recent_questions.add(self._hash(best))
            if len(self.recent_questions) > 50:
                self.recent_questions.clear()
            self.screen_candidates.clear()
            self.audio_candidates.clear()
            self.new_question.emit(best)

    def _looks_like_question(self, text: str) -> bool:
        if len(text) < 5:
            return False
        patterns = [
            r'[？?]',
            r'^(请|你|如何|什么|为什么|怎么|解释|描述|说说|列举|介绍|比较|区别|阐述|说明|谈谈)',
            r'[吗呢么吧]$',
            r'是.*还是',
            r'是否|是不是|有没有|能不能|会不会|要不要',
        ]
        return any(re.search(p, text) for p in patterns)

    def _can_trigger(self) -> bool:
        return time.time() - self.last_question_time > self.cooldown

    def _is_duplicate(self, text: str) -> bool:
        h = self._hash(text)
        return h in self.recent_questions

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()
