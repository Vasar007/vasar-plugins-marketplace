# Script results

Steps 6 and 7 and the light path use this file to write the flags of `scripts/trim_report.py` and to read its result. Run the script with `--help` for all flags.

- Examples of a usage error (exit code 2) are a bad flag, an unreadable path, an absolute `--glob` and a backup inside the workspace.
- A regex that matches nothing in the backup is a failure.
- The script converts CRLF to LF in both trees before it matches or compares.
- A glob is one relative pattern from the root of the tree. `*.md` matches only top-level files. `notes/*.md` matches only files in `notes/`. `**/*.md` matches files at any depth.
- A protected block is exactly the text that its regex matches. Text that you add after the match, such as an `Update:` line below the decision line, is not tested.
- For each approved tombstone, add `--allow-changed REGEX`. The script tests REGEX against the string `PATH:FIRST_LINE`. PATH is the relative path with forward slashes. FIRST_LINE is the first line of the protected block.
- To allow a block in one file, write the file in the regex, for example `'^notes/decisions\.md:## DEC-3\b'`. To allow it in any file, write `':## DEC-3\b'`.
- The script reports a matching block as ALLOWED. After the trim, the same file must still hold a line that matches REGEX. If not, the script reports WITHDRAWN, NO TOMBSTONE and fails. Do not end REGEX with `$`, so that it matches both the old heading and the tombstone heading.
- The script reports a block that it finds intact in another file as IN OTHER FILE. This does not fail. The reviewer finds out whether a plan names the move or the deduplication. The reviewer brief gives it the plan paths. If no plan names it, the reviewer reports it. On the light path, test each such line against your own cut list.
- If no file with the name of a deleted file survives, a reference to it is DANGLING. If another file has that name, the line is AMBIGUOUS. This passes, but you must look at each AMBIGUOUS line by hand. The name match ignores case.

## The subcommand `apply` (step 6)

- Exit code 0: the script applied the plan, and the checks pass. Exit code 1: it applied the plan, but a check failed. Read the check lines as for step 7, and fix each failure before the review.
- Exit code 2: a usage error, and no file changed. One example is a `--delete` path that is not a file of `orig`. Others are a `--glob` with `..` and a workspace that the script cannot read. If a `--delete` file does not match the glob, widen the glob, and repeat the dry run.
- Exit code 3: each `REFUSED` line names a file that the script cannot apply, and no file changed. If a workspace file changed after the plan, the planner of that batch plans again from the workspace of now. Two batches that change the same file give this case too. Do not restore such a file from the backup. The restore discards the change of the other batch or of the user. Before the new `apply` run, take a second backup of the workspace, as step 2 says. Pass it as `--before` of that run. After the last batch, run the report form against the first backup, as step 7 says. If a deletion has no `--delete`, the user did not approve it. Then the planner removes it from the plan and repeats the dry run. If the backup copy of a file differs from `orig`, stop and tell the user. If a name differs only by case, find the cause. If the plan renames that file or folder by case, the planner keeps the old name, and repeats the dry run. If not, the name changed in the workspace after the plan. Then the planner plans again from the workspace of now, with a second backup. A `REFUSED` line can name a link, a file in the place of a folder, or a path that is not a regular file. Then stop and tell the user.
- Exit code 4: a write failed, or a file changed after the test of the run. The `FAILED` line names the file or the folder. Fix the cause, and run the same command again. The script skips each file that is done, and prints a `DONE BEFORE` line for it.
- Exit code 1 with no `RESULT` line is a crash of the script. Read the traceback.
- A `KEPT` line names a `--delete` file that this batch keeps. If no other batch deletes it, the planner missed the deletion in `target`.
- A `CUT` line means that the output had more than 100 lines. After exit code 0 or 1, the report form with the same flags prints all the check lines and the whole size table. Run it before step 8. After exit code 3 with a failed plan check, run the report form on the copies of the planner. Set `--before` to the `orig` folder and `--after` to the `target` folder.
