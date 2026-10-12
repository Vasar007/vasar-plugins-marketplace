# Report skeleton and digest format

The orchestrator reads the report skeleton at step 2. The known-issues collector reads the digest format at step 1. The hunters, verifiers, and auditor do not need this file. They read [report-format.md](report-format.md).

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
