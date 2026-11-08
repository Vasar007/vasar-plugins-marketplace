# kb

This plugin wires Claude Code to a personal knowledge base (KB). The KB is a private git repository of Markdown notes. The plugin needs a local clone of that repository. It holds no notes and no hook logic itself. The hook scripts and the procedures stay in the KB, in its `_claude/` folder.

## What it does

The plugin adds the hooks in `hooks/hooks.json`. Each hook calls the launcher `scripts/kb-hook.sh`, and the launcher runs the script of the same name from the KB clone.

| Hook event | What the KB script does |
|---|---|
| `SessionStart` | Syncs the KB, then prints the KB root and the index lines. |
| `SubagentStart` | Gives each subagent the KB root and the core rule. |
| `PreToolUse` (`Edit`, `Write`, `NotebookEdit`) | Guards note writes. It blocks notes outside the KB, and blocks two sessions that edit one KB folder. |
| `PreToolUse` (`Bash`) | Approves the KB text checks and read-only git in the KB, so they run with no prompt. It never blocks a call. |
| `Stop` | If a file changed, syncs the KB after a turn. |
| `SessionEnd` | Removes the folder claims of the session. |

The plugin also adds the skills in `skills/`:

- `capture` reads `_claude/capture.md` in the KB and writes a solved problem, a lesson, or an owner rule into the KB.
- `close-task` reads `_claude/close-task.md` in the KB and closes the task folder of a merged pull request.
- `setup` runs `skills/setup/check.sh` and helps the owner to fix each missing piece. Claude does not start it by itself. Type `/kb:setup` to start it.

## Install

After you add the marketplace, run:

```text
/plugin install kb@vasar-plugins-marketplace
```

## Requirements

- Bash. On Windows, use Git Bash.
- A local clone of the KB repository. It must hold the file `_claude/RULES.md`.

The launcher looks for the clone in this order:

1. The folder in the environment variable `KB_DIR`.
2. The project folder of the session, or one of its child folders.

If the launcher finds no clone, the `SessionStart` hook prints one line and every other hook exits with code 0. So a session without a KB clone is not broken.

## Setup

Run `/kb:setup` once on each machine. It runs `check.sh`, which changes nothing and prints the OS and one line for each missing piece. The pieces are these: the KB clone, `KB_DIR`, and the allow rules for `kb-search.sh` and for the KB text checks. They also include the three `git -C <KB root>` allow rules (`status`, `log`, `show`) and the ask rule for `--output`. Further pieces are the import lines and the "KB root" line in `~/.claude/CLAUDE.md`, the sync timer, and the git configuration. The skill shows each change and waits for the owner's yes.

## Limits

- A session that signs in with a token or an API key does not load synced plugins, so it runs no KB hook.
- If the KB clone has no `_claude/hooks/allow-read.sh` yet, `cd <KB root> && git ...` from a session outside the KB root asks. The plain rules then cover `git -C <KB root> ...` and the checks in the KB root.
- There is no plain allow rule for `git diff`. A plain rule also lets `git diff <file outside the KB> /dev/null` print any file with no prompt. The `allow-read` script of the KB clone handles `git diff`.
- Do not run these hooks and the same hooks from `~/.claude/settings.json` on one machine. Each hook then runs twice.
