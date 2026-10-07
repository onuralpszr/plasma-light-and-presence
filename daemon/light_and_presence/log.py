# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>
"""Minimal logging to stderr, which systemd sends to the journal."""
import sys
import time

verbose = False


def _emit(*args):
    print(time.strftime("%H:%M:%S"), *args, file=sys.stderr, flush=True)


def debug(*args):
    if verbose:
        _emit(*args)


def info(*args):
    _emit(*args)


def warning(*args):
    _emit("warning:", *args)
