"""Tests for InstallContext and error hierarchy."""

from __future__ import annotations

from pathlib import Path


class TestInstallContext:
    """Test InstallContext dataclass."""

    def test_context_requires_project_dir(self):
        """InstallContext requires project_dir."""
        from installer.context import InstallContext

        ctx = InstallContext(project_dir=Path("/tmp/test"))
        assert ctx.project_dir == Path("/tmp/test")

    def test_context_has_default_values(self):
        """InstallContext has sensible defaults."""
        from installer.context import InstallContext

        ctx = InstallContext(project_dir=Path("/tmp/test"))
        assert ctx.non_interactive is False
        assert ctx.local_mode is False
        assert ctx.local_repo_dir is None
        assert ctx.completed_steps == []
        assert ctx.config == {}
        assert ctx.target_version is None

    def test_context_accepts_target_version(self):
        """InstallContext accepts target_version for dev installs."""
        from installer.context import InstallContext

        ctx = InstallContext(
            project_dir=Path("/tmp/test"),
            target_version="dev-abc1234-20260124",
        )
        assert ctx.target_version == "dev-abc1234-20260124"

    def test_mark_completed_adds_step(self):
        """mark_completed adds step to completed_steps."""
        from installer.context import InstallContext

        ctx = InstallContext(project_dir=Path("/tmp/test"))
        ctx.mark_completed("bootstrap")
        assert "bootstrap" in ctx.completed_steps

    def test_mark_completed_is_idempotent(self):
        """mark_completed doesn't add duplicates."""
        from installer.context import InstallContext

        ctx = InstallContext(project_dir=Path("/tmp/test"))
        ctx.mark_completed("bootstrap")
        ctx.mark_completed("bootstrap")
        assert ctx.completed_steps.count("bootstrap") == 1


class TestErrorHierarchy:
    """Test custom exception hierarchy."""

    def test_install_error_is_exception(self):
        """InstallError is a base exception."""
        from installer.errors import InstallError

        assert issubclass(InstallError, Exception)

    def test_fatal_install_error_is_install_error(self):
        """FatalInstallError inherits from InstallError."""
        from installer.errors import FatalInstallError, InstallError

        assert issubclass(FatalInstallError, InstallError)

    def test_errors_have_message(self):
        """All errors can have a message."""
        from installer.errors import FatalInstallError, InstallError

        for exc_class in [InstallError, FatalInstallError]:
            exc = exc_class("test message")
            assert str(exc) == "test message"
