---
name: bug-hunt
description: >-
  Read-only bug hunt over a whole repository. It finds new potential bugs in every area of a
  project and saves one verified bug report. One hunter agent searches each area in turn.
  Verifier agents try to refute each finding, and an auditor agent makes sure that the whole
  report is consistent. Agents read the code only from git archive snapshots. Known bugs from
  notes files and GitHub issues are skipped. Progress files make the run resumable after a
  crash. The skill never creates GitHub issues. Use it for "bug hunt", "hunt for bugs" or "find
  new bugs in this project". Use it also for "find potential bugs in every area", "audit the
  codebase for bugs" or "write a verified bug report". Do not use it to review one diff or one pull
  request. Use review-loop or code-review for that.
argument-hint: "<repo-path> [--ref=<branch|commit>] [--base=<branch>] [--report-dir=<path>] [--report-file=<name>] [--github=<owner/repo>] [--known=<file>...] [--bug-label=<label>] [--context=<file>] [--role=<text>] [--name=<project>] [--areas=N] [--split-threshold=N] [--hunter-model=<model>] [--hunter-effort=<level>] [--verifier-model=<model>] [--verifier-effort=<level>] [--auditor-model=<model>] [--auditor-effort=<level>]"
---

# Bug hunt

This skill finds new potential bugs in a whole project and saves one verified bug report.
Agents search the code area by area. Other agents then try to refute each finding.
The project stays read-only for the whole run.

The main session is the orchestrator. It plans the run, dispatches the agents, and checks the
structure of their output. It does not check the content of the findings. The verifier agents
and the auditor agent do that.

## Terms

- Project: the repository that the run analyzes.
- Analyzed commit: the commit that the hunters search. It comes from `--ref`.
- Base branch: the branch that the agents compare against for the field "Also on base".
- Snapshot: a copy of one commit that the setup helper exports with `git archive`. Agents read code only from snapshots.
- Scratch folder: a temporary folder outside the project and outside the report folder. It holds the snapshots, the known-issues digest, and the work folders of the agents.
- Area: a part of the code, grouped by concern. One hunter searches one area.
- Finding: one potential bug, written as a `BH-NN` entry in the report.
- Known issue: a bug that a notes file or a GitHub issue already describes.
- Known-issues digest: a scratch file that lists every known issue. The collector writes it.
- Structure check: a test of the report form that the orchestrator runs between steps. It looks at sections, IDs, fields, and files. It does not judge whether a finding is true.
- Progress file: a `_`-prefixed file where an agent records its steps, so that a new agent can resume after a crash.

## Inputs

The user gives the inputs as arguments or answers the step-0 questions.

| Input | Argument | Default |
| --- | --- | --- |
| Repository path | first argument | If the current working directory is a git repository, that directory |
| Project name | `--name` | The folder name of the repository |
| GitHub repository | `--github` | If the `origin` remote points to github.com, `owner/repo` from that remote. Else none. |
| Analyzed commit | `--ref` | `HEAD` of the repository. The orchestrator resolves it to a commit SHA. |
| Base branch | `--base` | The default branch of `origin`. If git cannot tell, ask. |
| Report folder | `--report-dir` | None. Ask. |
| Report file | `--report-file` | `bug-hunt-report.md`. If that file exists, propose `bug-hunt-report-<YYYY-MM-DD>.md`. |
| Notes files with known bugs | `--known`, repeatable | None |
| Label of bug issues | `--bug-label` | `bug` |
| Context file for orientation | `--context` | None |
| Role of the user | `--role` | "Not stated" |
| Number of areas | `--areas` | 5 |
| Split threshold for pass 1 | `--split-threshold` | 40 findings |
| Hunter model and effort | `--hunter-model`, `--hunter-effort` | `fable`, `max` |
| Verifier model and effort | `--verifier-model`, `--verifier-effort` | `opus`, `xhigh` |
| Auditor model and effort | `--auditor-model`, `--auditor-effort` | `opus`, `xhigh` |

Do not guess the report folder. Ask for it.
The context file is for orientation only. Do not read other files in its folder. If an agent needs one of them, the agent reads it.

## Rules for the whole run

These rules apply to the orchestrator and to every agent. They ship with this skill, so the
skill does not depend on any personal `CLAUDE.md`. If a `CLAUDE.md` file conflicts with rule 1
or rule 2, rules 1 and 2 win.

### 1. The project is read-only

Another session can work in the project at the same time. For this reason, agents read code
only from the snapshots.

- Do not edit, build, test, or run anything in the project folder. Do not create files there. The only exception is the report folder, as the report-folder point below says.
- Against the live repository, run only these git commands: `rev-parse`, `remote get-url`, `ls-tree`, `log`, `show`, `diff` between two revisions, `blame`, and `archive` with output into the scratch folder. Always use `git -C "<repo>"`.
- Do not run `git status`, `fetch`, `pull`, `checkout`, `switch`, `stash`, `reset`, `commit`, or any other command that writes. `git status` can write the index.
- In the report folder, create only new files whose names start with `bug-hunt` or `_bug-hunt`, and the `bug-hunt-artifacts` folder. Do not change or delete any file that existed before the run. This also holds when the report folder is inside the project. It is then the one exception to the first point.
- Run experiments only in a work folder inside the scratch folder. No GUI runs, no system-wide installs, and no changes to the machine configuration.
- The commands in this skill need a POSIX shell. On Windows, run them with the Bash tool (Git Bash), not with PowerShell.

### 2. No GitHub writes

Never create, edit, close, label, or comment on GitHub issues or pull requests. The user
reviews the report first. GitHub access in this skill is read-only, and only the
known-issues collector uses it.

### 3. The orchestrator checks structure, the verifiers check content

The orchestrator does not need to check every finding. Between steps, it runs the structure
checks in [references/structure-checks.md](references/structure-checks.md) and nothing more.

The orchestrator can:

- Make sure that files and folders exist.
- Count sections, IDs, required fields, and verdicts.
- Make sure that no progress file of a finished agent is left.
- Compare the claims in an agent reply with these counts.

The orchestrator must not:

- Read the snapshot code, or re-run repros.
- Judge whether a finding is true, or change a severity or a verdict.
- Rewrite entries in the report. If an entry has a defect, a repair dispatch fixes it.

### 4. Mark what is not confirmed

Every claim that an agent did not confirm starts with "Not confirmed:" and says where the
agent looked. A guess must never read as a fact.

### 5. Plain English

All report text follows the skill `simple-english:simple-english`. At step 0, the
orchestrator looks for this skill in the list of available skills.

- If it is installed, every brief tells the agent to load it with the Skill tool.
- If it is not installed, every brief points to the fallback rules in [references/report-format.md](references/report-format.md). The final report says that the fallback was used.

### 6. Crash-recovery progress files

Every agent that can run long keeps a progress file in the report folder. The file has:

- A `STATUS` line.
- A checklist of steps.
- An append-only `## Log` section.
- A `## Current draft` section with the work in progress.
- A `## NEXT` section with the single next action.

The agent updates the file at every step, not only at the end. On resume, the agent reads
the file first and continues from `## NEXT`. When the deliverable is complete, the agent
deletes the file. A progress file that is left behind means that work is not finished.

The orchestrator keeps its own file, `_bug-hunt-session-progress.md`, in the same way. It
updates the file at each step boundary and after each agent reply.

### 7. Models, effort, and dispatch

- Use the defaults in the Inputs table. The user's explicit choice of a model or an effort level always wins.
- The hunter default is Fable. Fable is never dispatched silently. The user's OK to the step-0 meta-plan approves the Fable dispatches and the effort levels in it. Without that OK, do not dispatch Fable.
- Pass `model` and `effort` on every dispatch of the three plugin agents. The agent files default to Opus, so a dispatch outside this skill never runs Fable.
- If the active model does not support an effort level, Claude Code uses the next lower level.
- The `effort` parameter of the `Agent` tool needs Claude Code v2.1.292 or later. Not confirmed: which effort applies on an older version. The docs at <https://code.claude.com/docs/en/sub-agents> state only the version requirement and do not describe the older behavior.
- Every dispatch is a single unnamed `Agent` call: no `name`, no `team_name`, no `SendMessage`.
- Every brief says "do this work yourself, do not dispatch subagents". The three agent files do not have the `Agent` tool.
- Follow the skill `dev-essentials:subagent-orchestration` for everything else about dispatch.

### 8. Run format

The run format has two parts: the check scope in rule 3 and the reporting rules below. The
step-0 meta-plan states it, and the OK of the user to the meta-plan accepts it. After the OK,
rule 3 replaces two things for this run only. The first is the "Trust but verify" section of
`dev-essentials:subagent-orchestration`. The second is any rule in the instructions of the
user that asks the orchestrator to re-check every subagent claim. The section "Run format
agreement" of that skill has the shared rule.

- Between steps, write at most one short status line to chat for each step, for example "Step 3: area 2 of 5 done, 4 findings." All results go into the report.
- In chat, ask only questions that block the run.
- End the run with one final report (step 7).

## Agents and dispatches

| Step | Role | `subagent_type` | Model | Effort | Count |
| --- | --- | --- | --- | --- | --- |
| 0 | Scoping helper | `general-purpose` | `sonnet` | session default | 1 |
| 1 | Setup helper | `general-purpose` | `haiku` | session default | 1 |
| 1 | Known-issues collector | `general-purpose` | `sonnet` | session default | 1 |
| 3 | Hunter | `dev-essentials:bug-hunter` | hunter model | hunter effort | 1 for each area, one after the other |
| 4 | Verifier | `dev-essentials:bug-verifier` | verifier model | verifier effort | 1 for each part, one after the other |
| 5 | Auditor | `dev-essentials:bug-report-auditor` | auditor model | auditor effort | 1 |
| 6 | Cleanup helper | `general-purpose` | `haiku` | session default | 1 |

The folder of this skill is `${CLAUDE_SKILL_DIR}`. In the reference files, `{SKILL_DIR}` stands for this folder.

The brief for each role is in [references/agent-briefs.md](references/agent-briefs.md). Fill
every placeholder before you dispatch. The agent sees only its brief.

## Pipeline

### Resume check

Do this before step 0. If the report folder is known and it holds
`_bug-hunt-session-progress.md`, read that file and continue from its `## NEXT` section. If
the file records the meta-plan approval, do not ask for it again.

The scratch folder of the old session can be gone. If a snapshot or the digest is missing,
run step 1 again in full: dispatch the setup helper and the collector in the same message,
with the commit SHAs from the progress file. If the report already lists notes-file bugs with
`N-NN` IDs, tell the collector to keep them. Then run the structure checks for step 1. In
these step-1 checks, C13 can also print the progress file of the hunter, verifier, or auditor
that `## NEXT` names. That hit is not a defect. The scratch folder can have a new path. Write the path that is now
in use into `_bug-hunt-session-progress.md` before you fill the next brief. If an agent progress file exists
for the step in `## NEXT`, dispatch that role again with the same brief. Add the resume note
from [references/agent-briefs.md](references/agent-briefs.md).

### Step 0. Meta-plan and questions

1. Resolve the inputs from the arguments. For the defaults, use only light read-only calls: `git -C "<repo>" rev-parse --verify "<ref>^{commit}"`, `git -C "<repo>" rev-parse --abbrev-ref origin/HEAD`, and `git -C "<repo>" remote get-url origin`. Make sure that the report folder exists, and list the files in it that start with `bug-hunt` or `_bug-hunt`.
2. Pick the scratch folder. If the environment gives a session scratchpad directory, use it with a `bug-hunt` subfolder. Else, create a new folder in the system temp folder, for example `bug-hunt-<YYYYMMDD-HHMM>`. The scratch folder must not be inside the project or the report folder.
3. Dispatch the scoping helper. It proposes the areas from the tree of the analyzed commit.
4. Look for `simple-english:simple-english` in the list of available skills.
5. Write the meta-plan in chat. It has these parts:
   1. Inputs: a table with each value and where it came from (argument or default).
   2. Areas: a table with the number, name, paths, file count, size, and order.
   3. Excluded paths, each with a reason, for example vendored or generated code.
   4. Agents: a table with the model and effort of each role. Say in one sentence that the OK approves the Fable dispatches.
   5. Files: the report path, the artifacts folder, the progress file names, and the scratch folder. If the report folder is inside the analyzed repository, say so here. The run then creates new files in the project tree, and only there.
   6. Verification: the split threshold and the split rule of step 4.
   7. Run format: the orchestrator checks only the structure of the output (rule 3), and the verifiers and the auditor check the content. Chat gets at most one status line for each step and one final report (rule 8). Say in one sentence that the OK also accepts this run format.
   8. Plain English: whether `simple-english` is installed, or the fallback is used.
   9. Cleanup: the list of what step 6 deletes and what it keeps.
   10. Questions: a numbered list, or "No questions".
6. Ask only questions that block the run. Examples: the report folder is missing, the report file exists, the report folder already holds a `bug-hunt-artifacts` folder or a `_bug-hunt-progress-*.md` file and no resume applies (a new run would write into the files of the old run), the base branch is unknown, Fable is not available, or there is no known-issue source.
7. Wait for the user's explicit OK. If the user changes a value, apply the change. If the change raises a new question, show the meta-plan again. Else do not show it again.
8. After the OK, write `_bug-hunt-session-progress.md` in the report folder. Record the inputs, the commit SHAs, the scratch folder, the approved models and effort levels, the areas, and the approval itself.

### Step 1. Isolation

Dispatch the setup helper and the known-issues collector in the same message, so that they
run in parallel.

- The setup helper exports the analyzed commit to `<scratch>/snapshot-ref` and the base branch to `<scratch>/snapshot-base`. It creates `<scratch>/work`. If the analyzed commit and the base are the same commit, it skips the base export, and every finding gets "Also on base: Not applicable".
- The collector writes the known-issues digest to `<scratch>/known-issues.md`.

Then run the structure checks for step 1. Record the limits that the setup helper reports, such
as submodules or Git LFS files that the snapshots do not hold. They go into the Scope section.

### Step 2. Report skeleton

Write the report file from the skeleton in
[references/report-format.md](references/report-format.md). Fill the Scope section from the
meta-plan and the setup reply. Write one section for each area, in the approved order. Leave
the placeholders in the other sections. The agents replace them.

### Step 3. Search

For each area, in the approved order:

1. Compute the next ID with the command in [references/structure-checks.md](references/structure-checks.md). The first area starts at `BH-01`.
2. Dispatch one hunter with the hunter brief. Tell the first hunter that it also fills the section "Known issues that this report does not repeat".
3. Wait for the reply. Do not dispatch the next hunter before this one finishes.
4. Run the structure checks for step 3. Compare the reply with the counts.
5. Update the session progress file: the area is done, and the next ID.

Hunters run strictly one after the other. Later hunters read the "Notes for other areas" of
earlier hunters, and the numbering continues across areas.

### Step 4. Verification pass 1

1. Count the findings. Call the number N.
2. If N is 0, skip this step. The auditor writes the Summary in step 5.
3. If N is at most the split threshold, use one part. Else, use `ceil(N / threshold)` parts. Split the ID range into consecutive ranges of near-equal size.
4. Dispatch one verifier for each part, one after the other, on the same report file. Tell the last part that it also writes the Summary.
5. After each part, run the structure checks for step 4.

Each verifier tries to refute each finding in its range and sets one verdict: Confirmed,
Unconfirmed (needs owner review), Rejected, or Duplicate of #NN, N-NN, or BH-NN. The verdict rules
are in [references/report-format.md](references/report-format.md).

### Step 5. Verification pass 2

Dispatch one auditor. It makes sure that the whole report is valid, consistent, and complete
after the edits: fields against the Summary, cross-references, counts, links, and plain
English. Then run the structure checks for step 5.

### Step 6. Cleanup

Dispatch the cleanup helper with the exact list of paths to delete:

- The scratch folder, with the snapshots, the digest, and every work folder.
- Every `_bug-hunt-progress-*.md` file in the report folder.

Keep the report file and the `bug-hunt-artifacts` folder. Then run the structure checks for
step 6. As the last action before the final report, delete `_bug-hunt-session-progress.md`.

### Step 7. Final report

Write one report in chat, in the language of the user's request. The report file itself stays
in English. If the instructions of the user define an end-of-run report format, use it, and put
the content below into its matching sections. Else use these three sections, in this order:

1. Blocked on me: the decisions that only the user can make. List each Unconfirmed finding by ID and point to its "To decide:" line. If there are none, write "Nothing".
2. Changed: the report path and the artifacts folder with the number of subfolders. Say that the run made no change in the project, no commits, and no GitHub issues.
3. Found: the counts for each verdict. The Confirmed findings by severity, with ID and title, at most 10. The leads that the verifiers or the auditor reported but did not confirm. The limits of the run, the use of the plain-English fallback, any change from the meta-plan, and any leftover file.

## Failure handling

- If an agent stops on a usage limit or crashes, dispatch a new agent of the same role. Give it the same brief and the resume note. The new agent reads the progress file and continues.
- If a structure check fails, dispatch one repair agent of the same role. Give it the same brief and the repair note with the list of defects. If the check fails again, stop the run. Keep all files, and report the defects under "Blocked on me".
- If the collector cannot reach GitHub, ask the user what to do. The user can reconnect the GitHub MCP server with `/mcp` or continue with the notes files only. Do not fall back to another GitHub client.
- If an agent reports a blocker, such as a missing snapshot, fix the cause with the right helper. Then dispatch the agent again.

## Common failure modes

- The orchestrator reads the code or re-checks findings itself. This duplicates the verifiers and fills the main context.
- A hunter reads the live repository instead of the snapshot, so the line numbers do not match the analyzed commit.
- Hunters run in parallel. The numbering breaks, and the notes for other areas get lost.
- An agent runs `git status` in the live repository.
- A progress file, a snapshot, or a work folder stays after the run.
- Interim results go to chat instead of the report.
- An agent creates or comments on a GitHub issue.
- A finding without a failure scenario passes as Confirmed.

## Reference files

- [references/report-format.md](references/report-format.md): the report skeleton, the finding format, the verdict rules, the Summary format, the artifacts layout, the digest format, and the plain-English fallback rules.
- [references/agent-briefs.md](references/agent-briefs.md): the placeholders, the shared blocks, and the briefs for every role.
- [references/structure-checks.md](references/structure-checks.md): the commands that the orchestrator runs between steps.
