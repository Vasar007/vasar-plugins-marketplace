---
name: setup
description: Set up the KB wiring on this machine once. The owner approves each change.
disable-model-invocation: true
---

This skill needs Bash (Git Bash on Windows) and git.

1. Run `bash "${CLAUDE_PLUGIN_ROOT}/skills/setup/check.sh"`. It changes nothing. It prints the OS, one `MISSING:` line for each missing piece, and one `STALE:` line for each old rule with a relative path.
2. For each `MISSING:` or `STALE:` line, show the exact change: a diff for a file, or the command for a timer or for git. Wait for the owner's yes before each change.
   - Write each rule exactly as `check.sh` prints it, in `permissions.allow` or `permissions.ask` of `~/.claude/settings.json`.
   - For a `STALE:` line, an older version of this skill wrote that rule with a relative path. It also matches a script with the same path in another project. To find out how the KB rules call the scripts, run `grep -rlF -e 'bash _claude/tools/' -e 'python3 -B _claude/tools/' <KB root>/_claude`. If it finds no file, remove that rule from `permissions.allow`. If it finds a file, keep the rule, tell the owner why, and remove nothing. Each KB search asks without it.
   - For the `MISSING: allow rules: the clone path` line, change no file and show no change. Tell the owner that a move of the clone also changes `KB_DIR`, `~/.claude/CLAUDE.md`, and the sync timer.
   - Never add a rule for a git command that changes the KB, such as `git add`, `commit`, `push`, `reset`, or `checkout`.
   - Write `KB_DIR` in the `env` block of `~/.claude/settings.json` as the full path of the KB clone. Without it, no hook runs a KB script, also in a session inside the clone.
3. If the KB clone is missing, clone it first, because the other pieces name its path.
4. On Windows, write paths in the `C:/...` form, and run the timer step in PowerShell.
5. At the end, run `check.sh` again and print its result. If `check.sh` prints no `MISSING:` line and no `STALE:` line, the setup is done.
