"""Screen capture: PIL screenshot + PaddleOCR."""

from PIL import ImageGrab
import numpy as np


class ScreenCapture:
    def __init__(self):
        self._ocr = None

    def capture_text(self, region: tuple = None) -> str:
        """Take screenshot, optionally crop, run OCR, return text.

        Args:
            region: (left, top, right, bottom) in physical pixels, or None.
        """
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True, lang='ch', show_log=False, use_gpu=False,
            )

        if region:
            frame = np.array(ImageGrab.grab(bbox=region))
        else:
            frame = np.array(ImageGrab.grab())

        result = self._ocr.ocr(frame, cls=True)
        texts = []
        if result and len(result) > 0:
            for line in result:
                for item in line:
                    _, info = item[0], item[1]
                    text, conf = info[0], info[1]
                    text = text.strip()
                    if conf > 0.5 and len(text) > 2:
                        texts.append(text)
        return " ".join(texts)

    def cleanup(self):
        self._ocr = None
