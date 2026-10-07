#!/usr/bin/python3
"""Stream the HID human-presence sensor live (run as root).
Prints every report as it arrives; restores settings on exit (Ctrl+C ok)."""
import glob, os, struct, time, select

P = next(d for d in glob.glob('/sys/bus/iio/devices/iio:device*')
         if open(d + '/name').read().strip() == 'prox')
dev = '/dev/' + os.path.basename(P)
DURATION = 120
PHASES = [(0, 'sit and look at the screen'), (20, 'turn your head away (stay seated)'),
          (40, 'look back at the screen'), (55, 'get up and WALK AWAY (3 m+)'),
          (90, 'come BACK and sit down')]

def w(path, val):
    with open(f'{P}/{path}', 'w') as f:
        f.write(str(val))

def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v

chans = ['in_proximity0', 'in_proximity1', 'in_attention']
w('buffer/enable', 0)
for c in chans:
    w(f'scan_elements/{c}_en', 1)
w('trigger/current_trigger', os.path.basename(P).replace('iio:device', 'prox-dev'))
w('buffer/length', 64)
w('buffer/enable', 1)
print(f"streaming {dev} for {DURATION} s, follow the prompts", flush=True)

fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
t0 = time.time()
phase = -1
n = 0
try:
    while (el := time.time() - t0) < DURATION:
        cur = max(i for i, (s, _) in enumerate(PHASES) if el >= s)
        if cur != phase:
            phase = cur
            print(f"\n>>> {el:5.1f}s  NOW: {PHASES[cur][1]}", flush=True)
        r, _, _ = select.select([fd], [], [], 0.25)
        if not r:
            continue
        data = os.read(fd, 12 * 64)
        for i in range(0, len(data) - 11, 12):
            p0, p1, att = struct.unpack_from('<III', data, i)
            n += 1
            print(f"  {el:5.1f}s  presence={sx(p0, 8):4}  distance={sx(p1, 16) / 1000:6.3f} m"
                  f"  attention={sx(att, 8):4}", flush=True)
except KeyboardInterrupt:
    pass
finally:
    os.close(fd)
    w('buffer/enable', 0)
    for c in chans:
        w(f'scan_elements/{c}_en', 0)
    w('trigger/current_trigger', '')
    print(f"\n{n} reports in {time.time() - t0:.0f} s; sensor settings restored")
