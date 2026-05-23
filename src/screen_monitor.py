"""Screen capture: PIL-based screenshot + manual crop + OCR."""

import os
from PIL import Image, ImageGrab
import numpy as np


class ScreenCapture:
    def __init__(self):
        self._reader = None

    def capture_text(self, region: tuple = None) -> str:
        """Take screenshot using PIL.ImageGrab, optionally crop, run OCR.

        Args:
            region: (left, top, right, bottom) in physical pixels.
        """
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

        if region:
            frame = np.array(ImageGrab.grab(bbox=region))
        else:
            frame = np.array(ImageGrab.grab())

        results = self._reader.readtext(frame)
        texts = []
        for _bbox, text, conf in results:
            text = text.strip()
            if conf > 0.5 and len(text) > 2:
                texts.append(text)
        return " ".join(texts)

    def cleanup(self):
        pass
