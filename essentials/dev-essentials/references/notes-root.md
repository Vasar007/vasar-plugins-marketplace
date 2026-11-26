# Notes folder

The skills and commands of `dev-essentials` keep the working files of a task in one notes folder. These files are plans, research files, reports, reviews, drafts, and the `_`-prefixed progress files. This file says which folder is the notes folder.

## Find the notes folder

Find the notes folder before the first read or write in it, and use the same folder for the whole run. The folder belongs to the branch of the task. That is the current branch, unless the skill or the command names another branch, for example the head branch of a pull request.

Take the first item of this list that gives a folder:

1. The request. The user can name a folder for the notes, the plans, or the reports of the task. The user names it in words or with an option, for example `--notes-dir` of `implement-task`. A folder for one kind of file only, for example `--plan-dir` of `implement-batch`, holds that kind only.
2. The `CLAUDE.md` file of the repository. It can name a folder for notes. A folder that it names for one kind of file only, for example plans or reports, holds that kind only. The other files take the next items of this list.
3. A KB clone. A knowledge base (KB) clone is a local git clone of a set of notes about many repositories. The test for a KB clone has two parts: the variable `KB_DIR` holds a full path, and that folder holds `_claude/RULES.md`. This command prints the folder of the clone, or nothing:

   ```bash
   case "${KB_DIR-}" in /*|[A-Za-z]:[\\/]*) [ -f "$KB_DIR/_claude/RULES.md" ] && printf '%s\n' "$KB_DIR" ;; esac
   ```

   If the command prints a folder, read the section "Where notes go" of `_claude/RULES.md` in that folder, and do what it says. It gives the task folder of the branch, and it says how to make a task folder that does not exist. The task folder is the notes folder. In that section, a path `Notes/<X>` means `<X>` in the task folder.
4. The fallback: `~/claude-notes/<repo>/<branch>/` in the home folder of the user.
   - `<repo>` is the last part of the URL of the `origin` remote, without `.git`. The command `git remote get-url origin` prints the URL. With no `origin` remote, `<repo>` is the name of the folder of the main worktree. That folder is the first path that `git worktree list` prints.
   - `<branch>` is the name of the branch, with each `/` replaced by `-`. In a detached HEAD, it is the short ID of the commit.

## Use the notes folder

- Each skill and command keeps its own subfolders in the notes folder. Examples are `Plans/`, `Results/`, `Reviews/`, `PRs/`, `Tasks/`, and `Docs/`. So `Plans/<slug>-plan.md` in the notes folder is the file `<notes folder>/Plans/<slug>-plan.md`.
- Write a notes file with the `Write` tool. The tool makes the folders of the path, so you need no `mkdir` command.
- Never commit a notes file. If the notes folder is inside the repository and git does not ignore it, stage explicit paths only.
- The folders of items 3 and 4 are outside the repository. So no commit can take their files, and the removal of a worktree keeps them.
- Claude Code asks before a write outside the working folders of the session. To allow the writes to the fallback folder, the user can add `~/claude-notes` to the working folders, for example with `/add-dir`. An unattended run cannot wait for that answer. So the user adds the folder before a workflow starts, with `/add-dir` or with `permissions.additionalDirectories` in the configuration file.
