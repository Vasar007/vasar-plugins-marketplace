---
name: dotnet-build-test
description: "How to build and test .NET solutions reliably. `dotnet build` is authoritative. LSP and IDE diagnostics go stale after rebases and are not authoritative. Avoid `dotnet build --no-incremental` for a routine build: it can trigger external codegen targets and produce thousands of MSB4062 errors that drown the real signal. Run tests and builds in the foreground only. If the user explicitly asks for it, use `run_in_background: true`. A subagent can use it for a test run over 10 minutes (Rule 3). Triggers on phrases like 'build the solution', 'run dotnet build', 'run the tests', or 'test this'. Also on 'verify the change', 'check for compile errors', 'check for regressions', or 'the LSP says X is broken'. Also triggers before any build or test command in a .NET repo."
---

# .NET Build & Test Conventions

## Rule 1 — `dotnet build` is the authority; LSP is not

A plain, incremental `dotnet build` is the authoritative compiler signal. LSP and IDE diagnostics are a hint, NOT an authority. Do not claim a regression from LSP alone. Run a fresh `dotnet build` first.

### Why

After rebases, merges, or edits across files, LSP keeps stale type information for files whose dependencies changed. Typical symptoms:

- `CS1739`, "no parameter named X", but X exists in the new signature
- `CS0246`, "type not found", for a type in a project that LSP did not analyze again
- `CS0103`, "name does not exist", from the same cause

These look like real regressions, but they are LSP cache misses.

### How to apply

Default build command:

```bash
dotnet build <path-to-solution>.sln -c Debug
```

Use no other flags. If the build succeeds, the LSP diagnostic is stale. Report it as "LSP cache stale, real build clean", not as "regression introduced".

The opposite failure is to trust a green LSP where the compiler finds an error. Do not claim "build clean" without a run of `dotnet build`. If you only looked at LSP, say so, and let the user decide whether to wait for a real build.

### Quick filter for verbose build output

```bash
dotnet build <path-to-solution>.sln -c Debug 2>&1 | grep -E "(CS[0-9]+|Build succ|Build FAIL|error|Warning\(s\)|Error\(s\))" | head -30
```

The filter keeps the compiler errors (`CS####`), the build result lines, and the warning and error counts. It drops the per-project "Started" and "Done Building" lines. The filter needs a POSIX shell with `grep` and `head`. On Windows, run it in Git Bash.

## Rule 2 — Avoid `dotnet build --no-incremental` for verification

`--no-incremental` triggers a full clean rebuild with external codegen or formatting targets, for example a `<codegen>.targets` file that runs `dotnet format`. These targets resolve the SDK from the PATH of the calling environment. If the system has a newer SDK than the version that `global.json` pins, they fail with errors like these:

```
error MSB4062: The "CheckIfPackageReferenceShouldBeFrameworkReference" task could not be loaded
... Could not load file or assembly 'System.Runtime, Version=10.0.0.0, ...
```

These errors are SDK and MSBuild infrastructure noise, NOT compile errors in the project under test. They cascade across every project in the solution and bury the real application-level signal.

### How to apply

- Default: `dotnet build <path-to-solution>.sln -c Debug` (incremental, one configuration). Targets run again only on dirty inputs, and the codegen path stays inside the pinned SDK of the project.
- A build from scratch is rare, usually only after a corrupted `obj/` or `bin/`. If you truly need one, delete those folders by hand and run a plain `dotnet build`. Do NOT use `--no-incremental` as a shortcut.
- After a successful `dotnet build`, `--no-build` is **not always safe** for a test run. A solution-level incremental build does NOT always refresh the output of a REFERENCED project in the output folder of the test project. This happens after edits in a project that the test project references, not in the test project itself. Then `dotnet test --no-build` runs against a stale DLL. It reports a green, complete-looking result for the OLD code, not for the edited code.
- If anything changed in a project that the test project references since the last full build of that reference chain, `--no-build` is NOT safe. If you are not sure (the common case after any edit), run `dotnet build <TestProject>.csproj`, or `dotnet test <TestProject>.csproj` without `--no-build`. Then MSBuild's own up-to-date logic refreshes the output of the referenced project.
- Always add a focused `--filter`. Never run the whole suite without a filter in a repo with integration tests. Cosmos, database, and external service tests are slow. Ask the user before you run slow suites that your filter does not cover. If `dotnet-backend-dev:create-tests` is loaded, see it for detailed test-scope conventions.

### Reporting gate: no green test result without verbatim proof

`dev-essentials:engineering-discipline` Rule 5 has the general rule: a `verified` claim needs verbatim proof in the `Failed: X, Passed: Y, Total: Z` format. Apply it here. The .NET addition: a test run that ends suspiciously fast for the known size of the suite is a sign. Before you report success, rule out a stale-binary false green (see the `--no-build` points above).

### Related but distinct: warning-count deltas across incremental builds are meaningless

An incremental build reports diagnostics only for the projects where `CoreCompile` runs again. So its warning count covers only part of the solution. A count delta between an incremental build and a full build, or between two incremental builds with different changed files, means nothing. Example: two builds one commit apart reported `1176` and then `2362` warnings for a 6-character diff. The second commit touched a file that almost every project references, so most projects compiled again.

To compare warnings, use one of these two ways:

1. Make both sides full clean rebuilds. Delete `obj/` and `bin/`, then run a plain `dotnet build`. Never use `--no-incremental` for this (Rule 2).
2. Compare by changed line numbers, not by totals. Get the changed lines with `git diff -U0 <parent> <commit> -- <file>`. Match them against the line numbers that the build log gives for that file. A warning on an unrelated line in a file that you touched is pre-existing.

Two incremental builds are NOT a safe basis for a comparison. For a routine "is it green" build, still avoid `--no-incremental` (Rule 2).

## Rule 3 — Tests run foreground, with two exceptions

Never run tests with `run_in_background: true` or an equivalent. Run tests in the foreground, and wait for the result. The same holds for builds, deploys, and any other long-running command. This rule has two exceptions: a request of the user, and a long test run in a subagent (see below).

### Why

- The user wants to see the test output as it happens and to review the result directly.
- A background run hides progress, leaves stale task IDs, and tempts you to claim success before the run ends.
- In automated workflows, an interrupted background transfer can leave corrupted artifacts on remote servers and break instances.

### How to apply

- For `dotnet test`, `npm test`, `dotnet build`, a deploy script, or a similar command, call Bash directly with a generous `timeout` (up to 10 minutes). Do not use `run_in_background`.
- If a test command runs much longer than expected, stop and report it as a likely break. Do not wait silently.
- The system can move a command to the background after a timeout. If that happens, tell the user. Do not pretend that it ran in the foreground.
- If the user explicitly says "run this in the background", you can set `run_in_background: true`. The only other valid reason is a long test run in a subagent (see the next section).

### Exception: a long test run in a subagent

A foreground Bash command runs for at most 10 minutes by default. At its timeout, Claude Code moves the command to the background. A subagent must report the test result in the same run, so it cannot wait for a notification. Also, at the end of the run of a foreground subagent, its commands stop. If a subagent must report a test run that can take longer than 10 minutes, it does these steps:

1. Make a log folder outside the repository with `mktemp -d`.
2. Start the run with `run_in_background: true` and a `timeout` that covers the run, at most 2 hours (`7200000`). Without a `timeout`, an unattended session stops a background command after 30 minutes. Send the output to a log file in that folder. Then write the exit code to an exit file in the same folder.
3. Wait in foreground calls of less than 10 minutes each. Each call checks for the exit file in a loop with a short `sleep`. Do not end the run of the subagent before the exit file exists, unless step 5 applies.
4. When the exit file exists, read the log file. Report the result from the exit code and the log only.
5. If Claude Code reports that the background command stopped at its time limit, the exit file does not come. Stop the wait, report the test run as failed, and give that reason.

### Don't poll a backgrounded task

A task can run in the background because the user asked, or because a task notification system delivers its results. Do not poll such a task with sleep loops or repeated tool calls. At the end of the task, the runtime sends a notification. The only poll that this skill allows is the exit-file wait of the section above. For parallel agent dispatch, see `dev-essentials:subagent-orchestration` Rule 3.
