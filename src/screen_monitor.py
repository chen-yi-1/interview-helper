"""Screen capture: single-shot screenshot + OCR, triggered by hotkey."""


class ScreenCapture:
    def __init__(self):
        self._camera = None
        self._reader = None

    def capture_text(self) -> str:
        """Take one screenshot, run OCR, return extracted text."""
        if self._camera is None:
            import dxcam
            self._camera = dxcam.create()
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

        frame = self._camera.grab()
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
