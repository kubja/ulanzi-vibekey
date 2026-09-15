#!/usr/bin/env python3
import os
import sys
import select
import glob
import time

def find_devices():
    devices = {}
    
    # hidraw
    for p in ["/dev/hidraw1", "/dev/hidraw2"]:
        if os.path.exists(p):
            try:
                fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
                devices[fd] = os.path.basename(p)
            except Exception as e:
                print(f"Failed to open {p}: {e}")
                
    # event devices
    for p in glob.glob("/dev/input/by-id/*AU05*"):
        try:
            fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
            devices[fd] = os.path.basename(p)
        except Exception as e:
            print(f"Failed to open {p}: {e}")

    return devices

def main():
    devices = find_devices()
    if not devices:
        print("No AU05 devices opened!")
        return

    print("Opened devices:")
    for fd, name in devices.items():
        print(f"  [{fd}] {name}")

    print("\nListening for inputs... (Press buttons or turn knob on AU05)")
    sys.stdout.flush()

    try:
        while True:
            rlist, _, _ = select.select(list(devices.keys()), [], [], 0.5)
            for fd in rlist:
                name = devices[fd]
                try:
                    data = os.read(fd, 256)
                    if data:
                        hex_str = " ".join(f"{b:02x}" for b in data)
                        print(f"[{time.strftime('%H:%M:%S')}] {name:30s} ({len(data):2d} bytes): {hex_str}")
                        sys.stdout.flush()
                except BlockingIOError:
                    pass
                except Exception as e:
                    print(f"Error reading {name}: {e}")
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        for fd in devices:
            os.close(fd)

if __name__ == "__main__":
    main()
