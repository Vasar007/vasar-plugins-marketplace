---
description: Probe of the run environment. It shows whether a plain dotnet build works in the sandbox. It checks that dotnet build and dotnet test with -m:1 work on the fixture, and that the test run leaves its marker files.
tags: [probe]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Read, Glob, Grep]
max_turns: 40
timeout_seconds: 900
---

Run the three commands below in the repo root, one by one, with the Bash tool. After each command, append the command, its exit code, and the last 5 lines of its output to a file named probe.txt. If a command fails, run the next command anyway. Do not fix a failure.

1. dotnet build
2. dotnet build -m:1
3. dotnet test -m:1
