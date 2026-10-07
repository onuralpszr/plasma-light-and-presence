#!/bin/bash
# Keep the RGB camera sensor powered (without streaming) while running hpd-diag,
# so the CVS vision chip has a live sensor to look through. Run with sudo.
set -u
S=/sys/bus/i2c/drivers/ov08x40/i2c-OVTI08F4:00/power
echo on > $S/control; sleep 1
echo "ov08x40 runtime: $(cat $S/runtime_status)"
python3 "$(dirname "$(readlink -f "$0")")"/hpd-diag.py
echo auto > $S/control
echo "ov08x40 back to auto: $(cat $S/runtime_status)"
