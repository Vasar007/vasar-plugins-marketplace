# Structure checks

The orchestrator runs these checks between steps. They test the form of the report and the files around it, not the truth of the findings. The script [../scripts/check_report.py](../scripts/check_report.py) runs them. It needs Python 3 and only its standard library. Run it with `python3 -I`, in the Bash tool on Windows.

Set these values first. `{SKILL_DIR}` is the folder of this skill.

```bash
C="{SKILL_DIR}/scripts/check_report.py"
R="<absolute path of the report file>"
D="<absolute path of the report folder>"
S="<absolute path of the scratch folder>"
```

Each output line starts with one word:

- `DEFECT:` a structure error. The check fails, and the exit code is 1.
- `WARN:` a fact to record, for example files left in a work folder, or a process that still uses the scratch folder. The check does not fail.
- `INFO:` the counts: findings, next free ID, verdicts, pending entries, artifact folders, and open notes. Compare them with the reply of the agent.

## Command for each step

| After | Command |
| --- | --- |
| Step 1 | `python3 -I "$C" setup --report-dir "$D" --scratch "$S" --base yes` |
| Step 2 | `python3 -I "$C" report --report "$R" --scratch "$S" --areas-done 0 --stage search` |
| Hunter of area K | `python3 -I "$C" report --report "$R" --scratch "$S" --areas-done K --stage search` |
| Verifier part that ends at `BH-N` | `python3 -I "$C" report --report "$R" --scratch "$S" --areas-done <number of areas> --stage verify --verified-to N`, with the number only (`--verified-to 20` for `BH-20`) |
| Last verifier part | The same command with `--stage summary` |
| Step 5 | The same command with `--stage final` |
| Step 6 | `python3 -I "$C" cleanup --report-dir "$D" --scratch "$S"` |

If the command prints no `DEFECT` line and the `INFO` counts match the reply, the step passes.

- If no base snapshot exists, use `--base no` at step 1. These cases give no base snapshot: the analyzed commit is the base, or the base is `none`.
- If the base is `none`, add `--base no` to the `report` commands. Then no entry has the field "Also on base".
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
- At the stage `final`: the subsection "For the owner's review" exists, no placeholder is left, and no open note is left.
- No control character in the report. Every artifact link resolves. Every artifact folder has a `repro.md` and belongs to an entry. No `bin` or `obj` folder, no binary file, no file over 1 MB, and no scratch folder path in the artifacts.
- No progress file is left in the report folder except `_bug-hunt-session-progress.md` and the `--allow` names.
- WARN lines for files left in work folders and for processes whose command line holds the scratch path.

## Leftover processes

A WARN line names each process whose command line holds the scratch path, with `pid=` and `started=`. The scan skips the check itself and the processes that started it. Write the process ID and the start time into the session progress file. Step 6 passes them to the cleanup helper, which tests each process again before it stops it.
