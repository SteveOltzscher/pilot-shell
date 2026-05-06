## Step 7: Collect Review Results

**⛔ If `PILOT_CHANGES_REVIEW_ENABLED` is `"false"` (from Step 0 — Step 4 was skipped),** skip this step entirely and proceed to Step 9 (Phase B). There are no findings to collect.

**When enabled — mandatory. Never skip** — even if you're confident, context is high, or tests pass.

**⛔ NEVER use `TaskOutput`** to retrieve results — it dumps the full agent transcript into context, wasting thousands of tokens.

**Wait for Claude reviewer results (bash polling — NOT Read loop):**

```bash
OUTPUT_PATH="<findings-path>"
for i in $(seq 1 250); do [ -f "$OUTPUT_PATH" ] && echo "READY" && break; sleep 2; done
```

Then Read the file once. If not READY after ~8 min, re-launch synchronously.

**⛔ Validate findings:** After reading the JSON, verify that the `plan_file` field matches the current plan path. If it doesn't match, the findings are stale from a previous `/spec` — delete the file, re-launch the reviewer, and wait again.

#### Fix Claude Reviewer Findings

**Fix automatically — no user permission needed.**

1. **must_fix** → Fix immediately (security, crashes, TDD violations)
2. **should_fix** → Fix immediately (spec deviations, missing tests, error handling)
3. **suggestions** → Implement if quick

For each fix: implement → run relevant tests → log "Fixed: [title]"

#### Collect Codex Results (if launched)

**⛔ MANDATORY — NEVER skip or defer the Codex review.** If Codex was launched in Step 4, you MUST collect and act on its results before proceeding past Step 7. The Codex review runs as a `Bash(run_in_background=true)` — you will be automatically notified when it completes.

**⛔ The completion notification is the ONLY valid signal.** Do NOT read the output file to check if the review is done. The file may contain partial output from an in-progress review — reading it before the notification arrives leads to false conclusions ("no findings" when the review is still running). This is the #1 cause of premature Codex skip.

**⛔ If the notification hasn't arrived yet:** STOP. Do NOT proceed to Phase B, do NOT say "still running, moving on", do NOT read the output file, do NOT conclude the review failed. Wait for the `<task-notification>` with `<status>completed</status>`. If you are tempted to check the file — that is the exact mistake this rule prevents.

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
   Target: <branch or working-tree>
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

3. **If `latestFinished` is absent and the bash exit code was non-zero in the notification** (genuine launch failure, not a timeout): re-launch synchronously (not in background) and wait for results. If the second attempt also fails, escalate to the user with the captured error — do not silently proceed.

4. **Mark Codex as ran** so re-verify iterations within the same session do not re-run it:
```bash
SESS_ID="${PILOT_SESSION_ID:-default}"
CODEX_FLAG="$HOME/.pilot/sessions/$SESS_ID/codex-ran-<plan-slug>.flag"
mkdir -p "$(dirname "$CODEX_FLAG")" && touch "$CODEX_FLAG"
```

**Report:**
```
## Code Verification Complete
**Issues Found:** X
### Goal Achievement: N/M truths verified
### Must Fix (N) | Should Fix (N) | Suggestions (N)
```
