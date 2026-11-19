# Report format

When they write or review findings, the hunters, verifiers, and auditor follow this file. The hunters write the findings. The verifiers set the verdicts. The auditor makes sure that the whole file is consistent. The report skeleton is in [report-skeleton.md](report-skeleton.md). The orchestrator uses it.

## Contents

- Known issues section
- Area section
- Finding entry
- Verdicts
- Summary section
- Artifacts
- Words

## Known issues section

The first hunter replaces "Pending the first search." with a list from the known-issues
digest. One line for each known issue:

```markdown
- #12: <title>. Source: open issue with the label "bug".
- #31: <title>. Source: open issue with the label "chore".
- N-01: <short title>. Source: notes file `known-bugs.md`.
```

The section lists only the known bugs. These are the notes-file bugs and the open issues with
the bug label. They also include the other open issues that describe a problem in the
analyzed areas, for example a chore or an infrastructure issue. The list of all issue titles in the digest is only for
duplicate checks. Do not copy it into the report. Each notes-file bug keeps the ID `N-NN`
that the digest gives it.

If no known issue exists, write "None found in the given sources."

## Area section

Each hunter replaces "Pending search." in its own section with this layout:

```markdown
## Area 3: <name>

Files: <paths>. Out of scope: <paths or topics>.

### New details for known issues

- New details for #12: <new facts, with locations>.
- New details for N-01: <new facts, with locations>.

### BH-07: <title>

<finding entry>

### Notes for other areas

- For Area 4 (<name>): `path/to/file.ext:120`: <what to look at, and why>.
```

If the hunter has nothing for a subsection, it writes "None." under the heading. The two
subsections "New details for known issues" and "Notes for other areas" must always exist.

A hunter follows a lead for an area that was already searched itself (hunter rule, Method
step 10). A note for such an area that is still open after the last hunter is an open note.
A verifier follows it and then adds a space and `Result: <BH-NN, New details for BH-NN, or no bug, with the reason>.`
at the end of the note line.

## Finding entry

```markdown
### BH-07: <short title that names the wrong behavior>

- Severity: High
- Confidence: Medium
- Category: Wrong result
- Location: `src/orders/export.ext:142`
- Also on base: Yes, `src/orders/export.ext:139`
- Verdict: Pending verification
- Artifacts: [bug-hunt-artifacts/BH-07/repro.md](bug-hunt-artifacts/BH-07/repro.md)

Problem: <what the code does wrong, in two to four sentences>

Failure scenario: <the input or state, then the wrong result>

Evidence: <code facts with locations. Start each part that is not confirmed with "Not confirmed:" and say where you looked.>

Fix idea: <one short direction, not a patch>
```

Field rules:

- Labels: write each label exactly as in the example, at the start of the line, followed by a colon. The text can start on the same line or in the next paragraph. Put tags after the colon. Write "Failure scenario: with an empty file, ...", not "Failure scenario, empty file: ...". The structure check finds a field only by its exact label. Severity, Confidence, and Verdict take their value on the same line.
- ID: `BH-` and a number with at least two digits (`BH-01`, `BH-12`, `BH-105`). Numbers continue across areas. Never reuse or renumber an ID.
- Severity: one of the values below. Rate each finding on its own. Assume that the other findings are fixed. If another finding hides its effect today, say so in the Verification paragraph, and do not lower the severity for that reason.
  - Critical: data loss, a security hole, or a crash in a main path, with no workaround. Examples: a save cuts a file and reports no error. Any user can read the data of another user.
  - High: a wrong result or a crash in a common path. Examples: an export writes wrong totals for every order with a discount. The app crashes at a common dialog.
  - Medium: a wrong result in a less common path, or a problem with a workaround. Examples: a rare option gives a wrong result. A crash in a rare path that a second try avoids.
  - Low: a small wrong behavior with a small effect. Examples: a wrong message text. A wrong value in a log line.
  - Edge case: if a wrong result changes data or output that the user keeps or uses, rate it Medium. If it changes only a message, a log line, or a display detail, rate it Low.
- Confidence: High (the failure was shown, or the code path is proved), Medium (strong evidence, not shown), or Low (possible, the owner must look).
- Category: one of these values: `Crash`, `Wrong result`, `Data loss`, `Security`, `Concurrency`, `Resource leak`, `Error handling`, `Performance`, `Compatibility`, `Build or packaging`, or `Install or upgrade`. For another kind of bug, write `Other` and a name.
- Location: `path:line`, relative to the snapshot root. More than one location is allowed, separated by commas.
- Also on base: `Yes, <location in the base snapshot>`, `No (new in the analyzed commit)`, `Not compared (<reason>)`, or `Not applicable (the analyzed commit is the base)`. If the run has no base (`--base=none`), leave out this field.
- Verdict: the hunter writes "Pending verification". The verifier sets the final value.
- Artifacts: write this line only for an artifact folder that exists. If there is no artifact, leave out the line.
- Failure scenario: if the agent cannot show the failure, write `Failure scenario: Not shown: <reason>`.

## Verdicts

The verifier sets exactly one verdict for each finding:

| Verdict | When | What happens to the entry |
| --- | --- | --- |
| `Confirmed` | The evidence holds, and the failure scenario is shown or proved from the code. | It stays in its area section. |
| `Unconfirmed (needs owner review)` | The verifier did not refute it and did not prove it. | It stays in its area section. The Verification paragraph has the lines below. |
| `Rejected` | The finding is wrong, or it is not a real behavior bug. | It moves, whole and with its ID, to "Appendix: rejected findings". The first entry that moves there replaces "None yet.". No stub stays in the area section. |
| `Duplicate of #NN`, `Duplicate of N-NN`, or `Duplicate of BH-NN` | A GitHub issue (`#NN`), a notes-file bug (`N-NN`), or an earlier entry (`BH-NN`) describes the same bug. | It stays in its area section. The Verification paragraph names the original. |

If the verifier changes the severity or the confidence, it shows the old value next to the
new one: `- Severity: Medium (was High)`.

Each verifier adds a Verification paragraph after "Fix idea":

```markdown
Verification: <what the verifier did, what it found, and why it chose the verdict>
```

For an Unconfirmed finding, the lines below follow the Verification paragraph, each as its
own paragraph:

```markdown
Not covered: <what the verifier did not test or read, and why>

Where I looked: <files, commands, and documents that the verifier used>

To decide: <what the owner must do to decide>
```

## Summary section

The last verifier part replaces "Pending verification." under `## Summary`. If there are no
findings, the auditor writes it.

```markdown
## Summary

Findings: 23. Confirmed: 12. Unconfirmed (needs owner review): 5. Rejected: 4. Duplicate: 2.

| ID | Title | Area | Severity | Confidence | Verdict | Also on base |
| --- | --- | --- | --- | --- | --- | --- |
| BH-01 | <title> | Area 1 | High | High | Confirmed | Yes |
```

The table has one row for each finding, rejected ones included, in ID order. The counts must
add up to the number of findings. If there are no findings, write "Findings: 0." and no table.
If the run has no base, leave out the column "Also on base".

- Title: copy the title of the heading exactly. If a title must change, change the heading and the row together.
- Area: the area that the code belongs to. It can differ from the section that holds the entry.

The auditor ends the Summary with this subsection. It lists each Unconfirmed finding with the
short form of its "To decide:" line, and each other point that needs a decision of the owner.
If there is nothing, it writes "None.".

```markdown
### For the owner's review

- BH-04: <title>. To decide: <short form of the To decide line>.
```

## Artifacts

A hunter or a verifier copies only the repro files that matter to
`bug-hunt-artifacts/BH-NN/`. Do not copy secrets or personal data. Follow these rules:

- `repro.md` names only files that are in the artifact folder. Write each path relative to a copy of the repository, not to the scratch folder or to a work folder.
- Keep recorded output short, for example the first 40 lines and the last 10 lines. No file can be larger than 1 MB. Do not copy build output (`bin`, `obj`) or binary files.
- When you copy captured output, replace each scratch folder path with `<scratch>`.
- A repro must not depend on a fixed date or time. Use the current time, or a clock that the test controls.

Each folder has a `repro.md`:

```markdown
# Repro for BH-07

- Snapshot commit: <REF_SHA>
- Environment: <operating system and tool versions that the repro used>

## Steps

1. <step>

## Expected result

<what the correct code does>

## Actual result

<what the code does>

## Files in this folder

- `<file>`: <what it is>

## Not confirmed

<what this repro does not prove, or "Nothing">
```

## Words

In report text, use `confirm` and `make sure that`. Do not use `check`, `verify`,
`validate`, or `ensure`. The verdicts and the marker "Not confirmed:" already use `confirm`.

If the simple-english plugin is installed, its lint hook lints the whole file after each
Markdown edit. A hunter or a verifier fixes only the hits in its own lines, and lists the
hits in other sections in its reply. The auditor fixes all hits. The hook reports these
patterns:

- A mix of `check`, `checklist`, `verify`, `validate`, `ensure`, and `confirm` in one file.
- An "if" or "when" clause after the main clause.
- The words `should`, `would`, `may`, `might`, and `could`.
- A quote that ends with a period inside the quote marks. The hook reads it as the end of a
  sentence.

An edit by a script skips the hook, so read the result back.
