# Report format

Every agent that writes to the report follows this file. The orchestrator writes the skeleton.
The hunters write the findings. The verifiers set the verdicts. The auditor makes sure that
the whole file is consistent.

## Files in the report folder

```text
<report folder>/
├── bug-hunt-report.md            (or the report file name from the meta-plan)
└── bug-hunt-artifacts/
    └── BH-07/
        ├── repro.md
        └── <repro files>
```

During the run, the progress files also sit in the report folder. Step 6 deletes them.

## Skeleton

The orchestrator writes this skeleton in step 2. It fills every `{...}` value.

```markdown
# Bug hunt report: {PROJECT}

## Scope

- Project: {PROJECT}. GitHub repository: {GITHUB or "none"}.
- Analyzed code: {REF} at commit {REF_SHA}.
- Base branch for "Also on base": {BASE} at commit {BASE_SHA}.
- Date: {DATE}.
- Role of the author: {ROLE}.
- Areas: {AREA_LIST}.
- Excluded paths: {EXCLUDED}.
- Known-issue sources: {KNOWN_SOURCES}.
- Method: one hunter agent for each area ({HUNTER_MODEL}, effort {HUNTER_EFFORT}), one after the other. Verifier agents ({VERIFIER_MODEL}, effort {VERIFIER_EFFORT}) tried to refute each finding. One auditor agent ({AUDITOR_MODEL}, effort {AUDITOR_EFFORT}) made sure that the report is consistent.
- Limits: {LIMITS}.
- Every location refers to commit {REF_SHA}.
- No GitHub issues were created.

## Summary

Pending verification.

## Known issues that this report does not repeat

Pending the first search.

## Area 1: {AREA_1_NAME}

Pending search.

## Area 2: {AREA_2_NAME}

Pending search.

## Appendix: rejected findings

None yet.
```

Write one `## Area N: <name>` section for each area. If the setup helper reported no limits,
write "None found" for `{LIMITS}`.

## Known issues section

The first hunter replaces "Pending the first search." with a list from the known-issues
digest. One line for each known issue:

```markdown
- #12: <title>. Source: open issue with the label "bug".
- N-01: <short title>. Source: notes file `known-bugs.md`.
```

The section lists only the known bugs: the notes-file bugs and the open issues with the bug
label. The list of all issue titles in the digest is only for duplicate checks. Do not copy it
into the report. Each notes-file bug keeps the ID `N-NN` that the digest gives it.

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

## Finding entry

```markdown
### BH-07: <short title that names the wrong behavior>

- Severity: High
- Confidence: Medium
- Category: Wrong result
- Location: `src/orders/export.ext:142`
- Also on base: Yes
- Verdict: Pending verification
- Artifacts: [bug-hunt-artifacts/BH-07/repro.md](bug-hunt-artifacts/BH-07/repro.md)

Problem: <what the code does wrong, in two to four sentences>

Failure scenario: <the input or state, then the wrong result>

Evidence: <code facts with locations. Start each part that is not confirmed with "Not confirmed:" and say where you looked.>

Fix idea: <one short direction, not a patch>
```

Field rules:

- ID: `BH-` and a number with at least two digits (`BH-01`, `BH-12`, `BH-105`). Numbers continue across areas. Never reuse or renumber an ID.
- Severity: one of these values:
  - Critical: data loss, a security hole, or a crash in a main path, with no workaround.
  - High: a wrong result or a crash in a common path.
  - Medium: a wrong result in a less common path, or a problem with a workaround.
  - Low: a small wrong behavior with a small effect.
- Confidence: High (the failure was shown, or the code path is proved), Medium (strong evidence, not shown), or Low (possible, the owner must look).
- Category: one of Crash, Wrong result, Data loss, Security, Concurrency, Resource leak, Error handling, Performance, Compatibility, Build or packaging, Install or upgrade, or Other with a name.
- Location: `path:line`, relative to the snapshot root. More than one location is allowed, separated by commas.
- Also on base: Yes, No, Not checked (with the reason), or Not applicable (the analyzed commit is the base).
- Verdict: the hunter writes "Pending verification". The verifier sets the final value.
- Artifacts: write this line only for an artifact folder that exists. If there is no artifact, leave out the line.
- Failure scenario: if the agent cannot show the failure, write "Not shown:" and the reason.

## Verdicts

The verifier sets exactly one verdict for each finding:

| Verdict | When | What happens to the entry |
| --- | --- | --- |
| `Confirmed` | The evidence holds, and the failure scenario is shown or proved from the code. | It stays in its area section. |
| `Unconfirmed (needs owner review)` | The verifier did not refute it and did not prove it. | It stays in its area section. The Verification paragraph has the three lines below. |
| `Rejected` | The finding is wrong, or it is not a real behavior bug. | It moves, whole and with its ID, to "Appendix: rejected findings". No stub stays in the area section. |
| `Duplicate of #NN`, `Duplicate of N-NN`, or `Duplicate of BH-NN` | A GitHub issue (`#NN`), a notes-file bug (`N-NN`), or an earlier entry (`BH-NN`) describes the same bug. | It stays in its area section. The Verification paragraph names the original. |

If the verifier changes the severity, it shows the old value next to the new one:
`- Severity: Medium (was High)`.

Each verifier adds a Verification paragraph after "Fix idea":

```markdown
Verification: <what the verifier did, what it found, and why it chose the verdict>
```

For an Unconfirmed finding, three more lines follow the Verification paragraph, each as its
own paragraph:

```markdown
Not checked: <what the verifier did not check, and why>

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

## Artifacts

A hunter or a verifier copies only the repro files that matter to
`bug-hunt-artifacts/BH-NN/`. Do not copy secrets, personal data, or large binary files. Each
folder has a `repro.md`:

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

## Known-issues digest

The collector writes this file in the scratch folder. The report never links to it, because
step 6 deletes it.

```markdown
# Known-issues digest

Sources: <notes files>, <owner/repo> issues.

## From notes files

- N-01 (`<notes file>`): <short title>. <location, if the file gives one>.

## Open issues with the label "<label>"

- #12: <title>. <one-line summary of the bug>.

## Titles of all issues

- #12 (open): <title>
- #5 (closed): <title>
```

Number the notes-file bugs in order, `N-01`, `N-02`, and so on, across all notes files.

If a source is not available, the section says so and why.

## Plain-English fallback rules

If the skill `simple-english:simple-english` is not installed, use these rules. They
are a short form of that skill.

1. Keep sentences short: at most 20 words for a step and 25 words for an explanation.
2. Use active voice and simple tenses. Name the actor.
3. Put the condition before the command: "If the file is empty, the parser crashes."
4. Use "can", "will", and "must". Do not use "should", "would", "may", "might", or "could".
5. Do not use contractions, semicolons, or em-dashes.
6. Use one word for one meaning in the whole report.
7. Define a technical term at its first use, in fewer than ten words.
8. State facts. Delete filler words such as "simply", "robust", "crucial", and "in order to".
9. Do not change code, identifiers, paths, commands, or quoted error text.
10. Use bold text only in tables, or not at all. Use no emoji.
