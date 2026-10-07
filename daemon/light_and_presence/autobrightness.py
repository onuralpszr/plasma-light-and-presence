# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Brightness that follows the ambient light.

- Brightness follows a curve on log10(lux + 1), since the eye perceives light
  logarithmically.
- The light level is smoothed once per 2 s step, and the brightness only moves
  when the target differs by more than a small hysteresis, with a short fade.
- A brightness change made by the user that holds for a few seconds becomes
  an offset on top of the curve instead of being overwritten.
- A sharp drop (KDE dimming an idle screen) pauses the adjustment until the
  brightness comes back. Nothing is learned from it.
"""
import math
import time

import dbus

from . import config, log, state


class AutoBrightness:
    def __init__(self, display, sensor, settings):
        self.display = display
        self.sensor = sensor
        self.settings = settings
        self.lux = None
        self.offset = state.load_offset()
        self.pending = None      # (value, since) of an unexplained change
        self.paused_for = None   # brightness to wait for after idle dimming
        self.held = False        # another module (presence) owns the screen
        self.started = False

    @property
    def enabled(self):
        return self.settings.auto_enabled

    @property
    def paused(self):
        return self.paused_for is not None or self.held

    def apply_settings(self, settings):
        was = self.settings.auto_enabled
        self.settings = settings
        if was and not settings.auto_enabled:
            self.display.cancel_fade()
            self.pending = None
            self.paused_for = None
            log.info("automatic brightness disabled")
        elif settings.auto_enabled and not was:
            self.started = False
            log.info("automatic brightness enabled")

    # --- offset ----------------------------------------------------------
    def set_offset(self, value):
        self.offset = max(-config.OFFSET_LIMIT, min(config.OFFSET_LIMIT, float(value)))
        self.pending = None
        state.save_offset(self.offset)
        log.debug(f"offset set to {self.offset:+.1f}%")

    def reset_offset(self):
        self.set_offset(0.0)

    # --- curve -----------------------------------------------------------
    def curve_percent(self):
        x = math.log10(max(self.lux, 0.0) + 1)
        pts = self.settings.curve
        if x <= pts[0][0]:
            return pts[0][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x <= x1:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return pts[-1][1]

    def target_percent(self):
        if self.lux is None:
            return None
        s = self.settings
        return min(s.max_percent, max(s.min_percent, self.curve_percent() + self.offset))

    def target_raw(self):
        pct = self.target_percent()
        return None if pct is None else pct / 100 * self.display.max_raw

    # --- events ----------------------------------------------------------
    def on_external_change(self, before, value):
        """A brightness change that this daemon did not make."""
        if not self.enabled:
            return
        if self.paused_for is not None:
            if value >= self.paused_for - 2:
                log.debug("brightness restored, resuming")
                self.paused_for = None
            return
        if before and value <= before * config.DIM_RATIO:
            log.debug(f"sharp drop {before} -> {value}: idle dimming, pausing")
            self.display.cancel_fade()
            self.paused_for = before
            self.pending = None
            return
        self.display.cancel_fade()
        self.pending = (value, time.monotonic())

    def update_lux(self):
        new = self.sensor.filtered()
        if new is None:
            return
        a = self.settings.alpha
        self.lux = new if self.lux is None else a * new + (1 - a) * self.lux

    def tick(self):
        """Called every 2 s."""
        self.update_lux()
        if (not self.display.available or self.lux is None or not self.enabled
                or self.paused):
            return
        try:
            if not self.started:
                # Start from the curve plus the saved preference, not from
                # whatever brightness the session was left at.
                self.display.last_seen = self.display.current_raw()
                self.started = True
                log.debug(f"start: brightness {self.display.last_seen}, "
                          f"lux {self.lux:.0f}, offset {self.offset:+.1f}%")
            if self.pending:
                value, since = self.pending
                if time.monotonic() - since >= config.LEARN_AFTER_SECONDS:
                    self.offset = self.display.percent(value) - self.curve_percent()
                    self.offset = max(-config.OFFSET_LIMIT, min(config.OFFSET_LIMIT, self.offset))
                    state.save_offset(self.offset)
                    self.pending = None
                    log.info(f"learned offset {self.offset:+.1f}% at {self.lux:.0f} lx")
                return
            if self.display.fading:
                return
            cur = self.display.current_raw()
            target = self.target_raw()
            if abs(target - cur) / self.display.max_raw * 100 >= config.HYSTERESIS_PERCENT:
                log.debug(f"lux {self.lux:.0f}: {cur} -> {target:.0f}")
                self.display.fade(cur, target, osd=self.settings.show_osd,
                                  fade_ms=config.FADE_MS)
        except dbus.DBusException as e:
            log.debug("brightness error:", e.get_dbus_message())
            self.display.find()
