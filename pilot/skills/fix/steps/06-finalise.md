## Step 6: Finalise

### 6.1 Automated changes review (when enabled)

⛔ **Before running any reviewer, you MUST have completed Step 4 (Verify End-to-End) with concrete evidence.** Reviewers audit the fix; they are not a substitute for running the program.

The same two Console Settings toggles that drive `/spec`'s post-implementation review also govern `/fix`. Run whichever are enabled, and **auto-fix findings before** the worktree commit (6.2) and the approval gate (6.3) — so any review-driven change lands in the single bundled commit.

```bash
echo "CHANGES_REVIEW=$PILOT_CHANGES_REVIEW_ENABLED"          # changes review (CC: built-in /code-review skill; Codex: native agent)
echo "CODEX_REVIEW=$PILOT_CODEX_CHANGES_REVIEW_ENABLED"      # Codex companion review
```

**If BOTH are `"false"` or unset → skip this sub-step entirely and proceed to 6.2.**

#### 6.1.pre Stage the bugfix files (always run when any reviewer is enabled, before launching it)

The fix and its new test sit UNSTAGED in the working tree — and a brand-new test file is untracked. A pre-commit review of that unstaged tree misfires both ways: a reviewer that reads `git status --untracked-files=all` flags the new test as a spurious `critical` ("untracked deliverable"), while a reviewer that reads only `git diff HEAD` silently OMITS it, so the test goes unreviewed. Stage the change's own files with a **real `git add`** (NOT `git add -N`) before launching any reviewer below:

```bash
git add <fix_file> <test_file>   # only the bugfix's own files — never unrelated dirty paths
git status --short --untracked-files=all | grep '^??' || true   # should list only files NOT part of this fix
```

Staging is not committing — the commit (6.2) still waits for the review and the approval gate. All reviewers scope to `git diff HEAD` (which now includes the staged additions); never narrow to a committed ref-range, which is empty pre-commit.

<!-- CC-ONLY -->
#### 6.1.0 Shared bugfix summary (Codex companion only)

For `/fix` the "plan" is the conversation, not a file. When the Codex companion is enabled, inline a one-page summary into a temp file so the Codex reviewer has a concrete artifact to anchor on (skip this sub-step when only the inline `/code-review` runs — it reviews the diff directly and needs no plan artifact):

```bash
SESS_ID="${PILOT_SESSION_ID:-default}"
FIX_PLAN_FILE="/tmp/fix-review-plan-$SESS_ID-$$.md"
cat > "$FIX_PLAN_FILE" <<'PLAN_EOF'
# /fix Bugfix Summary
Bug: <one-line bug>
Root cause: <file>:<line> — <what>
Fix: <one-line fix description>
Reproducing test: <test file>::<test name> (added in Step 2 RED)
PLAN_EOF
CHANGED_FILES=$(git status --short --untracked-files=all | awk '{print "- " $2}')
```

#### 6.1.a Codex companion changes review (only when `PILOT_CODEX_CHANGES_REVIEW_ENABLED == "true"`) — launch FIRST

Independent second opinion via the Codex plugin companion. **Codex-once rule:** Codex runs at most once per `/fix` invocation. Before launching, check the sentinel; if it exists (a prior approval-gate loop already ran it), skip the launch and the Codex part of 6.1.c.

```bash
SESS_DIR="$HOME/.pilot/sessions/${PILOT_SESSION_ID:-default}"
mkdir -p "$SESS_DIR"
CODEX_FLAG="$SESS_DIR/codex-changes-review-ran-fix.flag"
[ -f "$CODEX_FLAG" ] && echo "Codex already reviewed this fix in this session — skipping (codex-once)."
```

1. **Locate the companion.** If missing, tell the user "Codex companion not found — install the openai-codex plugin or disable Codex Companion Changes Review in Console Settings" and continue with the inline `/code-review` (6.1.b) results when Changes Review is enabled — otherwise proceed without automated review and say so in the 6.6 report.

   ```bash
   CODEX_COMPANION=$(ls ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs 2>/dev/null | sort -V | tail -1)
   PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$(pwd)}"
   [ -z "$CODEX_COMPANION" ] && echo "MISSING"
   ```

2. **Build the review prompt file** by rendering the **template at `$HOME/.claude/agents/changes-review-codex.md`** (the same template `spec-verify` uses — single source of truth for code-review semantics). Reuse `$FIX_PLAN_FILE` from 6.1.0 as `{{PLAN_PATH}}` so the template's substitution points at a real artifact:

   ```bash
   PROMPT_TEMPLATE="$HOME/.claude/agents/changes-review-codex.md"
   PROMPT_FILE="/tmp/codex-fix-review-$SESS_ID-$$.md"

   PLAN_GOAL="Bugfix for: <one-line bug>. Root cause at <file>:<line>. The reproducing test must reliably fail before the fix and pass after."
   BASE_REF="$(git rev-parse --abbrev-ref HEAD@{upstream} 2>/dev/null | sed 's|^[^/]*/||' || echo main)"

   PLAN_PATH="$FIX_PLAN_FILE" PLAN_GOAL="$PLAN_GOAL" BASE_REF="$BASE_REF" CHANGED_FILES="$CHANGED_FILES" \
   PROMPT_TEMPLATE="$PROMPT_TEMPLATE" PROMPT_FILE="$PROMPT_FILE" \
   uv run --no-project --python python3 python -c '
   import os, pathlib
   text = pathlib.Path(os.environ["PROMPT_TEMPLATE"]).read_text()
   for key in ("PLAN_PATH", "PLAN_GOAL", "BASE_REF", "CHANGED_FILES"):
       text = text.replace("{{" + key + "}}", os.environ[key])
   pathlib.Path(os.environ["PROMPT_FILE"]).write_text(text)
   '
   ```

3. **Launch the task in background.** Use `task --background --prompt-file` (the companion's own background mode is supported for `task` — unlike `review`/`adversarial-review`).

   ⛔ **Launch the companion via Bash from the MAIN conversation — NEVER through a subagent** (`codex:codex-rescue` included): a subagent-launched job's ID is unreachable afterwards (no findings file, no `TaskOutput`, no `SendMessage`).

   ```
   Bash(
     command="cd $PROJECT_ROOT && node $CODEX_COMPANION task --background --prompt-file \"$PROMPT_FILE\"",
     run_in_background=false,
     timeout=60000
   )
   ```

   Capture the job ID from stdout (`task-…` token). **Verify registration before polling** — fail-fast guard against synthetic-ID launches:

   ```bash
   node "$CODEX_COMPANION" status "$JOB_ID" --json 2>/dev/null | grep -q '"status":' \
     || { echo "Codex launch did not register with broker (synthetic task id?). Skipping Codex this run."; JOB_ID=""; }
   ```

   If `$JOB_ID` is empty, skip the Codex part of 6.1.c. Otherwise run the **active stall monitor** — broker `status` alone is not a liveness signal (a silent job keeps reporting `running`/`verifying` and a status-only loop burns its whole timeout). It watches `job.logFile` mtime and returns the moment the job finishes OR stalls:

   ```bash
   STALL=90; CEILING=480   # seconds: max no-log-growth, then absolute ceiling
   LOGF=$(node "$CODEX_COMPANION" status "$JOB_ID" --json 2>/dev/null \
     | uv run --no-project --python python3 python -c "import json,sys
try: print((json.load(sys.stdin).get('job') or {}).get('logFile') or '')
except Exception: print('')")
   last_change=$(date +%s); last_mtime=0; start=$(date +%s)
   while :; do
     PSTATE=$(node "$CODEX_COMPANION" status "$JOB_ID" --json 2>/dev/null \
       | uv run --no-project --python python3 python -c "import json,sys
try: print((json.load(sys.stdin).get('job') or {}).get('status') or 'unknown')
except Exception: print('parse_error')")
     case "$PSTATE" in
       completed)                            echo "READY elapsed=$(($(date +%s)-start))s"; break ;;
       failed|cancelled|parse_error|unknown) echo "FAIL state=$PSTATE"; break ;;
     esac
     now=$(date +%s)
     m=$( { [ -n "$LOGF" ] && stat -f %m "$LOGF" 2>/dev/null; } || { [ -n "$LOGF" ] && stat -c %Y "$LOGF" 2>/dev/null; } || echo 0 )
     [ "$m" -gt "$last_mtime" ] && { last_mtime=$m; last_change=$now; }
     [ $((now - last_change)) -ge "$STALL" ]   && { echo "STALLED no_log_growth=$((now-last_change))s"; break; }
     [ $((now - start))       -ge "$CEILING" ] && { echo "CEILING elapsed=$((now-start))s"; break; }
     sleep 15
   done
   ```

   Run the monitor as `Bash(run_in_background=true, timeout=600000)` (background so `sleep` is allowed; the CEILING exits before the bash timeout). Use `PSTATE`, never a variable named `status` (read-only in zsh). If `LOGF` came back empty, the monitor degrades to status + CEILING only. ⛔ **Wait for the completion notification** — do NOT read the result file before the `<task-notification>` arrives. The inline review (6.1.b) runs while Codex churns.

   **Outcome handling.** `READY` → fetch the result in 6.1.c. `FAIL` → treat as a failed run (6.1.d launch-failure handling). `STALLED`/`CEILING` → the job went silent: cancel it (`node "$CODEX_COMPANION" cancel "$JOB_ID" --json 2>/dev/null || true`) and re-launch ONCE under the same monitor; if it stalls again, do NOT spin a third time and do NOT silently skip — proceed without the Codex pass, note the gap in the 6.6 report, and rely on the inline `/code-review` results.

#### 6.1.b Inline /code-review (only when `PILOT_CHANGES_REVIEW_ENABLED == "true"`)

Run AFTER launching Codex (6.1.a) so the companion works in parallel. Resolve the configured effort first, fail-closed to `xhigh` for an unset/invalid value (never pass the raw env var straight through):

```bash
EFFORT="${PILOT_CODE_REVIEW_EFFORT:-xhigh}"
case "$EFFORT" in low|medium|high|xhigh|max) ;; *) EFFORT=xhigh ;; esac
echo "$EFFORT"
```

Then invoke the built-in code review skill at that effort (substitute the resolved `<EFFORT>`):

```
Skill(skill='code-review', args='<EFFORT>')
```

- Execute the loaded review protocol fully. Do NOT pass `--fix` — findings are applied by this orchestrator (6.1.c), not by the review.
- The default scope (uncommitted working-tree changes + commits ahead of upstream) covers the `/fix` diff in a clean tree. **If the tree carries unrelated dirty files, pass the bugfix lineage AS THE TARGET in the Skill args** — `Skill(skill='code-review', args='<EFFORT> <fix file> <test file>')` — covering BOTH the fix AND the Step 2 reproducing test (never review the fix without its test, or weak test assertions go unaudited); prose-level scoping outside the args does not bind the review. A ref-range target only covers committed work and misses the uncommitted fix.
- `/code-review` does not know the bug — root-cause-vs-symptom judgment stays with this orchestrator (Step 1.3 trace + 6.5 checklist), and the Codex companion (6.1.a, when enabled) is the reviewer that receives the bug summary.
- Output: a ranked JSON array of findings `{file, line, summary, failure_scenario}` — most severe first, no severity labels.

#### 6.1.c Apply findings + collect Codex

**Inline /code-review findings (if run in 6.1.b):** classify each finding and act. **Lineage is evaluated FIRST:** a finding on a file outside the bug's lineage (the fix file, its test, and files the fix legitimately touched) is mention-only regardless of severity — out-of-lineage crashes are reported to the user, never auto-fixed. Only in-lineage findings are classified by the remaining rows:

| Finding class | Action |
|---------------|--------|
| Finding on a file outside the bug's lineage (CHECK FIRST — overrides all rows below) | Mention in one line; do not auto-apply |
| `failure_scenario` names a concrete crash, wrong output, security, or data-integrity problem | **must_fix** — fix immediately, then re-run the targeted test from Step 3.4 + the full suite from Step 5.2 |
| Cleanup / efficiency finding, single-site and within the bug's lineage | **should_fix** — fix |
| Finding that would expand scope (3+ files, architectural) | Summarise to the user; let them decide whether to fix here or open a `/spec` follow-up |

**Codex reviewer (if launched in 6.1.a):** on the completion notification, fetch via the public interface:

```bash
node "$CODEX_COMPANION" result "$JOB_ID" --json > /tmp/codex-fix-result-$$.json
```

Read `/tmp/codex-fix-result-$$.json`. Verify `storedJob.status === "completed"`, then parse `storedJob.result.rawOutput` as JSON (`{verdict, summary, findings, next_steps}`). If JSON parse fails, fall back to `storedJob.rendered` and surface as a suggestion-level finding.

**Act on Codex findings — same action map as the inline table above, keyed by Codex severity:** `critical`/`high` → must_fix; `medium`/`low` → should_fix (single-site, in-lineage) or summarise; `info` → mention only.

If a reviewer returns no blocking findings (Codex verdict `approve`, `/code-review` empty findings array): report "Review: no blocking findings" in one line and proceed.

#### 6.1.d Mark + cleanup

```bash
[ -n "$JOB_ID" ] && touch "$CODEX_FLAG"   # codex-once
rm -f "$PROMPT_FILE" "$FIX_PLAN_FILE" /tmp/codex-fix-result-$$.json
```

**Launch failure handling.** If the Codex job ended `failed` (genuine launch failure, not timeout): surface the captured stderr to the user, do **not** silently mark the bugfix done. Continue with the inline `/code-review` results.
<!-- /CC-ONLY -->
<!-- CODEX-START
When `PILOT_CHANGES_REVIEW_ENABLED == "true"`, run the managed Codex `changes-review` custom agent on the bugfix diff before finalising. (The Codex *companion* review — `PILOT_CODEX_CHANGES_REVIEW_ENABLED` — is a Claude-Code-only plugin path and does not run here.)

1. Build a one-page bugfix summary in a temp file as the review anchor:

```bash
FIX_PLAN_FILE="/tmp/fix-review-plan-${PILOT_SESSION_ID:-default}-$$.md"
cat > "$FIX_PLAN_FILE" <<'PLAN_EOF'
# /fix Bugfix Summary
Bug: <one-line bug>
Root cause: <file>:<line> — <what>
Fix: <one-line fix description>
Reproducing test: <test file>::<test name>
PLAN_EOF
```

2. Spawn the review agent and wait for its final JSON response:

```python
review = multi_agent_v1.spawn_agent(
    agent_type="changes-review",
    message="""
    Plan file: <FIX_PLAN_FILE path>
    User request: Bugfix — <one-line bug>
    Changed files: [git status --short list]

    Review the bugfix diff: quality and goal achievement. The "plan" is a one-page bugfix
    summary, not a multi-task spec — judge compliance against the bug, not absent feature tasks.
    Return ONLY valid JSON matching the changes-review schema. Include the plan file path in `plan_file`.
    """,
)
result = multi_agent_v1.wait_agent(targets=[review.agent_id], timeout_ms=600000)
```

3. Parse the agent's final message as JSON. If parsing fails, treat the raw final message as one `suggestion` finding and continue. Validate `plan_file` matches `$FIX_PLAN_FILE`; if not, discard the stale result and self-review instead.

4. Severity → action map: `must_fix` → fix now; `should_fix` → fix if single-site and within the bug's lineage (else summarise and let the user decide); `suggestion` → mention. After any fix, re-run the targeted test + full suite. Then `rm -f "$FIX_PLAN_FILE"`.
CODEX-END -->

### 6.2 Worktree mode — single commit

If a worktree was created: bundle test + fix (and any review-driven fixes from 6.1) into one commit.

```bash
git add <test_file> <fix_file>
git commit -m "fix: <one-line description>"
```

The conventional `fix:` prefix triggers a patch release if/when this branch ships. Do not split into multiple commits in the quick lane.

### 6.3 Approval gate (only when enabled)

⛔ **Before showing the approval question, you MUST have completed Step 4 (Verify End-to-End) with evidence.** "Tests pass" is not enough — the approval summary must include what you actually ran and what you observed. If you cannot fill in `**E2E:**` below with concrete evidence, you have not finished Step 4 — go back, do not ask for approval.

Read `PILOT_PLAN_APPROVAL_ENABLED`. If `"false"` → skip 6.3 entirely, mark done.

When approval is enabled, summarise + ask:

1. `"Approve — done"`
2. `"Request changes"`
3. `"Explain the fix in more detail"` — always present.

```
AskUserQuestion(
  question="Bugfix complete.\n\nBug: <one line>\nRoot cause: <file>:<line> — <what>\nFix: <one-line description of the change>\nTests: reproducing test added (<test_name>), full suite green.\nReview: <none | /code-review (configured effort) or native changes-review: N findings, all resolved | Codex: approve | ...>\nE2E: <command/URL you ran and the concrete observation that proves the fix — e.g. 'curl /search -d {} → 200 with [results]', 'opened /tasks page, saved end_date=2026-05-15, list shows 2026-05-15', 'ran pilot register-plan ./foo.md PENDING → exit 0, plan visible in console'>\n\nReview the diff in the Console's Changes tab. Approve when ready.",
  options=[<see list above>]
)
```

Handle:

- **Approve** → done.
- **Request changes** → user describes problem in free-form. Treat as a new investigation: re-run Step 1.3 (re-trace) → Step 2 onward (6.1 reviews re-run on the new fix; the codex-once flag keeps Codex to a single run per invocation, and the inline `/code-review` re-run is scoped to the files changed since the previous review by passing them as the target — `Skill(skill='code-review', args='<EFFORT> <changed files>')` (same resolved `<EFFORT>` as 6.1.b) — not the whole diff again).
- **Explain the fix in more detail** → write a fuller walkthrough (causal chain from trigger → root cause; why the boundary you fixed at is correct; line-by-line meaning of the diff; alternatives considered and rejected). Do NOT modify code. Then re-ask 6.3 — drop the "Explain" option from the new list to avoid loops.

### 6.4 Console notification (always, when binary present)

```bash
~/.pilot/bin/pilot notify plan_approval "Bugfix complete" "<one-line bug>" 2>/dev/null || true
```

Best-effort — don't block on failure.

### 6.5 Pre-report verification checklist

Walk every box before writing the report. **Missing any one = not done** — return to the relevant step.

- [ ] Reproducing test passes (Step 3.3 fresh run, this message).
- [ ] Full anti-regression suite green (Step 5.2 fresh run).
- [ ] E2E executed against the actual program with concrete evidence captured (Step 4).
- [ ] Enabled reviewers (6.1) ran; all `must_fix` / `should_fix` resolved or escalated.
- [ ] `git diff | grep -E "SPEC-DEBUG|^\\+.*\\b(console\\.log|print\\()"` returns nothing (no leftover instrumentation).
- [ ] Diff is small and every changed line traces to the bug (lineage rule).
- [ ] Worktree mode: single bundled `fix:` commit. Non-worktree: changes ready, no commit yet.

If any box is unchecked, do not write the report and do not ask for approval — fix the gap first.

### 6.6 Report

```
Bugfix complete — <bug>.
Root cause: <file>:<line>.
Tests: 1 new reproducing test, full suite green.
Review: <none enabled | /code-review (configured effort) / native changes-review + Codex, no blocking findings | N findings resolved>.
E2E: <command/URL run> → <observation that proves the symptom is gone>.

Run /clear before starting new work — this resets context while keeping project rules loaded.
```

The `E2E:` line is **mandatory** — it documents that the actual program was exercised, not just the unit tests.

### 6.7 Post-mortem flag (optional, one line)

Ask once, now that you have more information than when you started: **what would have prevented this bug?** If the answer is architectural — no clean test seam, hidden coupling between modules, validation absent at the boundary the bad data crossed, repeated near-miss in the same area — name it as a `/spec` follow-up candidate in one line:

```
Follow-up (architectural): <one-line description> — candidate for /spec.
```

Skip when the answer is "nothing structural, it was a one-line typo / off-by-one / wrong default." Don't manufacture follow-ups.

ARGUMENTS: $ARGUMENTS
