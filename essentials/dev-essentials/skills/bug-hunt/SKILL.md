---
name: bug-hunt
description: >-
  Read-only bug hunt over a whole repository. It finds new potential bugs area by area, has
  other agents try to refute each one, and saves one verified bug report. It skips bugs that
  notes files or GitHub issues already describe, and it never creates issues. Use it for "bug
  hunt", "hunt for bugs", "find new bugs in this project", "find potential bugs in every area",
  "audit the codebase for bugs", or "write a verified bug report". Do not use it to review one
  diff or one pull request. Use review-loop or code-review for that.
argument-hint: "<repo-path> [--ref=<branch|commit>] [--base=<branch>|none] [--base-from=local|remote] [--report-dir=<path>] [--report-file=<name>] [--github=<owner/repo>] [--known=<file>...] [--bug-label=<label>] [--context=<file>] [--role=<text>] [--name=<project>] [--areas=N] [--split-threshold=N] [--experiments=yes|no] [--stop-after=<points>] [--resume-at=<HH:MM,...>] [--start-at=<HH:MM>] [--hunter-model=<model>] [--hunter-effort=<level>] [--verifier-model=<model>] [--verifier-effort=<level>] [--auditor-model=<model>] [--auditor-effort=<level>]"
---

# Bug hunt

This skill finds new potential bugs in a whole project and saves one verified bug report.
Agents search the code area by area. Other agents then try to refute each finding.
The project stays read-only for the whole run.

The main session is the orchestrator. It plans the run, dispatches the agents, and checks the
structure of their output. It does not check the content of the findings. The verifier agents
and the auditor agent do that.

Earlier runs forgot two rules most often. Keep both in view for the whole run: the
orchestrator checks only structure (rule 3), and all text follows plain English (rule 5).

## Terms

- Project: the repository that the run analyzes.
- Analyzed commit: the commit that the hunters search. It comes from `--ref`.
- Base branch: the branch that the agents compare against for the field "Also on base". The user can turn off the comparison with `--base=none`.
- Snapshot: a copy of one commit that the setup helper exports with `git archive`. Agents read code only from snapshots.
- Scratch folder: a temporary folder outside the project and outside the report folder. It holds the snapshots, the known-issues digest, and the work folders of the agents.
- Area: a part of the code, grouped by concern. One hunter searches one area.
- Finding: one potential bug, written as a `BH-NN` entry in the report.
- Known issue: a bug that a notes file or a GitHub issue already describes.
- Known-issues digest: a scratch file that lists every known issue. The collector writes it.
- Structure check: a test of the report form that `scripts/check_report.py` runs between steps. It looks at sections, IDs, fields, and files. It does not judge whether a finding is true.
- Progress file: a `_`-prefixed file where an agent records its steps, so that a new agent can resume after a crash.
- Run context file: `bug-hunt-context.md` in the report folder. It holds the stable facts of the run: the commits, the areas, the experiment rules, and the notes that agents pass on. Agents read it first. The run keeps it for later rounds.
- Final summary file: `bug-hunt-final-summary.md` in the report folder. It holds the final chat report, saved as is.
- Pause point: a step boundary where the run stops until the user or a scheduled prompt resumes it.

## Inputs

The user gives the inputs as arguments or answers the step-0 questions.

| Input | Argument | Default |
| --- | --- | --- |
| Repository path | first argument | If the current working directory is a git repository, that directory |
| Project name | `--name` | The folder name of the repository |
| GitHub repository | `--github` | None. Ask. Propose `owner/repo` from the `origin` remote, and say that the remote can hold an old name. |
| Analyzed commit | `--ref` | `HEAD` of the repository. The orchestrator resolves it to a commit SHA. |
| Base branch | `--base` | The default branch of `origin`, as a branch name without the remote prefix (`main`, not `origin/main`). If git cannot tell, ask. `none` turns off the base comparison. |
| Base source | `--base-from` | Default: `local`. `local`: the local branch. `remote`: a fresh clone of the branch from the remote into the scratch folder. |
| Report folder | `--report-dir` | None. Ask. |
| Report file | `--report-file` | `bug-hunt-report.md`. If that file exists, propose `bug-hunt-report-<YYYY-MM-DD>.md`. |
| Notes files with known bugs | `--known`, repeatable | None |
| Label of bug issues | `--bug-label` | `bug` |
| Context file for orientation | `--context` | None |
| Role of the user | `--role` | "Not stated" |
| Number of areas | `--areas` | 5 |
| Split threshold for pass 1 | `--split-threshold` | 40 findings |
| Experiments | `--experiments` | Default: ask at step 0, and propose `yes`. `yes`: agents can build, restore, test, and run code on snapshot copies in their work folders. `no`: agents only read code. |
| Services for experiments | step-0 answer | None. Examples: a database server, a container runtime. |
| Pause points | `--stop-after` | None. See [references/pauses.md](references/pauses.md). |
| Resume and start times | `--resume-at`, `--start-at` | None |
| Hunter model and effort | `--hunter-model`, `--hunter-effort` | `fable`, `max` |
| Verifier model and effort | `--verifier-model`, `--verifier-effort` | `opus`, `xhigh` |
| Auditor model and effort | `--auditor-model`, `--auditor-effort` | `opus`, `xhigh` |

Do not guess the report folder. Ask for it. Do not take the GitHub repository from the
remote without the user's OK. GitHub redirects a renamed repository, so the remote can show
an old name.
The context file is for orientation only. Do not read other files in its folder. If an agent needs one of them, the agent reads it.

## Rules for the whole run

These rules apply to the orchestrator. The agent files and the briefs carry them to the
agents. If a `CLAUDE.md` file conflicts with rule 1 or rule 2, rules 1 and 2 win.

### 1. The project is read-only

Another session can work in the project at the same time. For this reason, agents read code
only from the snapshots.

- Do not edit, build, test, or run anything in the project folder. Do not create files there. The only exception is the report folder, as the report-folder point below says.
- Against the live repository, run only these git commands: `rev-parse`, `remote get-url`, `ls-tree`, `log`, `show`, `diff` between two revisions, `blame`, `archive` with output into the scratch folder, and `--no-optional-locks status`. Always use `git -C "<repo>"`. The orchestrator follows this list too, also at cleanup.
- Do not run a plain `git status`. It can write the index. To see whether the project is unchanged, run `git -C "<repo>" --no-optional-locks status --porcelain`. Do not run `fetch`, `pull`, `checkout`, `switch`, `stash`, `reset`, `commit`, or any other command that writes.
- For a newer base than the live repository holds, the setup helper clones the base branch from the remote into the scratch folder. Never fetch into the live repository.
- In the report folder, create only new files whose names start with `bug-hunt` or `_bug-hunt`, and the `bug-hunt-artifacts` folder. Do not change or delete any file that existed before the run. This also holds when the report folder is inside the project. It is then the one exception to the first point.
- Run experiments only in a work folder inside the scratch folder. If the experiments input is not `yes`, run none. No GUI runs, no system-wide installs, and no changes to the machine configuration.
- The commands in this skill need a POSIX shell and Python 3. On Windows, run them with the Bash tool (Git Bash), not with PowerShell. If `python3` is not available, stop the run at step 0 and report this under "Blocked on me". The structure check script needs it.

### 2. No GitHub writes

Never create, edit, close, label, or comment on GitHub issues or pull requests. The user
reviews the report first. GitHub access in this skill is read-only. The known-issues
collector reads issues with the GitHub MCP tools. The hunters and verifiers can run the
read-only `gh` commands in their agent files.

### 3. The orchestrator checks structure, the verifiers check content

The orchestrator does not need to check every finding. Between steps, it runs only the structure
check in [references/structure-checks.md](references/structure-checks.md) and compares each
agent reply with its counts.

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
- If it is not installed, every brief points to the fallback rules in [references/plain-english-fallback.md](references/plain-english-fallback.md). The final report says that the fallback was used.

### 6. Crash-recovery progress files

Every agent that can run long keeps a progress file in the report folder: a `STATUS` line, a
checklist of steps, an append-only `## Log`, a `## Current draft` with the work in progress,
and a `## NEXT` with the single next action. The agent updates it at every step, resumes from
`## NEXT` after a crash, and deletes it when the deliverable is complete. A progress file that
is left behind means that work is not finished.

The orchestrator keeps `_bug-hunt-session-progress.md` in the same way. It updates the file at
each step boundary and after each agent reply. It records the agent ID of each dispatch, and
each pause with its resume job. After each dispatch, it writes this into `## NEXT`: "Waiting
for agent <ID> (<role>), dispatched <time>. If the agent runs, do not dispatch this role
again." If two agents run at the same time, the note names each one. The resume check in
this file tells a running agent from a stopped one. Edit progress files and the report with the Edit tool. A
script that rewrites a Markdown file can damage it. Two examples are a backslash escape, and
a split on a heading name that the text also quotes.

### 7. Models, effort, and dispatch

- Use the defaults in the Inputs table. The user's explicit choice of a model or an effort level always wins.
- The hunter default is Fable. Fable is never dispatched silently. The user's OK to the step-0 meta-plan approves the Fable dispatches and the effort levels in it. Without that OK, do not dispatch Fable.
- Pass `model` and `effort` on every dispatch of the three plugin agents. The agent files default to Opus, so a dispatch outside this skill never runs Fable.
- Dispatch the hunter, verifier, and auditor only with their plugin `subagent_type`. If that type is not available, stop the run and report it under "Blocked on me". Their briefs do not carry the read-only rules.
- Every dispatch is a single unnamed `Agent` call: no `name` and no `team_name`. Use `SendMessage` only for the restore case in "Failure handling".
- Every general-purpose brief says "do this work yourself, do not dispatch subagents". The three plugin agents cannot dispatch, because their `tools` lists have no `Agent` tool.
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
- If the session has a task tool (`TaskCreate` or `TodoWrite`), keep one task for each step, area, and verifier part. The user then sees the progress. A restart of Claude Code clears the list. After a restart, create it again from the session progress file.

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
every placeholder before you dispatch. A general-purpose helper sees only its brief. A plugin agent sees its agent file and its brief.

## Pipeline

### Pause points

After a step, an area, or a verifier part that is a pause point, stop as
[references/pauses.md](references/pauses.md) says. If the user asks for a stop, a start time,
or a resume time, read that file too.

### Resume check

Do this before step 0. If the report folder becomes known only from a step-0 answer, do it
then, before you show the meta-plan again.

1. If the report folder holds `_bug-hunt-session-progress.md`, read it and continue from its `## NEXT`. If it records the meta-plan approval, do not ask for it again. If `## NEXT` records a pause, do not continue. Wait for the user, or for the scheduled resume prompt that names this file.
2. If a snapshot or the digest is missing, run step 1 again in full with the commit SHAs from the progress file. If the report already lists `N-NN` IDs, tell the collector to keep them. Then run the step-1 structure check.
3. Write the scratch folder path that is now in use into the progress file before you fill the next brief.
4. If `## NEXT` says "Waiting for agent <ID>", find out if that agent still runs. The agent runs if this session dispatched it and its progress file is less than 30 minutes old. If it has no progress file yet, the dispatch time in the note must be less than 30 minutes ago. If the agent runs, write one line to chat: "Waiting for agent <ID> (<role>). If it stopped, say so." Then end the turn. A scheduled resume prompt that fires while the agent runs ends here. In all other cases, the agent stopped, for example after a crash or a restart. The user can also say that it stopped, or the agent reply can report a crash or a usage limit. Then restore the agent with `SendMessage` as "Failure handling" says. If that fails, go to point 5.
5. If an agent progress file exists for the step in `## NEXT`, fill the brief for that role again from the recorded values, add the resume note from [references/agent-briefs.md](references/agent-briefs.md), and dispatch it.

### Step 0. Meta-plan and questions

1. Resolve the inputs from the arguments. The command `rev-parse --abbrev-ref origin/HEAD` prints `origin/<branch>`. Remove the `origin/` prefix, because `{BASE}` is the branch name alone. For the defaults, use only light read-only calls: `git -C "<repo>" rev-parse --verify "<ref>^{commit}"`, `git -C "<repo>" rev-parse --abbrev-ref origin/HEAD`, `git -C "<repo>" remote get-url origin`, and `git -C "<repo>" log -1 --format=%cs "<base>"` for the date of the local base. Make sure that the report folder exists, and list the files in it that start with `bug-hunt` or `_bug-hunt`.
2. Pick the scratch folder. If the environment gives a session scratchpad directory, use it with a `bug-hunt` subfolder. Else, create a new folder in the system temp folder, for example `bug-hunt-<YYYYMMDD-HHMM>`. The scratch folder must not be inside the project or the report folder.
3. Dispatch the scoping helper. It proposes the areas from the tree of the analyzed commit.
4. Look for `simple-english:simple-english` in the list of available skills.
5. Write the meta-plan in chat. It has these parts:
   1. Inputs: a table with each value and where it came from (argument or default).
   2. Areas: a table with the number, name, paths, file count, size, and order.
   3. Excluded paths, each with a reason, for example vendored or generated code.
   4. Agents: a table with the model and effort of each role. Say in one sentence that the OK approves the Fable dispatches. If the `Agent` tool has no `effort` parameter, say that the agents run at the effort in their agent files. Not confirmed: the behavior on versions older than v2.1.292 (looked up in the sub-agents docs page, which gives only the minimum version of the per-call parameter).
   5. Files: the report path, the run context file, the final summary file, the artifacts folder, the progress file names, and the scratch folder. If the report folder is inside the analyzed repository, say so here. The run then creates new files in the project tree, and only there.
   6. Verification: the split threshold and the split rule of step 4.
   7. Base: the base branch and its source. For a local base, give the date of its last commit. If the analyzed commit is the base, or the base is `none`, say so.
   8. Experiments: whether agents can build, restore, test, and run code on snapshot copies, and which services, for example a database, are available.
   9. Pauses: the pause points, the resume times, and the start time, or "None".
   10. Run format: the orchestrator checks only the structure of the output (rule 3), and the verifiers and the auditor check the content. Chat gets at most one status line for each step and one final report (rule 8). Say in one sentence that the OK also accepts this run format.
   11. Plain English: whether `simple-english` is installed, or the fallback is used.
   12. Cleanup: the list of what step 6 deletes and what it keeps.
   13. Questions: a numbered list. Always ask the user to confirm the analyzed commit, the base and its source, and the GitHub repository name. Also ask for the bug label and the other known-bug sources, the experiments and services, and the pause points. Then add each question that blocks the run.
6. Ask only questions that block the run. Examples: the report folder is missing, the report file exists, the report folder already holds a `bug-hunt-artifacts` folder or a `_bug-hunt-progress-*.md` file and no resume applies (a new run would write into the files of the old run), the run context file or the final summary file exists and no resume applies (reuse the context file, or use the dated names `bug-hunt-context-<YYYY-MM-DD>.md` and `bug-hunt-final-summary-<YYYY-MM-DD>.md`), the base branch is unknown, the GitHub repository is not confirmed, Fable is not available, a plugin agent type for the hunter, verifier, or auditor is not available, or there is no known-issue source.
7. Wait for the user's explicit OK. If the user changes a value, apply the change. If the change raises a new question, show the meta-plan again. Else do not show it again.
8. After the OK, write `_bug-hunt-session-progress.md` in the report folder. Record the inputs, the commit SHAs, the base source, the scratch folder, the approved models and effort levels, the areas, the experiments and services, the pause points and times, and the approval itself. If a start time is set, schedule the start as [references/pauses.md](references/pauses.md) says, and end the turn.

### Step 1. Isolation

Dispatch the setup helper and the known-issues collector in the same message, so that they
run in parallel.

- The setup helper exports the analyzed commit to `<scratch>/snapshot-ref`. For a local base, it exports the base branch to `<scratch>/snapshot-base`. For a remote base, it clones the base branch into `<scratch>/snapshot-base` and reports the commit SHA. Record that SHA. The helper also creates `<scratch>/work` and the shared tools folder `<scratch>/tools`. If the analyzed commit and the base are the same commit, it skips the base export, and every finding gets "Also on base: Not applicable". If the base is `none`, it skips the base export, and the findings have no "Also on base" field.
- The collector writes the known-issues digest to `<scratch>/known-issues.md`.

Then run the structure check for step 1. Record the limits that the setup helper reports, such
as submodules or Git LFS files that the snapshots do not hold. They go into the Scope section.

### Step 2. Report skeleton

Write the report file from the skeleton in
[references/report-skeleton.md](references/report-skeleton.md). Fill the Scope section from the
meta-plan and the setup reply. Write one section for each area, in the approved order. Leave
the placeholders in the other sections. The agents replace them. Then write the run context
file from the template in the same file. If the user chose to reuse the run context file of
an earlier round, update that file for this run instead. Then run the structure check for step 2.

### Step 3. Search

For each area, in the approved order:

1. Compute the next ID with the `next-id` command in [references/structure-checks.md](references/structure-checks.md). The first area starts at `BH-01`.
2. Dispatch one hunter with the hunter brief. Tell the first hunter that it also fills the section "Known issues that this report does not repeat".
3. Wait for the reply. Do not dispatch the next hunter before this one finishes.
4. Run the structure check for step 3. Compare the reply with the counts.
5. Update the session progress file: the area is done, the next ID, and the agent ID. In the run context file, set the area to "Searched", and append the build and test notes of the reply under "Build and test notes".

Hunters run strictly one after the other. Later hunters read the "Notes for other areas" of
earlier hunters, and the numbering continues across areas. After the last hunter, run the
`open-notes` command. Each open note goes into the brief of the verifier part that holds the
area that the note names.

### Step 4. Verification pass 1

1. Count the findings. Call the number N.
2. If N is 0, skip this step. The auditor writes the Summary in step 5.
3. If N is at most the split threshold, use one part. Else, use `ceil(N / threshold)` parts. Each part covers whole areas. Choose the area borders that make the parts closest to equal size. Split inside an area only if that area alone has more findings than the threshold.
4. Dispatch one verifier for each part, one after the other, on the same report file. Tell the last part that it also writes the Summary.
5. After each part, run the structure check for step 4. Append the "Severity use" lines of the reply under "Severity notes" in the run context file. Later parts read them.

Each verifier tries to refute each finding in its range and sets one verdict: Confirmed,
Unconfirmed (needs owner review), Rejected, or Duplicate of #NN, N-NN, or BH-NN. The verdict rules
are in [references/report-format.md](references/report-format.md).

### Step 5. Verification pass 2

Dispatch one auditor. It makes sure that the whole report is valid, consistent, and complete
after the edits: fields against the Summary, cross-references, counts, links, and plain
English. It also writes the subsection "For the owner's review" at the end of the Summary.
Then run the structure check for step 5.

### Step 6. Cleanup

First, delete the scheduled jobs of the run: run `CronList`, and run `CronDelete` for each job
ID that the session progress file records. A job that fires after the run would act on a
progress file that no longer exists.

Dispatch the cleanup helper with the process IDs and start times from the WARN lines of the
structure check, and with the exact list of paths to delete:

- The scratch folder, with the snapshots, the digest, the tools folder, and every work folder.
- Every `_bug-hunt-progress-*.md` file in the report folder.

Keep the report file, the run context file, and the `bug-hunt-artifacts` folder. Then run the
structure check for step 6. To see whether the project is unchanged, use only the
`--no-optional-locks status` command of rule 1. As the last action before the final report,
delete `_bug-hunt-session-progress.md`.

### Step 7. Final report

Write one report in chat, in the language of the user's request. The report file itself stays
in English. If the instructions of the user define an end-of-run report format, use it, and put
the content below into its matching sections. Else use these three sections, in this order:

1. Blocked on me: the decisions that only the user can make. List each Unconfirmed finding by ID and point to "For the owner's review" in the Summary. If there are none, write "Nothing".
2. Changed: the report path, the run context file, the final summary file, and the artifacts folder with the number of subfolders. Say that the run made no change in the project, no commits, and no GitHub issues.
3. Found: the counts for each verdict. The Confirmed findings by severity, with ID and title, at most 10. The leads that the verifiers or the auditor reported but did not confirm. The limits of the run, the use of the plain-English fallback, any change from the meta-plan, and any leftover file.

Save the final report, as is, to `bug-hunt-final-summary.md` in the report folder with the
Write tool. If step 0 chose a dated name, use that name. Then post the same text in chat.

## Failure handling

- If an agent stops on a usage limit or crashes, dispatch a new agent of the same role. Give it the same brief and the resume note. The new agent reads the progress file and continues.
- If the user asks to restore a stopped agent, send a message to its recorded agent ID with `SendMessage`. The agent continues with its full history. After a restart of Claude Code, this works if the user resumes the same session. If it fails, dispatch a new agent with the resume note.
- If a structure check fails, dispatch one repair agent of the same role. Give it the same brief and the repair note with the list of defects. If the check fails again, stop the run. Keep all files, and report the defects under "Blocked on me".
- If the collector cannot reach GitHub, ask the user what to do. The user can reconnect the GitHub MCP server with `/mcp` or continue with the notes files only. Do not fall back to another GitHub client.
- If an agent reports a blocker, such as a missing snapshot, fix the cause with the right helper. Then dispatch the agent again.
