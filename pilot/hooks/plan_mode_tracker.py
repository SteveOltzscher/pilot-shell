#!/usr/bin/env python3
"""Track EnterPlanMode/ExitPlanMode state via a session-scoped sentinel file.

Registered as:
  PostToolUse(EnterPlanMode) -> writes the sentinel
  PostToolUse(ExitPlanMode)  -> deletes the sentinel
  PreToolUse(Edit|Write|MultiEdit) -> injects a warning if the sentinel is active
                                      and the target file is not a plan doc

The sentinel lives at:
  ~/.pilot/sessions/<session_id>/plan-mode-active

Purpose: ensure spec-implement never runs on Opus because ExitPlanMode was
accidentally skipped. The warning gives the model one last chance to call
ExitPlanMode before touching implementation files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib.util import (
    _sessions_base,
    pre_tool_use_context,
    read_hook_stdin,
    resolve_session_id,
)

_WARNING = (
    "[Pilot] PLAN MODE STILL ACTIVE - ExitPlanMode has NOT been called yet. "
    "Call ExitPlanMode NOW before editing any implementation file, or the "
    "entire implementation leg will run on Opus instead of Sonnet. "
    "If you are inside spec-implement and MODEL_SWITCH=true, call ExitPlanMode "
    "immediately as step 1.0 requires."
)


def sentinel_path() -> Path:
    session_dir = _sessions_base() / resolve_session_id()
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / "plan-mode-active"


def is_plan_file(file_path: str) -> bool:
    """Return True for plan doc files (docs/plans/*.md) - legitimate writes during planning."""
    p = Path(file_path)
    return p.suffix.lower() == ".md" and "plans" in p.parts


def main() -> int:
    data = read_hook_stdin()
    tool_name = data.get("tool_name", "")
    is_post = "tool_response" in data

    if is_post:
        # PostToolUse: update sentinel state
        if tool_name == "EnterPlanMode":
            response = data.get("tool_response", {})
            if isinstance(response, dict) and response.get("is_error"):
                return 0
            sentinel_path().write_text("")
        elif tool_name == "ExitPlanMode":
            response = data.get("tool_response", {})
            if isinstance(response, dict) and response.get("is_error"):
                return 0
            sentinel_path().unlink(missing_ok=True)
    else:
        # PreToolUse: warn if editing a non-plan file while plan mode is active
        if not sentinel_path().exists():
            return 0
        file_path = data.get("tool_input", {}).get("file_path", "")
        if file_path and not is_plan_file(file_path):
            print(pre_tool_use_context(_WARNING))

    return 0


if __name__ == "__main__":
    sys.exit(main())
