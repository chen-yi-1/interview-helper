import queue
import numpy as np
from PySide6.QtCore import QThread, Signal


class AudioMonitor(QThread):
    new_text = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.sample_rate = config.get('audio_sample_rate', 16000)
        self.vad_threshold = config.get('vad_threshold', 0.5)
        self.silence_duration = config.get('silence_duration', 1.5)
        self.whisper_model = config.get('whisper_model', 'base')
        self.whisper_device = config.get('whisper_device', 'cpu')
        self.language = config.get('language', 'zh')
        self.audio_device_index = config.get('audio_device_index')

    def run(self):
        import sounddevice as sd
        from faster_whisper import WhisperModel

        whisper = WhisperModel(
            self.whisper_model,
            device=self.whisper_device,
            compute_type='int8',
        )

        device_idx = self.audio_device_index
        if device_idx is None:
            device_idx = self._find_loopback_device()

        if device_idx is None:
            print("警告: 未找到 WASAPI 音频回环设备, 音频监听不可用")
            return

        audio_queue = queue.Queue()
        is_recording = False
        audio_buffer = []
        silence_samples = 0
        silence_limit = int(self.sample_rate * self.silence_duration)

        def _create_vad():
            try:
                from silero_vad import load_silero_vad, get_speech_timestamps
                model = load_silero_vad()
                return lambda x: len(get_speech_timestamps(
                    x, model, threshold=self.vad_threshold,
                    sampling_rate=self.sample_rate,
                )) > 0
            except Exception:
                print("警告: silero-vad 加载失败, 使用能量阈值 VAD")
                return lambda x: np.max(np.abs(x)) > 0.02

        vad_fn = _create_vad()

        def callback(indata, frames, _time, _status):
            audio_queue.put(indata.copy())

        stream = sd.InputStream(
            device=device_idx,
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=callback,
        )

        with stream:
            while not self.isInterruptionRequested():
                try:
                    frames = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                frame_flat = frames.flatten()
                is_speech = vad_fn(frame_flat)

                if is_speech:
                    if not is_recording:
                        is_recording = True
                        audio_buffer = []
                    audio_buffer.append(frames)
                    silence_samples = 0
                elif is_recording:
                    silence_samples += len(frames)
                    audio_buffer.append(frames)
                    if silence_samples > silence_limit:
                        audio_data = np.concatenate(audio_buffer)
                        is_recording = False
                        audio_buffer = []
                        silence_samples = 0
                        worker = TranscribeWorker(
                            whisper, audio_data, self.language, self.new_text
                        )
                        worker.start()

            if is_recording and audio_buffer:
                audio_data = np.concatenate(audio_buffer)
                if len(audio_data) > self.sample_rate * 0.5:
                    TranscribeWorker(
                        whisper, audio_data, self.language, self.new_text
                    ).start()

    def _find_loopback_device(self):
        import sounddevice as sd
        hostapis = sd.query_hostapis()
        for ha in hostapis:
            if 'wasapi' in ha['name'].lower():
                for dev_idx in ha['devices']:
                    dev = sd.query_devices(dev_idx)
                    if dev['max_input_channels'] > 0:
                        print(f"使用 WASAPI 设备: [{dev_idx}] {dev['name']}")
                        return dev_idx
        return None


class TranscribeWorker(QThread):
    def __init__(self, model, audio_data, language, signal):
        super().__init__()
        self.model = model
        self.audio_data = audio_data
        self.language = language
        self.signal = signal

    def run(self):
        try:
            segments, _ = self.model.transcribe(
                self.audio_data.flatten(),
                language=self.language,
                vad_filter=True,
            )
            text = " ".join(seg.text for seg in segments).strip()
            if text and len(text) > 3:
                self.signal.emit(text)
        except Exception as e:
            print(f"转写错误: {e}")
