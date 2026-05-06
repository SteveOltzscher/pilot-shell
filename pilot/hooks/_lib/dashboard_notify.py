"""Send notifications to the Console dashboard via HTTP API.

Fire-and-forget — silently ignores all errors.
"""

from __future__ import annotations

import json
import urllib.request

from _lib.console_settings import get_console_url


def send_dashboard_notification(
    type: str,
    title: str,
    message: str,
    plan_path: str | None = None,
) -> bool:
    """POST a notification to the Console API. Returns True on success."""
    url = f"{get_console_url()}/api/notifications"
    payload: dict[str, str] = {"type": type, "title": title, "message": message}
    if plan_path:
        payload["planPath"] = plan_path

    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=3)
        return resp.status == 201
    except Exception:
        return False
