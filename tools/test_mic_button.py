#!/usr/bin/env python3
import os
import sys
import glob
import select
import time

nodes = {}
for p in glob.glob("/sys/class/hidraw/hidraw*"):
    uevent = os.path.join(p, "device/uevent")
    if os.path.exists(uevent):
        with open(uevent) as f:
            c = f.read()
        if "FFF1" in c.upper() and "00DD" in c.upper():
            dev = "/dev/" + os.path.basename(p)
            fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
            nodes[fd] = dev

print(f"Listening on AU05 nodes: {list(nodes.values())}")
print(">>> TEST: Please press and HOLD the mic button for 3 seconds, then RELEASE it! <<<")
sys.stdout.flush()

start = time.time()
while time.time() - start < 8:
    r, _, _ = select.select(list(nodes.keys()), [], [], 0.1)
    for fd in r:
        try:
            d = os.read(fd, 64)
            if d:
                hex_str = " ".join(f"{b:02x}" for b in d)
                elapsed = time.time() - start
                print(f"[{elapsed:5.2f}s] {nodes[fd]}: {hex_str}")
                sys.stdout.flush()
        except Exception:
            pass

for fd in nodes:
    os.close(fd)
print("Test completed.")
