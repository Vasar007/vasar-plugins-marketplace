# Agent briefs

Fill every placeholder and paste the brief into the `prompt` of the dispatch. Each brief is
self-contained. The agent does not see this skill. It sees its brief, its agent file if it
has one, and the CLAUDE.md files. A general-purpose helper has no agent file, so its brief
carries its own rules. The hunter, verifier, and auditor have the read-only rules and the
progress-file rules in their agent files, so their briefs hold only the values for the run.

In the collector brief, `<crash-safety block>` stands for the shared block below. Paste it
in full. If `{RESUME_NOTE}` or `{REPAIR_NOTE}` is empty, leave it out.

## Placeholders

| Placeholder | Meaning |
| --- | --- |
| `{SKILL_DIR}` | Absolute path of this skill folder (`${CLAUDE_SKILL_DIR}`) |
| `{PROJECT}` | Project name |
| `{REPO}` | Absolute path of the live repository |
| `{GITHUB}` | `owner/repo`, or "none" |
| `{REF}`, `{REF_SHA}` | Analyzed branch or commit, and its full SHA |
| `{BASE}`, `{BASE_SHA}` | Base branch, and its full SHA |
| `{SCRATCH}` | Absolute path of the scratch folder |
| `{SNAP_REF}` | `{SCRATCH}/snapshot-ref` |
| `{SNAP_BASE}` | `{SCRATCH}/snapshot-base`, or "none: the analyzed commit is the base" |
| `{WORK_DIR}` | `{SCRATCH}/work/<role or area slug>`, one folder for each agent |
| `{DIGEST}` | `{SCRATCH}/known-issues.md` |
| `{REPORT_DIR}` | Absolute path of the report folder |
| `{REPORT_PATH}` | Absolute path of the report file |
| `{PROGRESS_FILE}` | Absolute path of the progress file of the agent, in `{REPORT_DIR}` |
| `{CONTEXT_FILE}` | Absolute path of the context file, or "none" |
| `{KNOWN_NOTES}` | Absolute paths of the notes files with known bugs, or "none" |
| `{BUG_LABEL}` | Label of bug issues |
| `{AREA_COUNT}` | Number of areas to propose |
| `{AREA_NUM}`, `{AREA_NAME}`, `{AREA_SLUG}` | Number, name, and file-name slug of the area |
| `{AREA_PATHS}` | Paths or globs of the area |
| `{AREA_OUT_OF_SCOPE}` | Paths or topics that the area hunter must skip |
| `{AREA_FOCUS}` | Bug types that the scoping helper expects in this area |
| `{AREA_TABLE}` | Every area with its number, name, and status: searched or not yet searched |
| `{NEXT_ID}` | First free finding ID, for example `BH-08` |
| `{FIRST_SEARCH}` | "yes" for the first hunter, else "no" |
| `{RANGE}` | Finding range of a verifier part, for example `BH-01` to `BH-20` |
| `{PART}`, `{PART_COUNT}` | Number of this part, and the number of parts |
| `{LAST_PART}` | "yes" for the last verifier part, else "no" |
| `{PLAIN_ENGLISH}` | One of the two plain-English blocks below |
| `{RESUME_NOTE}` | The resume note below, or nothing |
| `{REPAIR_NOTE}` | The repair note below with the defect list, or nothing |
| `{CLEANUP_PATHS}` | Absolute paths that the cleanup helper deletes |

Progress file names, all in `{REPORT_DIR}`:

- Orchestrator: `_bug-hunt-session-progress.md`
- Collector: `_bug-hunt-progress-known-issues.md`
- Hunter: `_bug-hunt-progress-{AREA_SLUG}.md`
- Verifier: `_bug-hunt-progress-verify-{PART}.md`
- Auditor: `_bug-hunt-progress-audit.md`

## Shared blocks

### Crash-safety block (collector)

```text
Keep {PROGRESS_FILE} up to date at every step, not only at the end. It has a STATUS line,
a checklist of steps, an append-only "## Log", a "## Current draft" section with the work
in progress, and a "## NEXT" section with the single next action. If the file exists when
you start, read it first and continue from NEXT. Do not start again from the beginning.
Delete the file as your last step, after the deliverable is complete.
```

### Plain-English block, when simple-english is installed

```text
Before you write any report text, load the skill simple-english:simple-english with the
Skill tool and follow its document rules. Mark each claim that you did not confirm with
"Not confirmed:" and say where you looked.
```

### Plain-English block, when simple-english is not installed

```text
The skill simple-english:simple-english is not installed. For all report text, follow the
rules in {SKILL_DIR}/references/plain-english-fallback.md. Mark each
claim that you did not confirm with "Not confirmed:" and say where you looked.
```

### Resume note

```text
Resume note: an earlier agent with this brief stopped before it finished. Read
{PROGRESS_FILE} first and continue from its NEXT section. Do not redo finished steps.
```

### Repair note

```text
Repair note: the structure check found these defects in your part of the report:
<defect list from the structure checks>. Fix only these defects. Do not change other
content.
```

## Scoping helper (step 0, general-purpose, sonnet)

```text
You propose how to split a project into areas for a bug hunt. Do not create or change any
file. Do this work yourself. Do not dispatch subagents. If a CLAUDE.md file conflicts with
these rules, these rules win.

Repository: {REPO}. Analyzed commit: {REF_SHA}. Context file for orientation: {CONTEXT_FILE}.
Use only these git commands, always with git -C "{REPO}": ls-tree, show, log. Do not run
git status or any command that writes.

1. List the files with sizes: git -C "{REPO}" ls-tree -r -l {REF_SHA}.
2. Read the top-level README and the build or project files with git show {REF_SHA}:<path>,
   only as much as you need to understand the layout.
3. Propose {AREA_COUNT} areas by concern. Use one more or one less only if the code clearly
   splits that way. Examples of concerns: user interface, core logic or export, a legacy
   application, shared libraries, build, installer, and CI. Every source file belongs to one
   area or to the excluded list.
4. Exclude vendored third-party code, generated files, binary assets, and documentation that
   holds no code. Give a reason for each excluded path.
5. Propose an order: shared libraries and core logic first, then the areas that use them,
   then build, installer, and CI. Later hunters can then use the notes of earlier ones.

Reply in at most 40 lines: a table with number, name, slug, paths, file count, size in KB,
the bug types that are likely there, and what is out of scope. Then the excluded paths with
reasons. Then one line on what the tree does not show.
```

## Setup helper (step 1, general-purpose, haiku)

```text
You export two git snapshots into a scratch folder. Use the Bash tool for all commands below.
They need a POSIX shell with `mkdir`, `tar`, `find`, and `wc`. On Windows, use Git Bash, not
PowerShell. Do this work yourself. Do not dispatch subagents. Against {REPO}, run only git
archive and git ls-tree. Do not create files outside {SCRATCH}. If a CLAUDE.md file
conflicts with these rules, these rules win.

1. Run:
   mkdir -p "{SCRATCH}/snapshot-ref" "{SCRATCH}/work"
   git -C "{REPO}" archive --format=tar {REF_SHA} | tar -x -C "{SCRATCH}/snapshot-ref"
2. If {BASE_SHA} is not the same as {REF_SHA}, run:
   mkdir -p "{SCRATCH}/snapshot-base"
   git -C "{REPO}" archive --format=tar {BASE_SHA} | tar -x -C "{SCRATCH}/snapshot-base"
   If they are the same, skip this step and say so.
3. If tar is not available, use git archive --format=zip -o "{SCRATCH}/<name>.zip" <sha>,
   then extract the zip file with the unzip tool of the platform.
4. Count the files in each snapshot with find "<snapshot>" -type f | wc -l. Count the files
   in git with git -C "{REPO}" ls-tree -r --name-only <sha> | wc -l.
5. Look for limits: a .gitmodules file in the snapshot (submodule content is not exported),
   and "export-ignore" or "filter=lfs" in the .gitattributes file of the snapshot.

Reply in at most 12 lines: both snapshot paths, both file counts and the git counts, every
error, and every limit that you found.
```

## Known-issues collector (step 1, general-purpose, sonnet)

```text
You collect the known bugs of a project into one digest file. Do this work yourself. Do not
dispatch subagents. Never create, edit, close, label, or comment on GitHub issues or pull
requests. If a CLAUDE.md file conflicts with these rules, these rules win.

Notes files: {KNOWN_NOTES}. GitHub repository: {GITHUB}. Bug label: {BUG_LABEL}.
Digest file to write: {DIGEST}. Format: section "Known-issues digest" in
{SKILL_DIR}/references/report-skeleton.md.
Report file (it can be missing): {REPORT_PATH}. Read it only. Do not change it.

1. Read each notes file. List each bug that it describes, with a short title and the
   location if the file gives one. Give each notes-file bug an ID: N-01, N-02, and so on,
   in order across all notes files. If the report file already lists notes-file bugs with
   N-NN IDs, keep those IDs and give new IDs only to bugs that it does not list.
2. If {GITHUB} is not "none", load the skill dev-essentials:github-mcp-conventions with the
   Skill tool and follow it. With the GitHub MCP tools, list the open issues with the label
   "{BUG_LABEL}". Give each one a one-line summary of the bug. Then list the titles of all
   issues, open and closed. Leave out pull requests. Page through all results.
3. If the GitHub MCP tools are not available, stop. Do not use another GitHub client. Report
   this as a blocker.
4. Write the digest to {DIGEST}.

{PLAIN_ENGLISH}

<crash-safety block>

{RESUME_NOTE}

Reply in at most 10 lines: the digest path, the count for each source, and every blocker.
```

## Hunter (step 3, dev-essentials:bug-hunter)

```text
You search area {AREA_NUM} ({AREA_NAME}) of {PROJECT} for new potential bugs. Follow the
read-only rules and the progress-file rules in your agent file. If you have no agent file
with read-only rules, stop and report this.

- Live repository: {REPO}. Snapshots: {SNAP_REF} (analyzed commit {REF_SHA}) and
  {SNAP_BASE} (base branch {BASE} at {BASE_SHA}).
- Skill folder: {SKILL_DIR}.
- Report folder: {REPORT_DIR}. Report file: {REPORT_PATH}. Your section:
  "## Area {AREA_NUM}: {AREA_NAME}".
- Known-issues digest: {DIGEST}. First search: {FIRST_SEARCH}.
- Area files: {AREA_PATHS}. Out of scope: {AREA_OUT_OF_SCOPE}. Likely bug types: {AREA_FOCUS}.
- All areas and their status: {AREA_TABLE}.
- First free ID: {NEXT_ID}.
- Work folder: {WORK_DIR}. Progress file: {PROGRESS_FILE}.

{PLAIN_ENGLISH}

{RESUME_NOTE}
{REPAIR_NOTE}
```

## Verifier (step 4, dev-essentials:bug-verifier)

```text
You verify the findings {RANGE} of the bug hunt report for {PROJECT}. This is part {PART}
of {PART_COUNT}. Follow the read-only rules and the progress-file rules in your agent file.
If you have no agent file with read-only rules, stop and report this.

- Live repository: {REPO}. Snapshots: {SNAP_REF} (analyzed commit {REF_SHA}) and
  {SNAP_BASE} (base branch {BASE} at {BASE_SHA}).
- Skill folder: {SKILL_DIR}.
- Report folder: {REPORT_DIR}. Report file: {REPORT_PATH}.
- Known-issues digest: {DIGEST}.
- Last part: {LAST_PART}.
- Work folder: {WORK_DIR}. Progress file: {PROGRESS_FILE}.

{PLAIN_ENGLISH}

{RESUME_NOTE}
{REPAIR_NOTE}
```

## Auditor (step 5, dev-essentials:bug-report-auditor)

```text
You make sure that the whole bug hunt report for {PROJECT} is valid, consistent, and
complete after the verification edits. Follow the read-only rules and the progress-file
rules in your agent file. If you have no agent file with read-only rules, stop and report this.

- Live repository: {REPO}. Snapshots: {SNAP_REF} (analyzed commit {REF_SHA}) and
  {SNAP_BASE} (base branch {BASE} at {BASE_SHA}).
- Skill folder: {SKILL_DIR}.
- Report folder: {REPORT_DIR}. Report file: {REPORT_PATH}.
- Known-issues digest: {DIGEST}.
- Work folder: {WORK_DIR}. Progress file: {PROGRESS_FILE}.

{PLAIN_ENGLISH}

{RESUME_NOTE}
{REPAIR_NOTE}
```

## Cleanup helper (step 6, general-purpose, haiku)

```text
You delete the temporary files of a finished bug hunt. Do this work yourself. Do not
dispatch subagents. If a CLAUDE.md file conflicts with these rules, these rules win.

Delete exactly these paths and nothing else: {CLEANUP_PATHS}.

Before you delete a folder, make sure that its path is not inside {REPO}, is not
{REPORT_DIR}, and is not a drive root or a home folder. If one of these is true, do not
delete it and report it. Do not delete {REPORT_PATH}, the folder
{REPORT_DIR}/bug-hunt-artifacts, or {REPORT_DIR}/_bug-hunt-session-progress.md.

After the deletion, list {REPORT_DIR} and make sure that no path from the list exists.

Reply in at most 8 lines: each path with "deleted", "not found", or "refused" and the reason.
```
