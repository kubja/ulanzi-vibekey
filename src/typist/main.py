#!/usr/bin/env python3
import sys
import signal
import logging
import argparse
import threading
from pathlib import Path

from typist.config import Config
from typist.device import AU05Device, KEY_VOICE, KEY_BUTTON_2, KEY_BUTTON_3
from typist.audio_recorder import AudioRecorder
from typist.transcriber import WhisperTranscriber
from typist.keyboard_emulator import KeyboardEmulator

logger = logging.getLogger("typist")

class TypistApp:
    def __init__(self, cfg: Config):
        self.config = cfg
        logger.info("Initializing Typist Voice Typing Assistant...")
        self.keyboard = KeyboardEmulator(key_delay=self.config.key_delay)
        self.recorder = AudioRecorder(sample_rate=self.config.sample_rate, channels=self.config.channels)
        self.transcriber = WhisperTranscriber(config=self.config)
        self.device = AU05Device(
            vendor_id=self.config.vendor_id,
            product_id=self.config.product_id,
            on_key_down=self.on_key_down,
            on_key_up=self.on_key_up,
            on_knob=self.on_knob,
        )
        self.processing_lock = threading.Lock()
        self.cancelled = False

    def on_key_down(self, key_name: str):
        logger.info(f"Button pressed: {key_name}")

        if key_name == KEY_VOICE:
            if self.config.dictation_mode == "toggle":
                if self.recorder.is_recording:
                    self._stop_and_transcribe()
                else:
                    self._start_recording()
            else:
                self._start_recording()

        elif key_name == KEY_BUTTON_3:
            if self.recorder.is_recording:
                logger.info("Recording cancelled by user.")
                self.cancelled = True
                self.recorder.stop_recording()

    def on_key_up(self, key_name: str):
        logger.info(f"Button released: {key_name}")

        if key_name == KEY_VOICE and self.config.dictation_mode == "hold":
            self._stop_and_transcribe()

    def on_knob(self, delta: int):
        direction = "Clockwise (+1)" if delta > 0 else "Counter-Clockwise (-1)"
        logger.debug(f"Knob rotated: {direction}")

    def _start_recording(self):
        self.cancelled = False
        print("\n🎤 [LISTENING...] Speak now (release button when finished)...")
        sys.stdout.flush()
        self.recorder.start_recording()

    def _stop_and_transcribe(self):
        if not self.recorder.is_recording:
            return

        mode_desc = f"local faster-whisper ({self.config.local_model_size})" if self.config.whisper_mode == "local" else f"remote Whisper ({self.config.whisper_model})"
        print(f"⏹️  [PROCESSING...] Transcribing with {mode_desc}...")
        sys.stdout.flush()

        threading.Thread(target=self._transcribe_worker, daemon=True).start()

    def _transcribe_worker(self):
        with self.processing_lock:
            pcm_bytes = self.recorder.stop_recording()
            if self.cancelled:
                self.cancelled = False
                print("❌ Dictation cancelled.\n")
                return

            if not pcm_bytes:
                print("⚠️  No speech detected.\n")
                return

            text = self.transcriber.transcribe(pcm_bytes, sample_rate=self.config.sample_rate)
            if not text:
                print("⚠️  No transcription returned.\n")
                return

            if self.config.append_space:
                text += " "

            print(f"✍️  [TYPING]: \"{text}\"\n")
            sys.stdout.flush()
            self.keyboard.type_text(text)

    def run(self):
        mode_desc = f"local ({self.config.local_model_size})" if self.config.whisper_mode == "local" else f"remote ({self.config.whisper_api_url})"
        print("=" * 64)
        print("  TYPIST - Ulanzi AU05 Voice Typing Assistant")
        print(f"  STT Engine: {mode_desc}")
        print(f"  Dictation Mode: {self.config.dictation_mode}")
        print("  Hold the Voice Key on your AU05 to talk, release to type!")
        print("=" * 64)
        sys.stdout.flush()

        self.device.run()

    def stop(self):
        logger.info("Shutting down Typist...")
        self.device.stop()
        self.recorder.stop_recording()
        self.transcriber.close()
        self.keyboard.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Typist - Ulanzi Vibe Key AU05 Driver & Voice Typing Assistant",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-c", "--config", help="Path to typist.toml configuration file")
    parser.add_argument("--init-config", action="store_true", help="Generate a default typist.toml config file and exit")
    parser.add_argument("-m", "--mode", choices=["remote", "local"], help="Whisper STT mode: remote (API) or local (faster-whisper)")
    parser.add_argument("-u", "--url", dest="whisper_api_url", help="Remote Whisper API transcription URL")
    parser.add_argument("-k", "--api-key", dest="whisper_api_key", help="Remote API bearer token")
    parser.add_argument("--model", dest="whisper_model", help="Remote Whisper model name")
    parser.add_argument("--local-model", dest="local_model_size", choices=["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"], help="Local model size for faster-whisper")
    parser.add_argument("--device", dest="local_device", choices=["auto", "cpu", "cuda"], help="Compute device for local model")
    parser.add_argument("--language", dest="whisper_language", help="Spoken language ISO code (e.g. en, fr, de, es, auto)")
    parser.add_argument("-p", "--prompt", dest="whisper_prompt", help="Initial prompt / vocabulary biasing")
    parser.add_argument("--dictation-mode", choices=["hold", "toggle"], help="Dictation trigger mode")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    return parser.parse_args()


def main():
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

    if args.init_config:
        out_path = Path("typist.toml")
        if out_path.exists():
            print(f"Error: {out_path} already exists!", file=sys.stderr)
            sys.exit(1)
        cfg_template = Config().to_toml()
        out_path.write_text(cfg_template)
        print(f"Created default configuration file at: {out_path.resolve()}")
        sys.exit(0)

    # Collect CLI overrides
    overrides = {}
    if args.mode:
        overrides["whisper_mode"] = args.mode
    if args.whisper_api_url:
        overrides["whisper_api_url"] = args.whisper_api_url
    if args.whisper_api_key:
        overrides["whisper_api_key"] = args.whisper_api_key
    if args.whisper_model:
        overrides["whisper_model"] = args.whisper_model
    if args.local_model_size:
        overrides["local_model_size"] = args.local_model_size
    if args.local_device:
        overrides["local_device"] = args.local_device
    if args.whisper_language:
        overrides["whisper_language"] = args.whisper_language
    if args.whisper_prompt:
        overrides["whisper_prompt"] = args.whisper_prompt
    if args.dictation_mode:
        overrides["dictation_mode"] = args.dictation_mode

    cfg = Config.load(config_path=args.config, overrides=overrides)
    app = TypistApp(cfg)

    def sig_handler(sig, frame):
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
