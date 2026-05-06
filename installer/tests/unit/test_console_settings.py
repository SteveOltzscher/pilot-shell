"""Tests for the vendored ``installer.console_settings`` helper.

Mirrors ``launcher/tests/unit/test_console_settings.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from installer import console_settings


@pytest.fixture
def settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(console_settings, "_SETTINGS_PATH", path)
    return path


class TestGetWorkerPort:
    def test_default_when_missing(self, settings_file: Path) -> None:
        assert not settings_file.exists()
        assert console_settings.get_worker_port() == 41777

    def test_default_when_corrupt(self, settings_file: Path) -> None:
        settings_file.write_text("not-json")
        assert console_settings.get_worker_port() == 41777

    def test_reads_configured_port(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "9999"}))
        assert console_settings.get_worker_port() == 9999

    def test_falls_back_on_out_of_range(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "70000"}))
        assert console_settings.get_worker_port() == 41777


class TestGetConsoleDisplay:
    def test_default(self, settings_file: Path) -> None:
        assert not settings_file.exists()
        assert console_settings.get_console_display() == "localhost:41777"

    def test_with_custom_port(self, settings_file: Path) -> None:
        settings_file.write_text(json.dumps({"CLAUDE_PILOT_WORKER_PORT": "5050"}))
        assert console_settings.get_console_display() == "localhost:5050"
