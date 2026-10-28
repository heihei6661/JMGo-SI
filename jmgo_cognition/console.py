"""Console helpers (Windows code pages break on CJK output)."""
from __future__ import annotations

import contextlib
import sys


def utf8_stdio() -> None:
    """Best-effort UTF-8 stdout/stderr on Windows and redirected consoles."""
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, OSError, ValueError):
            stream.reconfigure(encoding="utf-8", errors="replace")
