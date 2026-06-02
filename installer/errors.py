"""Custom exception hierarchy for installer."""

from __future__ import annotations


class InstallError(Exception):
    """Base exception for recoverable installation errors."""

    pass


class FatalInstallError(InstallError):
    """Fatal error that requires abort and rollback."""

    pass


class InstallationCancelled(InstallError):
    """Installation was cancelled by user (CTRL+C)."""

    def __init__(self, step_name: str) -> None:
        self.step_name = step_name
        super().__init__(f"Installation cancelled during {step_name}")

    def __str__(self) -> str:
        return f"Installation cancelled during {self.step_name}"
