# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Entry point: wires the sensors, the display and the D-Bus service."""
import argparse
import os
import signal
import sys

import dbus
import dbus.mainloop.glib
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from . import __version__, config, log  # noqa: E402
from .autobrightness import AutoBrightness  # noqa: E402
from .brightness import Display  # noqa: E402
from .light import LightSensor  # noqa: E402
from .presence import Presence  # noqa: E402
from .service import Service  # noqa: E402


class Daemon:
    def __init__(self, dry_run=False):
        self.sysbus = dbus.SystemBus()
        self.sesbus = dbus.SessionBus()
        self.settings = config.load()
        self.service = None
        self.reload_id = 0

        self.sensor = LightSensor(self.sysbus, self.settings)
        self.display = Display(self.sesbus, dry_run=dry_run)
        self.auto = AutoBrightness(self.display, self.sensor, self.settings)
        self.presence = Presence(self.sysbus, self.sesbus, self.display, self.auto,
                                 self.settings, self.notify)
        self.display.on_external_change = self.on_brightness_changed

        self.monitor = self._watch_config()
        GLib.timeout_add(500, self._sample)
        GLib.timeout_add_seconds(2, self._tick)

    def notify(self):
        if self.service:
            self.service.notify()

    # --- timers -------------------------------------------------------------
    def _sample(self):
        self.sensor.sample()
        return True

    def _tick(self):
        self.auto.tick()
        self.notify()
        return True

    def on_brightness_changed(self, before, value):
        if not self.presence.on_external_brightness(before, value):
            self.auto.on_external_change(before, value)
        self.notify()

    # --- settings -----------------------------------------------------------
    def _watch_config(self):
        # KConfig replaces the file on save, so watch the directory.
        directory = Gio.File.new_for_path(config.config_home())
        try:
            monitor = directory.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        except GLib.Error as e:
            log.warning("cannot watch the settings file:", e.message)
            return None
        monitor.connect("changed", self._on_config_event)
        return monitor

    def _on_config_event(self, monitor, file, other, event):
        names = {f.get_basename() for f in (file, other) if f is not None}
        if config.CONFIG_NAME not in names:
            return
        if self.reload_id:
            GLib.source_remove(self.reload_id)
        self.reload_id = GLib.timeout_add(300, self._reload_later)

    def _reload_later(self):
        self.reload_id = 0
        self.reload()
        return False

    def reload(self):
        new = config.load()
        if new == self.settings:
            return
        log.debug("settings changed, applying")
        self.settings = new
        self.sensor.apply_settings(new)
        self.auto.apply_settings(new)
        self.presence.apply_settings(new)
        self.notify()

    def _write(self, group, key, value):
        try:
            config.write_entry(group, key, value)
        except OSError as e:
            log.warning("cannot write the settings file:", e)
        self.reload()

    def set_auto_enabled(self, on):
        self._write("AutoBrightness", "Enabled", on)

    def set_presence_enabled(self, on):
        self._write("Presence", "Enabled", on)

    def set_show_osd(self, on):
        self._write("AutoBrightness", "ShowOsd", on)

    def shutdown(self):
        self.presence.shutdown()


def main():
    parser = argparse.ArgumentParser(
        prog="plasma-light-and-presence",
        description="Adjust screen brightness from the ambient light sensor and "
                    "react to human presence.")
    parser.add_argument("--debug", action="store_true", help="log every decision")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the sensors but never change the brightness")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()
    log.verbose = args.debug or os.environ.get("LIGHT_AND_PRESENCE_DEBUG") == "1"

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    try:
        daemon = Daemon(dry_run=args.dry_run)
    except dbus.DBusException as e:
        print("cannot connect to D-Bus:", e.get_dbus_message(), file=sys.stderr)
        sys.exit(1)
    try:
        daemon.service = Service(daemon.sesbus, daemon)
    except dbus.exceptions.NameExistsException:
        print("another instance is already running", file=sys.stderr)
        sys.exit(1)

    loop = GLib.MainLoop()

    def stop():
        daemon.shutdown()
        loop.quit()
        return False

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
    log.info(f"plasma-light-and-presence {__version__} started"
             + (" (dry run)" if args.dry_run else ""))
    loop.run()
