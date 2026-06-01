"""Property-based tests for the pure invariant-bearing helpers in ``_lib/util.py``.

Two surfaces, both previously example-only (``plan_in_current_project`` had no
coverage at all — it is the cross-session-bleed guard):

- ``plan_in_current_project`` containment — the enforcing ``False`` direction
  is the load-bearing one (spec-review #6): without a generated out-of-root
  case, a trivially-broken ``return True`` would pass.
- ``_extract_section_bullets`` round-trips + exact-heading matching (Codex #3).

The example tests in ``test_util_plan_parsing.py`` cover specific shapes; these
cover the laws across the input space.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import _lib.util as util
from _lib.util import _extract_section_bullets, plan_in_current_project
from hypothesis import given, settings
from hypothesis import strategies as st

# Absolute, clearly-nonexistent base — realpath is applied to both root and plan
# inside the function, so any /tmp→/private/tmp resolution stays consistent.
_BASE = "/pilot_test_root/project"

_seg = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=8)

# Single-line, strip-stable, non-empty text for headings and bullet bodies.
_clean = (
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 ", min_size=1, max_size=20)
    .map(str.strip)
    .filter(lambda s: bool(s) and not re.match(r"^\d+\.", s))
)


# --- plan_in_current_project containment -----------------------------------


@given(subsegs=st.lists(_seg, min_size=1, max_size=4))
@settings(max_examples=150)
def test_plan_inside_root_is_true(subsegs):
    """A plan path nested anywhere under the project root is contained."""
    root = Path(_BASE)
    plan = root.joinpath(*subsegs)
    with patch.object(util, "current_project_root", return_value=root):
        assert plan_in_current_project(plan) is True


@given(insegs=st.lists(_seg, min_size=1, max_size=3), outseg=_seg)
@settings(max_examples=150)
def test_plan_outside_root_is_false(insegs, outseg):
    """A sibling path outside the root is NOT contained — the enforcing direction."""
    root = Path(_BASE)
    outside = root.parent / f"not_{outseg}" / Path(*insegs)
    with patch.object(util, "current_project_root", return_value=root):
        assert plan_in_current_project(outside) is False


@given(subsegs=st.lists(_seg, min_size=1, max_size=3))
@settings(max_examples=100)
def test_unresolvable_root_fails_open_true(subsegs):
    """When the project root can't be determined, fail open (True = legacy behaviour)."""
    with patch.object(util, "current_project_root", return_value=None):
        assert plan_in_current_project(Path(_BASE, *subsegs)) is True


# --- _extract_section_bullets parsing --------------------------------------


@given(h2=_clean, bullets=st.lists(_clean, max_size=6))
@settings(max_examples=150)
def test_section_bullets_roundtrip(h2, bullets):
    """Bullets written under an `## H2` section are extracted verbatim, in order."""
    doc = f"## {h2}\n" + "\n".join(f"- {b}" for b in bullets) + "\n"
    assert _extract_section_bullets(doc, h2) == bullets


@given(base=_clean, suffix=_clean)
@settings(max_examples=150)
def test_section_heading_match_is_exact_not_substring(base, suffix):
    """`## <base> <suffix>` must NOT match a query for `## <base>` (Codex #3 exact-match)."""
    other = f"{base} {suffix}"
    doc = f"## {other}\n- present\n"
    assert _extract_section_bullets(doc, base) == []
