import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

DEFAULT_CONFIG_LOCATIONS = [
    Path("typist.toml"),
    Path.home() / ".config" / "typist" / "config.toml",
]

@dataclass
class Config:
    # Mode: 'remote' or 'local'
    whisper_mode: str = "remote"

    # Remote Whisper endpoint settings
    whisper_api_url: str = "http://localhost:8008/v1/audio/transcriptions"
    whisper_api_key: Optional[str] = None
    whisper_model: str = "openai/whisper-large-v3-turbo"
    whisper_prompt: str = ""
    whisper_language: Optional[str] = None

    # Local Whisper settings (using faster-whisper)
    local_model_size: str = "base"
    local_device: str = "auto"          # 'auto', 'cpu', 'cuda'
    local_compute_type: str = "default" # 'default', 'float16', 'int8'

    # Hardware target
    vendor_id: int = 0xfff1
    product_id: int = 0x00dd

    # Dictation mode: 'hold' (push-to-talk) or 'toggle'
    dictation_mode: str = "hold"

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1

    # Typing settings
    key_delay: float = 0.003
    append_space: bool = True

    @classmethod
    def load(cls, config_path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> "Config":
        data: Dict[str, Any] = {}

        # 1. Check specified config file or standard paths
        target_path: Optional[Path] = None
        if config_path:
            p = Path(config_path)
            if p.is_file():
                target_path = p
        else:
            for loc in DEFAULT_CONFIG_LOCATIONS:
                if loc.is_file():
                    target_path = loc
                    break

        if target_path:
            try:
                with open(target_path, "rb") as f:
                    toml_data = tomllib.load(f)
                # Flatten or extract sections
                if "whisper" in toml_data:
                    w = toml_data["whisper"]
                    data["whisper_mode"] = w.get("mode", data.get("whisper_mode", "remote"))
                    data["whisper_api_url"] = w.get("api_url", data.get("whisper_api_url"))
                    data["whisper_api_key"] = w.get("api_key", data.get("whisper_api_key"))
                    data["whisper_model"] = w.get("model", data.get("whisper_model"))
                    data["whisper_prompt"] = w.get("prompt", data.get("whisper_prompt", ""))
                    data["whisper_language"] = w.get("language", data.get("whisper_language"))
                    data["local_model_size"] = w.get("local_model_size", data.get("local_model_size", "base"))
                    data["local_device"] = w.get("local_device", data.get("local_device", "auto"))
                    data["local_compute_type"] = w.get("local_compute_type", data.get("local_compute_type", "default"))

                if "hardware" in toml_data:
                    h = toml_data["hardware"]
                    if "vendor_id" in h:
                        data["vendor_id"] = int(str(h["vendor_id"]), 16) if isinstance(h["vendor_id"], str) else h["vendor_id"]
                    if "product_id" in h:
                        data["product_id"] = int(str(h["product_id"]), 16) if isinstance(h["product_id"], str) else h["product_id"]

                if "typing" in toml_data:
                    t = toml_data["typing"]
                    data["dictation_mode"] = t.get("dictation_mode", data.get("dictation_mode", "hold"))
                    data["key_delay"] = t.get("key_delay", data.get("key_delay", 0.003))
                    data["append_space"] = t.get("append_space", data.get("append_space", True))

                # Allow top-level keys
                for k, v in toml_data.items():
                    if k not in ("whisper", "hardware", "typing") and not isinstance(v, dict):
                        data[k] = v
            except Exception as e:
                print(f"[WARN] Failed to parse config file {target_path}: {e}", file=sys.stderr)

        # 2. Environment variables override
        env_mode = os.getenv("WHISPER_MODE")
        if env_mode:
            data["whisper_mode"] = env_mode

        env_url = os.getenv("WHISPER_API_URL")
        if env_url:
            data["whisper_api_url"] = env_url

        env_key = os.getenv("WHISPER_API_KEY")
        if env_key:
            data["whisper_api_key"] = env_key

        env_model = os.getenv("WHISPER_MODEL")
        if env_model:
            data["whisper_model"] = env_model

        env_prompt = os.getenv("WHISPER_PROMPT")
        if env_prompt is not None:
            data["whisper_prompt"] = env_prompt

        env_lang = os.getenv("WHISPER_LANGUAGE")
        if env_lang:
            data["whisper_language"] = env_lang

        env_local_size = os.getenv("WHISPER_LOCAL_MODEL")
        if env_local_size:
            data["local_model_size"] = env_local_size

        env_dict_mode = os.getenv("DICTATION_MODE")
        if env_dict_mode:
            data["dictation_mode"] = env_dict_mode

        env_delay = os.getenv("KEY_DELAY")
        if env_delay:
            try:
                data["key_delay"] = float(env_delay)
            except ValueError:
                pass

        env_space = os.getenv("APPEND_SPACE")
        if env_space:
            data["append_space"] = env_space.lower() in ("true", "1", "yes")

        # 3. CLI Overrides
        if overrides:
            for k, v in overrides.items():
                if v is not None:
                    data[k] = v

        # Filter to only valid fields
        valid_keys = cls.__dataclass_fields__.keys()
        cleaned_data = {k: v for k, v in data.items() if k in valid_keys and v is not None}
        return cls(**cleaned_data)

    def to_toml(self) -> str:
        """Export config template as TOML string."""
        return f"""# Typist Configuration File

[whisper]
# 'remote' (OpenAI-compatible STT endpoint) or 'local' (runs faster-whisper locally)
mode = "{self.whisper_mode}"

# Remote Whisper settings
api_url = "{self.whisper_api_url}"
# api_key = "{self.whisper_api_key or ''}"
model = "{self.whisper_model}"
prompt = "{self.whisper_prompt}"
# language = "en"

# Local Whisper settings (active when mode = "local")
local_model_size = "{self.local_model_size}"   # tiny, base, small, medium, large-v3, large-v3-turbo
local_device = "{self.local_device}"           # auto, cpu, cuda
local_compute_type = "{self.local_compute_type}" # default, float16, int8

[hardware]
vendor_id = 0x{self.vendor_id:04x}
product_id = 0x{self.product_id:04x}

[typing]
# 'hold' (push-to-talk) or 'toggle'
dictation_mode = "{self.dictation_mode}"
key_delay = {self.key_delay}
append_space = {str(self.append_space).lower()}
"""

config = Config.load()
