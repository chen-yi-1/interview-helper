from PySide6.QtCore import QThread, Signal


class ScreenMonitor(QThread):
    new_text = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.interval = config.get('ocr_interval', 2.0)

    def run(self):
        import dxcam
        import easyocr

        camera = dxcam.create()
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
        previous_texts = set()

        try:
            while not self.isInterruptionRequested():
                frame = camera.grab()
                if frame is None:
                    self.msleep(100)
                    continue

                results = reader.readtext(frame)
                current_texts = set()

                for _bbox, text, conf in results:
                    text = text.strip()
                    if conf > 0.5 and len(text) > 2:
                        current_texts.add(text)

                new_texts = current_texts - previous_texts
                if new_texts:
                    combined = " ".join(sorted(new_texts))
                    self.new_text.emit(combined)

                previous_texts = current_texts
                self.msleep(int(self.interval * 1000))
        finally:
            del camera
