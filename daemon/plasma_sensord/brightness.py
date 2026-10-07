# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Screen brightness through KDE's org.kde.ScreenBrightness (session bus)."""
import time

import dbus
from gi.repository import GLib

from . import log

BRIGHT_BUS = "org.kde.ScreenBrightness"
BRIGHT_PATH = "/org/kde/ScreenBrightness"
DISPLAY_IFACE = "org.kde.ScreenBrightness.Display"
SUPPRESS_INDICATOR = 0x1  # no OSD for this change
FADE_STEP_MS = 50


class Display:
    """The internal display.

    Changes made by this daemon are remembered for a few seconds so that the
    PropertiesChanged signals they cause are not mistaken for user changes.
    KDE also re-announces unchanged values; those are ignored too.
    """

    def __init__(self, bus, dry_run=False):
        self.bus = bus
        self.dry_run = dry_run
        self.obj = None
        self.path = None
        self.max_raw = 10000
        self.last_seen = None
        self.ours = []
        self.fade_id = 0
        self.on_external_change = None  # callback(before, value)
        bus.add_signal_receiver(self._on_props, "PropertiesChanged",
                                dbus.PROPERTIES_IFACE, BRIGHT_BUS,
                                path_keyword="path")
        bus.add_signal_receiver(self._on_owner, "NameOwnerChanged",
                                "org.freedesktop.DBus", arg0=BRIGHT_BUS)
        self.find()

    @property
    def available(self):
        return self.obj is not None

    def find(self):
        self.obj = None
        self.path = None
        try:
            root = self.bus.get_object(BRIGHT_BUS, BRIGHT_PATH)
            names = dbus.Interface(root, dbus.PROPERTIES_IFACE).Get(
                BRIGHT_BUS, "DisplaysDBusNames")
        except dbus.DBusException as e:
            log.warning("KDE screen brightness unavailable:", e.get_dbus_message())
            return
        candidates = list(names) or ["display0"]
        for name in candidates:
            path = f"{BRIGHT_PATH}/{name}"
            try:
                obj = self.bus.get_object(BRIGHT_BUS, path)
                props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
                if not props.Get(DISPLAY_IFACE, "IsInternal"):
                    continue
                self.obj = obj
                self.path = path
                self.max_raw = max(1, int(props.Get(DISPLAY_IFACE, "MaxBrightness")))
                self.last_seen = int(props.Get(DISPLAY_IFACE, "Brightness"))
                log.debug("internal display:", name, "max", self.max_raw)
                return
            except dbus.DBusException:
                continue
        log.info("no internal display found")

    def _on_owner(self, name, old, new):
        self.cancel_fade()
        if new:
            self.find()
        else:
            self.obj = None

    def current_raw(self):
        props = dbus.Interface(self.obj, dbus.PROPERTIES_IFACE)
        return int(props.Get(DISPLAY_IFACE, "Brightness"))

    def percent(self, raw=None):
        raw = self.last_seen if raw is None else raw
        if raw is None:
            return 0.0
        return raw / self.max_raw * 100

    def set_raw(self, value, osd=False):
        value = int(round(max(0, min(self.max_raw, value))))
        self.last_seen = value
        self.ours.append((value, time.monotonic()))
        self.ours = self.ours[-64:]
        if self.dry_run:
            log.debug("dry run: would set brightness", value)
            return
        flags = 0 if osd else SUPPRESS_INDICATOR
        dbus.Interface(self.obj, DISPLAY_IFACE).SetBrightness(
            dbus.Int32(value), dbus.UInt32(flags))

    def _is_ours(self, value):
        now = time.monotonic()
        return any(abs(v - value) <= 2 and now - t < 3 for v, t in self.ours)

    def _on_props(self, iface, changed, invalidated, path=None):
        if path != self.path or iface != DISPLAY_IFACE or "Brightness" not in changed:
            return
        value = int(changed["Brightness"])
        if self._is_ours(value):
            return
        if self.last_seen is not None and abs(value - self.last_seen) <= 2:
            return  # an unchanged value announced again, not a user change
        before, self.last_seen = self.last_seen, value
        if self.on_external_change:
            self.on_external_change(before, value)

    def fade(self, start, end, osd=False, fade_ms=800, on_done=None):
        """Move from start to end in short steps; OSD only on the last one."""
        self.cancel_fade()
        steps = max(1, fade_ms // FADE_STEP_MS)
        state = {"i": 0}

        def step():
            state["i"] += 1
            last = state["i"] >= steps
            try:
                self.set_raw(start + (end - start) * state["i"] / steps, osd=osd and last)
            except dbus.DBusException as e:
                log.debug("brightness change failed:", e.get_dbus_message())
                last = True
            if last:
                self.fade_id = 0
                if on_done:
                    on_done()
                return False
            return True

        self.fade_id = GLib.timeout_add(FADE_STEP_MS, step)

    @property
    def fading(self):
        return self.fade_id != 0

    def cancel_fade(self):
        if self.fade_id:
            GLib.source_remove(self.fade_id)
            self.fade_id = 0
