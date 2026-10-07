# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Human presence: dim when away, lock when away longer, wake on return.

Presence is optional. Many laptops have no presence sensor, and some have one
that only reports "not available" (for example a camera based sensor that
works only while the camera streams). The module therefore treats a sensor as
usable only after it has reported changing, valid values. Until then nothing
is done and PresenceAvailable stays false.

Two sources are supported:
- an IIO device named "prox" (the kernel's HID human presence driver), read
  through sysfs. Reads may block while the sensor hub answers, so they run in
  a worker thread.
- iio-sensor-proxy's proximity sensor (ProximityNear), when it has one.

The screen is never unlocked by this module. Coming back only wakes the
display, which shows the lock screen if the session is locked.
"""
import glob
import os
import threading
import time

import dbus
from gi.repository import GLib

from . import log

SENSOR_BUS = "net.hadess.SensorProxy"
SENSOR_PATH = "/net/hadess/SensorProxy"
SCREENSAVER_BUS = "org.freedesktop.ScreenSaver"
SCREENSAVER_PATH = "/ScreenSaver"
INHIBIT_BUS = "org.freedesktop.PowerManagement.Inhibit"
INHIBIT_PATH = "/org/freedesktop/PowerManagement/Inhibit"
POLICY_BUS = "org.kde.Solid.PowerManagement.PolicyAgent"
POLICY_PATH = "/org/kde/Solid/PowerManagement/PolicyAgent"

FAST_POLL = 1.0       # seconds between reads while a sensor may be usable
SLOW_POLL = 15.0      # after PROBE_TIME without any useful value
PROBE_TIME = 120.0


class Reading:
    """One sample; None means the sensor does not know."""

    def __init__(self, present=None, attentive=None, distance=None):
        self.present = present
        self.attentive = attentive
        self.distance = distance

    def key(self):
        return (self.present, self.attentive, self.distance)

    @property
    def valid(self):
        return any(v is not None for v in self.key())


def _read(path):
    with open(path, encoding="ascii") as f:
        return f.read().strip()


def _bits(device, channel):
    """Storage bits and signedness from scan_elements, e.g. "le:s8/32>>0"."""
    try:
        kind = _read(os.path.join(device, "scan_elements", f"in_{channel}_type"))
        sign, rest = kind.split(":")[1][0], kind.split(":")[1][1:]
        return int(rest.split("/")[0]), sign == "s"
    except (OSError, ValueError, IndexError):
        return 32, True


def _signed(value, bits, signed):
    value &= (1 << bits) - 1
    if signed and value >> (bits - 1):
        value -= 1 << bits
    return value


class IioPresenceSource:
    """The HID human presence sensor ("prox") through IIO sysfs."""

    def __init__(self, device):
        self.device = device
        self.has_distance = os.path.exists(os.path.join(device, "in_proximity1_raw"))
        self.has_attention = os.path.exists(os.path.join(device, "in_attention_input"))
        self.presence_bits = _bits(device, "proximity0")
        self.distance_bits = _bits(device, "proximity1")
        self.name = f"IIO {os.path.basename(device)}"

    @staticmethod
    def find():
        for name_file in sorted(glob.glob("/sys/bus/iio/devices/iio:device*/name")):
            try:
                if _read(name_file) != "prox":
                    continue
            except OSError:
                continue
            device = os.path.dirname(name_file)
            if os.path.exists(os.path.join(device, "in_proximity0_raw")):
                return IioPresenceSource(device)
        return None

    def read(self):
        r = Reading()
        try:
            v = _signed(int(_read(os.path.join(self.device, "in_proximity0_raw"))),
                        *self.presence_bits)
            if v >= 0:
                r.present = v > 0
        except (OSError, ValueError):
            pass
        if self.has_distance:
            try:
                v = _signed(int(_read(os.path.join(self.device, "in_proximity1_raw"))),
                            *self.distance_bits)
                if v >= 0:
                    scale = float(_read(os.path.join(self.device, "in_proximity1_scale")))
                    r.distance = round(v * scale, 3)
            except (OSError, ValueError):
                pass
        if self.has_attention:
            try:
                # Reported as a percentage; out of range means unknown.
                v = int(float(_read(os.path.join(self.device, "in_attention_input"))))
                if 0 <= v <= 100:
                    r.attentive = v > 0
            except (OSError, ValueError):
                pass
        return r


class ProxyPresenceSource:
    """iio-sensor-proxy's proximity sensor: near means present."""

    name = "iio-sensor-proxy"

    def __init__(self, props):
        self.props = props

    @staticmethod
    def find(bus):
        try:
            proxy = bus.get_object(SENSOR_BUS, SENSOR_PATH)
            props = dbus.Interface(proxy, dbus.PROPERTIES_IFACE)
            if not props.Get(SENSOR_BUS, "HasProximity"):
                return None
            dbus.Interface(proxy, SENSOR_BUS).ClaimProximity()
            return ProxyPresenceSource(props)
        except dbus.DBusException:
            return None

    def read(self):
        try:
            return Reading(present=bool(self.props.Get(SENSOR_BUS, "ProximityNear")))
        except dbus.DBusException:
            return Reading()


class Poller:
    """Reads a source in a worker thread and hands results to the main loop."""

    def __init__(self, source, callback):
        self.source = source
        self.callback = callback
        self.interval = FAST_POLL
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="presence", daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            reading = self.source.read()
            GLib.idle_add(self._deliver, reading)
            self.stop_event.wait(self.interval)

    def _deliver(self, reading):
        if not self.stop_event.is_set():
            self.callback(reading)
        return False

    def stop(self):
        self.stop_event.set()


class Presence:
    def __init__(self, system_bus, session_bus, display, auto, settings, notify):
        self.sysbus = system_bus
        self.bus = session_bus
        self.display = display
        self.auto = auto
        self.settings = settings
        self.notify = notify

        self.source = None
        self.poller = None
        self.started_at = None
        self.first = None          # first valid reading, to detect a change
        self.usable = False

        self.present = None
        self.attentive = None
        self.distance = None
        self.away_since = None
        self.look_away_since = None
        self.dimmed = None         # "away" or "look" while this module dims
        self.dim_target = None
        self.restore_raw = None
        self.locked_by_us = False
        self.screen_locked = False

        self.bus.add_signal_receiver(self._on_screensaver, "ActiveChanged",
                                     SCREENSAVER_BUS, path=SCREENSAVER_PATH)
        try:
            ss = self.bus.get_object(SCREENSAVER_BUS, SCREENSAVER_PATH)
            self.screen_locked = bool(dbus.Interface(ss, SCREENSAVER_BUS).GetActive())
        except dbus.DBusException:
            pass
        self.apply_settings(settings)

    # --- properties for the D-Bus service ---------------------------------
    @property
    def available(self):
        return self.usable

    @property
    def active(self):
        return self.usable and self.settings.presence_enabled

    @property
    def state_text(self):
        if not self.active:
            return "unavailable" if not self.usable else "disabled"
        if self.present is None:
            return "unknown"
        if not self.present:
            return "away"
        if self.attentive is False:
            return "looking-away"
        return "present"

    # --- setup -------------------------------------------------------------
    def apply_settings(self, settings):
        self.settings = settings
        if settings.presence_enabled:
            self._start()
        else:
            self._stop()

    def _start(self):
        if self.poller:
            return
        self.source = IioPresenceSource.find() or ProxyPresenceSource.find(self.sysbus)
        if not self.source:
            log.debug("no presence sensor found")
            return
        log.debug("probing presence sensor:", self.source.name)
        self.started_at = time.monotonic()
        self.poller = Poller(self.source, self._on_reading)

    def _stop(self):
        if self.poller:
            self.poller.stop()
            self.poller = None
        self.restore()
        self.present = self.attentive = self.distance = None
        self.away_since = self.look_away_since = None
        self.notify()

    def shutdown(self):
        if self.poller:
            self.poller.stop()
            self.poller = None
        # The main loop is about to stop, so a fade would never finish.
        self.display.cancel_fade()
        self.restore(immediate=True)

    # --- readings ------------------------------------------------------------
    def _on_reading(self, r):
        if not self.usable:
            if r.valid:
                if self.first is None:
                    self.first = r.key()
                elif r.key() != self.first:
                    self.usable = True
                    self.poller.interval = FAST_POLL
                    log.info(f"presence sensor is usable ({self.source.name})")
            if not self.usable:
                if time.monotonic() - self.started_at > PROBE_TIME:
                    self.poller.interval = SLOW_POLL
                return
        now = time.monotonic()
        was_present = self.present
        self.present, self.attentive, self.distance = r.present, r.attentive, r.distance

        if self.present is False:
            if self.away_since is None:
                self.away_since = now
        else:
            self.away_since = None
        if self.present and self.attentive is False:
            if self.look_away_since is None:
                self.look_away_since = now
        else:
            self.look_away_since = None

        if self.present and was_present is False:
            self._on_return()
        elif self.present and self.attentive and self.dimmed == "look":
            self.restore()
        self._act(now)
        self.notify()

    def _on_return(self):
        log.debug("user returned")
        self.restore()
        if self.settings.wake_on_return and (self.screen_locked or self.locked_by_us):
            # Wakes the display. The lock screen stays; nothing is unlocked.
            self._call(SCREENSAVER_BUS, SCREENSAVER_PATH, SCREENSAVER_BUS,
                       "SimulateUserActivity")
        self.locked_by_us = False

    def _act(self, now):
        s = self.settings
        if not self.active or self.screen_locked:
            return
        if self.away_since is not None:
            away = now - self.away_since
            if s.lock_when_away and away >= s.lock_away_seconds:
                if not self._inhibited():
                    self.lock()
                return
            if s.dim_when_away and away >= s.dim_away_seconds and self.dimmed != "away":
                if not self._inhibited():
                    self.dim("away")
            return
        if (self.look_away_since is not None and s.dim_when_looking_away
                and now - self.look_away_since >= s.look_away_seconds
                and self.dimmed is None and not self._inhibited()):
            self.dim("look")

    # --- actions -------------------------------------------------------------
    def dim(self, reason):
        if not self.display.available:
            return
        try:
            current = self.display.current_raw() if self.dimmed is None else self.restore_raw
        except dbus.DBusException:
            return
        if self.dimmed is None:
            self.restore_raw = current
        target = self.restore_raw * self.settings.dim_level_percent / 100
        self.dimmed = reason
        self.dim_target = target
        self.auto.held = True
        log.info(f"dimming ({reason})")
        self.display.fade(self.display.last_seen or current, target, fade_ms=1500)

    def restore(self, immediate=False):
        if self.dimmed is None:
            return
        log.debug("restoring brightness")
        self.dimmed = None
        self.auto.held = False
        if not self.display.available:
            return
        target = self.auto.target_raw() if self.auto.enabled else None
        if target is None:
            target = self.restore_raw
        if immediate:
            try:
                self.display.set_raw(target)
            except dbus.DBusException:
                pass
            return
        start = self.display.last_seen if self.display.last_seen is not None else target
        self.display.fade(start, target, fade_ms=400)

    def on_external_brightness(self, before, value):
        """A brightness change not made by this daemon while dimmed.

        Returns True when it was handled here. KDE's own idle dimming lowers
        the brightness further and later restores it to the dimmed value;
        both are ignored. Anything else means the user took over.
        """
        if self.dimmed is None:
            return False
        if before is not None and value < before:
            return True
        if self.dim_target is not None and abs(value - self.dim_target) <= self.display.max_raw * 0.02:
            return True
        log.debug("user changed brightness while dimmed")
        self.dimmed = None
        self.auto.held = False
        return True

    def lock(self):
        if self.locked_by_us:
            return
        self.locked_by_us = True
        log.info("locking the session (away)")
        try:
            pid, _, _, _ = GLib.spawn_async(
                ["loginctl", "lock-session"],
                flags=GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.DO_NOT_REAP_CHILD)
        except GLib.Error as e:
            log.warning("loginctl failed:", e.message)
            self._lock_fallback()
            return

        def done(pid, status):
            GLib.spawn_close_pid(pid)
            try:
                GLib.spawn_check_wait_status(status)
            except GLib.Error as e:
                log.debug("loginctl lock-session failed:", e.message)
                self._lock_fallback()

        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, done)

    def _lock_fallback(self):
        # A user service may not belong to a login session; ask the
        # session's screen locker directly.
        self._call(SCREENSAVER_BUS, SCREENSAVER_PATH, SCREENSAVER_BUS, "Lock")

    def _on_screensaver(self, active):
        self.screen_locked = bool(active)
        if not self.screen_locked:
            self.locked_by_us = False
            self.restore()
        self.notify()

    def _inhibited(self):
        if not self.settings.respect_inhibitors:
            return False
        try:
            obj = self.bus.get_object(INHIBIT_BUS, INHIBIT_PATH)
            if bool(dbus.Interface(obj, INHIBIT_BUS).HasInhibit()):
                return True
        except dbus.DBusException:
            pass
        try:
            obj = self.bus.get_object(POLICY_BUS, POLICY_PATH)
            active = dbus.Interface(obj, dbus.PROPERTIES_IFACE).Get(
                "org.kde.Solid.PowerManagement.PolicyAgent", "ActiveInhibitions")
            if len(active) > 0:
                return True
        except dbus.DBusException:
            pass
        return False

    def _call(self, service, path, iface, method):
        try:
            obj = self.bus.get_object(service, path)
            getattr(dbus.Interface(obj, iface), method)(
                reply_handler=lambda *a: None,
                error_handler=lambda e: log.warning(f"{method} failed:", e.get_dbus_message()))
        except dbus.DBusException as e:
            log.warning(f"{method} failed:", e.get_dbus_message())
