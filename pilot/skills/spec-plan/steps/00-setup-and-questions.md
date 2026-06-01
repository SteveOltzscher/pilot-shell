## Step 0: Setup & Question Policy

### 0.1 Read Toggle Configuration

**Run first, before any other step.** Read all toggle env vars in a single Bash call:

<!-- CC-ONLY -->
```bash
echo "QUESTIONS=$PILOT_PLAN_QUESTIONS_ENABLED REVIEWER=$PILOT_SPEC_REVIEW_ENABLED CODEX_SPEC=$PILOT_CODEX_SPEC_REVIEW_ENABLED APPROVAL=$PILOT_PLAN_APPROVAL_ENABLED MODEL_SWITCH=$PILOT_MODEL_SWITCH_ENABLED"
```

Reference these values throughout: Steps 4/6 (questions), 10 (reviewer + Codex — Codex controlled by Console Settings), and 12 (approval + Model Switching handoff).
<!-- /CC-ONLY -->
<!-- CODEX-START
```bash
echo "QUESTIONS=$PILOT_PLAN_QUESTIONS_ENABLED REVIEWER=$PILOT_SPEC_REVIEW_ENABLED APPROVAL=$PILOT_PLAN_APPROVAL_ENABLED MODEL_SWITCH=$PILOT_MODEL_SWITCH_ENABLED"
```

Reference these values throughout: Steps 4/6 (questions), 10 (native Codex `spec-review` subagent), and 12 (approval + Model Switching handoff).
CODEX-END -->

### 0.2 Asking User Questions

**If `PILOT_PLAN_QUESTIONS_ENABLED` is `"false"` (above),** skip all `AskUserQuestion` calls in Steps 4 and 6. Make reasonable default choices (including selecting the recommended approach in Step 6) and document them in the plan under an "Autonomous Decisions" sub-section. Continue to the next step immediately.

<!-- CC-ONLY -->
**Use the `AskUserQuestion` tool for user questions** (when questions are enabled) — it renders a structured form that's much easier to answer than a plain-text numbered list, with each question its own entry of predefined options. Don't fall back to numbered questions in prose.
<!-- /CC-ONLY -->
<!-- CODEX-START
**Use plain-text numbered options for user questions** (when questions are enabled) — the Claude question tool isn't callable in Codex. Present each question with 2-4 concrete options and wait for the user's response.

**Codex speed override:** `PILOT_PLAN_QUESTIONS_ENABLED=true` allows questions; it does not require two question rounds. Ask only when the missing answer can materially change scope, architecture, or user-visible behavior. Keep Codex planning to one bundled prompt with at most 3 short questions, unless the user has explicitly asked for deeper planning.
CODEX-END -->

<!-- CC-ONLY -->
**Default is to ask, not skip.** Every plan benefits from at least one round of user alignment. Only skip questions when the task is a single-file change with zero ambiguity.

**Questions batched into max 2 interactions:** Batch 1 (before exploration) clarifies task/scope/priorities. Batch 2 (after exploration) covers approach selection and design decisions. **Both batches are expected for most tasks** — skipping both is the exception, not the norm.

**Principles:** Present options with trade-offs (not open-ended). Start open, narrow down. Challenge vagueness — make abstract concrete. 1-2 focused questions beat 4 vague ones. Questions clarify HOW to implement, not whether to expand scope.
<!-- /CC-ONLY -->
<!-- CODEX-START
**Codex default is to proceed after one bounded alignment check.** If the request is clear enough to make reversible assumptions, do not ask before drafting the plan.

**Questions are capped at one interaction:** ask before exploration only when the answer changes scope or architecture. Skip Batch 2 unless the wrong choice would cause visible rework.

**Principles:** prefer concrete assumptions, short trade-offs, and fast plan delivery. Questions clarify blocking decisions only.
CODEX-END -->
