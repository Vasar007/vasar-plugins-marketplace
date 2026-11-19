# No Worktree: Work in the Folder of the User

These are the steps of the option `--no-worktree` of `implement-task` and `implement-batch`. With this option, the run works in the folder of the user. These steps keep the work of the user there safe.

Do the steps in their order, before any other step of the worktree setup. "The workflow file" is the file of the workflow that sent you here. It names the base branch.

## Steps

Record the path that `git rev-parse --show-toplevel` prints as the worktree path, and use it wherever the workflow file names the worktree. Then run `git -C "<worktree>" status --porcelain --untracked-files=no`. If it prints a line, stop before any work, in every mode. Name each changed file, and ask the user to commit or stash it (hard stop 1 of `dev-essentials:work-modes`). Else a change in a file of a task goes into the task commit. Then record the output of `git -C "<worktree>" ls-files --others --exclude-standard`. Each file in it is a file of the user with no other copy. Never write, stage, or delete one of them. A build or a test run of a task can still rewrite its own output in this list. An example is a compiled file that `.gitignore` does not name. If a task needs one, ask the user first (hard stop 1 of `dev-essentials:work-modes`). Find the default branch with `git -C "<worktree>" symbolic-ref --quiet --short refs/remotes/origin/HEAD`, and take the name after `origin/`. If the ref does not exist, take the name from the `ref: refs/heads/<name>` line of `git -C "<worktree>" ls-remote --symref origin HEAD`. If that also gives no name, treat `main` or `master` as the default branch. Then run `git -C "<worktree>" branch --show-current`:

- If it prints the default branch, the base branch, or nothing (a detached HEAD), do not commit there. Do what the `--no-worktree` row of "Autonomy" in the workflow file says. If the user says yes to work on that branch, make local commits only, and do no step of `finish.md`. For a new branch, run `git -C "<worktree>" switch -c <branch>`. If a branch of that name exists, ask the user (hard stop 6 of `dev-essentials:work-modes`).
- If it prints another branch, work on that branch, and create no branch. If the request names another branch ref, ask the user first (hard stop 6 of `dev-essentials:work-modes`).

Then, unless the user said yes to work on the current branch, run `git -C "<worktree>" rev-list --count origin/<base>..HEAD`, with the base branch. If it fails, or prints more than 0, the pull request can take commits that no review loop of this run covers. Outside the full mode, list the commits or the error, and ask the user (hard stop 6 of `dev-essentials:work-modes`). In the full mode, go on. List the commits or the error in the final report as the reason that the run does no step of `finish.md`.

Then go on with the worktree setup of the workflow file.
