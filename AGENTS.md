# Instructions for AI Agents & Contributors

This repository contains the codebase for **Typist**, an open-source driver and voice typing assistant for the **Ulanzi Vibe Key AU05** hardware controller (`fff1:00dd`), supporting both remote OpenAI-compatible Whisper endpoints and local in-process faster-whisper STT with native OS keyboard emulation.

All AI agents (Antigravity, Claude, Cursor, Copilot, etc.) and human contributors working on this codebase **MUST** strictly follow these development rules.

---

## 1. 🚨 Zero Credentials in Code or Commits (MANDATORY)

- **NEVER hardcode or commit credentials, API keys, tokens, passwords, private IPs, Tailscale IPs, private keys, or certificates.**
  - Prohibited: OpenAI/LiteLLM keys (`sk-...`), API keys, Bearer tokens, private hostnames, or specific internal network IPs (e.g. `100.65.*.*`).
- **Use Environment Variables & Configuration Files**:
  - Read all credentials, hostnames, and endpoints from environment variables or the gitignored `.env` / `typist.toml` files.
  - When introducing a new configuration variable or secret, add a placeholder entry to [`.env.example`](file:///.env.example) and update local uncommitted `.env`.
- **Pre-Commit Verification**:
  - Always review `git diff` and verify that no secrets, credentials, or private addresses are present before staging or committing changes.

---

## 2. 🧭 Codebase Map

```
typist/
├── AGENTS.md                  # This file: agent rules and contributor guidelines
├── README.md                  # Project overview and user guide
├── LICENSE                    # MIT License
├── pyproject.toml             # Python build configuration and dependencies
├── .env.example               # Template for environment variables (safe to commit)
├── .gitignore                 # Excludes .env, build artifacts, venvs, and temp files
├── main.py                    # Root entrypoint runner
├── src/
│   └── typist/
│       ├── __init__.py        # Package init & version
│       ├── config.py          # Unified config loader (TOML, .env, CLI args)
│       ├── device.py          # Hardware driver & USB keepalive loop
│       ├── audio_recorder.py  # PipeWire & sounddevice audio capture
│       ├── transcriber.py     # Remote & local faster-whisper STT client
│       ├── keyboard_emulator.py # Linux uinput and cross-platform keyboard typing
│       └── main.py            # Application CLI and orchestration logic
├── udev/
│   ├── 99-ulanzi-au05.rules   # Device permissions for plugdev users
│   └── 99-uinput.rules        # uinput permissions for virtual keyboard
├── systemd/
│   └── typist.service         # Systemd user service unit template
├── tools/
│   └── sniff.py               # Low-level HID/event packet sniffing utility
└── packaging/                 # Platform packaging scripts (deb, windows, macos)
```

---

## 3. 🛠️ Development Rules & Hygiene

- Maintain documentation integrity.
- Keep commits incremental, focused, and well-described.
- Ensure cross-platform compatibility across Linux, Windows, and macOS.
