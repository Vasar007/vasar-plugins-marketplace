---
name: dotnet-build-test
description: "Build and test rules for .NET solutions. A plain `dotnet build` is the authority, not LSP or IDE diagnostics. Avoid `--no-incremental`. Run builds and tests in the foreground. The two exceptions to this rule are a request of the user and a long test run in a subagent."
when_to_use: "Use it for 'build the solution', 'run the tests', 'check for compile errors', or 'the LSP says X is broken'. Use it before any build or test command in a .NET repo."
---

# .NET Build & Test Conventions

## Rule 1: `dotnet build` is the authority; LSP is not

A plain, incremental `dotnet build` is the authoritative compiler signal. LSP and IDE diagnostics are a hint, not an authority. Do not claim a regression from LSP alone. Run a fresh `dotnet build` first.

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
log="$(mktemp)"
dotnet build <path-to-solution>.sln -c Debug > "$log" 2>&1
ec=$?
grep -E "(CS[0-9]+|Build succ|Build FAIL|error|Warning\(s\)|Error\(s\))" "$log" | grep -v ": warning " | head -30
echo "exit code: $ec"
rm -f "$log"
```

The filter keeps the compiler errors (`CS####`), the build result lines, and the warning and error counts. It drops the per-project "Started" and "Done Building" lines. It also drops each warning line, so that the errors and the result lines stay in the output. The warning count stays. The filter needs a POSIX shell with `grep` and `head`. On Windows, run it in Git Bash.

Run the whole block in one Bash call. The block keeps the exit code of `dotnet build` in `ec`, because a pipe returns the exit code of its last command.

### Quick filter for test output

The build filter drops the test result line and the names of the failed tests. For a test run, use this filter. It keeps the exit code of `dotnet test`. The first `grep` keeps the errors and the failed tests, each with the three lines after it. The second `grep` keeps the result lines and the line that says that no test matches the filter. It also keeps the count lines of Microsoft.Testing.Platform (`total:`, `failed:`, `succeeded:`, `skipped:`). The second `grep` has no `head`, so a long list of failed tests does not cut the result lines:

```bash
log="$(mktemp)"
dotnet test <path> -c Debug --filter "<filter>" > "$log" 2>&1
ec=$?
grep -iE -A3 "(CS[0-9]+|error|build fail|^ *failed )" "$log" | grep -v ": warning " | grep -v "^--$" | head -40
grep -iE "(failed!|passed!|no test matches|^ *(total|failed|succeeded|skipped): [0-9])" "$log"
echo "exit code: $ec"
rm -f "$log"
```

If the exit code is 0 and the result line shows zero failed tests, the run is green. Any other result is not green.

## Rule 2: Avoid `dotnet build --no-incremental` for verification

`--no-incremental` triggers a full clean rebuild with external codegen or formatting targets, for example a `<codegen>.targets` file that runs `dotnet format`. These targets resolve the SDK from the PATH of the calling environment. If the system has a newer SDK than the version that `global.json` pins, they fail with errors like these:

```text
error MSB4062: The "CheckIfPackageReferenceShouldBeFrameworkReference" task could not be loaded
... Could not load file or assembly 'System.Runtime, Version=10.0.0.0, ...
```

These errors are SDK and MSBuild infrastructure noise, not compile errors in the project under test. They cascade across every project in the solution and bury the real application-level signal.

### How to apply

- Default: `dotnet build <path-to-solution>.sln -c Debug` (incremental, one configuration). Targets run again only on dirty inputs, and the codegen path stays inside the pinned SDK of the project.
- A build from scratch is rare, usually only after a corrupted `obj/` or `bin/`. If you truly need one, delete those folders by hand and run a plain `dotnet build`. Do not use `--no-incremental` as a shortcut.
- After a successful `dotnet build`, `--no-build` is **not always safe** for a test run. A solution-level incremental build does not always refresh the output of a REFERENCED project in the output folder of the test project. This happens after edits in a project that the test project references, not in the test project itself. Then `dotnet test --no-build` runs against a stale DLL. It reports a green, complete-looking result for the OLD code, not for the edited code.
- If anything changed in a project that the test project references since the last full build of that reference chain, `--no-build` is not safe. If you are not sure (the common case after any edit), run `dotnet build <TestProject>.csproj`, or `dotnet test <TestProject>.csproj` without `--no-build`. Then MSBuild's own up-to-date logic refreshes the output of the referenced project.
- Always add a focused `--filter`. Never run the whole suite without a filter in a repo with integration tests. Tests against an emulator (for example, the Cosmos DB emulator), a database, or an external service are slow. Ask the user before you run slow suites that your filter does not cover. If `dotnet-backend-dev:create-tests` is loaded, see it for detailed test-scope conventions.

### Reporting gate: no green test result without verbatim proof

`dev-essentials:engineering-discipline` Rule 5 has the general rule: a `verified` claim needs verbatim proof in the `Failed: X, Passed: Y, Total: Z` format. Apply it here. The .NET addition: a test run that ends suspiciously fast for the known size of the suite is a sign. Before you report success, rule out a stale-binary false green (see the `--no-build` points above).

### Related but distinct: warning-count deltas across incremental builds are meaningless

An incremental build reports diagnostics only for the projects where `CoreCompile` runs again. So its warning count covers only part of the solution. A count delta between an incremental build and a full build, or between two incremental builds with different changed files, means nothing. Example: two builds one commit apart reported `1176` and then `2362` warnings for a 6-character diff. The second commit touched a file that almost every project references, so most projects compiled again.

To compare warnings, use one of these two ways:

1. Make both sides full clean rebuilds. Delete `obj/` and `bin/`, then run a plain `dotnet build`. Never use `--no-incremental` for this (Rule 2).
2. Compare by changed line numbers, not by totals. Get the changed lines with `git diff -U0 <parent> <commit> -- <file>`. Match them against the line numbers that the build log gives for that file. A warning on an unrelated line in a file that you touched is pre-existing.

Two incremental builds are not a safe basis for a comparison. For a routine "is it green" build, still avoid `--no-incremental` (Rule 2).

## Rule 3: Tests run foreground, with two exceptions

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

A foreground Bash command times out after 2 minutes by default. The `timeout` parameter raises this to at most 10 minutes (`600000`). At its timeout, Claude Code moves the command to the background. A subagent that Claude starts from the main conversation runs in the background by default, but a caller can still wait for it. So an agent that uses this recipe sets `background: true` in its frontmatter. A background subagent can leave a background command running past the end of its turn. When that command ends, Claude Code sends the subagent a notification. When the run of a foreground subagent ends, its background commands stop. If a subagent must report a test run that can take longer than 10 minutes, it does these steps:

1. Make a log folder outside the repository with `mktemp -d`.
2. Start the run with `run_in_background: true` and a `timeout` that covers the run, at most 2 hours (`7200000`). Without a `timeout`, an unattended session stops a background command after 30 minutes. Send the output to a log file in that folder. Then write the exit code to an exit file in the same folder.
3. Wait for the notification that the command ended. Do not poll the log or the exit file with `sleep` loops or repeated tool calls. Write the report only after the notification arrives.
4. Read the exit file and the log file. Report the result from the exit code and the log only.
5. If Claude Code reports that the background command stopped at its time limit, the exit file does not come. Report the test run as failed, and give that reason.

### Don't poll a backgrounded task

A task can run in the background because the user asked, or because a task notification system delivers its results. Do not poll such a task with sleep loops or repeated tool calls. At the end of the task, the runtime sends a notification. This skill allows no poll, also not for the long test run of the section above. For parallel agent dispatch, see `dev-essentials:subagent-orchestration` Rule 3.
