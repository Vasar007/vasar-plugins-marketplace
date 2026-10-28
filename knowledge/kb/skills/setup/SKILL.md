---
name: setup
description: Set up the KB wiring on this machine once. The owner approves each change.
disable-model-invocation: true
---

This skill needs Bash (Git Bash on Windows) and git.

1. Run `bash "${CLAUDE_PLUGIN_ROOT}/skills/setup/check.sh"`. It changes nothing. It prints the OS and one line for each missing piece.
2. For each missing piece, show the exact change: a diff for a file, or the command for a timer or for git. Wait for the owner's yes before each change.
3. If the KB clone is missing, clone it first. The other pieces name its path.
4. On Windows, write paths in the `C:/...` form, and run the timer step in PowerShell.
5. At the end, run `check.sh` again and print its result. If `check.sh` prints no `MISSING:` line, the setup is done.
