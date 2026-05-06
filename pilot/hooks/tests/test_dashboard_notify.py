"""Tests for _dashboard_notify helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from _lib.dashboard_notify import send_dashboard_notification


class TestSendDashboardNotification:
    @patch("_lib.dashboard_notify.get_console_url", return_value="http://127.0.0.1:41777")
    @patch("_lib.dashboard_notify.urllib.request.urlopen")
    @patch("_lib.dashboard_notify.urllib.request.Request")
    def test_sends_notification_to_console_api(self, mock_request_cls, mock_urlopen, _mock_url):
        """Should POST notification to Console API."""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_urlopen.return_value = mock_response

        result = send_dashboard_notification("plan_approval", "Plan Review", "Needs approval")

        assert result is True
        mock_request_cls.assert_called_once()
        call_args = mock_request_cls.call_args
        assert "/api/notifications" in call_args[0][0]
        assert ":41777" in call_args[0][0]
        body = json.loads(call_args[1]["data"])
        assert body["type"] == "plan_approval"
        assert body["title"] == "Plan Review"
        assert body["message"] == "Needs approval"

    @patch("_lib.dashboard_notify.urllib.request.urlopen")
    @patch("_lib.dashboard_notify.urllib.request.Request")
    def test_includes_optional_plan_path(self, mock_request_cls, mock_urlopen):
        """Should include planPath when provided."""
        mock_urlopen.return_value = MagicMock(status=201)

        send_dashboard_notification("info", "Title", "Msg", plan_path="/plans/test.md")

        body = json.loads(mock_request_cls.call_args[1]["data"])
        assert body["planPath"] == "/plans/test.md"

    @patch("_lib.dashboard_notify.urllib.request.urlopen", side_effect=Exception("Connection refused"))
    def test_silently_ignores_connection_errors(self, mock_urlopen):
        """Should return False without raising on connection errors."""
        result = send_dashboard_notification("info", "Title", "Msg")
        assert result is False

    @patch("_lib.dashboard_notify.urllib.request.urlopen", side_effect=TimeoutError("timeout"))
    def test_silently_ignores_timeout(self, mock_urlopen):
        """Should return False without raising on timeout."""
        result = send_dashboard_notification("info", "Title", "Msg")
        assert result is False
