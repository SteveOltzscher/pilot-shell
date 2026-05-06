## Step 11: Plan Verification

### 11.0: No-Placeholders Self-Check (always — before launching reviewers)

⛔ Walk the plan file once, fresh-eyed, and grep for the patterns below. **Every match is a plan failure** — fix inline before sending the plan to a reviewer or asking for approval.

**Forbidden placeholder patterns:**

- `TBD`, `TODO`, `FIXME`, "implement later", "fill in details", "details below"
- "add appropriate error handling", "add validation", "handle edge cases" — without specifying which cases
- "write tests for the above" — tasks must specify the actual test cases, not a meta-instruction
- "similar to Task N" — implementers may read tasks out of order; repeat the relevant content
- Steps that describe *what* to do without showing *how* (code blocks required for code steps)
- References to types, functions, methods, files, or env vars not defined in any task
- Bracketed angle-brackets like `<your-code-here>`, `<insert-X>` outside of header literal placeholders
- Goal Verification truths that are not falsifiable ("works correctly", "is fast enough")

```bash
# Quick grep (run in worktree or repo root):
grep -nEi "TBD|TODO|FIXME|implement later|fill in details|appropriate error handling|similar to Task" "<plan_path>"
```

If anything matches, fix it inline (no new round-trip needed). Then proceed to spec-review launch below.

---

**⛔ If `PILOT_SPEC_REVIEW_ENABLED` is `"false"` (from Step 0),** skip the rest of this step and proceed to Step 13.

**When enabled:** Run spec-review for every feature spec. Small plans benefit from a second pair of eyes just as much as large ones — missing edge cases and unclear DoD criteria are size-independent.

```bash
SESS_ID=$(echo $PILOT_SESSION_ID)
```

**Derive plan slug** from the plan filename: strip the date prefix (`YYYY-MM-DD-`) and `.md` extension. Example: `2026-03-02-sku-builder-modal-cleanup.md` → `sku-builder-modal-cleanup`.

Output path: `~/.pilot/sessions/<SESS_ID>/findings-spec-review-<plan-slug>.json`

**⛔ Delete stale findings before launching** (previous run of the same plan may have left a file):

```bash
rm -f "$OUTPUT_PATH"
```

```
Task(
  subagent_type="pilot:spec-review",
  run_in_background=true,
  prompt="""
  **Plan file:** <plan-path>
  **User request:** <original task description>
  **Clarifications:** <any Q&A>
  **Output path:** <absolute path to findings JSON>

  Review for alignment with requirements AND adversarial risks.
  Write findings JSON to output_path using Write tool.
  IMPORTANT: Include the plan file path in your output JSON as the "plan_file" field.
  """
)
```

**⛔ NEVER use `TaskOutput`** to retrieve results — it dumps the full agent transcript into context, wasting thousands of tokens.

#### Codex Adversarial Review (Optional — launch immediately after Claude reviewer)

**If `PILOT_CODEX_SPEC_REVIEW_ENABLED` is `"true"` (from Step 0):**

Launch Codex review NOW — it runs in parallel with the Claude reviewer above.

**⛔ Codex-once rule.** Codex runs at most once per `/spec` invocation. Before launching, check the sentinel file. If it exists, the review already ran in this session — skip the launch and the collection sub-step below. Plan iterations (annotation feedback, plan edits, fixing prior findings) do NOT trigger another Codex run.

```bash
SESS_ID="${PILOT_SESSION_ID:-default}"
CODEX_FLAG="$HOME/.pilot/sessions/$SESS_ID/codex-ran-<plan-slug>.flag"
if [ -f "$CODEX_FLAG" ]; then
  echo "Codex already reviewed this plan in this session — skipping (codex-once)."
  # Skip the launch and the Codex collection sub-step. Continue with Claude reviewer results only.
fi
```

1. Detect companion path, project root, and base branch:
```bash
CODEX_COMPANION=$(ls ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs 2>/dev/null | sort -V | tail -1)
PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$(pwd)}"
# Use worktree base branch if in worktree, otherwise detect repo default branch
BASE_BRANCH=$(~/.pilot/bin/pilot worktree status --json 2>/dev/null | grep -o '"base_branch":"[^"]*"' | cut -d'"' -f4)
[ -z "$BASE_BRANCH" ] && BASE_BRANCH=$(cd "$PROJECT_ROOT" && git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo "main")
```

2. Launch adversarial review in background. **⛔ Use `Bash(run_in_background=true, timeout=600000)`** — the companion's `--background` flag is a no-op for reviews (only works for `task`), so we use Claude Code's background bash instead. **The `timeout=600000` (10 min, the Bash tool maximum) is MANDATORY** — Bash defaults to 120000 ms (2 min), which SIGKILLs the codex process mid-investigation and produces zero findings. Adversarial reviews on plans typically take 1–6 minutes; the 10-minute ceiling is the safety margin. The companion writes a persistent job record at `$CLAUDE_PLUGIN_DATA/state/<slug>-<hash>/jobs/review-<id>.json` (`status`, `rendered`, `result.parsed`) — that file, not the bash stdout, is the authoritative findings source after completion.

   ```
   Bash(
     command="cd $PROJECT_ROOT && node $CODEX_COMPANION adversarial-review --base $BASE_BRANCH \"Challenge this plan: <plan summary/goal>. Plan file: <plan-path>. Focus on: wrong assumptions, missing edge cases, scope gaps, and design choices that could fail under real-world conditions.\"",
     run_in_background=true,
     timeout=600000
   )
   ```
**Do NOT wait** — proceed to collect the Claude reviewer results first.

#### Collect Review Results

**Wait for Claude reviewer results (bash polling — NOT Read loop):**

```bash
OUTPUT_PATH="<findings-path>"
for i in $(seq 1 150); do [ -f "$OUTPUT_PATH" ] && echo "READY" && break; sleep 2; done
```

Then Read the file once. If not READY after 5 min, re-launch synchronously.

**⛔ Validate findings:** After reading the JSON, verify that the `plan_file` field matches the current plan path. If it doesn't match, the findings are stale from a previous `/spec` — delete the file, re-launch the reviewer, and wait again.

**Fix Claude reviewer findings immediately** — must_fix → should_fix. Suggestions if reasonable.

#### Collect Codex Results (if launched)

**⛔ MANDATORY — NEVER skip or defer the Codex review.** If Codex was launched above, you MUST collect and act on its results before proceeding. The Codex review runs as `Bash(run_in_background=true)` — you will be automatically notified when it completes.

**⛔ The completion notification is the ONLY valid signal.** Do NOT read the output file to check if the review is done. The file may contain partial output from an in-progress review — reading it before the notification arrives leads to false conclusions ("no findings" when the review is still running). This is the #1 cause of premature Codex skip.

**⛔ If the notification hasn't arrived yet:** Do NOT proceed to Step 12 or approval. Do NOT read the output file. Do NOT conclude the review failed. Wait for the `<task-notification>` with `<status>completed</status>`. If you are tempted to check the file — that is the exact mistake this rule prevents.

**⛔ "Wait" does NOT mean "end your turn."** Ending the conversation turn lets the user think the workflow is finished and triggers a stop hook that pulls you out. Do not output a closing text message ("Waiting for codex…", "Holding for completion…"), do not call `ScheduleWakeup` as a substitute for staying engaged. Stay in-turn until the `<task-notification>` arrives. While waiting, do something productive in the same turn:
- Re-read the plan file once and pre-emptively spot any gaps you would fix anyway.
- If the user has queued a related request (e.g. a second bug to bundle), investigate / draft plan text for it now so you are ready to act when Codex completes.
- Run sanity-check Bash one-liners that don't fork long-running processes (path checks, file existence, small `git log` queries).
- As an absolute last resort with no other useful work, call `AskUserQuestion` to ask a short clarifying question — `AskUserQuestion` is the only tool whitelisted for a legitimate session-pause while a background task is in flight.

The completion notification arrives automatically as a mid-turn tool-result-style event; you do not need to poll for it.

1. **When (and ONLY when) the completion notification arrives, retrieve the findings from the persistent job state — NOT from the bash stdout file.** The companion writes the rendered review to a job record that survives bash truncation, mid-flight kills, and shell-pipe weirdness. Use the companion's own `status` + `result` subcommands (the supported public interface in `lib/render.mjs:211-283` and `state.mjs:resolveJobsDir`):

   ```bash
   STATUS_JSON=$(node "$CODEX_COMPANION" status --json)
   JOB_ID=$(printf '%s' "$STATUS_JSON" | python3 -c "
   import json,sys
   d=json.load(sys.stdin)
   lf=d.get('latestFinished') or {}
   if lf.get('kind')=='adversarial-review' and lf.get('status')=='completed':
       print(lf['id']); sys.exit(0)
   for j in (d.get('running') or []):
       if j.get('kind')=='adversarial-review':
           print('STILL_RUNNING:'+j['id']); sys.exit(0)
   sys.exit(1)
   ")
   ```

   - If `$JOB_ID` is empty → no adversarial-review job ran. Re-launch synchronously (foreground `Bash(timeout=600000)`).
   - If `$JOB_ID` starts with `STILL_RUNNING:` → the bash was killed before the review completed (the most common failure mode pre-fix). Re-launch synchronously with foreground bash, `timeout=600000`. Do NOT trust any partial output.
   - Else, fetch the rendered findings:

     ```bash
     node "$CODEX_COMPANION" result "$JOB_ID" --json > /tmp/codex-result-$$.json
     ```

   Then read `/tmp/codex-result-$$.json` via `ctx_execute_file` and extract `storedJob.rendered` (the full markdown report) and `storedJob.result.parsed` (structured `{verdict, summary, findings, next_steps}`). **Verify before parsing**: `storedJob.status === "completed"` AND `storedJob.rendered` starts with `"# Codex Adversarial Review"`. If either check fails, treat as a re-launch trigger — do NOT silently proceed.

2. **Parse the rendered findings.** Format (from `lib/render.mjs:211-283`):
   ```
   # Codex Adversarial Review
   Target: <branch>
   Verdict: <approve|needs-attention|reject>
   <summary>
   Findings:
   - [<severity>] <title> (<file>:<lines>)
     <body>
     Recommendation: <recommendation>
   Next steps:
   - <step>
   ```
   Severity → action map: `[critical]` / `[high]` → must_fix; `[medium]` / `[low]` → should_fix; `[info]` → suggestion. Fix every must_fix and should_fix inline.

3. **If `latestFinished` is absent and the bash exit code was non-zero in the notification** (genuine launch failure, not a timeout): re-launch synchronously and wait. If the second attempt also fails, escalate to the user with the captured error — do not silently proceed.

4. **Mark Codex as ran** so re-iterations of this plan within the same session do not re-run it:
```bash
mkdir -p "$(dirname "$CODEX_FLAG")" && touch "$CODEX_FLAG"
```

**If Codex was NOT launched**, proceed after all Claude reviewer must_fix/should_fix resolved.
