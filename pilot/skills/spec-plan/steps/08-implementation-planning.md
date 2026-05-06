## Step 8: Implementation Planning

### 8.0: File Structure (when 4+ tasks expected, otherwise inline per task)

When the plan will have 4+ tasks, write a `## File Structure` section before tasks listing every file with one-line responsibility — decomposition decisions get locked in here. For 1–3 task plans skip this; the per-task `Files:` block already gives the same view.

```markdown
## File Structure

- `src/foo/bar.ts` (create) — pure function: `parseFoo(input) → Foo`. No I/O.
- `src/foo/loader.ts` (create) — fetches and caches Foo from API. Wraps `parseFoo`.
- `tests/foo/bar.test.ts` (create) — unit tests for `parseFoo`.
```

One responsibility per file. Files that change together live together. In existing codebases, follow established patterns — don't restructure unrelated code.

### 8.1: Task Granularity

**Task Granularity:** Each task: independently testable, focused (2-4 files max), verifiable. Split if multiple unrelated DoD criteria; merge if one can't be tested without the other. Don't create tasks for setup/boilerplate with no standalone value — fold into the first task that uses them.

**Task Structure:**

```markdown
### Task N: [Component Name]

**Objective:** [1-2 sentences]
**Dependencies:** [None | Task X, Task Y]
**Mapped Scenarios:** [None | TS-001, TS-002]

**Files:**

- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py`
- Test: `tests/exact/path/to/test.py`

**Trivial:** [Omit, OR a one-line justification: "≤ 5 net new lines, no new branch/loop/try with non-trivial body, no new public symbol, no new error path; covered by `<existing-test-or-verify-command>`"]

**Key Decisions / Notes:**

- [Technical approach, pattern to follow with file:line ref]

**Definition of Done:**

- [ ] Relevant existing/new tests pass (`Trivial:` only skips RED/new-test creation; it does not skip verification)
- [ ] No diagnostics errors
- [ ] [Verifiable criterion — e.g., "API returns 404 for nonexistent resources"]

**Verify:**

- `uv run pytest tests/path/to/test.py -q`
```

**DoD must be verifiable.** ✅ "GET /api/users?role=admin returns only admin users" ❌ "Feature works correctly"

#### Test plan parsimony

**Testing posture preference.** If there is no project-level testing rule/memory and this plan would introduce several test classes or force a choice between unit-only vs unit+functional coverage, ask one concise question about testing posture. Default to the parsimonious posture here if questions are disabled or the user does not specify a preference.

When listing files for a task, do not auto-create a new `tests/.../test_<file>.py` line for every modified production file. Apply these rules in order:

1. If an existing test class for this production class already exists, reuse it (modify, do not duplicate).
2. If the change is genuinely trivial (≤ 5 net new lines, no new branch/loop/try with non-trivial body, no new public symbol, no new error path), set the task's `Trivial:` field with the justification and the existing covering test/verification command — and omit the test file from `Files:`.
3. Otherwise, plan **at most 1 new unit test class + at most 1 new functional/integration test class** for this production class. More than that requires an explicit `Why >2 test classes:` note in `Key Decisions`.
4. Never plan a test file per method or per branch. The test class is the unit; methods inside it cover branches.

The reviewer agent (`pilot/agents/changes-review.md`) and `spec-verify` Step 5 audit these rules against the actual diff — they are not advisory.

**Performance considerations:** When a task processes data on a hot path (render loops, request handlers, polling callbacks), note it in Key Decisions. Flag: expensive computations that should be cached/memoized, heavy dependencies that have lighter alternatives, and repeated work that can be avoided when input hasn't changed.

**Zero-context assumption:** Assume implementer knows nothing. Provide exact file paths, explain domain concepts, reference similar patterns.

**Assumptions:** After creating tasks, write the `## Assumptions` section — one bullet per assumption: what you assume, which finding supports it, which task numbers depend on it. When implementation hits a surprise, this list tells the implementer which tasks are affected.

#### Step 8.2: Goal Verification Criteria

After creating tasks, derive for the `## Goal Verification` section:

1. State the goal
2. Derive 3-7 observable truths (falsifiable, user-perspective)
3. For each truth, identify supporting artifacts (files with real implementation, not stubs)
