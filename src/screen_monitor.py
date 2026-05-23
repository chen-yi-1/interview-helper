"""Screen capture: single-shot screenshot + OCR, triggered by hotkey."""


class ScreenCapture:
    def __init__(self):
        self._camera = None
        self._reader = None

    def capture_text(self, region: tuple = None) -> str:
        """Take screenshot (optionally of a region), run OCR, return text.

        Args:
            region: (left, top, right, bottom) or None for full screen.
        """
        if self._camera is None:
            import dxcam
            self._camera = dxcam.create(output_idx=0)
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

        frame = self._camera.grab(region=region)
        if frame is None:
            return ""

        results = self._reader.readtext(frame)
        texts = []
        for _bbox, text, conf in results:
            text = text.strip()
            if conf > 0.5 and len(text) > 2:
                texts.append(text)
        return " ".join(texts)

    def cleanup(self):
        if self._camera is not None:
            del self._camera
            self._camera = None
