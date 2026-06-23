"""Tests for the impeccable design-detector install function in the dependencies step."""

from __future__ import annotations

from unittest.mock import patch


class TestInstallImpeccable:
    """Test install_impeccable function (best-effort, manifest-pinned npm global)."""

    @patch("installer.steps.dependencies.npm_global_cmd", side_effect=lambda x: x)
    @patch("installer.steps.dependencies._run_bash_with_retry")
    @patch("installer.steps.dependencies.command_exists")
    def test_returns_true_on_successful_install(self, mock_cmd, mock_run, _mock_npm):
        """Returns True and issues a manifest-pinned npm install for impeccable."""
        from installer.steps.dependencies import install_impeccable

        mock_cmd.return_value = False  # not present -> fresh install
        mock_run.return_value = True
        assert install_impeccable() is True
        # the install command targets the impeccable package, pinned (contains '@')
        issued = " ".join(str(c.args) for c in mock_run.call_args_list)
        assert "impeccable@" in issued

    @patch("installer.steps.dependencies.npm_global_cmd", side_effect=lambda x: x)
    @patch("installer.steps.dependencies._run_bash_with_retry")
    @patch("installer.steps.dependencies.command_exists")
    def test_returns_false_when_install_fails(self, mock_cmd, mock_run, _mock_npm):
        """Returns False (best-effort, non-aborting) when the npm install fails."""
        from installer.steps.dependencies import install_impeccable

        mock_cmd.return_value = False
        mock_run.return_value = False
        assert install_impeccable() is False
