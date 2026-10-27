---
name: review-loop
description: "Iterative multi-agent review loop for a branch, a PR, a diff, a spec, a class, a method, or any file. Each cycle reviews, triages the findings on their merits, fixes only the proven findings, and reviews the fixes again."
when_to_use: "Use it for 'run a review loop', 'review and fix this branch', 'review and fix this PR', 'review and fix the spec', or '/review-loop'. For a review with no edits, such as 'review PR 42', use help-review-pr."
---

# Review Loop

This skill runs review cycles. In each cycle, one or more reviewer subagents review the target, and the orchestrator triages their findings. Then a fixer subagent tests each finding against a primary source and fixes only what it can prove. The next cycle re-reviews only the fix diff, or the whole target with `--no-commit`. The orchestrator is the session that runs this skill and dispatches the reviewer and the fixer.

## When NOT to use

- To act on pull-request review comments from human reviewers, use `dev-essentials:process-pr-comments`.
- To write or update a PR description, use the `dev-essentials:pr-composer` agent.
- For one review pass with no fixes and no loop, use `dev-essentials:help-review-pr` for a pull request, or ask Claude to review the diff inline.

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| `target=` | `branch` | What to review: `branch`, `pr <id>`, `commits <N>`, `diff <range>`, `file <path>`, `class <FQN>`, `method <FQN>`, or `spec <path>`. Phase 1 resolves it. |
| `--base <branch>` | detected from git | The base branch for the `branch` and `pr` targets. |
| `--rounds <N>` | `2` | The maximum number of review-fix-re-review cycles. The default gives one review-and-fix pass and one re-review of the fix diff. |
| `--skip <severities>` | `none` | Comma-separated severity tokens to defer **by label, unread**, without triage. Valid tokens: `blocker`, `critical`, `high`, `medium`, `low`, `nit`, and `none`. Each token is independent: `--skip medium,low` defers Medium and Low, but NOT Nit. The default `none` defers nothing by label. Every finding then goes to the merit-based triage of Phase 4 (see "Default configuration" and Phase 4). Do not pass an explicit set, for example `--skip medium,low,nit`, unless the user wants deferral by label. |
| `--reviewer <id>` | `general-purpose` | The reviewer subagent or subagents. One reviewer by default. Values: `general-purpose`, `audit-team`, `dual`, `feature-dev:code-reviewer`, `pair <a>+<b>`, `quad <a>,<b>,<c>,<d>`, or any `<plugin>:<agent>`. The values with more than one reviewer are opt-in, for targets that need several points of view. **`audit-team` is not an agent ID**. It is a slash command that takes a documentation `<path>`. So it works only for `target=spec <path>` and for a `target=file <path>` with the extension `.md`. For any other target, Phase 2 warns and uses `general-purpose`. |
| `--reviewer-model <model>` | `opus` | The model of each reviewer subagent, passed in the `model` field of each reviewer `Agent` call. The default is Opus, because a review needs judgment, and because this model also plans each fix (Phase 5, step 5a). It accepts any value of the `model` parameter of the `Agent` tool, or `inherit` for the model of the session. |
| `--reviewer-effort <level>` | `high` | The effort level of each reviewer dispatch, passed in the `effort` field of each reviewer `Agent` call. It also applies to the fix plan of step 5a and to the re-review of Phase 8. The reviewer-model subagents of the orchestrated mode use it too. It does not reach `/audit-team`, which dispatches its own agents. Valid values: `low`, `medium`, `high`, `xhigh`, and `max`. |
| `--reviewer-focus <tokens>` | the default list of the brief | Comma-separated focus tokens, for example `security,performance,test-coverage`. They replace the default focus list of the reviewer brief. `references/reviewer-briefs.md` defines the valid tokens and the rule for unknown tokens. |
| `--fixer <id>` | `general-purpose` | The subagent that tests and fixes the findings (the fixer). It takes one agent ID: `general-purpose` or any `<plugin>:<agent>`. The values `audit-team`, `dual`, `pair`, and `quad` are for reviewers only (see Phase 2). |
| `--fixer-model <model>` | `sonnet` | The model of the fixer, passed in the `model` field of the fixer `Agent` call. The default is Sonnet, because the fixer carries out an approach that the reviewer model already planned (Phase 5, step 5a). It accepts `inherit` for the model of the session. |
| `--fixer-effort <level>` | `medium` | The effort level of the fixer, passed in the `effort` field of the fixer `Agent` call. The default is `medium`, because the fixer carries out a plan that is already made. It accepts the same values as `--reviewer-effort`. |
| `--audit-team-args <...>` | none | Free text for the `/audit-team` command, added after the `<path>` argument that Phase 2 supplies. It works only with `--reviewer audit-team`. `references/audit-team-adapter.md` has the argument rules. A value of the user for `[agent-count]` or `[model]` always wins. |
| `--no-verify-fix` | off | Skip the fix edits of Phase 5. Phase 6 still runs on the existing code as a sanity check. Phase 7 does not run. Phase 9 still runs. |
| `--dry-run` | off | Skip the fix edits of Phase 5, skip Phase 6 (nothing changed, so there is nothing to build or test), and skip Phase 7. Phase 9 still runs. |
| `--no-commit` | off | Only for `target=spec` and `target=file`. A diff, branch, or PR target reads committed code, so a re-review does not see fixes that stay uncommitted. For another target, stop and ask. For a caller that keeps the target out of commits, for example a plan file in a gitignored folder. Phase 7 makes no commit, and the fixes stay in the working tree. Phase 6 skips its failure check, because no fix commit exists. Phase 8 re-reviews the whole target file. |
| `--interactive` | off | Wait for the user to acknowledge the Phase 4 triage before Phase 5. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |
| `--save-reports` | off | Write every full cycle report to `Notes/Reviews/`. This includes a run with `--rounds 1`. |
| `--print-reports` | off | Print every full cycle report in chat. This includes a run with `--rounds` 2 or more. |
| `--include-resolved` | off | Only for `target=pr <id>`. Phase 1 also keeps the resolved threads (`is_resolved: true`), and the reviewer brief gets the section "Previously addressed in this PR". The open threads (`is_resolved: false`) always go into the brief as the section "Open reviewer threads", with or without this flag. Other targets ignore the flag. |

## Default configuration

The defaults in the table above are the configuration that this loop is meant to run with. They ship with this skill. A global or per-repo `CLAUDE.md` does not have to state them, and a caller does not have to repeat them. Out of the box: **2 cycles, one reviewer on `--reviewer-model`, one fixer on `--fixer-model`, a commit per cycle, and nothing auto-deferred by severity label**. The reviewer works at `--reviewer-effort` and the fixer at `--fixer-effort`. For any other behavior, override only the flag that needs it.

- **The reviewer model plans each fix, and the fixer only carries it out**. See Phase 5, step 5a. The model that found the problem chooses the approach before anyone edits a file. It bases the approach on how the existing code already solves the same case.
- **The fix pass of every cycle gets its own commit**. Phase 7 commits after the first fix pass and after each later one. So the changes of each cycle land as a separate commit that a reader can review. If a caller wants a single commit, it squashes the round commits afterwards. Only `--no-commit` turns off Phase 7, for a target that stays out of commits.
- **Nothing is deferred by label**. Severity still orders the triage table and the deferred list of Phase 9. It does not decide on its own what gets fixed. Phase 4 decides that on the merits of each finding.
- **Fable is not a default reviewer, and never a silent one**. Use `--reviewer-model fable` only rarely, for large, complex, or critical-path change sets. Sometimes Fable is the idea of the orchestrator and not the instruction of the user. Then, with `--interactive`, ask the user first, every time, as the "Model selection" section of `dev-essentials:subagent-orchestration` says. Without `--interactive`, keep Opus (see "Autonomy").
- **An explicit choice of the user outranks these defaults**. If the user names a round count, a reviewer, a fixer, a model, an effort level, or a `--skip` set for a run, use it. These defaults are the baseline, not a policy to push the user back to.

## Autonomy

This workflow has three modes. The user picks one with a flag.

- Default (no flag): the run does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. The dangerous gates still stop. A dangerous gate comes before deletion of data, a post to an outside system, a push, or pull request creation. Examples of posts: GitHub comments, reviews, and issues, or documentation pages.
- `--interactive`: every gate stops and waits for the user, as the gate text says.
- `--autonomous`: no gate stops. This includes the dangerous gates. The flag is the yes of the user at each gate of this workflow, also at a gate whose text asks for an explicit yes. The run still stops for a question that blocks the work (see below).

These rules apply in all modes:

- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run passed without a stop. With `--autonomous`, also list each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It does not add steps. Some steps run only with a flag such as `--push`, `--commit-push`, or `--apply`, or only on a request of the user. Such a step still needs that flag or request.
- A flag that names an action approves that action for this run, so the action needs no new stop. Examples: `--push` and `--commit-push`. An action that a step of this workflow names as its default needs no new stop either.
- If this workflow has a merge step and the branch policy allows a merge without a review, `--autonomous` merges. Else it does not merge. Never bypass branch protection. Do not use an admin override, a force push, or a change to the branch policy. In the other modes, the merge stays with the user.
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. If both checks below pass, you can delete such a branch with `git branch -D`. First, its pull request is merged. Find the pull request with `list_pull_requests`, with `head: "<owner>:<branch>"` and `state: "all"`. `<owner>` is the `owner` value of the call. The default state lists open pull requests only, and GitHub ignores a `head` value without the `<owner>:` prefix. Then read the pull request with `pull_request_read` (`method: "get"`), and make sure that `merged` is `true`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the run cannot read the state of the pull request, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Flag interaction matrix

These flags change which phases run. Read this matrix before each phase:

| Flag | Phase 5 (fix edits) | Phase 6 (build/test) | Phase 7 (commit) | Phase 8 (loop) | Phase 9 (summary) |
|---|---|---|---|---|---|
| _(none)_ | runs | runs | commits | continues (if eligible) | runs |
| `--dry-run` | **skipped** | **skipped** (nothing changed) | **skipped** | **stops** (no edits to re-review) | runs |
| `--no-verify-fix` | **skipped** | runs against existing code | **skipped** | **stops** (no edits to re-review) | runs |
| `--no-commit` | runs | runs, with no failure check | **skipped** | continues (if eligible), and re-reviews the whole target | runs |

Rules:

- `--dry-run` and `--no-verify-fix` exclude each other. If a run has both, **STOP and ask the user which behavior to use** before any phase.
- `--interactive` and `--autonomous` do not depend on these two flags.

## Guardrails

These rules hold for the whole run.

- **Never push by default**. Commits stay local, and the push is a decision of the user. Do not push unless the user explicitly allows it, for example "you can push after each fix commit".
- **Never touch unrelated files**. Edit only the files that the triage names, plus a supporting file that the fix structurally needs (see section 6 of `references/verify-fix-discipline.md`). Do not start unrelated refactors.
- **Fix only what a primary source proves**. Apply only the findings with the verdict APPLY or PARTIAL. REJECT means no edit. See `dev-essentials:engineering-discipline` Rule 5.
- **Judge findings on their merits, not on their labels**. The default `--skip none` defers nothing unread. In return, Phase 4 records `blocking: true|false` on every finding. Without `--autonomous`, Phase 4 also asks the user about each fix that is not clearly safe or in scope, before the fixer touches it. Phase 8 reads the flag **in addition to** the severity, not instead of it. An unresolved `blocking: true` finding blocks `stop-clean` at any severity, and an unflagged Blocker, Critical, or High blocks it too.
- **Be honest about uncertainty**. Mark an unclear finding as PARTIAL or REJECT, and give the reason. Do not skip it in silence, and do not apply it blindly.
- **Do not over-fix**. Fix the findings of the triage only. This is not a refactoring session.
- **Respect `--rounds`**. Do not loop past the maximum. Report the unresolved findings under "Deferred items" in the final summary.
- **Build and test after every fix pass (Phase 6)**. No flag skips Phase 6 after a fix pass. This session owns every red signal after a fix round: investigate and fix it, or escalate to the user.
- **Filter the findings once, in Phase 4**. The reviewer reports every finding with a severity and a confidence, because a filter in the reviewer prompt drops real findings. Phase 4 decides what to fix. A usual count is about 1 Critical or High, 4 Medium, and 3 Low or Nit findings. The count is for each 1,000 lines of diff or file content. A count far above that is a signal for the triage, not a reason to drop findings. Then judge each Medium, Low, and Nit on its merit with more care. Do not ask for a second review.
- **Fall back to `general-purpose` for an unknown or failed agent ID**. Phase 2 has the rules. They hold for `--reviewer` and `--fixer`. If `general-purpose` is also not available, **STOP and ask the user to install at least one reviewer plugin**.
- **Take the round number from the cycle counter of this skill**. The counter starts at 1. Never take the round number from the conversation history.

## Report destination rules

The value of `--rounds` decides where a cycle report goes. At the end of a cycle, the real number of cycles is not known yet. With `--rounds 1`, the run prints the full cycle report in chat. With `--rounds` 2 or more, the run writes each cycle report to `Notes/Reviews/<target-slug>-cycle-<N>.md`, so that long reports do not fill the chat context.

- `--save-reports` writes each report to a file. This includes a run with `--rounds 1`.
- `--print-reports` prints each report in chat. This includes a run with `--rounds` 2 or more.
- The Phase 9 summary runs after the last cycle, so it uses the real number of cycles. It goes to `Notes/Reviews/<target-slug>-summary.md` in a run with more than one cycle or with `--save-reports`. Else it goes to chat.
- The run format (see "Run format") does not change these destinations. It changes only what chat shows. When a report goes to a file, chat gets one status line for it.

## Run format

The run format says what the orchestrator checks itself and how the run reports in chat. This section follows the section "Run format agreement" in `dev-essentials:subagent-orchestration`.

After Phase 2, state the run format in a few lines. If Phase 1 has a scope hint, add it. Do not wait for an answer. If the calling workflow already stated the same run format in this session, do not state it again.

- Check scope: the orchestrator checks the structure only. It makes sure that the target resolved and that each finding has a severity, a type, and a file reference. It makes sure that the fixer gave a verdict for each finding that it received. It also reads the Phase 6 result, and makes sure that each Phase 7 commit holds only the intended files. The fixer tests the content of each finding (APPLY, PARTIAL, or REJECT), and the re-review of the next round tests each fix. The fixes of the last round get no re-review, and the final report says so. The orchestrator does not re-read the cited code to test findings again.
- Reporting: when a cycle report goes to a file, chat gets at most one short status line for that cycle, for example "Cycle 1: 6 findings, 4 fixed, build passed, continue". If a cycle report goes to chat, print it. The Brief format and the full cycle reports go where the "Report destination rules" say. Questions that block the run still go to chat: the Phase 4 acknowledgment (with `--interactive`), and any finding that needs a decision of the user (without `--autonomous`). If the instructions of the user define an end-of-run report format, the final report uses it. Else print the Phase 9 summary. If a calling workflow runs this skill, give the Phase 9 summary to that workflow, and print only the status line.
- Agreement: unless the user objects, the run format applies from the statement after Phase 2. With `--interactive`, the acknowledgment of the Phase 4 triage is also the agreement. In three cases the agreement is implicit, and the run does not stop for it: the run has no `--interactive`, the user asked for full autonomy, or the request gives the same rules. The user can change the format at any time.

If the run format applies, the check scope replaces two things for this run only. The first is tiers 1 and 2 of the section `Trust but verify` in `dev-essentials:subagent-orchestration`. Tier 3 still applies. The second is any rule in the instructions of the user that asks the orchestrator to re-check every subagent claim. The triage judgment of Phase 4, Phase 6, and the Role 3 reads of the large-target mode still run.

## Severity and type taxonomy

Every finding has one severity and one type. Use these exact tokens in all output formats and phases. Do not invent new levels, and do not abbreviate. The triage of Phase 4 and the deferred list of Phase 9 depend on them.

- Severities, from the highest: `Blocker`, `Critical`, `High`, `Medium`, `Low`, `Nit`.
- Types: `Bug`, `Reliability`, `Security`, `Performance`, `Maintainability`, `Test`, `Style`, `Architecture`, `Spec`, `Docs`. Use `Spec` and `Docs` for targets that are not code.

The Common Rules of `references/reviewer-briefs.md` give the reviewer a one-line definition of each severity. `references/triage-matrix.md` gives the full definitions with examples, and the action for each severity.

## Phases (the workflow)

### Phase 1 — Resolve target

Turn `target=` into a diff or a set of files. Follow this table exactly. Do not guess.

| `target=` | Resolution |
|---|---|
| `branch` | Find `<base>`. A `--base <branch>` of the user always wins. Else detect it: (1) Run `git symbolic-ref refs/remotes/origin/HEAD`, and remove the prefix `refs/remotes/origin/`. This gives the default branch of the remote, for example `main`, `master`, or `release/1.0/master`. (2) If that command fails or prints nothing, try `git rev-parse --verify origin/main`, then `git rev-parse --verify origin/master`, and use the first that succeeds. (3) If none succeeds, **STOP and ask the user for the base branch**. Then run `git fetch origin <base>` to refresh the remote-tracking ref. If the fetch fails, for example with no network or no remote, **STOP and ask the user**. Do NOT fall back to a stale local `<base>` ref. Then diff with the remote-tracking name: `git diff origin/<base>...HEAD`. Never diff against a local `<base>` ref, because it can be missing or stale. |
| `pr <id>` | Read the PR with the GitHub MCP tool `pull_request_read` (`method: "get"`), with explicit `owner` and `repo` (see `dev-essentials:github-mcp-conventions`). If the MCP call fails (MCP not available, PR not found, or no auth), **STOP and ask the user**. Do NOT fall back to a local diff. From the PR metadata, take the target branch name (`base.ref`). Run `git fetch origin <targetBranch> "+refs/pull/<id>/head:refs/remotes/origin/pull/<id>/head"` (`dev-essentials:github-mcp-conventions` Rule 7). The `pull/<id>/head` ref also exists for a PR from a fork, whose source branch is not on `origin`. If the fetch fails, **STOP and ask the user**. Then diff with the remote-tracking names: `git diff origin/<targetBranch>...origin/pull/<id>/head`. Never rely on local branch names, because they can be missing or stale. **Thread fetch, at the same time as the diff (the two do not depend on each other):** call `pull_request_read` with `method: "get_review_comments"`. Read all pages with a bounded `perPage` (see `dev-essentials:github-mcp-conventions` Rule 3). By default, keep only the open threads (`is_resolved: false`). With `--include-resolved`, also keep the resolved threads (`is_resolved: true`). Phase 3 gets the threads. |
| `commits <N>` or `last-N` | `git diff HEAD~N..HEAD`. |
| `diff <range>` | `git diff <range>`, with the range as given. |
| `file <path>` | Read the file at `<path>` in full. |
| `spec <path>` | Read the file at `<path>` in full. Brief the reviewer for a spec review. |
| `class <FQN>` | Find the class with `grep -rn "class <SimpleName>"` under the repository root. If exactly one match exists, take that file and line range. If no match or more than one match exists, **STOP and ask the user**: "Which file and line range contains `<FQN>`?" Never pick a candidate in silence. |
| `method <FQN>` | First find the file of the containing type, as for `class <FQN>` (`grep -rn "class <ContainingType>"` under the repository root). If no file or more than one file matches, **STOP and ask the user** which file to use. In that file, search for `\b<MethodName>\b` followed by `(` on the same line or within 2 lines, for long parameter lists. If **exactly one** match exists, take the lines from the method declaration to its closing brace. Count braces, or read up to the next method or the end of the class. If **no match or more than one match** exists (overloads), **STOP and ask the user**: "Found `<N>` matches for method `<MethodName>` in `<file>`. Which line range do you want me to review?" Do NOT pick in silence. |

A free-form scope hint, for example "phases 5-13" or "cleanup module", goes into the reviewer brief as a context hint. The Brief format of the cycle repeats it as "scope hint: `<text>`", so that the user sees that the hint arrived.

### Phase 2 — Resolve reviewer + fixer

Before the dispatch, resolve `--reviewer` and `--fixer`. Use these rules exactly:

- `general-purpose`: a built-in agent type. It needs no lookup.
- `audit-team`: a **slash command, not an agent ID**, so it does not go through the `subagent_type` path of the `Agent` tool. Read `references/audit-team-adapter.md` and follow it. It has the target restriction, the argument mapping, the output mapping, and the source of the step 5a fix plan.
- `<plugin>:<agent>`: look for the ID in the list of available agent types that the session shows for the `Agent` tool. If the ID is not in that list, **fall back to `general-purpose` and print a warning**: "Reviewer `<id>` not found. Using `general-purpose`. To use this reviewer, install its plugin and run again."
  The dispatch can also fail at run time. Examples: the agent name is wrong, or the installed plugin version no longer has the agent. Then treat the ID as unknown, and apply the same fallback to `--reviewer` and `--fixer`. Print a warning that names the failed dispatch, for example "Agent `<id>` dispatch failed. Using `<fallback>`. Make sure that the agent name exists in the installed plugin."
- `dual`: dispatch `feature-dev:code-reviewer` and `general-purpose` in parallel. If `feature-dev` is not installed, use two `general-purpose` reviewers with two different briefs, and print a warning that names the fallback. If `general-purpose` is also not available, **STOP and ask the user to install at least one reviewer plugin**. Do NOT continue with no reviewer.
- `pair <a>+<b>` or `quad <a>,<b>,<c>,<d>`: resolve each ID on its own. If a slot does not resolve, replace ONLY that slot with `general-purpose`. Print a warning that names the slot, for example "Slot `<id>` not found. Using `general-purpose`." Do NOT turn the full pair or quad into `dual`.
- The **same fallback rule applies to `--fixer`**. An unknown fixer ID falls back to `general-purpose` with a warning. The values `audit-team`, `dual`, `pair <a>+<b>`, and `quad <a>,<b>,<c>,<d>` are for reviewers only. For such a `--fixer` value, also use `general-purpose`, and print a warning: "`--fixer` takes one agent ID. Using `general-purpose`."
- `--audit-team-args` with no `--reviewer audit-team`: if the user gave no `--reviewer` at all, read the args as an implicit `--reviewer audit-team`. Do not discard them in silence. If `--reviewer` has another value, ignore `--audit-team-args`, and print a warning: "`--audit-team-args` is set, but `--reviewer` is `<value>`, not `audit-team`. Ignoring `--audit-team-args`."

The fallback rule applies to every unknown agent ID. Each warning names the ID that did not resolve and the agent that replaces it.

After Phase 2, state the run format (see "Run format"). Do not wait for an answer.

### Phase 3 — Round-N review

Before you write the reviewer brief or resolve `--reviewer-focus` tokens, read `references/reviewer-briefs.md`. It has the Common Rules, the Full format of the reviewer report, and one brief for each target type. It also has the valid `--reviewer-focus` tokens and the rule for unknown tokens.

Build each reviewer prompt from these parts. For `audit-team`, build no prompt. See `references/audit-team-adapter.md` § "Phase 3". The reviewer does not see this skill or its files.

1. The Common Rules and the Full format, word for word.
2. The brief for the target type, with its placeholders filled in. Set Round N from the cycle counter of this skill.
3. The diff or the file contents that Phase 1 resolved. Do not ask the reviewer to fetch them again.
4. For `target=pr <id>`: the thread sections of the `pr` brief, filled from the threads of Phase 1. If Phase 1 found open threads, the section "Open reviewer threads" is always present. The section "Previously addressed in this PR" comes only with `--include-resolved`.

Dispatch the reviewers as `dev-essentials:subagent-orchestration` Rule 3 says. For more than one reviewer, put all `Agent` calls in one message, so that they run at the same time. Pass `--reviewer-model` in the `model` field of each reviewer call. Pass `--reviewer-effort` in the `effort` field of each reviewer call.

**Large-target orchestrated mode (optional)**. For a large target, Phase 3 can use a different dispatch shape that saves the context of the orchestrator. A large target has a diff of more than about 2,000 lines or 30 changed files. The mode also fits a target where `--reviewer-focus` alone does not reduce the reading enough. A Target Explorer subagent builds a fact map of the target, with no judgment. Parallel Area Explorer subagents return structured findings only, with no raw diff or file content. Last, the orchestrator reads only the lines that the findings point to, and makes sure that each diagnosis matches them. This is a **mode, not a replacement**: for smaller targets, the default dispatch above stays. `references/orchestrated-review.md` has the roles and the prompt templates.

### Phase 4 — Triage

**Count check (before triage):** compare the count of findings with the usual count of the "Guardrails" section. If the count is far above it, judge each Medium, Low, and Nit with more care in the steps below. Do not drop a finding unread, and do not ask for a second review.

After all reviewer output is in, write a triage table before any action:

```text
Round <N> findings:
  Blocker:  <X>  (will fix; <Y> blocking)
  Critical: <X>  (will fix; <Y> blocking)
  High:     <X>  (will fix; <Y> blocking)
  Medium:   <X>  (deferred — --skip medium; <Y> blocking)
  Low:      <X>  (deferred — --skip low; <Y> blocking)
  Nit:      <X>  (deferred — --skip nit; <Y> blocking)

A row with a merit deferral shows: (will fix <F>; deferred <D> on merit; <Y> blocking)

Proceeding to verify+fix <F> issues. Deferring <D>.
```

Apply `--skip` exactly. Each severity token in `--skip` is its own gate: `--skip medium,low` defers Medium and Low, but a Nit can still get a fix. With `--skip none` (the default), no row shows a `--skip` deferral. If Phase 4 deferred a finding of that severity on its merits, the row shows a merit deferral count. Otherwise it shows none. Without `--interactive`, write the triage into the cycle report, print its status line, and start Phase 5. With `--interactive`, print the triage, and **wait for the user to acknowledge it** before Phase 5. The acknowledgment is also the final agreement to the run format (see "Run format").

**Judge every finding on its merits, not on its label**. The default is `--skip none`, so that nothing is deferred unread. This does not mean that you fix everything without thought. For each finding, read the conclusion of the reviewer: the call **Must fix before merge**, **Acceptable risks**, or **Needs discussion** in the Conclusion section of the report. Do not triage on the severity label alone.

- A Medium is worth a fix at any label in two cases: it brings back a variant of the bug under repair, or it leaves the regression of the fix without test coverage.
- A Low or Nit that is only cosmetic is not worth a fix. Record it as deferred and move on.
- Low confidence alone does not defer a Blocker, Critical, High, or Medium finding. Phase 5 tests each finding against a primary source, and a finding that does not hold gets REJECT there. A Low or Nit finding with low confidence is deferred like a cosmetic one.
- If the fix is clear-cut, give it to Phase 5 as normal. Some fixes are **not** clearly safe or in scope: they need a large refactor, they touch a design decision, or the right resolution is truly ambiguous. For such a finding, without `--autonomous`, do not decide alone. Show the finding and the proposed fix or fixes as a short addendum to the triage (a short list, not a second review). Ask the user before the fixer touches it. This holds without `--interactive` too. The default approval covers the routine acknowledgment, never a real ambiguity. With `--autonomous`, do not ask. Decide as "Autonomy" says, and list the finding and the decision in the section "Decisions for your review" of the Phase 9 summary.

**Record `blocking: true|false` on every finding, independent of its severity label**. Phase 4 sets `blocking: true` on a finding that it concludes must be resolved before merge. By default, this is any Blocker, Critical, or High, plus any Medium, Low, or Nit that the judgment above raises. Set `blocking: false` for anything that Phase 4 records and moves on from. This includes a Blocker, Critical, or High that the user and the session explicitly agreed to defer. In that case, say so in the triage. The `(<Y> blocking)` count of each severity row only sums up this flag. Phase 8 (`stop-clean`) and the deferred list of Phase 9 read the flag of each finding, not that count. Phase 8 also reads the severity label (see Phase 8).

Phase 9 lists every deferred finding, deferred by `--skip` or by the judgment above.

`references/triage-matrix.md` has the full mapping from severity to action and the full definition of the `blocking` flag.

### Phase 5 — Verify-then-fix

**If `--dry-run` or `--no-verify-fix` is set, skip this phase** (see "Flag interaction matrix").

**Head gate for `target=pr <id>`**. The fixer edits the files of the branch that is checked out, and Phase 7 commits on that branch. The findings cite the lines of the PR head. So before the first fix of the run, compare `git rev-parse HEAD` with `git rev-parse origin/pull/<id>/head`. Phase 1 fetched that ref. Also run `git symbolic-ref -q HEAD`. On a detached HEAD it fails, and Phase 7 then makes commits that no branch holds. If the two SHAs are equal and HEAD is on a branch, continue. Else the checked-out branch is not the PR head:

- Without `--autonomous`, stop and ask the user to choose. The user checks out the PR branch at the PR head, and the run compares the SHAs again. Or the run continues as `--dry-run`.
- With `--autonomous`, do not ask. Continue as `--dry-run`. The Phase 9 summary says why: the checked-out branch was not the PR head, or HEAD was detached.

A run that continues as `--dry-run` skips Phases 5, 6, and 7, and Phase 8 stops (see "Flag interaction matrix").

**Head gate for `target=diff <range>`**. If the right side of the range is not `HEAD`, the same risk holds. The fixer then edits a branch that the findings do not cite. Before the first fix of the run, compare `git rev-parse HEAD` with `git rev-parse <right side of the range>`. If the two SHAs are equal, continue. Also run `git symbolic-ref -q HEAD`, as for `target=pr`. If the SHAs differ or HEAD is detached, follow the same two choices as for `target=pr`: ask the user, or with `--autonomous` continue as `--dry-run`. A range with `HEAD` on the right side needs no check. A range with no right side (`A..` or `A...`) has `HEAD` on its right side. A single revision `A` compares with the working tree, so it also needs no check.

**Step 5a: the reviewer model plans the fix, and the fixer only carries it out**. Every finding cleared for a fix gets a fix _approach_ before the fixer edits anything. The approach comes from the model of the reviewer (`--reviewer-model`). The plan comes from the reviewer subagent that raised the finding, or from a new dispatch. Use the same model and the same `--reviewer-effort`. The plan gives the general approach, the architecture, and the direction, **not** code line by line. Base it on how the existing code already handles the same case: find the working pattern in the codebase and follow it, and do not invent a new one. Put the plan of each finding into the fixer brief as the required approach. The fixer works from that plan, and does not choose its own approach from scratch. It still classifies each finding APPLY, PARTIAL, or REJECT by the rules below. A planned fix is not automatically a proven one.

**Step 5b: dispatch the fixer**. Pass `--fixer-model` in the `model` field of the fixer `Agent` call. Pass `--fixer-effort` in the `effort` field. The fixer keeps theories without proof out of the fix pass. This proof-before-fix rule is the main value of this skill over a plain fix loop. The fixer does not see this skill. So put these parts into the fixer brief:

1. The findings of the triage, each with its plan.
2. The rules below, word for word.
3. The absolute path of `references/verify-fix-discipline.md`, which is the base directory of this skill plus that path. Tell the fixer to read that file before its first edit.

The rules that the fixer MUST follow:

- Classify each finding as **APPLY**, **PARTIAL**, or **REJECT** before you touch any file.
  - APPLY: a primary source proves the finding: official docs, a known working example, the working code of the repository, CLAUDE.md, or a throwaway test. Apply the fix as described.
  - PARTIAL: the finding is partly correct, but the proposed fix needs a change. Apply the proven part, and note what you changed.
  - REJECT: no primary source proves the finding, or the finding is ambiguous, or it rests on pattern matching only. Do NOT apply it. Report the reason for the rejection.
- **Never touch unrelated files**. Edit only the files that the triage names, plus a directly related supporting file that the fix structurally needs (see section 6 of `references/verify-fix-discipline.md`). Examples: the matching `*Tests.cs` for a finding about missing test coverage, or the registration file for a finding about a missing configuration option. The strict no-drift default still applies: do not start unrelated refactors.
- **Do not over-fix**. Fix the named issue. Do not refactor the code around it, and do not fix nearby issues that are not on the triage list.
- **Be honest about uncertainty**. Mark an ambiguous finding as PARTIAL or REJECT, with reasons. Do not skip it in silence, and do not apply it blindly.
- After each fix, make sure that the edit matches the intent of the reviewer. If the intent is unclear, do not guess. Keep only the part of the edit that a primary source proves, and mark the finding PARTIAL. If no part is proven, undo the edit and mark the finding REJECT. In both cases, put the open question in the reason.
- Report the verdict of every finding, REJECT included. Discard nothing in silence.

Follow `dev-essentials:engineering-discipline` Rule 2: make no critical decision alone that the triage does not allow. Examples: a change of a public signature, a new DI dependency, or a weaker test assertion.

### Phase 6 — Build / test verify

**If `--dry-run` is set, skip this phase** (nothing changed, so there is nothing to build or test). With `--no-verify-fix`, Phase 6 runs on the existing code as a sanity check.

After the fixer finishes, dispatch the agent type `dev-essentials:test-runner` to run the build and the tests of the repository. Give it the absolute worktree path and the commands that the list below finds. Give it a test filter, or say in words that the whole test suite must run. If its status is STOPPED, answer its question and dispatch it again, or ask the user. Read only its report: the status, the verbatim result lines, and the errors. With `--no-verify-fix`, run them on the existing code. In all other cases, this build and test run is **mandatory**, and no flag skips it. The reason is `dev-essentials:engineering-discipline` Rule 1 (own every red signal in your session). A failure that the fix pass causes is a failure of this skill, not a pre-existing issue.

**Targets that are not code:** `target=spec`, or `target=file <path>` with a documentation extension (`.md`, `.txt`, `.rst`, `.adoc`). If `CLAUDE.md` documents no validator for them, **skip Phase 6**, with one note in the brief of the cycle: `Phase 6 skipped — non-code target with no validator`. If `CLAUDE.md` documents a validator, for example `openspec validate` or a doc linter, Phase 6 runs that validator instead of a build and tests.

**Code targets with no build command to detect:** these targets always point at code: `target=class <FQN>`, `target=method <FQN>`, and `target=file <path>` with an extension that is not a documentation format. Do **not** skip Phase 6 for them. Follow step 3 below, and ask the user: "What is the build command for this repo?" Record the answer, and run Phase 6 as normal. The mandatory build and test run has no exception for code targets.

Find the commands in this order, exactly:

1. Read the `CLAUDE.md` of the repository. If it documents a build command or a test command, use it.
2. If `CLAUDE.md` says nothing, detect a manifest in the repository. For every manifest type, use the same rule: **exactly one** file, use it. **None**, go to the next type. **Two or more**, **STOP and ask the user** with the list of files before you continue.
   - `*.sln` (C# and .NET): with exactly one `.sln`, run `dotnet build <solution>` and `dotnet test <solution>`. With two or more, ask: "Multiple solutions found: `<list>`. Which solution does Phase 6 build and test?" Use the answer for both commands.
   - Other stacks (Node, Rust, Python, Go, and others): this skill has no detection rule of its own for them. If the language has a clear analogue of `.sln`, apply the same rule to it: `package.json`, `Cargo.toml`, `pyproject.toml` or `setup.py`, `go.mod`, and so on. Run the build and test commands from the folder of the chosen manifest, not from the repository root. Change into that folder, or use the matching option (`--prefix`, `--manifest-path`, or `-C`). **If the language or the command form for that folder is unclear, STOP and ask the user for the build and test commands**. Do not guess, and do not fall back to a run from the repository root.
3. If no manifest matches: **STOP and ask the user**: "What is the build command for this repo?" Record the answer, and continue.

If the build or the tests fail:

- Report the failures honestly. Do not call them "pre-existing".
- If the run uses `--no-verify-fix`, or the fix pass of this cycle changed no file, no fix of this cycle is on disk. Then the failure is in the existing code. Do not run the failure check. Do not fix the failure in this loop. End the loop with `stop-blocked`. In the Phase 9 summary, list the failure with its file and its error message.
- With `--no-commit`, no fix commit exists. Do not run the failure check. Report the failure in the Phase 9 summary, and end the loop with `stop-blocked`.
- Without `--no-commit`, after a fix pass, do not guess the cause of a failure. Do not use file names or a read of the code to decide whether the fix pass caused it. Decide with a run. Phase 7 first commits the fixes of this cycle. Then do the failure check below.

Failure check (after the Phase 7 commit of this cycle). In this check, `<fix-commit>` is the Phase 7 commit of the review fixes of this cycle. It is never a regression-fix commit. Each run of a build or test command in this check is also a dispatch of the test runner. Its worktree path is the folder of that run.

1. Run `git status --porcelain` in the main worktree. Ignore the files that this loop wrote in this run. They are its cycle reports and summary under `Notes/Reviews/<target-slug>-*`, and any progress file of the loop. If it prints nothing else, the main worktree holds only `<fix-commit>`. Then the failed Phase 6 run is the result at `<fix-commit>`. If it prints other files, the main worktree also holds uncommitted changes. Then create a temporary worktree at `<fix-commit>`, in a folder outside the repository: `git worktree add --detach <temp-folder-1> <fix-commit>`. Run the build or test command that failed there. That run is the result at `<fix-commit>`.
2. If the command passed at `<fix-commit>`, skip this step, because the next step does not use the result at `<fix-commit>^`. Else, create a temporary worktree at the commit before the fixes, in a folder outside the repository: `git worktree add --detach <temp-folder-2> <fix-commit>^`. Run the build or test command that failed there. That run is the result at `<fix-commit>^`.
3. If the test tool can run only the failing tests, run only those in each temporary worktree. After its run, remove each temporary worktree with `git worktree remove --force <temp-folder>`. Remove it in every case: the run passes, fails, or cannot start.
4. Act on the two results:
   - The command passes at `<fix-commit>`: the committed code builds and passes, and the uncommitted changes in the main worktree cause the failure. Do not fix it in this loop. End the loop with `stop-blocked`. In the Phase 9 summary, list the failure, its error message, and the files that `git status --porcelain` printed.
   - The command fails at `<fix-commit>` and passes at `<fix-commit>^`: the fixes of this cycle broke the build or the tests. Treat the failure as a regression. Go back to Phase 5 with the failure and the diff of `<fix-commit>`, and try one more fix. Commit that fix (Phase 7), and run Phase 6 again. Do not run the failure check again in this cycle. If the fixer reports REJECT or PARTIAL, or Phase 6 fails again, end the loop with `stop-blocked`. Put the regression in the deferred list of Phase 9, and report to the user.
   - The command fails at `<fix-commit>` and at `<fix-commit>^` with the same error: the failure is also in the code before the fixes of this cycle. Do not fix it in this loop, because the fix is outside the review target. End the loop with `stop-blocked`. In the Phase 9 summary, list the failure with its file and its error message. Add the evidence: the command, and the SHA of the commit where it also fails. The user decides how to fix it (`dev-essentials:engineering-discipline` Rule 1).
   - In any other case, end the loop with `stop-blocked`. Examples: another error, or a command that cannot run in the worktree. In the Phase 9 summary, list the failure and the output of both runs.

The check only picks the next step. It never excuses a failure. Each path ends with a fix or with a report to the user.

### Phase 7 — Commit fixes

**If `--dry-run`, `--no-verify-fix`, or `--no-commit` is set, skip this phase** (see "Flag interaction matrix").

Stage and commit only the files that this fix pass changed. Never use `git add -A` or `git add .`.

Commit message format:

```text
Review round <N>: Fix <short summary of issues fixed>

<optional 1-3 lines explaining the most significant fix>
```

Rules:

- **One commit per round, every round**. The fix pass of the first round gets its own commit, and so does the fix pass of each later round. Never collect the rounds of a run into a single commit at the end. If a caller wants one commit, it squashes the round commits afterwards. Only `--no-commit` turns off this phase.
- Commit also after a failed Phase 6. If Phase 6 failed after a fix pass, commit the fixes of this cycle first. Then do the failure check of Phase 6, one time in each cycle. A regression fix from that check gets its own commit, with the subject `Review round <N>: Fix regression <short summary>`.
- **Never push by default**. The push is a decision of the user. The user can explicitly allow a push, for example "you can push after each fix commit".

### Phase 8 — Repeat or stop

Decide whether to run another cycle. The decision follows fixed rules.

- **Continue** only on two conditions, and both must hold. (a) The rounds used are fewer than `--rounds`. (b) The fixer applied at least one edit in this cycle, so new code is on disk.
  - If the fixer applied no edit in this cycle, **stop**, because there is no new code to re-review. Examples: all findings were REJECT, or the cycle ran with `--dry-run` or `--no-verify-fix`.
  - If the fixer applies no edit in a re-review cycle, skip Phase 6 in that cycle. There is no new code to build or test. Carry the build and test status of the previous cycle forward into Phase 9.
  - The re-review covers ONLY the files that the fix commit changed, not the full original target. This is on purpose: a re-review of the whole target mixes new findings with old deferred ones. With `--no-commit`, no fix commit exists, so the re-review covers the whole target file.
  - The re-review in Round N+1 always uses one `general-purpose` agent, for any `--reviewer` value. Dispatch it on `--reviewer-model` at `--reviewer-effort`, so that the re-review has the same judgment as Round 1. The reviewer setup (`audit-team`, `dual`, `pair`, `quad`) applies to Round 1 only. The goal is the question "did the fix resolve the issue, with no new regression?", not a full architecture review.
- **Stop** in every other case. Classify the stop verdict:
  - **stop-clean**: BOTH conditions hold. (1) No unresolved finding in the re-review scope is `blocking: true` or has the severity Blocker, Critical, or High. (2) No such finding is in the deferred list of the whole run. This covers three kinds of deferral. The first is by `--skip`. The second is after the unproven part of a PARTIAL verdict of the fixer or a REJECT verdict whose reason is missing proof. The third is by the merit judgment of Phase 4. A REJECT that a primary source refutes (the code is shown to be correct) resolves the finding. It is not a deferral, and Phase 9 lists it under "Rejected findings". Both halves of the test matter. `blocking: true` is the judgment of Phase 4 on each finding, so a flagged Medium, Low, or Nit blocks `stop-clean` exactly as a High does. The severity half reads the label, so an unflagged Blocker, Critical, or High can never clear the gate in silence. If either condition fails, use `stop-max-rounds` instead.
  - **stop-max-rounds**: the `--rounds` limit came before a re-review pass found the run clean. It covers all four cases that prevent `stop-clean`. (a) Issues remain open in the re-review scope. (b) `--skip` deferred every finding. (c) The fixer fixed every finding, but no re-review round ran to prove it. (d) Merge-blocking work is still open somewhere in the run, although the rounds limit was not reached. That work is a deferred Blocker, Critical, or High, for example through `--skip critical` or `--skip high`. It is also any unresolved finding that Phase 4 marked `blocking: true`, at **any** severity label.
  - **stop-blocked**: the build or the tests fail, and this session cannot fix them. Escalate to the user.

### Phase 9 — Final summary

Aggregate across all cycles. Follow the "Report destination rules": write to `Notes/Reviews/<target-slug>-summary.md` in a run with more than one cycle or with `--save-reports`, and else print in chat. If the run format applies, the final chat report follows the "Run format" section.

Format:

```text
## Review Loop Complete

Rounds: <N> of <max> max
Build: <passing (0 errors, 0 warnings) | failing (<details>) | skipped (no command resolved)>
Tests: <X passed, Y failed, Z skipped | not run>
Stop verdict: <stop-clean | stop-max-rounds | stop-blocked>

### Round 1 (<target-summary>)
  Found:    <B> Blocker, <C> Critical, <H> High, <M> Medium, <L> Low, <N> Nit
  Fixed:    <count> (APPLY=<A>, PARTIAL=<P>, REJECT=<R>)
  Deferred: <count> (per --skip / merit triage)

### Round 2 (re-review of fix diff, or of the whole target with `--no-commit`)
  Found: <count> issues
  Status: <clean | new issues>

...

### Deferred items (by severity; (blocking) = Phase 4 marked it must-fix-before-merge)
  [High]   H1: <short description> (blocking)
  [Medium] M1: <short description> (blocking)
  [Low]    L1: <short description>
  ...

### Rejected findings
  <#> REJECT: <reason>
  ...

### Decisions for your review (only with `--autonomous`)
  <#> <finding>: <decision and reason>
  ...
```

A `(blocking)` row, or a deferred Blocker, Critical, or High row, means that the run did not reach `stop-clean` (see Phase 8).

---

## Output formats

### Brief format (printed to chat after every cycle)

Print it at the end of every cycle. If the run format applies (see "Run format"), write it into the cycle report, and print only one status line. A run with more than one cycle collects these into the final summary of Phase 9.

```text
Cycle <N> — <target-summary>
  <count> findings: <Blk> Blocker, <Cri> Critical, <Hi> High, <Me> Medium, <Lo> Low, <Ni> Nit
  Triage: fix=<F>, deferred=<D> (per --skip / merit triage)
  Fix verdicts: APPLY=<A>, PARTIAL=<P>, REJECT=<R>
  Build: <pass|fail|skipped (no command resolved)>
  Tests: <X passed, Y failed, Z skipped | not run>
  Verdict: <continue|stop-clean|stop-max-rounds|stop-blocked>
```

### Full format

The Full format of the reviewer report is in `references/reviewer-briefs.md`, because the reviewer gets it with the Common Rules. Phase 3 reads that file in every run. Each cycle report uses the same format, and goes to chat or to `Notes/Reviews/<target-slug>-cycle-<N>.md` as the "Report destination rules" say.

## Files and related skills

| File or skill | When to read it, or why this skill depends on it |
|---|---|
| `references/reviewer-briefs.md` | Phase 3, in every run: the Common Rules, the Full format, a brief for each target type, and the `--reviewer-focus` tokens. |
| `references/orchestrated-review.md` | Phase 3, only in the large-target orchestrated mode. |
| `references/audit-team-adapter.md` | Phase 2, only with `--reviewer audit-team`. |
| `references/triage-matrix.md` | Phase 4: the severity scale, the action for each severity, and the `blocking` flag. |
| `references/verify-fix-discipline.md` | Phase 5: the playbook of the fixer. Read it before the fixer dispatch, and give its path to the fixer. |
| `examples/branch-review.md` | A full review of a feature branch, with both report formats filled in with real numbers. |
| `examples/spec-review.md` | A review of a spec change document of any spec framework. The example uses an OpenSpec change as one case. It shows the `audit-team` adapter and the findings. |
| `dev-essentials:engineering-discipline` | Rule 1 (own every red signal) drives the build and test run of Phase 6. Rule 2 (no critical decision alone) drives the REJECT of a signature change that the triage did not allow, in Phase 5. Rule 5 (no claim without proof) drives the primary-source rule of the reviewer and the fixer. |
| `dev-essentials:subagent-orchestration` | Rule 3 for the reviewer dispatch of Phase 3 and the fixer dispatch of Phase 5. Independent `Agent` calls go in one message. "Model selection" for Fable. `Trust but verify` and "Run format agreement" for the run format. |
| `dev-essentials:github-mcp-conventions` | For `target=pr <id>`: how to call `pull_request_read` with explicit `owner` and `repo`, and how to paginate (Rule 3). |
