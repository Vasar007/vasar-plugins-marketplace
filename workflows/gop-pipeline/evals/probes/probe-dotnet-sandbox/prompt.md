---
description: Probe of the run environment. It checks that dotnet builds and tests the fixture in the sandbox, and that the test run leaves its marker files.
tags: [probe]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Read, Glob, Grep]
max_turns: 40
timeout_seconds: 900
---

Run "dotnet build" and then "dotnet test" in the repo root, with the Bash tool. Write the last 5 lines of the output of each command to a file named probe.txt. If the first command fails, run the second command anyway. Do not fix a failure.
