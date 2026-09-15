# Typist - Ulanzi Vibe Key AU05 Driver & Voice Typing Assistant

Custom driver and voice typing application for the **Ulanzi AU05 Vibe Key** (`fff1:00dd`).

Typist listens to the AU05 voice key, records speech from the built-in microphone, transcribes it using **Whisper** (either locally in-process or via any remote OpenAI-compatible STT endpoint), and emulates native keystrokes directly into any active window on Linux (Wayland / GNOME / X11), Windows, and macOS.

---

## 🚀 Features

- **USB Keepalive / Anti-Disconnect**: Keeps device descriptors open to prevent the AU05 firmware's 4-second idle USB disconnect/reconnect loop.
- **Hardware-Level Key Capture**: Decodes raw HID reports (`Report ID 0x03`) to read the Voice Key (scancode `0x01`, which standard OS keyboard drivers ignore).
- **Flexible Whisper STT**:
  - **Local Mode**: Uses `faster-whisper` for fast, offline, on-device transcription with automatic GPU/CPU detection.
  - **Remote Mode**: Connects to any OpenAI-compatible Whisper endpoint (vLLM, Speaches, OpenAI, Groq, local homelab server).
- **Native OS Keyboard Emulation**: Types text directly at your cursor into any focused application (browsers, text editors, terminals, Slack, Discord, etc.).
- **Dictation Modes**: Push-to-Talk (hold key to speak, release to type) or Toggle mode.

---

## 🛠️ Linux Permissions (`udev`)

On Linux, raw input and `/dev/uinput` require user permissions. Install the included udev rules:

```bash
sudo cp udev/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Ensure your user is in the `plugdev` group:
```bash
sudo usermod -a -G plugdev $USER
```

---

## 💻 Quickstart

### 1. Installation

```bash
git clone https://github.com/jakubtom/typist.git
cd typist
python3 -m venv .venv
source .venv/bin/activate

# Basic installation (remote Whisper API)
pip install -e .

# Or with local faster-whisper support
pip install -e ".[local-whisper]"
```

### 2. Configure

Generate a default `typist.toml` configuration:
```bash
python3 main.py --init-config
```

Or configure via environment variables (see `.env.example`):
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

### 3. Run

```bash
python3 main.py
```

Press and hold the **Voice Key** on the AU05, speak, and release. The transcribed text will appear directly at your cursor.

---

## ⚙️ Configuration Reference (`typist.toml` / `.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `WHISPER_MODE` | `remote` | `remote` (OpenAI-compatible API) or `local` (faster-whisper) |
| `WHISPER_API_URL` | `http://localhost:8008/v1/audio/transcriptions` | Remote Whisper STT endpoint URL |
| `WHISPER_API_KEY` | `""` | Optional bearer token for remote API |
| `WHISPER_MODEL` | `openai/whisper-large-v3-turbo` | Remote Whisper model name |
| `WHISPER_LOCAL_MODEL` | `base` | Model size for local faster-whisper (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `WHISPER_LOCAL_DEVICE` | `auto` | `auto`, `cpu`, or `cuda` |
| `DICTATION_MODE` | `hold` | `hold` (push-to-talk) or `toggle` (click to start/stop) |
| `APPEND_SPACE` | `true` | Appends a space after each dictated phrase |
| `KEY_DELAY` | `0.003` | Keystroke delay in seconds |
