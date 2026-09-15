# Ulanzi Vibe Key AU05 Hardware Specification & Protocol Documentation

This document provides reverse-engineered technical specifications, USB descriptors, HID report structures, and protocol behaviors for the **Ulanzi Vibe Key AU05** (`fff1:00dd`) hardware controller.

---

## 1. 📟 Hardware Overview

| Parameter | Specification |
| :--- | :--- |
| **Product Name** | Ulanzi Vibe Key AU05 (SKU I018) |
| **Vendor ID (VID)** | `0xfff1` |
| **Product ID (PID)** | `0x00dd` |
| **Manufacturer** | `AU05` |
| **Product String** | `AU05` |
| **Default Serial Number** | `202606031150` |
| **USB Class** | Composite Device: USB Audio 1.0 + Multi-Interface HID |
| **Physical Controls** | • 3 Mechanical Key Switches<br>• 1 Rotary Encoder Knob (Turn Left, Turn Right, Push Click)<br>• 1 Dedicated Voice / Mic Key (Side/Front)<br>• 1 Omnidirectional Microphone |
| **Connectivity** | USB Type-C wired or 2.4 GHz USB wireless receiver dongle |

---

## 2. 🔌 USB Interface Topology

When connected to a host computer, the AU05 enumerates as 4 USB interfaces across 2 primary subsystems:

```
Ulanzi AU05 (fff1:00dd)
├── Interface 0: AudioControl (UAC 1.0)
├── Interface 1: AudioStreaming (PCM 48kHz Microphone)
│   └── EP 0x83 IN (Isochronous, 16-bit / 24-bit PCM)
├── Interface 2: HID Input (Mouse, Keyboard, Consumer Control)
│   ├── EP 0x82 IN  (Interrupt, 24 bytes, 1ms interval)
│   └── EP 0x02 OUT (Interrupt, 16 bytes, 5ms interval)
└── Interface 3: HID Vendor Communication Channel
    ├── EP 0x81 IN  (Interrupt, 64 bytes, 2ms interval)
    └── EP 0x01 OUT (Interrupt, 64 bytes, 2ms interval)
```

### Interface 0 & 1: USB Audio Class 1.0 (Microphone)
- **Audio Terminal**: Terminal Type `0x0201` (Microphone).
- **Format**: 48,000 Hz, 16-bit or 24-bit PCM.
- **Controls**: Feature Unit with Hardware Volume and Mute Control.
- **Kernel Support**: Handled natively by ALSA (`snd-usb-audio`) and PipeWire/PulseAudio (`alsa_input.usb-AU05...`).

### Interface 2: HID Standard Input Devices
Provides standard HID reports with Report IDs:
- `0x01`: Consumer Control
- `0x02`: Mouse (rotary wheel & buttons)
- `0x03`: Keyboard (8-byte standard boot report)

### Interface 3: Custom Vendor Communication (Report ID `0x55`)
- **Usage Page**: `0xfffc` (Vendor-Defined).
- **Packet Length**: 64 bytes total (`Report ID 0x55` + 63-byte payload).
- Used by the official Ulanzi Studio software for configuration, key remapping, and firmware synchronization.

---

## 3. 🔍 Reverse-Engineered HID Protocol & Quirks

### A. The 4-Second Idle Disconnect Phenomenon & Keepalive Loop
#### Behavior Observed:
When plugged into Linux without the proprietary Ulanzi software running, the AU05 disconnects and reconnects every 3.5 to 4.0 seconds continuously:
```text
usb 3-1: USB disconnect, device number 22
usb 3-1: new full-speed USB device number 23 using xhci_hcd
... (repeats every 3.5s)
```

#### Cause:
The AU05 firmware incorporates an unattached watchdog sleep timer. If no host process keeps an active handle to Interface 2 (`hidraw1`) or Interface 3 (`hidraw2`), the microcontroller assumes the connection is orphaned or that the proprietary host companion app is absent, causing a transceiver reboot cycle.

#### Solution (Spoofed Keepalive):
Holding open file descriptors to `/dev/hidraw1` and `/dev/hidraw2` signals continuous host presence to the USB controller. In our testing, holding the endpoints open maintains a **100% stable connection with zero disconnects**.

---

### B. The Voice Key Scancode Quirk (`0x01`)
#### Behavior Observed:
When pressing Button 2 (Enter) or Button 3 (Esc), standard Linux `/dev/input/event*` devices produce key events. However, pressing the **Voice Key** produces **zero events** on `/dev/input/event*`.

#### Root Cause:
Sniffing raw packets on `/dev/hidraw1` reveals the raw packet:
```text
[PRESS]   03 00 00 01 00 00 00 00 00
[RELEASE] 03 00 00 00 00 00 00 00 00
```
- Byte 0: `0x03` (Keyboard Report ID)
- Byte 1: `0x00` (Modifier bits)
- Byte 2: `0x00` (Reserved)
- Byte 3: `0x01` (Keycode)

In the USB HID Usage Tables (Section 10), Usage `0x01` is designated as **Keyboard ErrorRollOver** (indicating too many simultaneous keys pressed). Consequently, the Linux kernel keyboard driver (`hid-generic` / `evdev`) intentionally drops this packet as an error state rather than forwarding a keypress.

#### Solution:
Typist bypasses the kernel input subsystem and reads raw reports directly from `/dev/hidraw1` (or `hidapi` on macOS/Windows), detecting `0x01` as the physical Voice Key trigger.

---

## 4. 📊 HID Report Structure Reference

### 1. Keyboard Report (`Report ID 0x03`)
```
+----------+----------+----------+----------+-----------------------+
| Byte 0   | Byte 1   | Byte 2   | Byte 3   | Bytes 4-8             |
+----------+----------+----------+----------+-----------------------+
| ID (0x03)| Modifiers| Reserved | Keycode  | Additional Keycodes   |
+----------+----------+----------+----------+-----------------------+
```

| Key / Control | Scancode (Byte 3) | Kernel Event (`/dev/input`) | Typist Action |
| :--- | :--- | :--- | :--- |
| **Voice Key** | `0x01` | *Dropped by kernel* | Trigger Speech-to-Text Dictation |
| **Button 2** | `0x28` | `KEY_ENTER` (28) | Enter / Custom Action |
| **Button 3** | `0x29` | `KEY_ESC` (1) | Esc / Cancel Dictation |
| **All Released** | `0x00` | Release event | Stop recording & Transcribe |

---

### 2. Mouse / Rotary Knob Report (`Report ID 0x02`)
```
+----------+----------+----------+----------+----------+----------+
| Byte 0   | Byte 1   | Byte 2   | Byte 3   | Byte 4   | Byte 5   |
+----------+----------+----------+----------+----------+----------+
| ID (0x02)| Buttons  | X Delta  | Y Delta  | Wheel    | Pan      |
+----------+----------+----------+----------+----------+----------+
```

| Knob Action | Raw Packet (Hex) | Wheel Delta (Byte 4) |
| :--- | :--- | :--- |
| **Rotate Clockwise (CW)** | `02 00 00 00 01 00` | `+1` (`0x01`) |
| **Rotate Counter-Clockwise (CCW)** | `02 00 00 00 ff 00` | `-1` (`0xff`) |
| **Rest / Released** | `02 00 00 00 00 00` | `0` (`0x00`) |

---

### 3. Vendor Channel Report (`Report ID 0x55`)
- **Length**: 64 bytes
- **Header**: `0x55` (Report ID)
- **Periodic Heartbeat / Sync**: Emitted every ~10 seconds or when triggered:
```text
55 e8 4f 6b c3 06 c4 6d c5 38 90 c4 99 a3 60 aa ad 38 90 c4 99 a3 60 aa ...
```
- Holding this endpoint open prevents firmware sleep and maintains synchronous communication with the on-board controller.
