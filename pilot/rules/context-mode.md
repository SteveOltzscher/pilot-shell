# Context — Routing & Compaction

Two things to know: context-mode MCP keeps tool output out of your window; auto-compaction handles overflow. Both are automatic — your job is to route correctly and not panic at high context.

## Compaction Is Automatic

PreCompact hook → captures plan/tasks/decisions to Memory. Compaction → summarizes. SessionStart(compact) hook → re-injects state. You continue exactly where you were.

**⛔ NEVER rush or skip steps because of context level.** Don't cut corners, skip sub-agents, reduce coverage, or compress output to "finish before it runs out." Context level is never a valid reason to skip a workflow step (reviewer, verification, tests). Complete the current task at full quality.

When compaction occurs, your summary must preserve: active plan path + status, current objective, TDD phase, files being modified, key decisions, blockers. Condensable: pleasantries, intermediate file reads, repetitive "explored N similar" patterns.

## Think in Code — MANDATORY

To analyze, count, filter, compare, parse, or transform data: **write code** via `ctx_execute(language, code)` and `console.log()` only the answer. Don't read raw data into context. Pure JS, Node.js built-ins (`fs`, `path`, `child_process`), `try/catch`, handle null. One script replaces ten tool calls.

## Pass an explicit `timeout` — MANDATORY

`ctx_execute`, `ctx_batch_execute`, and `ctx_execute_file` accept an optional `timeout` (milliseconds). **When omitted, no server-side timer fires** — a slow grep, hung subprocess, or runaway script can sit for 15+ minutes before the MCP host RPC layer aborts. Always pass a `timeout` sized to what you expect the command to do. The `tool_redirect` hook nudges (soft, once per session) when `timeout` is missing.

| Command shape | `timeout` (ms) |
|---------------|----------------|
| Simple grep, file listing, `jq` filter, single short script | `30000` (30 s) |
| Medium script — multi-file analysis, JSON processing, dozens of fetches | `120000` (2 min) |
| Heavy batch — many network calls, large data processing, slow CLIs | `300000` (5 min) |
| Long build (Gradle/Maven/SBT, full test suite, container build) | up to `600000` (10 min) |

**Default when unsure**: `60000` (1 min). Pick the smallest bucket the work fits into — most scripts finish in <10 s. A grep that hits the 30-s cap is a signal that the search is too broad or the path is wrong — refine, don't bump the timeout. With `concurrency > 1` in `ctx_batch_execute`, `timeout` applies **per command**, not as a shared budget.

## Blocked Commands

| Command | Why | Use instead |
|---------|-----|-------------|
| `curl` / `wget` in Bash | Floods context | web-search/web-fetch MCP, or `ctx_execute` with `fetch()` |
| `fetch('http`, `requests.get(`, `http.get(` in Bash | Floods context | `ctx_execute` |
| Built-in `WebFetch` | Denied by hook | `mcp__plugin_pilot_web-fetch__fetch_url` |

## Redirected Tools

- **Bash** — only `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands. Long output → `ctx_execute(language: "shell", ...)` or `ctx_batch_execute`.
- **Read** — correct when you intend to Edit. For analyze/explore/summarize use `ctx_execute_file(path, language, code)`.
- **Grep** — large results flood context. Wrap in `ctx_execute(language: "shell", code: "grep ...")`.

## Tool Selection Hierarchy

1. **GATHER** — `ctx_batch_execute(commands, queries)`. Primary tool. Runs commands, auto-indexes, searches in ONE call.
2. **FOLLOW-UP** — `ctx_search(queries: [...])`. Pass ALL questions in one array.
3. **PROCESSING** — `ctx_execute` / `ctx_execute_file`. Sandbox; only stdout enters context.
4. **WEB** — dedicated MCP servers (`web-search`, `web-fetch`), NOT context-mode.
5. **INDEX** — `ctx_index(path: ...)`. Never pass large `content`.

## Decision Tree

```
About to run a command / read a file / call an API?
├── Bash whitelist (file mutations, git writes, navigation)?       → Bash
├── Output might be large or unsure?                               → ctx_execute / ctx_execute_file
├── Fetching web docs or HTML?                                     → web-fetch / web-search MCP
├── Processing output from another MCP tool?
│   ├── Already in context? → use it directly
│   ├── Multi-query needed? → save → ctx_index(path) → ctx_search
│   └── One-shot?           → save → ctx_execute_file(path)
└── Reading file to analyze (not edit)?                            → ctx_execute_file
```

## Automatic Triggers

Use context-mode without being asked for: API debugging, log analysis, test runs, git history, data inspection (CSV/JSON), infrastructure listings, build output, code metrics.

## Language Selection

| Situation | Language |
|-----------|----------|
| HTTP/API, JSON | `javascript` (native fetch, async/await) |
| Data analysis, CSV, stats | `python` (csv, statistics, re) |
| Shell pipes | `shell` (grep, awk, jq) |

## Search Strategy

BM25 uses OR semantics — more matched terms rank higher. Use 2–4 specific technical terms. Always pass `source` when multiple docs indexed. Always batch via `queries` array.

## Critical Rules

1. Always `console.log` your findings — stdout is all that enters context.
2. Write analysis code, not data dumps. Print conclusions with IDs, line numbers, exact values.
3. Files you need to EDIT → normal `Read`. context-mode is for analysis only.
4. Bash whitelist only — file mutations, git writes, navigation, process control, package install.
5. Never `ctx_index(content: large_data)` — always `ctx_index(path: ...)`.
6. Don't re-index data already in context.
7. Always pass a `timeout` to `ctx_execute` / `ctx_batch_execute` / `ctx_execute_file` — omitting it allows multi-minute hangs (see *Pass an explicit `timeout`*).

## Subagent Routing

The PreToolUse hook injects the routing block into subagent prompts. You don't need to instruct them about context-mode.

## ctx Commands

| Command | Action |
|---------|--------|
| `ctx stats` | `ctx_stats` MCP tool, display output |
| `ctx doctor` | `ctx_doctor` MCP tool, run the returned shell command |
| `ctx purge` | `ctx_purge` with `confirm: true` (irreversible) |

After `/clear` or `/compact` the knowledge base persists — use `ctx purge` to wipe.
