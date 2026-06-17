"""Dotnet file checker — single-file dotnet format check (no per-edit build)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from _lib.util import BLUE, NC, check_file_length

from _checkers.tdd import is_inside_dotnet_test_project, should_skip

DOTNET_EXTENSIONS = {".cs", ".razor"}
DEBUG = os.environ.get("HOOK_DEBUG", "").lower() == "true"

# `dotnet format --verify-no-changes` returns this (CheckFailedExitCode) when a
# file needs formatting; 1 (UnhandledException) and 3 (MSBuild-not-found) mean
# the tool itself failed. See dotnet/sdk FormatCommandCommon.cs.
_FORMAT_CHANGES_NEEDED = 2


def debug_log(message: str) -> None:
    """Print debug message if enabled."""
    if DEBUG:
        print(f"{BLUE}[DEBUG]{NC} {message}", file=sys.stderr)


def find_project_root(file_path: Path) -> Path | None:
    """Find nearest directory with a .csproj or .sln file."""
    current = file_path.parent
    depth = 0
    while current != current.parent:
        if list(current.glob("*.csproj")) or list(current.glob("*.sln")):
            return current
        current = current.parent
        depth += 1
        if depth > 20:
            break
    return None


def check_dotnet(file_path: Path) -> tuple[int, str]:
    """Check .NET file with a single-file `dotnet format`. Returns (0, reason)."""
    # Skip build output / generated / vendored dirs (bin, obj, generated, …) —
    # shares the TDD checker's skip list so the format and TDD paths agree.
    if should_skip(str(file_path)):
        return 0, ""

    stem = file_path.stem
    if stem.endswith("Tests") or stem.endswith("Test"):
        return 0, ""
    # Skip files inside a .NET test project (MyApp.Tests, IntegrationTests, …).
    # Uses is_inside_dotnet_test_project rather than a bare name-only predicate
    # so that production directories coincidentally ending with 'Test'
    # (e.g. ContextTest, LoadTest) are not mistakenly skipped.
    if is_inside_dotnet_test_project(file_path):
        return 0, ""

    length_warning = check_file_length(file_path)

    # `dotnet format whitespace` (folder mode) only loads C# documents — a
    # `.razor` --include matches nothing, so skip the subprocess entirely and
    # keep just the length check for components.
    if file_path.suffix != ".cs":
        return 0, length_warning

    project_root = find_project_root(file_path)
    if not project_root:
        return 0, length_warning

    dotnet_bin = shutil.which("dotnet")
    if not dotnet_bin:
        return 0, length_warning

    # The check is scoped to this one file via --include, so a positive result
    # always means exactly this file needs whitespace formatting. There is no need
    # to parse or count tool output (which is empty at --verbosity q anyway, and
    # whose non-path warning lines would otherwise be miscounted as issues).
    if _run_dotnet_format(dotnet_bin, project_root, file_path):
        reason = f"Dotnet: {file_path.name} has whitespace issues (run `dotnet format`)"
        if length_warning:
            reason = f"{reason}\n{length_warning}"
        return 0, reason

    return 0, length_warning


def _run_dotnet_format(
    dotnet_bin: str,
    project_root: Path,
    file_path: Path,
) -> bool:
    """Run `dotnet format whitespace --folder` scoped to the edited file.

    Returns True iff the file needs whitespace formatting (exit code 2). Tool
    failures (exit 1/3/4) and timeouts are swallowed and reported as False, so a
    misconfigured environment never mislabels its error text as a whitespace issue.
    """
    try:
        # `whitespace --folder` skips the MSBuild project load, restore, and analyzer
        # compilation (the dominant per-edit cost) while still applying .editorconfig
        # whitespace rules. Style/analyzer feedback is deferred to the LSP and
        # `dotnet build` / `dotnet test`.
        cmd = [
            dotnet_bin,
            "format",
            "whitespace",
            str(project_root),
            "--folder",
            "--verify-no-changes",
            "--verbosity",
            "q",
        ]

        try:
            include_path = file_path.relative_to(project_root)
        except ValueError:
            include_path = file_path
        cmd.extend(["--include", str(include_path)])

        debug_log(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=project_root,
            timeout=60,
        )
        debug_log(f"Format exit code: {result.returncode}")

        # Exit 2 = file needs formatting. Any other non-zero code is a real tool
        # failure (1 = unhandled exception, 3 = MSBuild not found, 4 = .NET CLI not
        # found); swallow it like a timeout instead of mislabeling it as an issue.
        if result.returncode == _FORMAT_CHANGES_NEEDED:
            return True
        if result.returncode != 0:
            debug_log(f"dotnet format failed (exit {result.returncode}); not reporting as issues")
    except subprocess.TimeoutExpired:
        debug_log("Format check timed out")
    except (OSError, subprocess.SubprocessError) as exc:
        debug_log(f"Format check failed to run: {exc}")
    return False
