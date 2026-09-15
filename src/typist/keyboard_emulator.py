import sys
import time
import logging
from typing import Optional

logger = logging.getLogger("typist.keyboard")

# Check if Linux uinput is available
USE_UINPUT = False
if sys.platform.startswith("linux"):
    try:
        import evdev
        from evdev import UInput, ecodes as e
        USE_UINPUT = True
    except ImportError:
        pass

# Fallback cross-platform controller (Windows / macOS / fallback Linux)
try:
    from pynput.keyboard import Controller as PynputController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


if USE_UINPUT:
    # Key mapping for evdev uinput
    CHAR_MAP = {
        'a': (e.KEY_A, False), 'b': (e.KEY_B, False), 'c': (e.KEY_C, False),
        'd': (e.KEY_D, False), 'e': (e.KEY_E, False), 'f': (e.KEY_F, False),
        'g': (e.KEY_G, False), 'h': (e.KEY_H, False), 'i': (e.KEY_I, False),
        'j': (e.KEY_J, False), 'k': (e.KEY_K, False), 'l': (e.KEY_L, False),
        'm': (e.KEY_M, False), 'n': (e.KEY_N, False), 'o': (e.KEY_O, False),
        'p': (e.KEY_P, False), 'q': (e.KEY_Q, False), 'r': (e.KEY_R, False),
        's': (e.KEY_S, False), 't': (e.KEY_T, False), 'u': (e.KEY_U, False),
        'v': (e.KEY_V, False), 'w': (e.KEY_W, False), 'x': (e.KEY_X, False),
        'y': (e.KEY_Y, False), 'z': (e.KEY_Z, False),
        'A': (e.KEY_A, True),  'B': (e.KEY_B, True),  'C': (e.KEY_C, True),
        'D': (e.KEY_D, True),  'E': (e.KEY_E, True),  'F': (e.KEY_F, True),
        'G': (e.KEY_G, True),  'H': (e.KEY_H, True),  'I': (e.KEY_I, True),
        'J': (e.KEY_J, True),  'K': (e.KEY_K, True),  'L': (e.KEY_L, True),
        'M': (e.KEY_M, True),  'N': (e.KEY_N, True),  'O': (e.KEY_O, True),
        'P': (e.KEY_P, True),  'Q': (e.KEY_Q, True),  'R': (e.KEY_R, True),
        'S': (e.KEY_S, True),  'T': (e.KEY_T, True),  'U': (e.KEY_U, True),
        'V': (e.KEY_V, True),  'W': (e.KEY_W, True),  'X': (e.KEY_X, True),
        'Y': (e.KEY_Y, True),  'Z': (e.KEY_Z, True),
        '0': (e.KEY_0, False), '1': (e.KEY_1, False), '2': (e.KEY_2, False),
        '3': (e.KEY_3, False), '4': (e.KEY_4, False), '5': (e.KEY_5, False),
        '6': (e.KEY_6, False), '7': (e.KEY_7, False), '8': (e.KEY_8, False),
        '9': (e.KEY_9, False),
        '!': (e.KEY_1, True),  '@': (e.KEY_2, True),  '#': (e.KEY_3, True),
        '$': (e.KEY_4, True),  '%': (e.KEY_5, True),  '^': (e.KEY_6, True),
        '&': (e.KEY_7, True),  '*': (e.KEY_8, True),  '(': (e.KEY_9, True),
        ')': (e.KEY_0, True),  '-': (e.KEY_MINUS, False), '_': (e.KEY_MINUS, True),
        '=': (e.KEY_EQUAL, False), '+': (e.KEY_EQUAL, True),
        '[': (e.KEY_LEFTBRACE, False), '{': (e.KEY_LEFTBRACE, True),
        ']': (e.KEY_RIGHTBRACE, False), '}': (e.KEY_RIGHTBRACE, True),
        '\\': (e.KEY_BACKSLASH, False), '|': (e.KEY_BACKSLASH, True),
        ';': (e.KEY_SEMICOLON, False), ':': (e.KEY_SEMICOLON, True),
        "'": (e.KEY_APOSTROPHE, False), '"': (e.KEY_APOSTROPHE, True),
        ',': (e.KEY_COMMA, False), '<': (e.KEY_COMMA, True),
        '.': (e.KEY_DOT, False), '>': (e.KEY_DOT, True),
        '/': (e.KEY_SLASH, False), '?': (e.KEY_SLASH, True),
        '`': (e.KEY_GRAVE, False), '~': (e.KEY_GRAVE, True),
        ' ': (e.KEY_SPACE, False),
        '\t': (e.KEY_TAB, False),
        '\n': (e.KEY_ENTER, False),
    }


class KeyboardEmulator:
    """
    Cross-platform keyboard emulator.
    - Uses Linux kernel uinput when available (Wayland/X11).
    - Falls back to pynput on Windows / macOS / without uinput.
    """
    def __init__(self, key_delay: float = 0.003):
        self.key_delay = key_delay
        self.ui = None
        self.pynput_ctrl = None

        if USE_UINPUT:
            try:
                all_keys = set()
                for keycode, _ in CHAR_MAP.values():
                    all_keys.add(keycode)
                all_keys.add(e.KEY_LEFTSHIFT)
                all_keys.add(e.KEY_LEFTCTRL)
                all_keys.add(e.KEY_LEFTALT)
                all_keys.add(e.KEY_BACKSPACE)
                all_keys.add(e.KEY_ESC)

                cap = {e.EV_KEY: list(all_keys)}
                self.ui = UInput(cap, name="typist-virtual-keyboard", version=0x1)
                time.sleep(0.1)
                logger.info("Initialized Linux uinput virtual keyboard.")
                return
            except Exception as ex:
                logger.warning(f"Could not initialize uinput ({ex}). Falling back to pynput.")

        if PYNPUT_AVAILABLE:
            self.pynput_ctrl = PynputController()
            logger.info("Initialized pynput cross-platform keyboard controller.")
        else:
            logger.error("No keyboard emulation backend available! Install evdev or pynput.")

    def type_text(self, text: str):
        if not text:
            return

        if self.ui:
            self._type_uinput(text)
        elif self.pynput_ctrl:
            self.pynput_ctrl.type(text)

    def _type_uinput(self, text: str):
        for ch in text:
            if ch in CHAR_MAP:
                keycode, shift = CHAR_MAP[ch]
                if shift:
                    self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
                    self.ui.syn()
                self.ui.write(e.EV_KEY, keycode, 1)
                self.ui.syn()
                time.sleep(self.key_delay)
                self.ui.write(e.EV_KEY, keycode, 0)
                self.ui.syn()
                if shift:
                    self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
                    self.ui.syn()
                time.sleep(self.key_delay)
            else:
                # Unicode hex input via Ctrl+Shift+U
                hex_str = f"{ord(ch):x}"
                self.ui.write(e.EV_KEY, e.KEY_LEFTCTRL, 1)
                self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
                self.ui.write(e.EV_KEY, e.KEY_U, 1)
                self.ui.syn()
                time.sleep(self.key_delay)
                self.ui.write(e.EV_KEY, e.KEY_U, 0)
                self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
                self.ui.write(e.EV_KEY, e.KEY_LEFTCTRL, 0)
                self.ui.syn()
                time.sleep(self.key_delay)
                for h in hex_str:
                    if h in CHAR_MAP:
                        kc, _ = CHAR_MAP[h]
                        self.ui.write(e.EV_KEY, kc, 1)
                        self.ui.syn()
                        time.sleep(self.key_delay)
                        self.ui.write(e.EV_KEY, kc, 0)
                        self.ui.syn()
                self.ui.write(e.EV_KEY, e.KEY_ENTER, 1)
                self.ui.syn()
                time.sleep(self.key_delay)
                self.ui.write(e.EV_KEY, e.KEY_ENTER, 0)
                self.ui.syn()

    def close(self):
        if self.ui:
            try:
                self.ui.close()
            except Exception:
                pass
            self.ui = None
