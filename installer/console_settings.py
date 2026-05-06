"""Read Console worker port/host from Pilot settings.

Vendored copy of ``launcher/console_settings.py`` — the installer must work
standalone (pipx, ``curl | sh``) where the launcher source tree may not be
on ``sys.path`` (see ``.claude/rules/pilot-shell-package-boundaries.md``).

Keep this file in sync with ``launcher/console_settings.py`` and
``pilot/hooks/_lib/console_settings.py`` if any is edited.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PORT = 41777
DEFAULT_HOST = "127.0.0.1"

_SETTINGS_PATH = Path.home() / ".pilot" / "memory" / "settings.json"


def _read_setting(key: str, default: str) -> str:
    """Return setting value from settings.json, or default on any error."""
    try:
        if not _SETTINGS_PATH.exists():
            return default
        data = json.loads(_SETTINGS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return default

    if not isinstance(data, dict):
        return default

    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        env = data.get("env")
        if isinstance(env, dict):
            value = env.get(key)

    if isinstance(value, str) and value.strip():
        return value
    return default


def get_worker_port() -> int:
    """Return the Console worker port (default 41777)."""
    raw = _read_setting("CLAUDE_PILOT_WORKER_PORT", str(DEFAULT_PORT))
    try:
        port = int(raw)
    except ValueError:
        return DEFAULT_PORT
    if not 1 <= port <= 65535:
        return DEFAULT_PORT
    return port


def get_console_display() -> str:
    """Return the user-facing form ``localhost:<port>``."""
    return f"localhost:{get_worker_port()}"
