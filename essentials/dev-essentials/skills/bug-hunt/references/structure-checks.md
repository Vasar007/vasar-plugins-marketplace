# Structure checks

The orchestrator runs these checks between steps. They test the form of the report and the files around it, not the truth of the findings. The script [../scripts/check_report.py](../scripts/check_report.py) runs them. It needs Python 3.12 or later and only its standard library. Run it with `python3 -I`, in the Bash tool on Windows.

Set these values first. `{SKILL_DIR}` is the folder of this skill.

```bash
C="{SKILL_DIR}/scripts/check_report.py"
R="<absolute path of the report file>"
D="<absolute path of the report folder>"
S="<absolute path of the scratch folder>"
P="<absolute path of the project repository>"
```

## Snapshot and cleanup commands

The script also does the fixed work of step 1 and step 6. Each command prints at most 40 lines, and the lines that need an action come first.

Step 1, before any other write into `$S`: `python3 -I "$C" snapshot --repo "$P" --ref-sha <full SHA> --scratch "$S" --base-from <local|remote|none>`. If the base is `none`, use `--base-from none`. For a local base, always add `--base-sha <full SHA of the base>`. A base that is the analyzed commit needs it too. For a remote base, add `--base-branch <branch>` and `--base-url <URL>`. If the user accepted the GitHub repository, the URL is `https://github.com/<owner/repo>.git`. Else take the URL from `git remote get-url origin`. Give the Bash call a timeout of 600000 ms, because a clone can take minutes.

Step 6: `python3 -I "$C" delete-temp --report-dir "$D" --scratch "$S" --repo "$P"`, with one `--pid "<pid>=<started>"` for each process that the session progress file records. Keep the quotes, because the start time holds spaces. Run it first as it is, then with `--apply` added. Give each of these Bash calls a timeout of 600000 ms, because the delete of a large scratch folder can take minutes. `$S` must be an absolute path. The session progress file can list paths under "Old scratch folders". Run both forms again for each of them, with that path in place of `$S`.

| Command | Exit code | What it means | What the orchestrator does |
| --- | --- | --- | --- |
| `snapshot` | 0 | The snapshots are ready, and the marker file `.bug-hunt-scratch` is in `$S` | Read the counts and the base SHA in the `SNAPSHOT:` lines. Copy each `LIMIT:` line and each `WARN:` line into the Scope section |
| `snapshot` | 1 | A git command or the extraction failed. An `ERROR:` line names it | Stop step 1, keep the files, and report the line under "Blocked on me" |
| `snapshot` | 2 | A `REFUSED:` line names each reason, and nothing changed | If a reason names Python, stop the run and report the reason under "Blocked on me". Never export the snapshots by hand, and never delete by hand. Else fix the input. If `$S` holds files of another source, pick a new scratch folder as step 0 item 2 of [inputs-and-meta-plan.md](inputs-and-meta-plan.md) says, and run the command again |
| `delete-temp` without `--apply` | 0 | `WOULD STOP:`, `WOULD DELETE:`, and `NOT FOUND:` lines name the plan | Make sure that it names only the folder of `--scratch` and the progress files. Then run it with `--apply` |
| `delete-temp --apply` | 0 | The cleanup is done. `NOT FOUND:` for `$S` after a resume also means done | Name each `NOT STOPPED:` line in the final report |
| `delete-temp --apply` | 1 | A `FAILED:` or `DEFECT:` line names what is left | If the cause is gone, for example a process that held a file is no longer running, run the command with `--apply` one more time. Else, or after a second exit code 1, report the lines under "Blocked on me". Do not delete anything by hand |
| `delete-temp`, with or without `--apply` | 2 | A `REFUSED:` line names a guard, and nothing changed | Report the reason under "Blocked on me". Never run the command again with another path, and never delete by hand |
| `snapshot` or `delete-temp` | 2, with an `error:` line and no `REFUSED:` line | A usage error: an option or a value is wrong | Correct the options as this file writes them. Then run the command again with the same paths |
| `snapshot` or `delete-temp` | None, because the Bash tool ended the call | The script did not finish, for example after a clone that hangs on Windows | For `snapshot`, act as for exit code 1. For `delete-temp`, run the dry run again, and act on its lines as for exit code 1 |

The guards of `delete-temp` refuse a scratch folder that `snapshot` did not make. They refuse a top entry of `$S` with a name that a run does not make. They refuse a git folder whose work tree is outside `$S`. They also refuse a link, a drive root, the home folder, the temp root, the report folder, and each folder of the project. So each agent keeps its clones and work files inside its work folder.

Each output line starts with one word:

- `DEFECT:` a structure error. The check fails, and the exit code is 1.
- `WARN:` a fact to record, for example files left in a work folder, or a process that still uses the scratch folder. The check does not fail.
- `INFO:` the counts: findings, next free ID, verdicts, pending entries, artifact folders, and open notes. Compare them with the reply of the agent.

## Command for each step

| After | Command |
| --- | --- |
| Step 1 | `python3 -I "$C" setup --report-dir "$D" --scratch "$S" --base yes` |
| Step 2 | `python3 -I "$C" report --report "$R" --scratch "$S" --areas-done 0 --stage search` |
| Hunter of area K | `python3 -I "$C" report --report "$R" --scratch "$S" --areas-done K --stage search --snapshot "$S/snapshot-ref"` |
| Verifier part that ends at `BH-N` | `python3 -I "$C" report --report "$R" --scratch "$S" --areas-done <number of areas> --stage verify --verified-to N --snapshot "$S/snapshot-ref"`, with the number only (`--verified-to 20` for `BH-20`) |
| Last verifier part | The same command with `--stage summary` |
| Step 5 | The same command with `--stage final` |
| Step 6 | `delete-temp --apply` runs it. To run it alone: `python3 -I "$C" cleanup --report-dir "$D" --scratch "$S"` |

If the command prints no `DEFECT` line and the `INFO` counts match the reply, the step passes.

- If no base snapshot exists, use `--base no` at step 1. These cases give no base snapshot: the analyzed commit is the base, or the base is `none`.
- If the base is `none`, add `--base no` to the `report` commands. Then no entry has the field "Also on base".
- If a base snapshot exists, add `--base-snapshot "$S/snapshot-base"` to each command with `--snapshot`. Then each location of "Also on base: Yes" must name a file and a line of the base snapshot.
- If `--snapshot` or `--base-snapshot` names no folder, the command ends with exit code 2 and tests nothing. Fix the path, and run the command again.
- During a resume, the progress file of the agent that `## NEXT` names can exist. Add `--allow <file name>` for it.
- If there are no findings, skip the verifier commands. The auditor writes the Summary.

More commands:

- Next free ID: `python3 -I "$C" next-id --report "$R"`. It prints for example `BH-08`.
- Open notes: `python3 -I "$C" open-notes --report "$R"`. It prints each note under "Notes for other areas" that names an area with the same or a lower number and has no `Result:`. The hunter of that area had already finished before the note was written.

## What the `report` command tests

- The title line, and the H2 sections in this order: Scope, Summary, Known issues, one section for each area, and the appendix.
- The areas up to `--areas-done` are filled and have both subsections. The later areas still say "Pending search.". The Known issues section is filled after the first search.
- The IDs are unique, have at least two digits, and have no gaps.
- Each entry has the required fields with their exact labels, and legal Severity, Confidence, and Verdict values. A changed value has the form `Medium (was High)`.
- Up to `--verified-to`, or for all entries at the stages `summary` and `final`: no pending verdict and a `Verification:` paragraph.
- Rejected entries are in the appendix, and only they are. Each Unconfirmed entry has the lines "Not covered:", "Where I looked:", and "To decide:".
- At the stages `summary` and `final`: the Summary count line matches the entries, and the table has one row for each ID, in ID order, with the title of the heading.
- At the stages `summary` and `final`: each row has the severity, confidence, verdict, and "Also on base" answer of its entry. The area column can differ.
- Each `Duplicate of BH-NN` names an earlier entry. Each `BH-NN` of a verdict, of a `Result:` note, and of the list "For the owner's review" names an entry. Each `N-NN` of a `Duplicate of` verdict or of a "New details for" line is in the Known issues section. Each `#NN` of these places is in the digest.
- With `--snapshot`: each location names a file of the snapshot and a line inside it. A path out of the snapshot is a defect, and the script does not read it.
- At the stage `final`: the subsection "For the owner's review" exists, no placeholder is left, and no open note is left. An appendix with entries has no "None yet." line.
- The command prints at most 100 DEFECT lines and then one line with the count of the rest.
- No control character in the report. Every artifact link resolves. Every artifact folder has a `repro.md` and belongs to an entry. No `bin` or `obj` folder, no binary file, no file over 1 MB, and no scratch folder path in the artifacts.
- No progress file is left in the report folder except `_bug-hunt-session-progress.md` and the `--allow` names.
- WARN lines for files left in work folders and for processes whose command line holds the scratch path.

## Leftover processes

A WARN line names each process whose command line holds the scratch path, with `pid=` and `started=`. The scan skips the check itself and the processes that started it. Write the process ID and the start time into the session progress file. Step 6 passes them to `delete-temp` as `--pid "<pid>=<started>"`. The script tests each process again before it stops it.
