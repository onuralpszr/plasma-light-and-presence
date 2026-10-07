# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Learned state (the brightness offset), kept apart from the settings."""
import configparser
import os

from . import log


def state_home():
    return os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")


STATE_FILE = os.path.join(state_home(), "plasma-light-and-presence", "state")


def _read_offset(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    cp = configparser.ConfigParser()
    try:
        cp.read_string(text)
        return cp.getfloat("state", "offset", fallback=0.0)
    except (configparser.Error, ValueError):
        return None


def load_offset():
    offset = _read_offset(STATE_FILE)
    return offset if offset is not None else 0.0


def save_offset(offset):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(f"[state]\noffset = {offset:.2f}\n")
        os.replace(tmp, STATE_FILE)
    except OSError as e:
        log.warning("cannot save state:", e)
