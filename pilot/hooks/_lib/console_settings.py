"""Read Console worker port/host from Pilot settings.

Vendored copy of ``launcher/console_settings.py`` — the plugin hooks ship
without the launcher source on ``sys.path``, so we cannot import across the
package boundary (see ``.claude/rules/pilot-shell-package-boundaries.md``).

Keep this file in sync with ``launcher/console_settings.py`` if either is
edited. Both read the same ``~/.pilot/memory/settings.json`` file written
by the Console's ``SettingsDefaultsManager``.
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


def get_worker_host() -> str:
    """Return the Console worker host (default 127.0.0.1)."""
    return _read_setting("CLAUDE_PILOT_WORKER_HOST", DEFAULT_HOST)


def _format_host(host: str) -> str:
    """Wrap IPv6 in brackets for use in URLs."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


def get_console_url() -> str:
    """Return the Console base URL, e.g. ``http://127.0.0.1:41777``."""
    return f"http://{_format_host(get_worker_host())}:{get_worker_port()}"


def get_console_display() -> str:
    """Return the user-facing form ``localhost:<port>`` for tips/banners."""
    return f"localhost:{get_worker_port()}"
