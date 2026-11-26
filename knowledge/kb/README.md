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
- The environment variable `KB_DIR` with the full path of that clone. `/kb:setup` writes it into the `env` block of `~/.claude/settings.json`.

The launcher runs scripts only from the clone that `KB_DIR` names. It never looks for a clone in the project folder of the session. So no KB hook runs a script of another repository with `_claude/RULES.md`. A session inside the KB clone gets `KB_DIR` from `~/.claude/settings.json`, as every other session does.

If `KB_DIR` is not set, is not a full path, or names a folder with no `_claude/RULES.md`, the launcher finds no clone. Then the `SessionStart` hook prints one line, and every other hook exits with code 0. So a session without a KB clone is not broken.

## Setup

Run `/kb:setup` once on each machine. It runs `check.sh`, which changes nothing and prints the OS and one line for each missing piece. The pieces are these: the KB clone, `KB_DIR`, and the allow rules for `kb-search.sh` and for the KB text checks. Each of these three rules holds the full path of the clone, for example `Bash(bash <KB root>/_claude/tools/kb-search.sh *)`. A Bash rule matches the command text, so the rule matches only a call of the script in the clone. They also include the three `git -C <KB root>` allow rules (`status`, `log`, `show`) and the ask rule for `--output`. The rules of the KB clone must call the scripts with this full path. Else each call asks. Further pieces are the import lines and the "KB root" line in `~/.claude/CLAUDE.md`, the sync timer, and the git configuration. The skill shows each change and waits for the owner's yes. If `permissions.allow` still holds an old rule with a relative path, such as `Bash(bash _claude/tools/kb-search.sh *)`, `check.sh` prints a `STALE:` line. It reads five files of the clone. These files tell a session which command to run: `_claude/RULES.md`, `_claude/capture.md`, `_claude/close-task.md`, `_claude/hooks/session-start.sh`, and `_claude/hooks/subagent-start.sh`. It looks only for the relative call of the script of that rule. If no file has that call, the line ends with the words "Remove it", and the skill removes the rule after the owner's yes. If a file has it, the line ends with "Keep it for now:" and the path of the first such file. The skill then changes nothing. A call in any other file does not keep the rule. With no clone that `KB_DIR` names, the line ends with "Remove it" too.

## Limits

- A session that signs in with a token or an API key does not load synced plugins, so it runs no KB hook.
- If the KB clone has no `_claude/hooks/allow-read.sh` yet, `cd <KB root> && git ...` from a session outside the KB root asks. The plain rules then cover `git -C <KB root> ...` and the KB text checks with the full path of the clone.
- `check.sh` prints the path rules only for the clone that `KB_DIR` names. For another clone, it prints one `MISSING:` line that asks you to set `KB_DIR`.
- The three script rules need a clone path with only these characters: ASCII letters, digits, `.`, `_`, `/`, `:`, `~`, and `-`. A space or a `*` in the path changes what a Bash rule matches. For such a path, `check.sh` prints one `MISSING:` line and no script rule. Move the clone to another path.
- There is no plain allow rule for `git diff`. A plain rule also lets `git diff <file outside the KB> /dev/null` print any file with no prompt. The `allow-read` script of the KB clone handles `git diff`.
- Do not run these hooks and the same hooks from `~/.claude/settings.json` on one machine. Each hook then runs twice.
