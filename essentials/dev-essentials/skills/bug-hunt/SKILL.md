---
name: bug-hunt
description: >-
  Read-only bug hunt over a whole repository. It finds new potential bugs area
  by area, verifies each one, and saves one bug report. A bug that a notes file
  or a GitHub issue already describes is not a new finding. The hunt never
  writes to GitHub.
when_to_use: >-
  Use it for "bug hunt", "find new bugs in this project", or "audit the codebase
  for bugs". Do not use it to review one diff or one pull request. Use
  review-loop for that.
argument-hint: "<repo-path> [--ref=<branch|commit>] [--base=<branch>|none] [--base-from=local|remote] [--report-dir=<path>] [--report-file=<name>] [--github=<owner/repo>] [--known=<file>...] [--bug-label=<label>] [--context=<file>] [--role=<text>] [--name=<project>] [--areas=N] [--split-threshold=N] [--experiments=yes|no] [--stop-after=<points>] [--resume-at=<HH:MM,...>] [--start-at=<HH:MM>] [--hunter-model=<model>] [--hunter-effort=<level>] [--verifier-model=<model>] [--verifier-effort=<level>] [--auditor-model=<model>] [--auditor-effort=<level>] [--interactive] [--autonomous]"
---

# Bug hunt

This skill finds new potential bugs in a whole project and saves one verified bug report.
The main session is the orchestrator. It plans the run and dispatches the agents.

Earlier runs forgot two rules most often: the orchestrator checks only the structure of the
agent output (rule 3), and all text follows plain English (rule 5).

## Terms

- Project: the repository that the run analyzes.
- Analyzed commit: the commit that the hunters search (`--ref`).
- Base branch: the branch that the agents compare against for the field "Also on base". `--base=none` turns off the comparison.
- Snapshot: a copy of one commit in the scratch folder. Agents read code only from snapshots.
- Scratch folder: a temporary folder outside the project and outside the report folder. It holds the snapshots, the known-issues digest, and the work folders of the agents.
- Area: a part of the code, grouped by concern. One hunter searches one area.
- Finding: one potential bug, written as a `BH-NN` entry in the report.
- Known issue: a bug that a notes file (`N-NN`) or a GitHub issue (`#NN`) already describes.
- Known-issues digest: the scratch file where the collector lists every known issue.
- Structure check: a test of the report form that `scripts/check_report.py` runs. It does not judge whether a finding is true.
- Progress file: a `_`-prefixed file where an agent records its steps, so that a new agent can resume after a crash.
- Run context file: `bug-hunt-context.md` in the report folder, with the stable facts of the run. Agents read it first. The run keeps it for later rounds.
- Final summary file: `bug-hunt-final-summary.md` in the report folder, the final chat report saved as is.
- Pause point: a step boundary where the run stops until the user or a scheduled prompt resumes it.

## Autonomy

This workflow has three modes. The user picks one with a flag: the default (no flag), `--interactive`, or `--autonomous`. A gate is a step where the run can stop and ask the user. This table lists each gate of this workflow and what each mode does there.

| Gate | Default | `--interactive` | `--autonomous` |
| --- | --- | --- | --- |
| Step 0 and rule 8: the meta-plan and the run format | Continue, unless the user objects | Wait for the OK | Same as default |
| Step 0 item 1: the GitHub repository from the remote | Take it, and mark it in the Scope section | Ask | Same as default |
| Rule 7: Fable dispatches of the meta-plan | The meta-plan approves them | The OK of the user approves them | Same as default |
| Step 6: cleanup | Delete only the paths that this run made, with no stop | Same | Same |

The run never commits, pushes, or writes to GitHub.

These rules apply in every mode:

- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that the run cannot fix also stops the run. Do not ask in other cases.
- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default of the gate, and continue.
- The final report lists each gate that the run passed without a stop. With `--autonomous`, it also lists each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It adds no steps. A step that runs only with a flag such as `--push` still needs that flag, and the flag is the approval of that step.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.

## Rules for the whole run

These rules apply to the orchestrator. The agent files and the briefs carry them to the
agents. If a `CLAUDE.md` file conflicts with rule 1 or rule 2, rules 1 and 2 win.

### 1. The project is read-only

- Do not edit, build, test, or run anything in the project folder. Do not create files there. The report folder is the only exception (see the report-folder point).
- Against the live repository, always use `git -C "<repo>"`. Run only these git commands: `rev-parse`, `remote get-url`, `ls-tree`, `log`, and `show`. Also `diff` between two revisions, `blame`, `archive` with output into the scratch folder, and `--no-optional-locks status`. The orchestrator follows this list too, also at cleanup.
- Do not run a plain `git status`, because it can write the index. Do not run `fetch`, `pull`, `checkout`, `switch`, `stash`, `reset`, `commit`, or any other command that writes. Never fetch into the live repository. For a newer base, the setup helper clones it into the scratch folder.
- In the report folder, create only new files whose names start with `bug-hunt` or `_bug-hunt`, and the `bug-hunt-artifacts` folder. Do not change or delete any file that existed before the run. If the report folder is inside the project, this point holds.
- The commands in this skill need a POSIX shell and Python 3. On Windows, run them with the Bash tool (Git Bash), not with PowerShell. If `python3` is not available, stop the run at step 0 and report this under "Blocked on me".

### 2. No GitHub writes

Never create, edit, close, label, or comment on GitHub issues or pull requests. The user
reviews the report first.

### 3. The orchestrator checks structure, the verifiers check content

Between steps, the orchestrator runs only the structure check in
[references/structure-checks.md](references/structure-checks.md) and compares each
agent reply with its counts.

The orchestrator must not:

- Read the snapshot code, or re-run repros.
- Judge whether a finding is true, or change a severity or a verdict.
- Rewrite entries in the report. If an entry has a defect, a repair dispatch fixes it.

### 4. Mark what is not confirmed

Every claim that an agent did not confirm starts with "Not confirmed:" and says where the
agent looked. A guess must never read as a fact.

### 5. Plain English

All report text follows the skill `simple-english:simple-english`.

- If it is installed, every brief tells the agent to load it with the Skill tool.
- If it is not installed, every brief points to the fallback rules in [references/plain-english-fallback.md](references/plain-english-fallback.md). The final report says that the fallback was used.

### 6. Crash-recovery progress files

Every agent that can run long keeps a progress file in the report folder. It has a `STATUS` line, a
checklist of steps, an append-only `## Log`. It has a `## Current draft` with the work in progress,
and a `## NEXT` with the single next action. A progress file that is left behind means that
work is not finished.

The orchestrator keeps `_bug-hunt-session-progress.md` with the same sections. It updates the file at
each step boundary and after each agent reply. It records the agent ID of each dispatch, and
each pause with its resume job. After each dispatch, it writes this into `## NEXT`: "Waiting
for agent `<ID>` (`<role>`), dispatched `<time>`. If the agent runs, do not dispatch this role
again." If two agents run at the same time, the note names each one. Edit progress files and
the report with the Edit tool, not with a script that rewrites the file.

### 7. Models, effort, and dispatch

- Use the models and effort levels of the approved meta-plan. The user's explicit choice of a model or an effort level always wins.
- Fable is never dispatched silently. The step-0 meta-plan names each Fable dispatch and its effort level. With `--interactive`, the OK of the user approves them, and without that OK you do not dispatch Fable. Without `--interactive`, the meta-plan approves them, because Fable is the documented default of this skill for the hunter.
- Pass `model` and `effort` on every dispatch of the plugin agents `dev-essentials:bug-hunter`, `dev-essentials:bug-verifier`, and `dev-essentials:bug-report-auditor`. Their agent files default to Opus.
- Dispatch the hunter, verifier, and auditor only with their plugin `subagent_type`, because their briefs do not carry the read-only rules. If that type is not available, stop the run and report it under "Blocked on me".
- Every dispatch is a single unnamed `Agent` call: no `name` and no `team_name`. A restore still uses `SendMessage` with the recorded agent ID.
- Follow the skill `dev-essentials:subagent-orchestration` for everything else about dispatch.

### 8. Run format

The run format is the check scope in rule 3 plus the reporting rules below. The step-0
meta-plan states it. With `--interactive`, the OK of the user accepts it. Without `--interactive`, the meta-plan accepts it unless the user objects. After the run format is accepted, rule 3
replaces tiers 1 and 2 of the section `Trust but verify` of
`dev-essentials:subagent-orchestration` for this run only. It also replaces any user instruction to test every subagent
claim. Tier 3 still applies to the deletions of step 6: re-read the path list before the cleanup helper runs. For the findings in the final report, the verifier and auditor verdicts are enough, and rule 3 still applies. The section "Run format agreement" of that skill has the shared rule.

- Between steps, write at most one status line to chat for each step, for example "Step 3: area 2 of 5 done, 4 findings." All results go into the report.
- In chat, ask only questions that block the run.
- End the run with one final report (step 7).
- If the session has a task tool (`TaskCreate` or `TodoWrite`), keep one task for each step, area, and verifier part. A restart of Claude Code clears the list. Then create it again from the session progress file.

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
every placeholder before you dispatch.

The hunters, verifiers, and auditor also read
[references/report-format.md](references/report-format.md).

## Pipeline

### Pauses, resume, and failures

After a step, an area, or a verifier part that is a pause point, stop as
[references/pauses.md](references/pauses.md) says. If the user asks for a stop, a start time,
or a resume time, read that file too.

Before step 0, look for `_bug-hunt-session-progress.md` in the report folder. If the report
folder becomes known only from a step-0 answer, look then, before you show the meta-plan
again. If the file exists, follow "Resume check" in
[references/resume-and-failures.md](references/resume-and-failures.md). If an agent stops or
fails, or a structure check fails, follow "Failure handling" in the same file.

### Step 0. Meta-plan and questions

Read [references/inputs-and-meta-plan.md](references/inputs-and-meta-plan.md) first.

1. Resolve the inputs from the arguments and the defaults. Do not guess the report folder. With `--interactive`, do not take the GitHub repository from the remote without the user's OK. Without `--interactive`, take it from the remote and mark it in the Scope section. This is the documented exception in `dev-essentials:github-mcp-conventions` Rule 1. Find out whether the report folder exists. If it is missing, ask. Else list the files in it that start with `bug-hunt` or `_bug-hunt`.
2. Pick the scratch folder. If the environment gives a session scratchpad directory, use it with a `bug-hunt` subfolder. Else, create a new folder in the system temp folder, for example `bug-hunt-<YYYYMMDD-HHMM>`. The scratch folder must not be inside the project or the report folder.
3. Dispatch the scoping helper. It proposes the areas from the tree of the analyzed commit.
4. Look for `simple-english:simple-english` in the list of available skills.
5. Write the meta-plan in chat, with every part that the reference file lists.
6. Ask only questions that block the run.
7. Without `--interactive`, and with no question that blocks the run, continue. The meta-plan in chat states the run. With `--interactive`, wait for the user's explicit OK. If the user changes a value, apply the change. If the change raises a new question, show the meta-plan again. Else do not show it again.
8. After the OK, or after item 7 without `--interactive`, do this. Write `_bug-hunt-session-progress.md` in the report folder, with the values that "Session progress file" in the reference file lists. If a start time is set, schedule the start as [references/pauses.md](references/pauses.md) says, and end the turn.

### Step 1. Isolation

Dispatch the setup helper and the known-issues collector in the same message, so that they
run in parallel. The setup helper exports the snapshots into the scratch folder. The collector
writes the known-issues digest to `<scratch>/known-issues.md`.

Then run the structure check for step 1. For a remote base, record the commit SHA that the
setup helper reports. Record the limits that it reports, such as submodules or Git LFS files
that the snapshots do not hold. They go into the Scope section.

### Step 2. Report skeleton

Write the report file from the skeleton in
[references/report-skeleton.md](references/report-skeleton.md). Fill the Scope section from the
meta-plan and the setup reply. Write one section for each area, in the approved order. Leave
the placeholders in the other sections. The agents replace them. Then write the run context
file from the template in the same file. If the user chose to reuse the run context file of
an earlier round, update that file for this run instead. Then run the structure check for step 2.

### Step 3. Search

For each area, in the approved order:

1. Compute the next ID with the `next-id` command in [references/structure-checks.md](references/structure-checks.md).
2. Dispatch one hunter with the hunter brief. Set `{FIRST_SEARCH}` to "yes" only for the first hunter. That hunter also fills the section "Known issues that this report does not repeat".
3. Wait for the reply. Do not dispatch the next hunter before this one finishes. Later hunters read the notes of earlier ones, and the IDs continue across areas.
4. Run the structure check for step 3. Compare the reply with the counts.
5. Update the session progress file: the area is done, the next ID, and the agent ID. In the run context file, set the area to "Searched", and append the build and test notes of the reply under "Build and test notes".

After the last hunter, run the `open-notes` command. Each open note goes into the brief of the
verifier part that holds the area that the note names.

### Step 4. Verification pass 1

1. Count the findings. Call the number N.
2. If N is 0, skip this step. The auditor writes the Summary in step 5.
3. If N is at most the split threshold, use one part. Else, use `ceil(N / threshold)` parts. Each part covers whole areas. Choose the area borders that make the parts closest to equal size. Split inside an area only for an area whose findings alone exceed the threshold.
4. Dispatch one verifier for each part, one after the other, on the same report file. Set `{LAST_PART}` to "yes" only for the last part. That part also writes the Summary.
5. After each part, run the structure check for step 4. Append the "Severity use" lines of the reply under "Severity notes" in the run context file. Later parts read them.

### Step 5. Verification pass 2

Dispatch one auditor. It makes the whole report consistent and writes "For the owner's review"
at the end of the Summary. Then run the structure check for step 5.

### Step 6. Cleanup

First, delete the scheduled jobs of the run: run `CronList`, and run `CronDelete` for each job
ID that the session progress file records.

Dispatch the cleanup helper. Give it the process IDs and start times from the WARN lines of the
structure check. Give it the exact list of paths to delete:

- The scratch folder, with the snapshots, the digest, the tools folder, and every work folder.
- Every `_bug-hunt-progress-*.md` file in the report folder.

Keep the report file, the run context file, and the `bug-hunt-artifacts` folder. Then run the
structure check for step 6. Run `git -C "<repo>" --no-optional-locks status --porcelain` again, compare it with the output from step 0, and report only the lines that differ. Skip the report folder files that the run made. Another session can cause the rest. As the last action before the final
report, delete `_bug-hunt-session-progress.md`.

### Step 7. Final report

Write one report in chat, in the language of the user's request. The report file itself stays
in English. If the instructions of the user define an end-of-run report format, use it, and put
the content below into its matching sections. Else use these three sections, in this order:

1. Blocked on me: the decisions that only the user can make. List each Unconfirmed finding by ID and point to "For the owner's review" in the Summary. If there are none, write "Nothing".
2. Changed: the report path, the run context file, the final summary file, and the artifacts folder with the number of subfolders. Say that the run made no change in the project, no commits, and no GitHub issues.
3. Found: the counts for each verdict. The Confirmed findings by severity, with ID and title, at most 10. The leads that the verifiers or the auditor reported but did not confirm. The limits of the run, the use of the plain-English fallback, any change from the meta-plan, and any leftover file. Also the lists that "Autonomy" asks for.

Save the final report, as is, to `bug-hunt-final-summary.md` in the report folder with the
Write tool. If step 0 chose a dated name, use that name. Then post the same text in chat.
