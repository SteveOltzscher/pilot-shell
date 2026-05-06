"""Tests for the vendored ``_lib.console_settings`` helper.

Mirrors ``launcher/tests/unit/test_console_settings.py``. Both files must
stay in sync with their respective modules.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from _lib import console_settings


@pytest.fixture
def settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Patch the module's settings path to a tmp file and return it."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(console_settings, "_SETTINGS_PATH", path)
    return path


class TestGetWorkerPort:
    def test_returns_default_when_settings_missing(self, settings_file: Path) -> None:
        assert not settings_file.exists()
        assert console_settings.get_worker_port() == 41777

    def test_returns_default_when_settings_corrupt(self, settings_file: Path) -> None:
        settings_file.write_text("not-json")
        assert console_settings.get_worker_port() == 41777

    def test_reads_configured_port(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "9999"}))
        assert console_settings.get_worker_port() == 9999

    def test_reads_legacy_nested_env(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"env": {"CLAUDE_PILOT_WORKER_PORT": "8080"}}))
        assert console_settings.get_worker_port() == 8080

    def test_falls_back_on_non_numeric(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "not-a-port"}))
        assert console_settings.get_worker_port() == 41777

    def test_falls_back_on_out_of_range(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "70000"}))
        assert console_settings.get_worker_port() == 41777


class TestGetConsoleUrl:
    def test_default_url(self, settings_file: Path) -> None:
        assert not settings_file.exists()
        assert console_settings.get_console_url() == "http://127.0.0.1:41777"

    def test_custom_port_url(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "9000"}))
        assert console_settings.get_console_url() == "http://127.0.0.1:9000"

    def test_ipv6_host_is_bracketed(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_HOST": "::1"}))
        assert console_settings.get_console_url() == "http://[::1]:41777"


class TestGetConsoleDisplay:
    def test_default(self, settings_file: Path) -> None:
        assert not settings_file.exists()
        assert console_settings.get_console_display() == "localhost:41777"

    def test_uses_localhost_with_custom_port(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "5050"}))
        assert console_settings.get_console_display() == "localhost:5050"
