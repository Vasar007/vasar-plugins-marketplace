# Report skeleton and digest format

The orchestrator reads the report skeleton and the run context template at step 2. The known-issues collector reads the digest format at step 1. The hunters, verifiers, and auditor do not need this file. They read [report-format.md](report-format.md) and the run context file.

## Files in the report folder

```text
<report folder>/
├── bug-hunt-report.md            (or the report file name from the meta-plan)
├── bug-hunt-context.md           (run context file, kept for later rounds)
├── bug-hunt-final-summary.md     (the final chat report, saved as is at step 7)
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

- Project: {PROJECT}. GitHub repository: {GITHUB}.
- Analyzed code: {REF} at commit {REF_SHA}.
- Base branch for "Also on base": {BASE} at commit {BASE_SHA}, from {BASE_SOURCE}.
- Date: {DATE}.
- Role of the author: {ROLE}.
- Areas: {AREA_LIST}.
- Excluded paths: {EXCLUDED}.
- Known-issue sources: {KNOWN_SOURCES}.
- Experiments: {EXPERIMENTS}.
- Severity scale:
  - Critical: data loss, a security hole, or a crash in a main path, with no workaround.
  - High: a wrong result or a crash in a common path.
  - Medium: a wrong result in a less common path, or a problem with a workaround.
  - Low: a small wrong behavior with a small effect.
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
write "None found" for `{LIMITS}`. `{BASE_SOURCE}` is "the local branch" or "a fresh clone
from the remote". If the base is `none`, write the line as "- Base branch: none. The user
chose no base comparison.". `{EXPERIMENTS}` says whether agents built, tested, and ran code
on snapshot copies, and which services were available.

## Run context file

The orchestrator writes `bug-hunt-context.md` in the report folder at step 2, from the
template below. It keeps the file up to date during the run. Each agent reads it first. Step 6
keeps it, so that a later round can reuse it.

```markdown
# Bug hunt context: {PROJECT}

This file holds the stable facts of the bug hunt. The orchestrator keeps it up to date.

## Project

- Project: {PROJECT}. GitHub repository: {GITHUB}.
- Analyzed code: {REF} at commit {REF_SHA}.
- Base: {BASE} at commit {BASE_SHA}, from {BASE_SOURCE}. Or "none".
- Report file: {REPORT_FILE}.
- Known-issue sources: {KNOWN_SOURCES}.

## Areas

| Number | Name | Slug | Paths | Out of scope | Likely bug types | Extra context | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | {name} | {slug} | {paths} | {topics or paths} | {bug types} | {for example: legacy code, no longer shipped} | Not yet searched |

## Excluded paths

- {path}: {reason}

## Experiments

- Builds, restores, tests, and runs on snapshot copies: {allowed or not allowed}.
- Services for experiments: {SERVICES or "none"}.

## Build and test notes

None yet.

## Severity notes

None yet.
```

In the sections "Build and test notes" and "Severity notes", the first note replaces
"None yet.".

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

## Other open issues

- #31 (labels: chore): <title>. <one-line summary of the problem>.

## Titles of all issues

- #12 (open): <title>
- #5 (closed): <title>
```

Number the notes-file bugs in order, `N-01`, `N-02`, and so on, across all notes files.

If a source is not available, the section says so and why.
