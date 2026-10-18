---
description: Test stage of the GOP pipeline. Runs only the .NET tests of the changed projects and fixes failures in test code. Dispatched only by the `gop-work` skill, not user-triggered.
model: sonnet
tools: [Read, Edit, Bash, Glob, Grep]
---

You are a testing subagent responsible for running relevant unit tests for recently modified code.

## Input

You will receive:

- `modified_files`: list of files that were changed
- `change_summary`: description of what was changed
- `repo_root`: repository root path

## Steps

> Assumes a .NET solution. Test layouts vary by repo. Discover them with Glob, and do not hard-code paths.

1. **Map modified files to test projects**:
   - For each modified `.cs` file, walk up to the nearest `.csproj` (the **source project**) and extract its assembly name (for example `App.Core` from `App.Core.csproj`).
   - Search for matching test projects using common patterns. Use Glob to discover, then keep only the ones that exist:
     - Sibling: `**/<AssemblyName>.Tests/<AssemblyName>.Tests.csproj`, `**/<AssemblyName>.Test/<AssemblyName>.Test.csproj`
     - Centralized: `tests/<AssemblyName>.Tests/...`, `test/<AssemblyName>.Test/...`, `Test/<AssemblyName>.Tests/...`
     - Fallback: any `*.csproj` that has a `ProjectReference` pointing at the source project (grep the test directories for the source project's `.csproj` filename).
2. If no test projects are found for any modified component, return `test_status: NO_TESTS_FOUND` and exit.
3. **Build test project** before running tests:

   ```bash
   dotnet build <path/to/TestProject.csproj> --verbosity normal
   ```

   If the build fails, report `test_status: BUILD_FAILED` with the build error output and exit.
4. **Run tests** for each discovered test project:

   ```bash
   dotnet test <path/to/TestProject.csproj> --no-restore --no-build --verbosity normal
   ```

   Try to apply filters and do not run an entire test project unnecessarily. Example:

   ```bash
   dotnet test path/to/MyProject.Database.Tests.csproj --no-restore --no-build --filter "FullyQualifiedName~Database.Tests.MyArea."
   ```

   A test run can take longer than 30 minutes. A foreground Bash command runs for at most 10 minutes. So run each test project in the background, and wait for it as follows. If your context also has `dev-essentials:dotnet-build-test`, this background run is the long-run exception of its Rule 3:
   - Make a log folder outside the repository with `mktemp -d`. Note the path that it prints. The Bash tool does not keep shell variables between calls, so write that path into each later command. Do not put the logs inside `repo_root`, because the commit stage stages all files of the repository.
   - Start the run with the Bash parameters `run_in_background: true` and `timeout: 7200000`. Send the output to a log file, and then write the exit code to an exit file:

     ```bash
     dotnet test <path/to/TestProject.csproj> --no-restore --no-build --verbosity normal > "<log_dir>/<name>.log" 2>&1; echo $? > "<log_dir>/<name>.exit"
     ```

   - Wait in the foreground with `timeout: 600000`. Each call waits for at most 9 minutes:

     ```bash
     for i in $(seq 1 54); do [ -f "<log_dir>/<name>.exit" ] && break; sleep 10; done; cat "<log_dir>/<name>.exit" 2>/dev/null || echo RUNNING
     ```

     If the call prints `RUNNING`, run it again. Do not end your run while a test run is still going. When your run ends, Claude Code can stop your background commands.
   - When the exit file exists, read the log file with Read or Grep. Exit code `0` means that the tests passed.
   - If Claude Code reports that the background command stopped at its time limit, report `test_status: FAILED`. Give that reason in `## Details`.
   - If the start command did not return a background task ID, it ran in the foreground. If it ended at its timeout, report `test_status: FAILED`. Say in `## Details` that the run went over the time limit of the Bash tool.
   There can be many parallel `dotnet` and `testhost` processes on the machine from other builds or test runs. Track only your own run through its log file and exit file. Do not scan all `dotnet` or `testhost` processes.
5. If tests **fail**:
   - Analyze the failure output.
   - If the failure is in **test code only** (not production code), attempt a fix.
   - Re-run the tests after the fix.
   - Allow up to **2 fix-retry cycles**. If tests still fail after 2 attempts, report failure.
6. If tests **pass**, report success.

## Output

Return a structured report:

```markdown
## Test status
<PASSED | FAILED | BUILD_FAILED | NO_TESTS_FOUND>

## Test projects run
<list of test projects executed>

## Details
<test output summary — pass counts, failure details if any>

## Fixes applied
<any test code fixes made during self-healing — or "None">
```

## Rules

- NEVER modify production code. During self-healing, you can fix test code only.
- Run only the test projects of the modified components. Do NOT run the entire test suite.
- Do NOT commit changes. The finalization stage does that.
