import os
import sys
import glob
import time
import select
import logging
from typing import Callable, Optional, Dict

logger = logging.getLogger("typist.device")

KEY_VOICE = "voice"        # Scancode 0x01 (Voice Key)
KEY_BUTTON_2 = "btn_enter" # Scancode 0x28 (Button 2)
KEY_BUTTON_3 = "btn_esc"   # Scancode 0x29 (Button 3)

SCANCODE_MAP = {
    0x01: KEY_VOICE,
    0x28: KEY_BUTTON_2,
    0x29: KEY_BUTTON_3,
}

# Cross-platform hidapi fallback
try:
    import hid
    HIDAPI_AVAILABLE = True
except ImportError:
    hid = None
    HIDAPI_AVAILABLE = False


class AU05Device:
    """
    Cross-platform driver interface for Ulanzi Vibe Key AU05 (fff1:00dd).
    - Linux: Native /dev/hidraw file descriptors held open to prevent 4s idle sleep/disconnect.
    - Windows / macOS: pyhidapi device handle held open to prevent sleep and receive HID reports.
    - Emits: on_key_down, on_key_up, on_knob.
    """
    def __init__(
        self,
        vendor_id: int = 0xfff1,
        product_id: int = 0x00dd,
        on_key_down: Optional[Callable[[str], None]] = None,
        on_key_up: Optional[Callable[[str], None]] = None,
        on_knob: Optional[Callable[[int], None]] = None,
    ):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.on_key_down = on_key_down
        self.on_key_up = on_key_up
        self.on_knob = on_knob

        self.hidraw1_fd: Optional[int] = None
        self.hidraw2_fd: Optional[int] = None
        self.hid_device = None
        self.current_key: Optional[str] = None
        self.running = False
        self.is_linux = sys.platform.startswith("linux")

    def _find_linux_nodes(self) -> Dict[str, str]:
        nodes = {}
        for dev_path in glob.glob("/sys/class/hidraw/hidraw*"):
            uevent_file = os.path.join(dev_path, "device/uevent")
            if os.path.exists(uevent_file):
                try:
                    with open(uevent_file, "r") as f:
                        content = f.read()
                    v_hex = f"{self.vendor_id:04X}"
                    p_hex = f"{self.product_id:04X}"
                    if v_hex in content.upper() and p_hex in content.upper():
                        hidraw_name = os.path.basename(dev_path)
                        dev_node = f"/dev/{hidraw_name}"
                        if "input2" in content:
                            nodes["input"] = dev_node
                        elif "input3" in content:
                            nodes["vendor"] = dev_node
                        else:
                            if "input" not in nodes:
                                nodes["input"] = dev_node
                            else:
                                nodes["vendor"] = dev_node
                except Exception:
                    pass
        return nodes

    def connect(self) -> bool:
        self.close()

        if self.is_linux:
            nodes = self._find_linux_nodes()
            if not nodes or "input" not in nodes:
                return False
            try:
                self.hidraw1_fd = os.open(nodes["input"], os.O_RDONLY | os.O_NONBLOCK)
                logger.info(f"Connected to AU05 input node: {nodes['input']}")
                if "vendor" in nodes:
                    self.hidraw2_fd = os.open(nodes["vendor"], os.O_RDONLY | os.O_NONBLOCK)
                    logger.info(f"Connected to AU05 vendor node (keepalive): {nodes['vendor']}")
                return True
            except Exception as e:
                logger.error(f"Failed to open Linux hidraw nodes: {e}")
                self.close()
                return False

        elif HIDAPI_AVAILABLE:
            try:
                self.hid_device = hid.device()
                self.hid_device.open(self.vendor_id, self.product_id)
                self.hid_device.set_nonblocking(True)
                logger.info(f"Connected to AU05 via hidapi ({self.vendor_id:04x}:{self.product_id:04x})")
                return True
            except Exception as e:
                logger.error(f"Failed to open hidapi device: {e}")
                self.close()
                return False
        else:
            logger.error("No HID backend available. On non-Linux, install 'hidapi'.")
            return False

    def close(self):
        if self.hidraw1_fd is not None:
            try:
                os.close(self.hidraw1_fd)
            except Exception:
                pass
            self.hidraw1_fd = None
        if self.hidraw2_fd is not None:
            try:
                os.close(self.hidraw2_fd)
            except Exception:
                pass
            self.hidraw2_fd = None
        if self.hid_device is not None:
            try:
                self.hid_device.close()
            except Exception:
                pass
            self.hid_device = None

    def _handle_packet(self, data: bytes):
        if not data:
            return

        report_id = data[0]

        # Report ID 3: Keyboard / Voice key
        if report_id == 0x03 and len(data) >= 4:
            scancode = data[3]
            key_name = SCANCODE_MAP.get(scancode)

            if scancode == 0x00:
                if self.current_key is not None:
                    released = self.current_key
                    self.current_key = None
                    if self.on_key_up:
                        self.on_key_up(released)
            elif key_name:
                if self.current_key != key_name:
                    self.current_key = key_name
                    if self.on_key_down:
                        self.on_key_down(key_name)

        # Report ID 2: Mouse / Knob
        elif report_id == 0x02 and len(data) >= 5:
            raw_wheel = data[4]
            if raw_wheel != 0:
                delta = 1 if raw_wheel == 0x01 else (-1 if raw_wheel == 0xff else 0)
                if delta != 0 and self.on_knob:
                    self.on_knob(delta)

    def run(self):
        self.running = True
        logger.info("AU05 event loop running.")

        while self.running:
            if (self.is_linux and self.hidraw1_fd is None) or (not self.is_linux and self.hid_device is None):
                if not self.connect():
                    time.sleep(1.0)
                    continue

            if self.is_linux:
                fds = [fd for fd in [self.hidraw1_fd, self.hidraw2_fd] if fd is not None]
                try:
                    rlist, _, _ = select.select(fds, [], [], 1.0)
                    for fd in rlist:
                        try:
                            data = os.read(fd, 128)
                            if fd == self.hidraw1_fd:
                                self._handle_packet(data)
                        except BlockingIOError:
                            pass
                        except OSError as e:
                            logger.warning(f"Device read error: {e}")
                            self.close()
                            break
                except Exception as e:
                    logger.error(f"Select loop error: {e}")
                    self.close()
                    time.sleep(1.0)
            else:
                try:
                    data = self.hid_device.read(128, timeout_ms=500)
                    if data:
                        self._handle_packet(bytes(data))
                except Exception as e:
                    logger.warning(f"HID read error: {e}")
                    self.close()
                    time.sleep(1.0)

    def stop(self):
        self.running = False
        self.close()
