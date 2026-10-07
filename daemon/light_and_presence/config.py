# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Settings from plasma-light-and-presencerc.

The file is written by the System Settings page through KConfigXT, so it uses
the KConfig INI dialect. System-wide defaults may be placed in
/etc/xdg/plasma-light-and-presencerc; the per-user file in ~/.config overrides them.
"""
import math
import os
import re

CONFIG_NAME = "plasma-light-and-presencerc"

# Smoothing weight per 2 s control step for each Responsiveness choice.
RESPONSIVENESS_ALPHA = {"Slow": 0.15, "Normal": 0.3, "Fast": 0.5}

DEFAULT_CURVE = "0:8 10:25 100:45 1000:75 10000:100"

# (group, key): (attribute, type, default)
ENTRIES = {
    ("AutoBrightness", "Enabled"): ("auto_enabled", bool, True),
    ("AutoBrightness", "MinPercent"): ("min_percent", int, 5),
    ("AutoBrightness", "MaxPercent"): ("max_percent", int, 100),
    ("AutoBrightness", "Responsiveness"): ("responsiveness", str, "Normal"),
    ("AutoBrightness", "ShowOsd"): ("show_osd", bool, False),
    ("AutoBrightness", "Curve"): ("curve_text", str, DEFAULT_CURVE),
    ("Presence", "Enabled"): ("presence_enabled", bool, True),
    ("Presence", "DimWhenAway"): ("dim_when_away", bool, True),
    ("Presence", "DimAwaySeconds"): ("dim_away_seconds", int, 30),
    ("Presence", "LockWhenAway"): ("lock_when_away", bool, True),
    ("Presence", "LockAwaySeconds"): ("lock_away_seconds", int, 60),
    ("Presence", "WakeOnReturn"): ("wake_on_return", bool, True),
    ("Presence", "DimWhenLookingAway"): ("dim_when_looking_away", bool, False),
    ("Presence", "LookAwaySeconds"): ("look_away_seconds", int, 20),
    ("Presence", "DimLevelPercent"): ("dim_level_percent", int, 30),
    ("Presence", "RespectInhibitors"): ("respect_inhibitors", bool, True),
    ("Sensors", "MaxLux"): ("max_lux", int, 40000),
    ("Sensors", "SpikeWindowSeconds"): ("spike_window_seconds", int, 6),
}

# Values that are not exposed in the settings file.
HYSTERESIS_PERCENT = 4.0
SPIKE_PERCENTILE = 30.0
FADE_MS = 800
LEARN_AFTER_SECONDS = 10.0
DIM_RATIO = 0.5
OFFSET_LIMIT = 50.0


def config_home():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def user_config_path():
    return os.path.join(config_home(), CONFIG_NAME)


def system_config_paths():
    dirs = os.environ.get("XDG_CONFIG_DIRS") or "/etc/xdg"
    # Later files override earlier ones, so read the least important first.
    return [os.path.join(d, CONFIG_NAME) for d in reversed(dirs.split(":")) if d]


_GROUP_RE = re.compile(r"^\[([^\]]*)\]")
_KEY_RE = re.compile(r"^([^=\[]+?)\s*(\[[^\]]*\])*\s*=\s*(.*)$")


def parse_kconfig(text):
    """Return {(group, key): value} for the plain (unlocalised) entries."""
    values = {}
    group = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _GROUP_RE.match(line)
        if m:
            group = m.group(1)
            continue
        m = _KEY_RE.match(line)
        if not m:
            continue
        key, suffix, value = m.group(1).strip(), m.group(2), m.group(3)
        if suffix and not suffix.startswith("[$"):
            continue  # a translated value such as Name[de]
        values[(group, key)] = value.strip()
    return values


def _convert(kind, text, default):
    if kind is bool:
        low = text.lower()
        if low in ("true", "on", "yes", "1"):
            return True
        if low in ("false", "off", "no", "0"):
            return False
        return default
    if kind is int:
        try:
            return int(text)
        except ValueError:
            return default
    return text


def parse_curve(text):
    """"lux:percent" pairs, returned as (log10(lux + 1), percent) points."""
    points = []
    for item in text.split():
        try:
            lux, pct = item.split(":")
            points.append((math.log10(max(float(lux), 0.0) + 1), float(pct)))
        except ValueError:
            continue
    if len(points) < 2:
        return parse_curve(DEFAULT_CURVE)
    return sorted(points)


class Settings:
    def __init__(self, raw=None):
        raw = raw or {}
        for (group, key), (attr, kind, default) in ENTRIES.items():
            value = default
            if (group, key) in raw:
                value = _convert(kind, raw[(group, key)], default)
            setattr(self, attr, value)
        self.min_percent = min(max(self.min_percent, 1), 100)
        self.max_percent = min(max(self.max_percent, self.min_percent), 100)
        self.curve = parse_curve(self.curve_text)
        self.alpha = RESPONSIVENESS_ALPHA.get(self.responsiveness, 0.3)
        self.spike_window_seconds = min(max(self.spike_window_seconds, 1), 30)

    @property
    def window_samples(self):
        # The light sensor is sampled every 0.5 s.
        return max(1, self.spike_window_seconds * 2)

    def __eq__(self, other):
        return isinstance(other, Settings) and vars(self) == vars(other)


def load():
    raw = {}
    for path in system_config_paths() + [user_config_path()]:
        try:
            with open(path, encoding="utf-8") as f:
                raw.update(parse_kconfig(f.read()))
        except OSError:
            continue
    return Settings(raw)


def write_entry(group, key, value):
    """Change one key in the user file, keeping everything else as it is."""
    path = user_config_path()
    if isinstance(value, bool):
        value = "true" if value else "false"
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        lines = []

    out = []
    current = None
    in_group = False
    done = False
    for line in lines:
        stripped = line.strip()
        m = _GROUP_RE.match(stripped)
        if m:
            if in_group and not done:
                _insert_before_blank(out, f"{key}={value}")
                done = True
            current = m.group(1)
            in_group = current == group
            out.append(line)
            continue
        if in_group and not done:
            km = _KEY_RE.match(stripped)
            if km and km.group(1).strip() == key and not km.group(2):
                out.append(f"{key}={value}")
                done = True
                continue
        out.append(line)
    if not done:
        if in_group:
            _insert_before_blank(out, f"{key}={value}")
        else:
            if out and out[-1].strip():
                out.append("")
            out.append(f"[{group}]")
            out.append(f"{key}={value}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".plasma-light-and-presence.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, path)


def _insert_before_blank(out, line):
    idx = len(out)
    while idx > 0 and not out[idx - 1].strip():
        idx -= 1
    out.insert(idx, line)
