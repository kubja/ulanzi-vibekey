import shutil
import subprocess
import threading
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger("typist.audio")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AudioRecorder:
    """
    Cross-platform audio recorder.
    - Uses PipeWire pw-record on Linux for low-latency AU05 capture when available.
    - Falls back to sounddevice on Windows, macOS, or systems without PipeWire.
    """
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._is_recording = False
        self._sd_stream = None
        self._use_pw = bool(shutil.which("pw-record"))

    def _find_au05_pipewire_source(self) -> Optional[str]:
        if not self._use_pw:
            return None
        try:
            out = subprocess.check_output(["pw-link", "-o"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                if "AU05" in line:
                    return line.split(":")[0].strip()
        except Exception:
            pass
        return None

    def _find_au05_sounddevice_index(self) -> Optional[int]:
        if not SOUNDDEVICE_AVAILABLE:
            return None
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if "AU05" in dev.get("name", "") and dev.get("max_input_channels", 0) > 0:
                    return idx
        except Exception:
            pass
        return None

    def start_recording(self):
        with self._lock:
            if self._is_recording:
                return
            self._buffer.clear()
            self._is_recording = True

        pw_target = self._find_au05_pipewire_source() if self._use_pw else None

        if self._use_pw and pw_target:
            self._start_pipewire(pw_target)
        elif SOUNDDEVICE_AVAILABLE:
            self._start_sounddevice()
        elif self._use_pw:
            self._start_pipewire(None)
        else:
            logger.error("No audio capture backend available! Install sounddevice or pipewire.")
            self._is_recording = False

    def _start_pipewire(self, target: Optional[str]):
        cmd = [
            "pw-record",
            "--rate", str(self.sample_rate),
            "--channels", str(self.channels),
            "--format", "s16",
        ]
        if target:
            cmd.extend(["--target", target])
        cmd.append("-")

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=4096
            )
            self._thread = threading.Thread(target=self._pw_reader_loop, daemon=True)
            self._thread.start()
        except Exception as e:
            logger.error(f"Failed to start pw-record: {e}")
            self._is_recording = False

    def _pw_reader_loop(self):
        while self._is_recording and self._proc and self._proc.stdout:
            try:
                chunk = self._proc.stdout.read(1024)
                if not chunk:
                    break
                with self._lock:
                    self._buffer.extend(chunk)
            except Exception:
                break

    def _start_sounddevice(self):
        dev_idx = self._find_au05_sounddevice_index()

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.debug(f"Audio status: {status}")
            with self._lock:
                self._buffer.extend(indata.tobytes())

        try:
            self._sd_stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=1024,
                device=dev_idx,
                channels=self.channels,
                dtype="int16",
                callback=audio_callback,
            )
            self._sd_stream.start()
        except Exception as e:
            logger.error(f"Failed to start sounddevice stream: {e}")
            self._is_recording = False

    def stop_recording(self) -> bytes:
        with self._lock:
            if not self._is_recording:
                return b""
            self._is_recording = False

        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=0.5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None

        if self._sd_stream:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception:
                pass
            self._sd_stream = None

        with self._lock:
            data = bytes(self._buffer)
            self._buffer.clear()

        duration_sec = len(data) / (self.sample_rate * 2)
        if duration_sec < 0.2:
            return b""

        # Basic energy check
        try:
            samples = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            if rms < 50:
                logger.debug("Audio below silence threshold.")
                return b""
        except Exception:
            pass

        return data

    @property
    def is_recording(self) -> bool:
        return self._is_recording
