import queue
import numpy as np
from PySide6.QtCore import QThread, Signal
from scipy import signal as scipy_signal

TARGET_SR = 16000


class AudioMonitor(QThread):
    new_text = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.target_sr = TARGET_SR
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

        dev_info = sd.query_devices(device_idx)
        native_sr = int(dev_info['default_samplerate'])
        print(f"设备原生采样率: {native_sr} Hz, 重采样至: {self.target_sr} Hz")
        silence_limit = int(self.target_sr * self.silence_duration)

        def _resample(chunk, orig_sr, target_sr):
            if orig_sr == target_sr:
                return chunk
            num_samples = int(len(chunk) * target_sr / orig_sr)
            return scipy_signal.resample(chunk, num_samples)

        def _create_vad():
            try:
                from silero_vad import load_silero_vad, get_speech_timestamps
                model = load_silero_vad()
                def vad_fn(chunk, sr):
                    if sr != TARGET_SR:
                        chunk = _resample(chunk, sr, TARGET_SR)
                    return len(get_speech_timestamps(
                        chunk, model, threshold=self.vad_threshold,
                        sampling_rate=TARGET_SR,
                    )) > 0
                return vad_fn
            except Exception:
                print("警告: silero-vad 加载失败, 使用能量阈值 VAD")
                return lambda chunk, sr: np.max(np.abs(chunk)) > 0.02

        vad_fn = _create_vad()
        audio_queue = queue.Queue()
        is_recording = False
        audio_buffer = []
        silence_samples = 0

        stream = sd.InputStream(
            device=device_idx,
            samplerate=native_sr,
            channels=1,
            dtype='float32',
            callback=lambda indata, frames, _t, _s: audio_queue.put(indata.copy()),
        )

        with stream:
            while not self.isInterruptionRequested():
                try:
                    frames = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                is_speech = vad_fn(frames.flatten(), native_sr)

                if is_speech:
                    if not is_recording:
                        is_recording = True
                        audio_buffer = []
                    # Resample to target SR and store
                    frames_resampled = _resample(frames.flatten(), native_sr, self.target_sr)
                    audio_buffer.append(frames_resampled)
                    silence_samples = 0
                elif is_recording:
                    frames_resampled = _resample(frames.flatten(), native_sr, self.target_sr)
                    audio_buffer.append(frames_resampled)
                    silence_samples += len(frames_resampled)
                    if silence_samples > silence_limit:
                        audio_data = np.concatenate(audio_buffer)
                        is_recording = False
                        audio_buffer = []
                        silence_samples = 0
                        worker = TranscribeWorker(whisper, audio_data, self.language, self.new_text)
                        worker.start()

            if is_recording and audio_buffer:
                audio_data = np.concatenate(audio_buffer)
                if len(audio_data) > self.target_sr * 0.5:
                    TranscribeWorker(whisper, audio_data, self.language, self.new_text).start()

    def _find_loopback_device(self):
        import sounddevice as sd
        hostapis = sd.query_hostapis()
        for ha in hostapis:
            if 'wasapi' not in ha['name'].lower():
                continue
            candidates = []
            for dev_idx in ha['devices']:
                dev = sd.query_devices(dev_idx)
                if dev['max_input_channels'] == 0:
                    continue
                name = dev['name'].lower()
                # Skip microphones — they are not loopback devices
                if any(kw in name for kw in ['麦克风', 'microphone', 'mic ']):
                    continue
                candidates.append((dev_idx, dev['name'], int(dev['default_samplerate'])))

            if candidates:
                idx, name, sr = candidates[0]
                print(f"使用 WASAPI 回环: [{idx}] {name} ({sr} Hz)")
                return idx
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
