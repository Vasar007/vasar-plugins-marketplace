---
name: dotnet-build-test
description: "How to build and test .NET solutions reliably — `dotnet build` is authoritative; LSP/IDE diagnostics are stale-cache-prone after rebases and not authoritative; avoid `dotnet build --no-incremental` for verification (it can trigger external codegen targets and produce thousands of MSB4062 errors that drown real signal); tests and builds run foreground only — never `run_in_background: true` unless the user explicitly asked. Triggers on phrases like 'build the solution', 'run dotnet build', 'run the tests', 'test this', 'verify the change', 'check for compile errors', 'check for regressions', 'the LSP says X is broken', or whenever the agent is about to invoke `dotnet build`, `dotnet test`, or any other build/test command in a .NET repo."
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
- For test runs after a successful `dotnet build`: **`--no-build` is not unconditionally safe.** A solution-level incremental build does NOT necessarily refresh a REFERENCED project's compiled output in the test project's own output directory — if edits landed in a project that the test project references (rather than in the test project itself), `dotnet test --no-build` can silently run against a stale DLL and report a fully green, complete-looking result that reflects the OLD code, not the edited code. This has cost real session time: on one incident 94,530 tests reported "passed" against a stale binary, versus 229 real failures once rebuilt correctly, and the same pattern recurred later on an unrelated task. The actual rule: `--no-build` is only safe when NOTHING in a project referenced by the test project has changed since the last full build of that reference chain. When in doubt (the common case after any edit), run `dotnet build <TestProject>.csproj` (or `dotnet test <TestProject>.csproj` without `--no-build`) so MSBuild's own up-to-date check actually re-links the referenced project's output. Combine with a focused `--filter` regardless. Never run the whole suite without a filter on a repo with integration tests (Cosmos, database, external service tests are slow — ask the user before running uncovered suites; see `dotnet-backend-dev:create-tests` if you have it loaded for detailed test-scope conventions).

### Reporting gate: no green test result without verbatim proof

The general "verified requires verbatim proof" rule and its required `Failed: X, Passed: Y, Total: Z` format are `dev-essentials:engineering-discipline` Rule 5 — apply it here. The .NET-specific addition: a suspiciously instant test run (given the known scale of the suite) is itself a signal to double-check for a stale-binary false green (see the `--no-build` caveat above) rather than reporting success.

### Related but distinct: warning-count deltas across incremental builds are meaningless

This is the mirror-image failure mode — the same incremental-build blind spot, but in the opposite direction. Comparing MSBuild **warning counts** between two builds is only valid if BOTH builds are full clean rebuilds (delete `obj/`/`bin/`, then plain `dotnet build` — never `--no-incremental`, per Rule 2). An incremental build only re-analyzes changed files — MSBuild/csc emit diagnostics only for projects where `CoreCompile` actually re-runs — so its warning count reflects a PARTIAL scan, not the whole project. A raw count delta between an incremental build and a full build, or between two incrementals with different changed-file sets, is meaningless. Proven case: a `--no-incremental` build of a large solution reported `2364 Warning(s)` (the real latent total); a plain incremental build run immediately afterwards reported `0 Warning(s)` because nothing needed recompiling. Two agents building the same branch one commit apart reported `1176` then `2362` warnings for a 6-character diff, because the second commit touched a file nearly every project references (e.g. a shared strings-resource file), cascade-invalidating most of the dependency graph, while the first commit's edits hit a much narrower subgraph.

To attribute new warnings to a specific change, don't compare totals — compare by CHANGED LINE NUMBERS in the diff (`git diff -U0 <parent> <commit> -- <file>`) and cross-reference them against the line numbers the build log cites for that file. A warning at an unrelated line in a file you touched is pre-existing.

This does not contradict the guidance above — the two coexist: still avoid `--no-incremental` for routine "is it green" verification (it triggers external codegen targets that pick up the system SDK instead of the project-pinned one). But if you genuinely need a warning-count comparison, either do both sides as full clean rebuilds (delete `obj/`/`bin/`, then plain `dotnet build`, per Rule 2 — never `--no-incremental`), or compare by line number instead of raw count — "both incremental" is NOT a safe comparison basis, as the `1176`/`2362` case above proves: two incremental builds one commit apart produced wildly different counts purely from which files each commit's edits happened to cascade-invalidate.

### Anti-patterns

- "LSP says CS1739, the rebase must have broken X" — the rebase may be clean; the LSP didn't reanalyze. Run `dotnet build` first.
- "Let me do a full rebuild with `--no-incremental` to be safe" — generates infrastructure noise and changes nothing semantically.
- Reporting "build green" without ever running `dotnet build` (relying purely on LSP "no diagnostics") — same trap from the other direction. LSP can also miss errors that the compiler catches.
- Reporting "tests passed" from a subagent's prose summary, or from a `--no-build` run after only a solution-level build, without independently re-deriving the verbatim `Failed/Passed/Total` line — this is the stale-binary false-green trap described above.

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
