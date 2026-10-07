# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""io.github.onuralpszr.LightAndPresence on the session bus.

Used by the System Settings page and the Plasma widget. Live values are
properties; every change is announced with PropertiesChanged.
"""
import dbus
import dbus.service

from . import __version__

SERVICE = "io.github.onuralpszr.LightAndPresence"
OBJECT_PATH = "/io/github/onuralpszr/LightAndPresence"
IFACE = SERVICE

# name -> (D-Bus signature, writable)
PROPERTIES = {
    "Version": ("s", False),
    "AutoBrightnessEnabled": ("b", True),
    "ShowOsd": ("b", True),
    "LightSensorAvailable": ("b", False),
    "DisplayAvailable": ("b", False),
    "Lux": ("d", False),
    "Brightness": ("d", False),
    "Target": ("d", False),
    "Offset": ("d", False),
    "Paused": ("b", False),
    "PresenceEnabled": ("b", True),
    "PresenceAvailable": ("b", False),
    "Present": ("b", False),
    "Attentive": ("b", False),
    "Distance": ("d", False),
    "PresenceState": ("s", False),
}


class Service(dbus.service.Object):
    def __init__(self, bus, daemon):
        self.daemon = daemon
        self.last = {}
        name = dbus.service.BusName(SERVICE, bus, do_not_queue=True)
        super().__init__(name, OBJECT_PATH)

    def values(self):
        d = self.daemon
        auto, display, presence = d.auto, d.display, d.presence
        target = auto.target_percent()
        return {
            "Version": dbus.String(__version__),
            "AutoBrightnessEnabled": dbus.Boolean(d.settings.auto_enabled),
            "ShowOsd": dbus.Boolean(d.settings.show_osd),
            "LightSensorAvailable": dbus.Boolean(d.sensor.available),
            "DisplayAvailable": dbus.Boolean(display.available),
            "Lux": dbus.Double(round(auto.lux or 0.0, 1)),
            "Brightness": dbus.Double(round(display.percent(), 1)),
            "Target": dbus.Double(round(target, 1) if target is not None else 0.0),
            "Offset": dbus.Double(round(auto.offset, 1)),
            "Paused": dbus.Boolean(auto.paused),
            "PresenceEnabled": dbus.Boolean(d.settings.presence_enabled),
            "PresenceAvailable": dbus.Boolean(presence.available),
            "Present": dbus.Boolean(presence.present is not False),
            "Attentive": dbus.Boolean(presence.attentive is not False),
            "Distance": dbus.Double(presence.distance if presence.distance is not None else -1.0),
            "PresenceState": dbus.String(presence.state_text),
        }

    def notify(self):
        now = self.values()
        changed = {k: v for k, v in now.items() if self.last.get(k) != v}
        if changed:
            self.last = now
            self.PropertiesChanged(IFACE, changed, dbus.Array([], signature="s"))

    # --- org.freedesktop.DBus.Properties ------------------------------------
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
    def Get(self, iface, prop):
        values = self.values()
        if prop not in values:
            raise dbus.exceptions.DBusException(
                f"no property {prop}", name="org.freedesktop.DBus.Error.UnknownProperty")
        return values[prop]

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return self.values()

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ssv")
    def Set(self, iface, prop, value):
        if prop == "AutoBrightnessEnabled":
            self.daemon.set_auto_enabled(bool(value))
        elif prop == "PresenceEnabled":
            self.daemon.set_presence_enabled(bool(value))
        elif prop == "ShowOsd":
            self.daemon.set_show_osd(bool(value))
        else:
            raise dbus.exceptions.DBusException(
                f"{prop} is read-only", name="org.freedesktop.DBus.Error.PropertyReadOnly")

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, iface, changed, invalidated):
        pass

    @dbus.service.method(dbus.INTROSPECTABLE_IFACE, in_signature="", out_signature="s",
                         path_keyword="object_path", connection_keyword="connection")
    def Introspect(self, object_path, connection):
        xml = super().Introspect(object_path, connection)
        props = "".join(
            f'    <property name="{name}" type="{sig}" access="{"readwrite" if rw else "read"}"/>\n'
            for name, (sig, rw) in PROPERTIES.items())
        marker = f'<interface name="{IFACE}">\n'
        return xml.replace(marker, marker + props, 1)

    # --- io.github.onuralpszr.LightAndPresence --------------------------------------------
    @dbus.service.method(IFACE, in_signature="b")
    def SetAutoBrightnessEnabled(self, on):
        self.daemon.set_auto_enabled(bool(on))

    @dbus.service.method(IFACE, in_signature="b")
    def SetPresenceEnabled(self, on):
        self.daemon.set_presence_enabled(bool(on))

    @dbus.service.method(IFACE, in_signature="d")
    def SetOffset(self, value):
        self.daemon.auto.set_offset(value)
        self.notify()

    @dbus.service.method(IFACE)
    def ResetOffset(self):
        self.daemon.auto.reset_offset()
        self.notify()

    @dbus.service.method(IFACE)
    def Reload(self):
        self.daemon.reload()

    # Argument-free variants, convenient from QML.
    @dbus.service.method(IFACE)
    def EnableAutoBrightness(self):
        self.daemon.set_auto_enabled(True)

    @dbus.service.method(IFACE)
    def DisableAutoBrightness(self):
        self.daemon.set_auto_enabled(False)

    @dbus.service.method(IFACE)
    def EnablePresence(self):
        self.daemon.set_presence_enabled(True)

    @dbus.service.method(IFACE)
    def DisablePresence(self):
        self.daemon.set_presence_enabled(False)
