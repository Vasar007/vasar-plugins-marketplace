---
name: dotnet-build-test
description: How to build and test .NET solutions reliably — `dotnet build` is authoritative; LSP/IDE diagnostics are stale-cache-prone after rebases and not authoritative; avoid `dotnet build --no-incremental` for verification (it can trigger external codegen targets and produce thousands of MSB4062 errors that drown real signal); tests and builds run foreground only — never `run_in_background: true` unless the user explicitly asked. Triggers on phrases like "build the solution", "run dotnet build", "run the tests", "test this", "verify the change", "check for compile errors", "check for regressions", "the LSP says X is broken", or whenever the agent is about to invoke `dotnet build`, `dotnet test`, or any other build/test command in a .NET repo.
---

# .NET Build & Test Conventions

Three rules for keeping the build/test feedback loop honest in .NET repos. Each one is the cure for a specific failure mode that has cost real session time.

## Rule 1 — `dotnet build` is the authority; LSP is not

When verifying a code change, **`dotnet build` (plain, incremental) is the authoritative compiler signal**. LSP / IDE diagnostics from the harness are a hint; they are NOT authoritative. Do not claim a regression based on LSP alone — confirm with a fresh `dotnet build` first.

### Why

LSP keeps stale type information for files whose dependencies just changed under it. Symptoms after rebases / merges / cross-file edits:

- `CS1739` — "no parameter named X" (when X exists in the new signature)
- `CS0246` — "type not found" (when the type is in a project the LSP hasn't reanalyzed)
- `CS0103` — "name does not exist" (same root cause)

These look like real regressions but are LSP cache misses.

### How to apply

Default verification command:

```bash
dotnet build ./Sources/<solution>.sln -c Debug
```

(no flags). If it succeeds, the LSP diagnostic is stale — surface it as "LSP cache stale, real build clean" rather than "regression introduced".

The other failure mode: trusting LSP green when the compiler would have caught the error. Don't claim "build clean" without running `dotnet build`. If you only checked LSP, say so — let the user decide whether to wait for a real build.

### Quick filter for verbose build output

```bash
dotnet build ./Sources/<sln>.sln -c Debug 2>&1 | grep -E "(CS[0-9]+|Build succ|Build FAIL|error|Warning\(s\)|Error\(s\))" | head -30
```

This surfaces compile-language errors (`CS####`), build-result lines, and warning/error counts — the actual "is it green" signal — and discards the per-project "Started/Done Building" chatter.

## Rule 2 — Avoid `dotnet build --no-incremental` for verification

`--no-incremental` triggers a full clean rebuild including external codegen / formatting targets (e.g. a `<codegen>.targets` file invoking `dotnet format`). These targets resolve the SDK from the calling environment's PATH — when the system has a newer SDK than the project's `global.json`-pinned version, they fail with errors like:

```
error MSB4062: The "CheckIfPackageReferenceShouldBeFrameworkReference" task could not be loaded
... Could not load file or assembly 'System.Runtime, Version=10.0.0.0, ...
```

These errors are SDK/MSBuild infrastructure noise, NOT compile errors in the project under test. They cascade across every project in the solution and bury the actual application-level signal.

### How to apply

- Default: `dotnet build ./Sources/<solution>.sln -c Debug` (incremental, single config). Targets re-run only on dirty inputs and the codegen path stays inside the project's pinned SDK.
- If you genuinely need a from-scratch build (rare — usually only after a corrupted `obj/`/`bin/`), delete those folders manually and run plain `dotnet build`. Do NOT use `--no-incremental` as a shortcut.
- For test runs after a successful `dotnet build`: use `--no-build` and a focused `--filter`. Never run the whole suite without a filter on a repo with integration tests (Cosmos, database, external service tests are slow — ask the user before running uncovered suites; see `dotnet-backend-dev:create-tests` if you have it loaded for detailed test-scope conventions).

### Anti-patterns

- "LSP says CS1739, the rebase must have broken X" — the rebase may be clean; the LSP didn't reanalyze. Run `dotnet build` first.
- "Let me do a full rebuild with `--no-incremental` to be safe" — generates infrastructure noise and changes nothing semantically.
- Reporting "build green" without ever running `dotnet build` (relying purely on LSP "no diagnostics") — same trap from the other direction. LSP can also miss errors that the compiler catches.

## Rule 3 — Tests run foreground; no background tasks unless the user asks

Never run tests with `run_in_background: true` (or any equivalent). Always run tests in the foreground and wait for the result synchronously. Same for builds, deploys, or any long-running command.

### Why

- The user wants to see test output as it happens and review the result directly.
- Backgrounded runs hide progress, leave stale task IDs around, and make it tempting to declare success before the run finishes.
- If tests are taking unusually long, treat it as a signal that something is broken — investigate the cause instead of waiting it out.
- Background tasks can cause real damage in automated workflows. Interrupted file transfers have left corrupted artifacts on remote servers, breaking instances — this has happened multiple times.

### How to apply

- For any `dotnet test`, `npm test`, `dotnet build`, deploy script, or similar: call Bash directly with a generous `timeout` (up to 10 min), not `run_in_background`.
- If a test command exceeds the expected duration by a wide margin, stop and report it as a likely break — do not wait silently.
- The system may auto-background a command after timeout. Acknowledge that to the user rather than pretending it ran in foreground.
- If the user explicitly says "run this in the background", that's the only valid reason to set `run_in_background: true`.

### Don't poll a backgrounded task

If something IS running in the background (because the user asked, or a task notification system is delivering results), do not poll with sleep loops or repeated tool calls. The runtime delivers a notification when the task completes. See `dev-essentials:subagent-orchestration` for the structured-pipeline parallel exception.
