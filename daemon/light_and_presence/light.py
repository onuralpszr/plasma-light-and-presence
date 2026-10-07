# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Ambient light through iio-sensor-proxy on the system bus."""
import collections

import dbus

from . import config, log

SENSOR_BUS = "net.hadess.SensorProxy"
SENSOR_PATH = "/net/hadess/SensorProxy"


class LightSensor:
    """Samples the light level every 0.5 s and filters out glitches.

    iio-sensor-proxy only signals when the value changes, so a steady reading
    would never reach a signal handler. The level is polled instead.
    Some sensors report short bursts of impossible values (more than
    100000 lux for a second in a dark room), so readings above MaxLux are
    dropped and the result is a low percentile of the recent window: a burst
    cannot move it, a real change does within a few seconds.
    """

    def __init__(self, bus, settings):
        self.bus = bus
        self.settings = settings
        self.props = None
        self.raw = None
        self.samples = collections.deque(maxlen=settings.window_samples)
        bus.add_signal_receiver(self._on_owner, "NameOwnerChanged",
                                "org.freedesktop.DBus", arg0=SENSOR_BUS)
        self.claim()

    @property
    def available(self):
        return self.props is not None

    def apply_settings(self, settings):
        self.settings = settings
        if self.samples.maxlen != settings.window_samples:
            self.samples = collections.deque(self.samples, maxlen=settings.window_samples)

    def claim(self):
        self.props = None
        try:
            proxy = self.bus.get_object(SENSOR_BUS, SENSOR_PATH)
            props = dbus.Interface(proxy, dbus.PROPERTIES_IFACE)
            if not props.Get(SENSOR_BUS, "HasAmbientLight"):
                log.info("iio-sensor-proxy reports no ambient light sensor")
                return
            dbus.Interface(proxy, SENSOR_BUS).ClaimLight()
            self.props = props
            first = float(props.Get(SENSOR_BUS, "LightLevel"))
            self._add(first)
            log.debug("claimed the light sensor, first reading", first)
        except dbus.DBusException as e:
            log.warning("iio-sensor-proxy unavailable:", e.get_dbus_message())

    def _on_owner(self, name, old, new):
        if new:
            self.claim()
        else:
            self.props = None

    def _add(self, value):
        self.raw = value
        if value <= self.settings.max_lux:
            self.samples.append(value)
        else:
            log.debug(f"dropped glitch reading {value:.0f} lx")

    def sample(self):
        """Called every 0.5 s."""
        if self.props is None:
            return
        try:
            self._add(float(self.props.Get(SENSOR_BUS, "LightLevel")))
        except dbus.DBusException as e:
            log.debug("light sensor read failed:", e.get_dbus_message())

    def filtered(self):
        if not self.samples:
            return None
        values = sorted(self.samples)
        idx = int(round((len(values) - 1) * config.SPIKE_PERCENTILE / 100))
        return values[idx]
