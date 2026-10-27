---
name: optimize-skill
description: >-
  Optimize one Claude Code skill for tokens and clarity, and keep its
  behavior. The run audits the skill, applies the plan in local commits, and
  makes sure that the skill still behaves the same. It never pushes.
when_to_use: >-
  Use it for "optimize this skill", "cut the tokens of this skill", or "audit
  this skill against the skill docs". Do not use it to review a code change.
  Use review-loop for that.
argument-hint: "<skill-folder|plugin:skill> [--report-dir=<path>] [--settled=<file>] [--auditor-model=<model>] [--applier-model=<model>] [--reviewer-model=<model>] [--review-fixer-model=<model>] [--interactive] [--autonomous]"
---

# Optimize skill

This skill makes one skill shorter and clearer, and keeps what the skill does. The main
session is the orchestrator. It collects the facts, dispatches the agents, and decides the
open items. The agents write the audit, apply it, and review it.

Earlier runs forgot two rules most often. A cut must not drop behavior (rule 1). The
orchestrator decides open items from the source of truth, not from the taste of the auditor
(rule 3).

## Terms

- Target: the skill that the run optimizes. Its files are `SKILL.md`, the files in its `references/`, `examples/`, and `scripts/` folders, and the agent files that the skill dispatches.
- Audit report: the Markdown file where the auditor writes the items, the executor section, and the "Not changed on purpose" list.
- Item: one planned change in the audit report, with an ID such as `O-01`.
- Settled list: the decisions of the user that the run must not change.
- Source of truth: the files that record decisions of the user. Examples are memory files, `CLAUDE.md` files, earlier plans and audits, the CHANGELOG, and commit messages.
- Open item: an item whose fix plan or risk offers a choice, or that changes behavior on purpose. Step 2 decides it.
- Pointer grep: a `grep` command that proves that a moved text has one home and that every link to it resolves.
- Behavior review: the step-5 review with one goal, "did the optimization keep behavior".
- Progress file: a `_`-prefixed file where an agent records its steps, so that a new agent can resume after a crash.

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| first argument | none, ask | The target: a skill folder, or a `plugin:skill` name in the current repository |
| `--report-dir` | none, ask | The folder for the audit report and the review report. Git must not track it. |
| `--settled` | none | A file with more settled decisions. The orchestrator adds its lines to the Settled list. |
| `--auditor-model` | `opus` | The model of the auditor |
| `--applier-model` | `sonnet` | The model of the applier |
| `--reviewer-model` | `opus` | The model of the behavior reviewer |
| `--review-fixer-model` | `sonnet` | The model of the review fixer |
| `--interactive` | off | Stop at every decision gate, and ask about each open item and each disputed finding. Without it, the run decides them itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the stop before a deletion that the user did not approve. The run still stops for a question that blocks the work. See "Autonomy". |

## Autonomy

This workflow has three modes. The user picks one with a flag: the default (no flag), `--interactive`, or `--autonomous`. A gate is a step where the run can stop and ask the user. This table lists each gate of this workflow and what each mode does there.

| Gate | Default | `--interactive` | `--autonomous` |
| --- | --- | --- | --- |
| Step 0 item 8: the scope | Continue | Wait for the OK | Same as default |
| Step 2: open items and disputed findings | Decide, and list them under "Decisions for your review" | Ask | Same as default |
| Step 2 item 5: delete a file that this run did not create | Ask before Step 3, unless the user approved it before | Same | No stop |
| Step 2 item 6: the decisions | Continue | Wait for the OK | Same as default |
| Step 6: the review triage | Continue | Wait for the OK | Same as default |

The run never pushes and never posts.

These rules apply in every mode:

- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that the run cannot fix also stops the run. Do not ask in other cases.
- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default of the gate, and continue.
- The final report lists each gate that the run passed without a stop. With `--autonomous`, it also lists each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It adds no steps. A step that runs only with a flag such as `--push` still needs that flag, and the flag is the approval of that step.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.

## Rules for the whole run

### 1. Cuts keep behavior

- Every instruction of the target keeps one home that the reader of that instruction reads. A moved block keeps its text, or the item gives the new text.
- A safety rule still reaches the agent or the step that needs it. An agent sees only its brief and its agent file, so each agent file stays self-sufficient. A rule that the orchestrator and an agent both need keeps a copy in each.
- A step that moves text to a reference file names that file at the step that needs it, before the step uses it.
- If an item changes behavior on purpose, it is an open item (step 2). It never hides in a Tokens item.

### 2. The Settled list wins

Never change a decision on the Settled list. The auditor plans no item against it. The applier
rejects an item that breaks it. The reviewer reports each change to it as a finding.

### 3. The orchestrator decides from the source of truth

At step 2 and step 6, decide each open item and each disputed finding from the source of
truth. The taste of the auditor or the reviewer is not a reason. If the source of truth does
not decide it, it is a critical decision. "Autonomy" says who decides it.

### 4. Commits stay local

The run makes at most two local commits: one at step 3 and one at step 6. Never push. Never
edit a `CLAUDE.md` file.

### 5. Mark what is not proven

Every claim that an agent did not prove starts with "Not proven:" and says where the
agent looked.

### 6. Plain English

All report text and all new skill text follow the skill `simple-english:simple-english`. If it
is not installed, they follow the fallback rules of the skill `bug-hunt` in this plugin:
`${CLAUDE_SKILL_DIR}/../bug-hunt/references/plain-english-fallback.md`. The final report says
that the fallback was used.

### 7. Dispatch

- Pass `model` on every dispatch. The user's explicit choice of a model always wins.
- Every dispatch is a single unnamed `Agent` call with `subagent_type: "general-purpose"`.
- Follow the skill `dev-essentials:subagent-orchestration` for everything else about dispatch.

### 8. Failures

If an agent stops or a fact test fails, send the agent the resume note or the defects with
`SendMessage`. If that fails, dispatch the role again with the same brief and `{RESUME_NOTE}`
or `{DEFECTS}`. Record the SHA of the commit from the reply of the agent. If the parent of that commit is
the base commit of that step, it is the commit of the agent. If a fact test
failed and that commit exists, the defects text must say: "Amend commit `<SHA>` with
`git -C "<repo>" commit --amend` and the same pathspec. Do not make a second commit." This
holds for the `SendMessage` repair and for the dispatch again. If the commit does not exist,
for example because the fact test "The commit exists" failed, the defects text must say: "No
commit of this step exists. Make the commit." Never amend the base commit of the user, and
never amend the commit of another step. Then do the fact tests again. If the repair fails again, stop the run, keep all files, and report the failure
under "Blocked on me".

### 9. Shell

The commands in this skill need a POSIX shell, git, and the `claude` CLI. On Windows, run them
with the Bash tool (Git Bash), not with PowerShell.

## Agents and dispatches

| Step | Role | Model | Writes |
| --- | --- | --- | --- |
| 1 | Auditor | auditor model | the audit report |
| 3 | Applier | applier model | the target files, one commit |
| 5 | Behavior reviewer | reviewer model | the review report |
| 6 | Review fixer | review fixer model | the target files, one commit |

The folder of this skill is `${CLAUDE_SKILL_DIR}`. The brief for each role is in
[references/briefs.md](references/briefs.md). Fill every placeholder before you dispatch.

## Pipeline

### Step 0. Scope and the Settled list

1. Resolve the target folder. It must be inside a git repository, not in a plugin cache. If it is not, stop and ask for the source folder.
2. List the target files. For each `subagent_type` of the form `plugin:agent` in the target, add the agent file `agents/<agent>.md` of that plugin. If the target is outside a plugin, take its agent files from `.claude/agents/` of the project.
3. Resolve the report folder. Do not guess it. Make sure that git does not track it: `git -C "<repo>" check-ignore -q "<report-dir>/"` succeeds, or the folder is outside the repository. If neither holds, stop and ask.
4. Record the base commit and the branch: `git -C "<repo>" rev-parse HEAD` and `git -C "<repo>" rev-parse --abbrev-ref HEAD`. Run `git -C "<repo>" status --porcelain -- "<target files>"`. If the output lists a target file, stop and ask.
5. Build the Settled list from the request, the `--settled` file, and the source of truth. Each line names the decision and its source.
6. Find the earlier audits and plans of the target in the report folder and in the source of truth. The auditor must not repeat or undo their items.
7. Look for `simple-english:simple-english` in the list of available skills. If it is not installed, make sure that the fallback file of rule 6 exists. If it does not, stop and ask.
8. Write the scope in chat: the target files with their sizes (`wc -c -w`), the report folder, the base commit, and the branch. Also write the Settled list, the earlier audits, and the models. With `--interactive`, wait for the user's OK. Else continue.

### Step 1. Audit and plan

Dispatch the auditor with the auditor brief. The auditor reads the guideline sources itself
and writes the audit report in the form of
[references/audit-report-format.md](references/audit-report-format.md).
[examples/bug-hunt-audit.md](examples/bug-hunt-audit.md) shows a full audit report in that form.

When the auditor replies, make sure that the report exists and that each item has every field
of the format. Also make sure that the report ends with the executor section and the "Not
changed on purpose" list. If a part is missing, send the auditor the list of gaps (rule 8).

### Step 2. Decide the open items

1. List the open items.
2. Decide each one from the source of truth (rule 3). Write a "Decision:" line under every open item. The value is APPLY, APPLY alternative (and its name), or REJECT, with its source.
3. If the source of truth does not decide an item, it is a critical decision. Choose the option that keeps the current behavior, because the audit report is not an approved plan. List the item under "Decisions for your review" in the final report. With `--interactive`, ask the user instead.
4. If an item breaks the Settled list, mark it "Decision: REJECT (Settled)".
5. If an item deletes a file that this run did not create, ask the user before step 3. If the user approved that deletion earlier or the run has `--autonomous`, do not ask.
6. With `--interactive`, show the decisions and wait for the user's OK. Else continue.
7. If no item is left to apply, skip steps 3 to 6 and say so in the final report.

### Step 3. Apply

Just before the dispatch, run `git -C "<repo>" status --porcelain -- "<target files>" "<executor paths>"`. The executor paths are the other files that the executor section names, for example the CHANGELOG. If the output lists a path, stop and ask, because the pathspec commit takes the whole file.

Dispatch the applier with the applier brief. When it replies, do these fact tests yourself:

- The commit exists. `git -C "<repo>" show --stat <commit>` lists only the target files, the new reference files, and the other files that the executor section names.
- The base commit is the parent of the commit, and the commit is HEAD: `git -C "<repo>" rev-parse <commit>^ HEAD` prints the base SHA and then the commit SHA.
- The reply has a class (APPLY, PARTIAL, or REJECT) for each item, and a reason for each PARTIAL and REJECT.
- The reply has the output of every pointer grep, the `SKILL.md` word count, and the validator output. If the executor section names a test command, the reply also has its output. The validators and the tests pass.
- `git -C "<repo>" status --short` shows no other changed target file.

If a fact test fails, send the applier the list of defects (rule 8). Do not judge the
content of the edits. The behavior review does that.

### Step 4. Prepare the review

Record the commit of step 3. The review compares the base commit of step 0 with it. If the
applier rejected an item that step 2 decided, add the item and the reason to the reviewer brief.

### Step 5. Behavior review

Dispatch the behavior reviewer with the reviewer brief. It runs one cycle and writes the
review report.

### Step 6. Fix the review findings

1. Triage each finding. Accept a finding that shows a lost or changed behavior. Reject a finding that only states a preference, or that breaks the Settled list. Decide disputed findings from the source of truth (rule 3). With `--interactive`, show the triage and wait for the user's OK. Else continue.
2. If no finding is accepted, skip the dispatch.
3. Else dispatch the review fixer with the accepted findings. It makes the second commit.
4. Do the fact tests of step 3 again for this commit, with the step-3 commit in place of the base commit. In place of a class for each item, the reply gives a fix for each accepted finding.

### Step 7. Final report

Write one report in chat, in the language of the user's request. If the instructions of the
user define an end-of-run report format, use it. Else use these three sections, in this order:

1. Blocked on me: the questions that wait for the user, and any failed fact test. If there are none, write "Nothing".
2. Changed: the two commits with their files, the audit report, the review report, and the `SKILL.md` size before and after (words and characters). Say that the run did not push.
3. Found: the item counts by class, the rejected items with their reasons, the accepted and rejected review findings, and the lists that "Autonomy" asks for.

Delete the progress files of the agents that finished. Keep the two reports.
