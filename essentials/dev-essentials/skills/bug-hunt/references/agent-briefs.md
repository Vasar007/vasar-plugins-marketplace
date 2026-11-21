# Agent briefs

Fill every placeholder and paste the brief into the `prompt` of the dispatch. Each brief is
self-contained. The agent does not see this skill. It sees its brief and the CLAUDE.md files.
A plugin agent also sees its agent file. A general-purpose helper has no agent file, so its brief
carries its own rules. The hunter, verifier, and auditor have the read-only rules and the
progress-file rules in their agent files. Their briefs hold only the values for the run.

## Contents

- Placeholders
- Shared blocks
- Scoping helper (step 0, general-purpose)
- Known-issues collector (step 1, general-purpose)
- Hunter (step 3, dev-essentials:bug-hunter)
- Verifier (step 4, dev-essentials:bug-verifier)
- Auditor (step 5, dev-essentials:bug-report-auditor)

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
| `{BASE}`, `{BASE_SHA}` | Base branch name without the remote prefix (for example `main`, not `origin/main`), and its full SHA |
| `{SCRATCH}` | Absolute path of the scratch folder |
| `{SNAP_REF}` | `{SCRATCH}/snapshot-ref` |
| `{SNAP_BASE}` | `{SCRATCH}/snapshot-base`, or "none: the analyzed commit is the base", or "none: no base comparison" |
| `{WORK_DIR}` | `{SCRATCH}/work/<role or area slug>`, one folder for each agent |
| `{TOOLS_DIR}` | `{SCRATCH}/tools`, the shared folder for downloaded tools and third-party sources |
| `{RUN_CONTEXT}` | Absolute path of `bug-hunt-context.md` in `{REPORT_DIR}` |
| `{CHECK_CMD}` | The full structure check command for this agent from `references/structure-checks.md`, with `--allow` and the name of its progress file |
| `{OPEN_NOTES}` | The output lines of the `open-notes` command for the areas of this verifier part, or "none" |
| `{DIGEST}` | `{SCRATCH}/known-issues.md` |
| `{REPORT_DIR}` | Absolute path of the report folder |
| `{REPORT_PATH}` | Absolute path of the report file |
| `{PROGRESS_FILE}` | Absolute path of the progress file of the agent, in `{REPORT_DIR}` |
| `{CONTEXT_FILE}` | Absolute path of the context file, or "none" |
| `{KNOWN_NOTES}` | Absolute paths of the notes files with known bugs, or "none" |
| `{BUG_LABEL}` | Label of bug issues |
| `{AREA_COUNT}` | Number of areas to propose |
| `{AREA_NUM}`, `{AREA_NAME}`, `{AREA_SLUG}` | Number, name, and file-name slug of the area |
| `{NEXT_ID}` | First free finding ID, for example `BH-08` |
| `{FIRST_SEARCH}` | "yes" for the first hunter, else "no" |
| `{RANGE}` | Finding range of a verifier part, for example `BH-01` to `BH-20` |
| `{PART}`, `{PART_COUNT}` | Number of this part, and the number of parts |
| `{LAST_PART}` | "yes" for the last verifier part, else "no" |
| `{PLAIN_ENGLISH}` | One of the plain-English blocks below |
| `{RESUME_NOTE}` | The resume note below, or nothing |
| `{REPAIR_NOTE}` | The repair note below with the defect list, or nothing |

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
a list of steps, an append-only "## Log", a "## Current draft" section with the work in
progress, and a "## NEXT" section with the single next action. Update NEXT after each step.
If the file exists when you start, read it first. Compare NEXT with the real state of your
output. If they differ, trust the output and correct NEXT. Then continue from NEXT. Do not
start again from the beginning. Delete the file as your last step, after the deliverable is
complete.
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
{PROGRESS_FILE} first. Compare its NEXT section with the real state of the report. If they
differ, trust the report and correct NEXT. Then continue from NEXT. Do not redo finished
steps.
```

### Repair note

```text
Repair note: the structure check found these defects in your part of the report:
<defect list from the structure check>. Fix only these defects. Do not change other
content.
```

## Scoping helper (step 0, general-purpose)

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
5. Propose an order and number the areas in it: shared libraries and core logic first, then the areas that use them,
   then build, installer, and CI. Later hunters can then use the notes of earlier ones.

Reply in at most 40 lines: a table with number, name, slug, paths, file count, size in KB,
the bug types that are likely there, what is out of scope, and extra context, for example
"legacy code, no longer shipped". Then the excluded paths with reasons. Then one line on
what the tree does not show.
```

## Known-issues collector (step 1, general-purpose)

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
   "{BUG_LABEL}". Give each one a one-line summary of the bug. Then list the other open
   issues, each with its labels and a one-line summary. Then list the titles of all issues,
   open and closed. Leave out pull requests. Page through all results.
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

- Run context file: {RUN_CONTEXT}. Read it first. Your area is row {AREA_NUM} of its Areas
  table.
- Live repository: {REPO}. Snapshots: {SNAP_REF} (analyzed commit {REF_SHA}) and
  {SNAP_BASE} (base branch {BASE} at {BASE_SHA}).
- Skill folder: {SKILL_DIR}.
- Report folder: {REPORT_DIR}. Report file: {REPORT_PATH}. Your section:
  "## Area {AREA_NUM}: {AREA_NAME}".
- Known-issues digest: {DIGEST}. First search: {FIRST_SEARCH}.
- First free ID: {NEXT_ID}.
- Work folder: {WORK_DIR}. Shared tools folder: {TOOLS_DIR}. Progress file: {PROGRESS_FILE}.
- Structure check to run before your reply: {CHECK_CMD}

{PLAIN_ENGLISH}

{RESUME_NOTE}
{REPAIR_NOTE}
```

## Verifier (step 4, dev-essentials:bug-verifier)

```text
You verify the findings {RANGE} of the bug hunt report for {PROJECT}. This is part {PART}
of {PART_COUNT}. Follow the read-only rules and the progress-file rules in your agent file.
If you have no agent file with read-only rules, stop and report this.

- Run context file: {RUN_CONTEXT}. Read it first.
- Live repository: {REPO}. Snapshots: {SNAP_REF} (analyzed commit {REF_SHA}) and
  {SNAP_BASE} (base branch {BASE} at {BASE_SHA}).
- Skill folder: {SKILL_DIR}.
- Report folder: {REPORT_DIR}. Report file: {REPORT_PATH}.
- Known-issues digest: {DIGEST}.
- Last part: {LAST_PART}.
- Open notes for your areas: {OPEN_NOTES}
- Work folder: {WORK_DIR}. Shared tools folder: {TOOLS_DIR}. Progress file: {PROGRESS_FILE}.
- Structure check to run before your reply: {CHECK_CMD}

{PLAIN_ENGLISH}

{RESUME_NOTE}
{REPAIR_NOTE}
```

## Auditor (step 5, dev-essentials:bug-report-auditor)

```text
You make sure that the whole bug hunt report for {PROJECT} is valid, consistent, and
complete after the verification edits. Follow the read-only rules and the progress-file
rules in your agent file. If you have no agent file with read-only rules, stop and report this.

- Run context file: {RUN_CONTEXT}. Read it first.
- Live repository: {REPO}. Snapshots: {SNAP_REF} (analyzed commit {REF_SHA}) and
  {SNAP_BASE} (base branch {BASE} at {BASE_SHA}).
- Skill folder: {SKILL_DIR}.
- Report folder: {REPORT_DIR}. Report file: {REPORT_PATH}.
- Known-issues digest: {DIGEST}.
- Work folder: {WORK_DIR}. Progress file: {PROGRESS_FILE}.
- Structure check to run before your reply: {CHECK_CMD}

{PLAIN_ENGLISH}

{RESUME_NOTE}
{REPAIR_NOTE}
```
