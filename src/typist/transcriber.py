import io
import wave
import logging
import numpy as np
import httpx
from typing import Optional
from typist.config import Config

logger = logging.getLogger("typist.transcriber")

# Common hallucinations emitted by Whisper when fed ambient silence or noise
HALLUCINATIONS = {
    "thank you.", "thank you", "thanks for watching!", "thanks for watching.",
    "bye.", "bye", "you", "so", "thank you very much.", "subscribe!",
    "please subscribe", "...", ".", "transcription by", "translated by",
}

class WhisperTranscriber:
    """
    Unified STT transcriber supporting both remote OpenAI-compatible Whisper endpoints
    (e.g., GX10, Speaches, vLLM, OpenAI, Groq) and local in-process faster-whisper.
    """
    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.Client(timeout=15.0)
        self.local_model = None

        if self.config.whisper_mode == "local":
            self._init_local_model()
        else:
            logger.info(f"Using remote Whisper endpoint: {self.config.whisper_api_url} ({self.config.whisper_model})")

    def _init_local_model(self):
        try:
            from faster_whisper import WhisperModel
            device = self.config.local_device
            compute_type = self.config.local_compute_type

            if device == "auto":
                try:
                    import ctranslate2
                    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
                except Exception:
                    device = "cpu"

            if compute_type == "default":
                compute_type = "float16" if device == "cuda" else "int8"

            logger.info(f"Loading local faster-whisper model '{self.config.local_model_size}' on {device} ({compute_type})...")
            self.local_model = WhisperModel(
                self.config.local_model_size,
                device=device,
                compute_type=compute_type,
            )
            logger.info("Local faster-whisper model loaded successfully.")
        except ImportError:
            logger.error(
                "faster-whisper is not installed. Local STT unavailable.\n"
                "Install it with: pip install 'typist[local-whisper]'\n"
                "Or switch to remote mode: typist --mode remote"
            )
            self.local_model = None
        except Exception as e:
            logger.error(f"Failed to load local Whisper model: {e}")
            self.local_model = None

    def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        if not pcm_bytes:
            return ""

        if self.config.whisper_mode == "local":
            return self._transcribe_local(pcm_bytes, sample_rate)
        else:
            return self._transcribe_remote(pcm_bytes, sample_rate)

    def _transcribe_remote(self, pcm_bytes: bytes, sample_rate: int) -> str:
        # Construct WAV in memory
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        wav_io.seek(0)

        files = {"file": ("audio.wav", wav_io.read(), "audio/wav")}
        data = {"model": self.config.whisper_model}
        if self.config.whisper_prompt:
            data["prompt"] = self.config.whisper_prompt
        if self.config.whisper_language:
            data["language"] = self.config.whisper_language

        headers = {}
        if self.config.whisper_api_key:
            headers["Authorization"] = f"Bearer {self.config.whisper_api_key}"

        try:
            resp = self.client.post(self.config.whisper_api_url, files=files, data=data, headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                text = result.get("text", "").strip()
                if text.lower() in HALLUCINATIONS:
                    logger.info(f"Filtered hallucination: '{text}'")
                    return ""
                return text
            else:
                logger.error(f"Remote Whisper API error {resp.status_code}: {resp.text}")
                return ""
        except Exception as e:
            logger.error(f"Failed to connect to Whisper API ({self.config.whisper_api_url}): {e}")
            return ""

    def _transcribe_local(self, pcm_bytes: bytes, sample_rate: int) -> str:
        if self.local_model is None:
            self._init_local_model()
            if self.local_model is None:
                return ""

        try:
            # Convert int16 PCM bytes to float32 numpy array
            audio_array = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            kwargs = {"vad_filter": True}
            if self.config.whisper_prompt:
                kwargs["initial_prompt"] = self.config.whisper_prompt
            if self.config.whisper_language:
                kwargs["language"] = self.config.whisper_language

            segments, _ = self.local_model.transcribe(audio_array, **kwargs)
            text = " ".join([seg.text.strip() for seg in segments if seg.text.strip()])
            if text.lower() in HALLUCINATIONS:
                logger.info(f"Filtered hallucination: '{text}'")
                return ""
            return text
        except Exception as e:
            logger.error(f"Local Whisper transcription error: {e}")
            return ""

    def close(self):
        self.client.close()
