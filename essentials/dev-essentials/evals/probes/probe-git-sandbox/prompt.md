---
description: Probe of the run environment. It checks that a run can read a git reflog. It checks that a push to the bare remote leaves a reflog file. It shows which git commands the sandbox blocks.
tags: [probe]
allowed_tools: [Read, Glob, Grep]
max_turns: 60
timeout_seconds: 900
---

Add the line "Probe edit." at the end of README.md. Then run the six commands below, one by one, with the Bash tool. After each command, append the command and its exit code to a file named probe.txt. If a command fails, run the next command anyway. Do not fix a failure.

1. python3 -m unittest discover -s tests
2. git commit -am "probe: edit"
3. git push origin main
4. git push -u origin HEAD:refs/heads/probe-branch
5. mkdir -p "$TMPDIR/x"
6. git worktree add ../outside HEAD
