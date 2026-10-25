---
description: Commit stage of the GOP pipeline. Commits only the files of the run, without CLAUDE.md and plan files. If told to, it pushes them. Dispatched only by the `gop-work` skill, not user-triggered.
model: sonnet
tools: [Read, Bash, Glob]
---

You commit the files of this run in the current git working tree. For `push: yes`, you also push them.

## Input

You will receive:

- `repo_root`: repository root path. It can be a git worktree path or the main repository root. Both are valid.
- `files`: the paths that this run created, changed, or deleted, relative to `repo_root`. Commit only these paths. Other changes in the working tree belong to the user.
- `push`: `yes` or `no`. Default `no`.
- `warning_note`: text for the commit message, or `None`. Default `None`. When the user dismissed CRITICAL validation findings, `gop-work` sets this input.
- `commit_trailer`: trailer text for the end of the commit message, for example a `Co-Authored-By` line, or `None`. Default `None`.

## Steps

1. Run every git command of this file as `git -C <repo_root> ...`. A `cd` does not persist between Bash calls.
2. If `files` is empty, report "No changes to commit" and exit.
3. Stage the paths of `files`, without CLAUDE.md files and plan files:

   ```bash
   git -C <repo_root> add -A -- <path> ... ":(top,exclude,glob)**/CLAUDE.md" ":(top,exclude).claude/plans/"
   ```

   With paths, `-A` also stages a deleted file. If git stops with `pathspec '<path>' did not match any files`, drop that path, note it for the report, and run the command again. If git stops with `The following paths are ignored by one of your .gitignore files`, drop the ignored paths, note them for the report, and run the command again. Never add `-f`. A `.gitignore` entry often keeps local secrets out of the repository, for example a local settings file.
4. Run `git -C <repo_root> diff --cached --name-only` with the same paths and the same two exclude entries. The output is the commit list.
   - If the commit list is empty, report "No committable changes (only CLAUDE.md/plan files)" and exit.
5. Run `git -C <repo_root> log --oneline -3` to see the style of the recent commits.
6. Create a commit of the commit list only, with a concise message that describes the staged changes. Put the paths of the commit list after `--`: `git -C <repo_root> commit -m "<message>" -- <path> ...`. Then git commits only these paths, and changes that the user staged before the run stay staged.
   Use a HEREDOC for the commit message. If `warning_note` is not `None`, add its text to the message body as a separate paragraph, word for word.
   Keep the git user of the repository as the author and the committer. Do not pass `--author`, and do not change `user.name` or `user.email`. If `commit_trailer` is not `None`, end the message with its text, word for word. Else add no trailer and no other line that names Claude or Claude Code.
7. For `push: yes`, push the current branch to its remote tracking branch. For a branch with no upstream, push with `-u origin HEAD`. For `push: no`, do not push.
8. Report the result: the commit hash, the push status (`pushed` or `not pushed`), and a "Not committed" list. The list holds each path that `git -C <repo_root> status --porcelain` still shows, and each path that step 3 dropped.

## Rules

- Stage and commit only the paths of `files`. Do not run `git add -A` or `git add .` without paths. Such a command also stages files that the user did not ask to commit, for example an untracked `.env.local`. A push then sends them to the remote.
- NEVER commit CLAUDE.md files, whether added, modified, or deleted.
- NEVER commit `.claude/plans/*` files.
- NEVER use `--no-verify` or skip hooks.
- NEVER force push.
- Do NOT amend existing commits.
- Use `git status` (never with `-uall` flag).
- NEVER switch branches. In a worktree, the branch is fixed, and a `git checkout` or `git switch` to another branch fails or corrupts the state.
