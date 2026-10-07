#!/usr/bin/python3
"""Human-presence sensor diagnostics (run as root).
1) reads the sensor's HID feature report (state, power, reporting mode, type, names)
2) streams 60 s of raw HID input reports incl. sensor state and vendor fields."""
import glob, os, fcntl, select, time, struct

HUB = next(os.path.dirname(p) for p in glob.glob('/sys/bus/hid/devices/*/HID-SENSOR-200011*'))
HIDRAW = '/dev/' + os.listdir(HUB + '/hidraw')[0]
IIO = next(d for d in glob.glob('/sys/bus/iio/devices/iio:device*')
           if open(d + '/name').read().strip() == 'prox')
RID = 1
SEL = {0x840: 'no events', 0x841: 'all events', 0x842: 'threshold events', 0x843: 'wake: no events',
       0x844: 'wake: all events', 0x845: 'wake: threshold events',
       0x800: 'undefined', 0x801: 'READY', 0x802: 'NOT AVAILABLE', 0x803: 'NO DATA',
       0x804: 'INITIALIZING', 0x805: 'ACCESS DENIED', 0x806: 'ERROR',
       0x810: 'unknown', 0x811: 'state changed', 0x812: 'property changed', 0x813: 'data updated',
       0x814: 'poll response', 0x815: 'change sensitivity',
       0x830: 'integrated', 0x831: 'attached', 0x832: 'external',
       0x850: 'undefined', 0x851: 'D0 full power', 0x852: 'D1 low power', 0x853: 'D2 standby+wake',
       0x854: 'D3 sleep+wake', 0x855: 'D4 off'}

def bits(buf, off, size):
    return (int.from_bytes(buf, 'little') >> off) & ((1 << size) - 1)

def sx(v, size):
    return v - (1 << size) if v >> (size - 1) else v

def sel(buf, off, base):
    v = bits(buf, off, 8)
    return f"{SEL.get(base + v - 1, '?')} ({v})"

def text(buf, off, count):
    raw = bytes(bits(buf, off + 16 * i, 16) & 0xff for i in range(count))
    return raw.split(b'\0')[0].decode(errors='replace')

def feature():
    n = 296
    buf = bytearray(n); buf[0] = RID
    fcntl.ioctl(fd, (3 << 30) | (n << 16) | (ord('H') << 8) | 7, buf)
    b = bytes(buf[1:])
    print(f"  reporting state : {sel(b, 0, 0x840)}")
    print(f"  sensor state    : {sel(b, 8, 0x800)}")
    print(f"  connection      : {sel(b, 16, 0x830)}")
    print(f"  power state     : {sel(b, 24, 0x850)}")
    print(f"  min interval    : {bits(b, 32, 32)} ms   report interval: {bits(b, 64, 32)} ms")
    print(f"  description     : {text(b, 96, 7)!r}  model: {text(b, 560, 23)!r}")
    print(f"  manufacturer    : {text(b, 928, 16)!r}  serial: {text(b, 208, 22)!r}")
    print(f"  friendly name   : {text(b, 1184, 32)!r}")
    t = bits(b, 2352, 4)
    print(f"  HPD type bits   : {t:04b} (bit0 vendor non-biometric, bit1 vendor biometric, "
          f"bit2 facial, bit3 audio)")

def w(path, val):
    with open(f'{IIO}/{path}', 'w') as f:
        f.write(str(val))

print(f"hub {os.path.basename(HUB)}  {HIDRAW}  iio {os.path.basename(IIO)}")
fd = os.open(HIDRAW, os.O_RDWR | os.O_NONBLOCK)
print("== feature report, sensor idle"); feature()

chans = ['in_proximity0', 'in_proximity1', 'in_attention']
w('buffer/enable', 0)
for c in chans:
    w(f'scan_elements/{c}_en', 1)
w('trigger/current_trigger', os.path.basename(IIO).replace('iio:device', 'prox-dev'))
w('buffer/length', 64)
w('buffer/enable', 1)
iiofd = os.open('/dev/' + os.path.basename(IIO), os.O_RDONLY | os.O_NONBLOCK)
time.sleep(1)
print("== feature report, sensor streaming"); feature()

PH = [(0, 'sit still, look at the screen'), (20, 'WALK AWAY (3 m+)'), (40, 'come back and sit')]
print("== raw input reports for 60 s")
t0 = time.time(); ph = -1; n = 0
try:
    while (el := time.time() - t0) < 60:
        cur = max(i for i, (s, _) in enumerate(PH) if el >= s)
        if cur != ph:
            ph = cur; print(f">>> {el:5.1f}s NOW: {PH[cur][1]}", flush=True)
        r, _, _ = select.select([fd, iiofd], [], [], 0.25)
        if iiofd in r:
            os.read(iiofd, 4096)
        if fd not in r:
            continue
        rep = os.read(fd, 4096)
        if not rep or rep[0] != RID:
            continue
        b = rep[1:]; n += 1
        cust = [sx(bits(b, o, 32), 32) for o in (336, 368)] + [bits(b, o, 8) for o in (400, 408, 416, 424)]
        print(f"  {el:5.1f}s state={sel(b, 0, 0x800):18} event={sel(b, 8, 0x810):20} "
              f"presence={bits(b, 224, 8)} prox={bits(b, 208, 16)} attn={bits(b, 232, 8)} "
              f"cust1-6={cust} cust27/28={bits(b, 48, 32)}/{bits(b, 16, 32)}", flush=True)
except KeyboardInterrupt:
    pass
finally:
    os.close(iiofd)
    w('buffer/enable', 0)
    for c in chans:
        w(f'scan_elements/{c}_en', 0)
    w('trigger/current_trigger', '')
    print(f"{n} reports; == feature report after"); feature()
    os.close(fd)
