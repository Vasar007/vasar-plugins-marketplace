---
name: review-loop
description: "Iterative multi-agent review loop for a branch, a PR, a diff, a spec, a class, a method, or any file. Each cycle reviews, triages the findings on their merits, fixes only the proven findings, and reviews the fixes again."
when_to_use: "Use it for 'run a review loop', 'review and fix this branch', 'review and fix this PR', 'review and fix the spec', or '/review-loop'. For a review with no edits, such as 'review PR 42', use help-review-pr."
---

# Review Loop

This skill runs review cycles. In each cycle, one or more reviewer subagents review the target and write a fix plan for each finding. The orchestrator triages the findings. Then the fixer tests each finding against a primary source and fixes only what it can prove. Phase 5, step 5b names the fixer: the orchestrator or a subagent. The next cycle re-reviews only the fix diff, or the whole target with `--no-commit`. The orchestrator is the session that runs this skill. It dispatches the reviewers. If step 5b chooses a fixer subagent, it also dispatches that subagent.

## Done test

The run is done after Phase 8 sets a stop verdict and Phase 9 runs. The last chat message of the run must hold these things. The first is this line as plain text: `Stop verdict: <stop-clean | stop-max-rounds | stop-blocked>`. The second is the path of each file that the run fixed. If the run fixed no file, the message says so. Write both in every run. These cases often lose them: the summary goes to a file, the instructions of the user set the format of the final report, or a calling workflow gets the summary. The user and the calling workflow read the verdict from this line.

After a compaction, invoke this skill again before the next phase.

## Hard rules

These rules hold for the whole run.

- **Never push by default**. Commits stay local, and the push is a decision of the user. Do not push unless the user explicitly allows it, for example "you can push after each fix commit".
- **Never touch unrelated files**. Edit only the files that the triage names, plus a supporting file that the fix structurally needs (see section 6 of `references/verify-fix-discipline.md`). Do not start unrelated refactors.
- **Fix only what a primary source proves**. Apply only the findings with the verdict APPLY or PARTIAL. REJECT means no edit. See `dev-essentials:engineering-discipline` Rule 5.
- **Judge findings on their merits, not on their labels**. The default `--skip none` defers nothing unread. In return, Phase 4 records `blocking: true|false` on every finding. Outside the full mode, Phase 4 also asks the user about each fix that is not clearly safe or in scope. It asks before the fixer touches it. Phase 8 reads the flag **in addition to** the severity, not instead of it. An unresolved `blocking: true` finding blocks `stop-clean` at any severity, and an unflagged Blocker, Critical, or High blocks it too.
- **Respect `--rounds`**. Do not loop past the maximum. Report the unresolved findings under "Deferred items" in the final summary.
- **Build and test after every fix pass (Phase 6)**. No flag skips Phase 6 after a fix pass. This session owns every red signal after a fix round: investigate and fix it, or escalate to the user.
- **Take the round number from the cycle counter of this skill**. The counter starts at 1. Never take the round number from the conversation history.
- Before the first fix, Phase 5 compares `HEAD` with the reviewed head. This holds for `target=pr`, and for a `target=diff` whose right side is not `HEAD`.

## When not to use

- To act on pull-request review comments from human reviewers, use `dev-essentials:process-pr-comments`.
- To write or update a PR description, use the `dev-essentials:compose-pr` skill.
- For one review pass with no fixes and no loop, use `dev-essentials:help-review-pr` for a pull request, or ask Claude to review the diff inline.

## Parameters

Read `references/parameters.md` before Phase 1. It gives the default and the meaning of each flag.

## Default configuration

The defaults in `references/parameters.md` are the configuration that this loop is meant to run with. They ship with this skill. A global or per-repo `CLAUDE.md` does not have to state them, and a caller does not have to repeat them. Out of the box: **2 cycles, one reviewer on `--reviewer-model` that also plans each fix, a commit per cycle, and nothing auto-deferred by severity label**. The orchestrator applies the fixes, unless Phase 5, step 5b sends the fix set to one fixer subagent on `--fixer-model`. The reviewer works at `--reviewer-effort` and the fixer subagent at `--fixer-effort`. For any other behavior, override only the flag that needs it.

- **The reviewer model plans each fix, and the fixer only carries it out**. The reviewer writes the fix plan of each finding in its report (Phase 3), so no separate dispatch plans the fixes. See Phase 5, step 5a. The model that found the problem chooses the approach before anyone edits a file. It bases the approach on how the existing code already solves the same case.
- **The fix pass of every cycle gets its own commit**. Phase 7 commits after the first fix pass and after each later one. So the changes of each cycle land as a separate commit that a reader can review. If a caller wants a single commit, it squashes the round commits afterwards. Only `--no-commit` turns off Phase 7, for a target that stays out of commits.
- **Nothing is deferred by label**. Severity still orders the triage table and the deferred list of Phase 9. It does not decide on its own what gets fixed. Phase 4 decides that on the merits of each finding.
- **Fable is not a default reviewer, and never a silent one**. Use `--reviewer-model fable` only rarely, for large, complex, or critical-path change sets. Sometimes Fable is the idea of the orchestrator and not the instruction of the user. Then, in the interactive mode, ask the user first, every time, as the "Model selection" section of `dev-essentials:subagent-orchestration` says. Outside the interactive mode, keep Opus for the reviewer (see "Autonomy").
- **An explicit choice of the user outranks these defaults**. If the user names a round count, a reviewer, a fixer, a model, an effort level, or a `--skip` set for a run, use it. These defaults are the baseline, not a policy to push the user back to. An explicit `--fixer`, `--fixer-model`, or `--fixer-effort` also sends every fix set to the fixer subagent (Phase 5, step 5b).

## Autonomy

Before the first step, load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the modes, the rules for every mode, and the hard stops. This table lists each gate of this workflow and what each mode does there.

| Gate | Partial (the default) | Interactive | Full |
| --- | --- | --- | --- |
| Phase 4: the triage | Continue | Wait for the acknowledgment | Same as partial |
| Phase 4: a fix that is not clearly safe or in scope | Ask | Ask | Decide, and list it under "Decisions for your review" |
| Phase 5: head gate for `target=pr` and `target=diff` | Stop and ask | Same | Continue as `--dry-run`, and say why |
| Push | Never, unless the user allows it in words | Same | Same |
| Fable on the own initiative of the agent | Keep Opus for the reviewer. A fixer subagent moves up by the model ladder, and the summary names the step | Ask before each Fable dispatch | Same as partial |

## Flag interaction matrix

These flags change which phases run. Read this matrix before each phase:

| Flag | Phase 5 (fix edits) | Phase 6 (build/test) | Phase 7 (commit) | Phase 8 (loop) | Phase 9 (summary) |
|---|---|---|---|---|---|
| _(none)_ | runs | runs | commits | continues (if eligible) | runs |
| `--dry-run` | **skipped** | **skipped** (nothing changed) | **skipped** | **stops** (no edits to re-review) | runs |
| `--no-verify-fix` | **skipped** | runs against existing code | **skipped** | **stops** (no edits to re-review) | runs |
| `--no-commit` | runs | runs, with no failure check | **skipped** | continues (if eligible), and re-reviews the whole target | runs |

Rules:

- `--dry-run` and `--no-verify-fix` exclude each other. If a run has both, **stop and ask the user which behavior to use** before any phase.
- The `--mode` of the run does not depend on these two flags.

## Guardrails

These rules hold for the whole run.

- **Be honest about uncertainty**. Mark an unclear finding as PARTIAL or REJECT, and give the reason. Do not skip it in silence, and do not apply it blindly.
- **Do not over-fix**. Fix the findings of the triage only. This is not a refactoring session.
- **Filter the findings once, in Phase 4**. The reviewer reports every finding with a severity and a confidence, because a filter in the reviewer prompt drops real findings. Phase 4 decides what to fix. A usual count is about 1 Critical or High, 4 Medium, and 3 Low or Nit findings. The count is for each 1,000 lines of diff or file content. A count far above that is a signal for the triage, not a reason to drop findings. Then judge each Medium, Low, and Nit on its merit with more care. Do not ask for a second review.
- **Fall back to `general-purpose` for an unknown or failed agent ID**. Phase 2 has the rules. They hold for `--reviewer` and `--fixer`. If `general-purpose` is also not available, **stop and ask the user to install at least one reviewer plugin**.

## Report destination rules

The notes folder is the folder that `${CLAUDE_PLUGIN_ROOT}/references/notes-root.md` gives. Read that file before the first read or write in the notes folder. The reviews folder is `Reviews/` in the notes folder.

The value of `--rounds` decides where a cycle report goes. At the end of a cycle, the real number of cycles is not known yet. With `--rounds 1`, the run prints the full cycle report in chat. With `--rounds` 2 or more, the run writes each cycle report to a file in the reviews folder. The file name is `<target-slug>-cycle-<N>.md`. So long reports do not fill the chat context.

- `--save-reports` writes each report to a file. This includes a run with `--rounds 1`.
- `--print-reports` prints each report in chat. This includes a run with `--rounds` 2 or more.
- The Phase 9 summary runs after the last cycle, so it uses the real number of cycles. It goes to `<target-slug>-summary.md` in the reviews folder in a run with more than one cycle or with `--save-reports`. Else it goes to chat.
- The run format (see "Run format") does not change these destinations. It changes only what chat shows. When a report goes to a file, chat gets one status line for it. For the Phase 9 summary, chat also gets the `Stop verdict:` line and the fixed-file paths of the done test. If the `Not covered:` line is not `none`, chat gets it too.

## Run format

The run format says what the orchestrator checks itself and how the run reports in chat. This section follows the section "Run format agreement" in `dev-essentials:subagent-orchestration`.

After Phase 2, state the run format in a few lines. If Phase 1 has a scope hint, add it. Do not wait for an answer. If the calling workflow already stated the same run format in this session, do not state it again.

- Check scope: if the orchestrator is not the fixer, it checks the structure only. It makes sure that the target resolved and that each finding has a severity, a type, and a file reference. It makes sure that the fixer gave a verdict for each finding that it received. It also reads the Phase 6 result, and makes sure that each Phase 7 commit holds only the intended files. The fixer tests the content of each finding (APPLY, PARTIAL, or REJECT). If the orchestrator is the fixer (Phase 5, step 5b), it reads the cited code and tests each finding itself. The re-review of the next round tests each fix. The fixes of the last round get no re-review, and the final report says so. The orchestrator does not re-read the cited code to test the verdict of a fixer subagent again.
- Reporting: when a cycle report goes to a file, chat gets at most one short status line for that cycle, for example "Cycle 1: 6 findings, 4 fixed, build passed, continue". If a cycle report goes to chat, print it. The Brief format and the full cycle reports go where the "Report destination rules" say. The Brief format is in `references/output-formats.md`. Questions that block the run still go to chat: the Phase 4 acknowledgment (in the interactive mode), and any finding that needs a decision of the user (outside the full mode). If the instructions of the user define an end-of-run report format, the final report uses it. Else print the Phase 9 summary. In both cases, the final report holds the `Stop verdict:` line of the done test. If a calling workflow runs this skill, give the Phase 9 summary to that workflow. Print only the status line, the `Stop verdict:` line, the fixed-file paths of the done test, and a `Not covered:` line that is not `none`.
- Agreement: unless the user objects, the run format applies from the statement after Phase 2. In the interactive mode, the acknowledgment of the Phase 4 triage is also the agreement. In these cases the agreement is implicit, and the run does not stop for it: the run is not in the interactive mode, the user asked for full autonomy, or the request gives the same rules. The user can change the format at any time.

If the run format applies, the check scope replaces these things for this run only. The first is tiers 1 and 2 of the section `Trust but verify` in `dev-essentials:subagent-orchestration`. Tier 3 still applies. The second is any rule in the instructions of the user that asks the orchestrator to re-check every subagent claim. The triage judgment of Phase 4, Phase 6, and the Role 3 reads of the large-target mode still run.

## Run as a workflow

If the user asks for a workflow run (the Workflow tool), keep the phases of this skill in the script. A workflow takes no input in the middle of a run.

- The reviewer and the fixer are separate `agent()` steps with the briefs of Phases 3 and 5.
- The triage of Phase 4 runs between them: in the main session between two workflows, or as its own `agent()` step. It judges each finding on its merits. A rule in code that sorts the findings by severity is no triage.
- Outside the full mode, a finding that needs a decision of the user gets no fix in this run. Ask the user after the run.
- The fixer step does not commit. Phase 6 runs in a later step. If Phase 6 is green, Phase 7 commits. Else end the workflow, and finish Phases 6 and 7 in the main session.
- After the run, the main session sets the stop verdict of Phase 8 and does Phase 9.

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
| `branch` | Find `<base>`. A `--base <branch>` of the user always wins. Else detect it: (1) Run `git symbolic-ref refs/remotes/origin/HEAD`, and remove the prefix `refs/remotes/origin/`. This gives the default branch of the remote, for example `main`, `master`, or `release/1.0/master`. (2) If that command fails or prints nothing, try `git rev-parse --verify origin/main`, then `git rev-parse --verify origin/master`, and use the first that succeeds. (3) If none succeeds, **stop and ask the user for the base branch**. Then run `git fetch origin <base>` to refresh the remote-tracking ref. If the fetch fails, for example with no network or no remote, **stop and ask the user**. Do not fall back to a stale local `<base>` ref. Then diff with the remote-tracking name: `git diff origin/<base>...HEAD`. Never diff against a local `<base>` ref, because it can be missing or stale. Run `git merge-base origin/<base> HEAD`, and keep it as the base SHA for Phase 6. |
| `pr <id>` | Read the PR with the GitHub MCP tool `pull_request_read` (`method: "get"`), with explicit `owner` and `repo` (see `dev-essentials:github-mcp-conventions`). If the MCP call fails (MCP not available, PR not found, or no auth), **stop and ask the user**. Do not fall back to a local diff. From the PR metadata, take the target branch name (`base.ref`). Run `git fetch origin <targetBranch> "+refs/pull/<id>/head:refs/remotes/origin/pull/<id>/head"` (`dev-essentials:github-mcp-conventions` Rule 7). The `pull/<id>/head` ref also exists for a PR from a fork, whose source branch is not on `origin`. If the fetch fails, **stop and ask the user**. Then diff with the remote-tracking names: `git diff origin/<targetBranch>...origin/pull/<id>/head`. Never rely on local branch names, because they can be missing or stale. Run `git merge-base origin/<targetBranch> origin/pull/<id>/head`, and keep it as the base SHA for Phase 6. **Thread fetch, at the same time as the diff (the two do not depend on each other):** call `pull_request_read` with `method: "get_review_comments"`. Read all pages with a bounded `perPage` (see `dev-essentials:github-mcp-conventions` Rule 3). By default, keep only the open threads (`is_resolved: false`). With `--include-resolved`, also keep the resolved threads (`is_resolved: true`). Phase 3 gets the threads. |
| `commits <N>` or `last-N` | `git diff HEAD~N..HEAD`. Run `git rev-parse HEAD~N`, and keep it as the base SHA for Phase 6. |
| `diff <range>` | `git diff <range>`, with the range as given. For a three-dot range `A...B`, run `git merge-base A B`, with `HEAD` for an empty side. For any other range, run `git rev-parse` on the left side. Keep the SHA as the base SHA for Phase 6. |
| `file <path>` | Read the file at `<path>` in full. |
| `spec <path>` | Read the file at `<path>` in full. Brief the reviewer for a spec review. |
| `class <FQN>` | Find the class with `grep -rn "class <SimpleName>"` under the repository root. If exactly one match exists, take that file and line range. If no match or more than one match exists, **stop and ask the user**: "Which file and line range contains `<FQN>`?" Never pick a candidate in silence. |
| `method <FQN>` | First find the file of the containing type, as for `class <FQN>` (`grep -rn "class <ContainingType>"` under the repository root). If no file or more than one file matches, **stop and ask the user** which file to use. In that file, search for `\b<MethodName>\b` followed by `(` on the same line or within 2 lines, for long parameter lists. If **exactly one** match exists, take the lines from the method declaration to its closing brace. Count braces, or read up to the next method or the end of the class. If **no match or more than one match** exists (overloads), **stop and ask the user**: "Found `<N>` matches for method `<MethodName>` in `<file>`. Which line range do you want me to review?" Do not pick in silence. |

A free-form scope hint, for example "phases 5-13" or "cleanup module", goes into the reviewer brief as a context hint. The Brief format of the cycle repeats it as "scope hint: `<text>`", so that the user sees that the hint arrived.

### Phase 2 — Resolve reviewer + fixer

Before the dispatch, resolve `--reviewer` and `--fixer`. Use these rules exactly:

- `general-purpose`: a built-in agent type. It needs no lookup.
- `audit-team`: a **slash command, not an agent ID**, so it does not go through the `subagent_type` path of the `Agent` tool. Read `references/audit-team-adapter.md` and follow it. It has the target restriction, the argument mapping, the output mapping, and the source of the step 5a fix plan.
- `<plugin>:<agent>`: look for the ID in the list of available agent types that the session shows for the `Agent` tool. If the ID is not in that list, **fall back to `general-purpose` and print a warning**: "Reviewer `<id>` not found. Using `general-purpose`. To use this reviewer, install its plugin and run again."
  The dispatch can also fail at run time. Examples: the agent name is wrong, or the installed plugin version no longer has the agent. Then treat the ID as unknown, and apply the same fallback to `--reviewer` and `--fixer`. Print a warning that names the failed dispatch, for example "Agent `<id>` dispatch failed. Using `<fallback>`. Make sure that the agent name exists in the installed plugin."
- `dual`: dispatch `feature-dev:code-reviewer` and `general-purpose` in parallel. If `feature-dev` is not installed, use two `general-purpose` reviewers with two different briefs, and print a warning that names the fallback. If `general-purpose` is also not available, **stop and ask the user to install at least one reviewer plugin**. Do not continue with no reviewer.
- `pair <a>+<b>` or `quad <a>,<b>,<c>,<d>`: resolve each ID on its own. If a slot does not resolve, replace only that slot with `general-purpose`. Print a warning that names the slot, for example "Slot `<id>` not found. Using `general-purpose`." Do not turn the full pair or quad into `dual`.
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

**Large-target orchestrated mode (optional)**. For a large target, Phase 3 can use a different dispatch shape that saves the context of the orchestrator. A large target has a diff of more than about 2,000 lines or 30 changed files. The mode also fits a target where `--reviewer-focus` alone does not reduce the reading enough. A Target Explorer subagent builds a fact map of the target, with no judgment. Parallel Area Explorer subagents return structured findings only, with no raw diff or file content. Last, the orchestrator reads only the lines that the findings point to, and makes sure that each diagnosis matches them. This is a **mode, not a replacement**: for smaller targets, the default dispatch above stays. `references/orchestrated-review.md` has the roles and the prompt templates. In that file, `{REVIEW_LOOP_DIR}` stands for `${CLAUDE_SKILL_DIR}`, the folder of this skill.

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

Apply `--skip` exactly. Each severity token in `--skip` is its own gate: `--skip medium,low` defers Medium and Low, but a Nit can still get a fix. With `--skip none` (the default), no row shows a `--skip` deferral. If Phase 4 deferred a finding of that severity on its merits, the row shows a merit deferral count. Otherwise it shows none. Outside the interactive mode, write the triage into the cycle report, print its status line, and start Phase 5. In the interactive mode, print the triage, and **wait for the user to acknowledge it** before Phase 5. The acknowledgment is also the final agreement to the run format (see "Run format").

**Judge every finding on its merits, not on its label**. The default is `--skip none`, so that nothing is deferred unread. This does not mean that you fix everything without thought. For each finding, read the conclusion of the reviewer: the call **Must fix before merge**, **Acceptable risks**, or **Needs discussion** in the Conclusion section of the report. Do not triage on the severity label alone.

- A Medium is worth a fix at any label in these cases: it brings back a variant of the bug under repair, or it leaves the regression of the fix without test coverage.
- Defer a Low or Nit finding. There are these exceptions: the reviewer put it under **Must fix before merge**, or one of the cases above applies to it. The reviewer reports every finding, so a Low or Nit under **Acceptable risks** or **Needs discussion** is a suggestion, not a defect. Record it as deferred and move on.
- Low confidence alone does not defer a Blocker, Critical, High, or Medium finding. Phase 5 tests each finding against a primary source, and a finding that does not hold gets REJECT there.
- If the fix is clear-cut, give it to Phase 5 as normal. Some fixes are **not** clearly safe or in scope: they need a large refactor, they touch a design decision, or the right resolution is truly ambiguous. For such a finding, outside the full mode, do not decide alone. Show the finding and the proposed fix or fixes as a short addendum to the triage (a short list, not a second review). Ask the user before the fixer touches it. This holds outside the interactive mode too. The default approval covers the routine acknowledgment, never a real ambiguity. In the full mode, do not ask. Decide as "Autonomy" says, and list the finding and the decision in the section "Decisions for your review" of the Phase 9 summary.

**Record `blocking: true|false` on every finding, independent of its severity label**. Phase 4 sets `blocking: true` on a finding that it concludes must be resolved before merge. By default, this is any Blocker, Critical, or High, plus any Medium, Low, or Nit that the judgment above raises. Set `blocking: false` for anything that Phase 4 records and moves on from. This includes a Blocker, Critical, or High that the user and the session explicitly agreed to defer. In that case, say so in the triage. The `(<Y> blocking)` count of each severity row only sums up this flag. Phase 8 (`stop-clean`) and the deferred list of Phase 9 read the flag of each finding, not that count. Phase 8 also reads the severity label (see Phase 8).

Phase 9 lists every deferred finding, deferred by `--skip` or by the judgment above.

`references/triage-matrix.md` has the full mapping from severity to action and the full definition of the `blocking` flag.

### Phase 5 — Verify-then-fix

**If `--dry-run` or `--no-verify-fix` is set, skip this phase** (see "Flag interaction matrix").

**Head gate for `target=pr <id>`**. The fixer edits the files of the branch that is checked out, and Phase 7 commits on that branch. The findings cite the lines of the PR head. So before the first fix of the run, compare `git rev-parse HEAD` with `git rev-parse origin/pull/<id>/head`. Phase 1 fetched that ref. Also run `git symbolic-ref -q HEAD`. On a detached HEAD it fails, and Phase 7 then makes commits that no branch holds. If the two SHAs are equal and HEAD is on a branch, continue. Else the checked-out branch is not the PR head:

- Outside the full mode, stop and ask the user to choose. The user checks out the PR branch at the PR head, and the run compares the SHAs again. Or the run continues as `--dry-run`.
- In the full mode, do not ask. Continue as `--dry-run`. The Phase 9 summary says why: the checked-out branch was not the PR head, or HEAD was detached.

A run that continues as `--dry-run` skips Phases 5, 6, and 7, and Phase 8 stops (see "Flag interaction matrix").

**Head gate for `target=diff <range>`**. If the right side of the range is not `HEAD`, the same risk holds. The fixer then edits a branch that the findings do not cite. Before the first fix of the run, compare `git rev-parse HEAD` with `git rev-parse <right side of the range>`. If the two SHAs are equal, continue. Also run `git symbolic-ref -q HEAD`, as for `target=pr`. If the SHAs differ or HEAD is detached, follow the same choices as for `target=pr`: ask the user, or in the full mode continue as `--dry-run`. A range with `HEAD` on the right side needs no check. A range with no right side (`A..` or `A...`) has `HEAD` on its right side. A single revision `A` compares with the working tree, so it also needs no check.

**Step 5a: the reviewer model plans the fix, and the fixer only carries it out**. Every finding cleared for a fix gets a fix _approach_ from the model of the reviewer (`--reviewer-model`) before the fixer edits anything. The approach is the **Fix plan** line of the finding in the reviewer report. It gives the general approach, the architecture, and the direction, **not** code line by line. It follows how the existing code already handles the same case. So no separate dispatch plans the fixes. One plan dispatch on `--reviewer-model` at `--reviewer-effort` runs only for the findings that have no usable plan. Give it all such findings of the cycle in one call, with the triage decision of each. A finding has no usable plan in these cases:

- The report gives it no fix plan. Examples: the `audit-team` reviewer (see `references/audit-team-adapter.md`), the large-target orchestrated mode, or a reviewer that left the line out.
- Phase 4 changed what the fix must do, and the user named no fix. If the user named the fix, that answer is the plan.
- The fix is the regression fix after the failure check of Phase 6.

The fixer works from the plan of each finding, and does not choose its own approach from scratch. It still classifies each finding APPLY, PARTIAL, or REJECT by the rules below. A planned fix is not automatically a proven one. The plan of a finding that Phase 4 deferred stays unused.

**Step 5b: choose the fixer**. In this skill, the fixer is the one who applies the fixes of a cycle: the orchestrator or a fixer subagent. Choose with the delegation tests of Rule 1 of `dev-essentials:subagent-orchestration`. The context test decides most fix sets. Phases 6 to 9 need only the verdicts and the changed paths. If the reads and the edits of the fix set put many files into the main context, dispatch a fixer subagent. Else the orchestrator applies the fixes itself. A few bounded edits in the files that the fix plans name stay in the orchestrator. Decide from the fix plans, not from the files that this session already holds. Name the test in the Brief format of the cycle. If the user or a calling workflow names `--fixer`, `--fixer-model`, or `--fixer-effort`, dispatch the fixer subagent for every fix set. An explicit choice outranks this default.

The fixer keeps theories without proof out of the fix pass. This proof-before-fix rule is the main value of this skill over a plain fix loop. In the orchestrator, read `references/verify-fix-discipline.md` before the first edit of the cycle, and follow it and the rules below.

A fixer subagent gets `--fixer-model` in the `model` field of its `Agent` call and `--fixer-effort` in the `effort` field. It does not see this skill. So put these parts into its brief:

1. The findings of the triage, each with its plan.
2. The rules below, word for word.
3. The absolute path of `references/verify-fix-discipline.md`, which is the base directory of this skill plus that path. Tell the fixer to read that file before its first edit.

The rules that the fixer must follow:

- Classify each finding as **APPLY**, **PARTIAL**, or **REJECT** before you touch any file.
  - APPLY: a primary source proves the finding: official docs, a known working example, the working code of the repository, CLAUDE.md, or a throwaway test. Apply the fix as described.
  - PARTIAL: the finding is partly correct, but the proposed fix needs a change. Apply the proven part, and note what you changed.
  - REJECT: no primary source proves the finding, or the finding is ambiguous, or it rests on pattern matching only. Do not apply it. Report the reason for the rejection.
- **Never touch unrelated files**. Edit only the files that the triage names, plus a directly related supporting file that the fix structurally needs (see section 6 of `references/verify-fix-discipline.md`). Examples: the matching `*Tests.cs` for a finding about missing test coverage, or the registration file for a finding about a missing configuration option. The strict no-drift default still applies: do not start unrelated refactors.
- **Do not over-fix**. Fix the named issue. Do not refactor the code around it, and do not fix nearby issues that are not on the triage list.
- **Be honest about uncertainty**. Mark an ambiguous finding as PARTIAL or REJECT, with reasons. Do not skip it in silence, and do not apply it blindly.
- After each fix, make sure that the edit matches the intent of the reviewer. If the intent is unclear, do not guess. Keep only the part of the edit that a primary source proves, and mark the finding PARTIAL. If no part is proven, undo the edit and mark the finding REJECT. In both cases, put the open question in the reason.
- Report the verdict of every finding, REJECT included. Discard nothing in silence.

Follow `dev-essentials:engineering-discipline` Rule 2: make no critical decision alone that the triage does not allow. Examples: a change of a public signature, a new DI dependency, or a weaker test assertion.

### Phase 6 — Build / test verify

**If `--dry-run` is set, skip this phase** (nothing changed, so there is nothing to build or test). With `--no-verify-fix`, Phase 6 runs on the existing code as a sanity check.

After the fixer finishes, run the build and the tests of the repository one time in the main loop, before the Phase 7 commit. Use the commands that the list below finds, in the worktree of the fixes. Run them as one filtered command that prints only the result lines and the errors. For .NET, use the build filter and the test filter of `dev-essentials:dotnet-build-test`. Keep the exit code of each command. If each command exits with code 0 and the result line shows zero failed tests, the run is green. Any other result is not green. Use a test filter, or run the whole test suite. If the test run can take longer than 10 minutes, dispatch the agent type `dev-essentials:test-runner`. Its brief gives the absolute worktree path and the same commands. It gives the test filter, or says in words that the whole test suite must run. It also says that the run can take longer than 10 minutes. If its status is STOPPED, answer its question and dispatch it again, or ask the user. Read only its report. With `--no-verify-fix`, run them on the existing code. In all other cases, this build and test run is **mandatory**, and no flag skips it. The reason is `dev-essentials:engineering-discipline` Rule 1 (own every red signal in your session). A failure that the fix pass causes is a failure of this skill, not a pre-existing issue.

**Targets that are not code:** `target=spec`, or `target=file <path>` with a documentation extension (`.md`, `.txt`, `.rst`, `.adoc`). If `CLAUDE.md` documents no validator for them, **skip Phase 6**, with one note in the brief of the cycle: `Phase 6 skipped — non-code target with no validator`. If `CLAUDE.md` documents a validator, Phase 6 runs that validator instead of a build and tests. It can be, for example, the validator of a spec framework or a doc linter.

**Code targets with no build command to detect:** these targets always point at code: `target=class <FQN>`, `target=method <FQN>`, and `target=file <path>` with an extension that is not a documentation format. Do **not** skip Phase 6 for them. Follow step 3 below, and ask the user: "What is the build command for this repo?" Record the answer, and run Phase 6 as normal. The mandatory build and test run has no exception for code targets.

Find the commands in this order, exactly:

1. Read the `CLAUDE.md` of the repository. For a `branch`, `pr`, `commits`, or `diff` target, read the copy at the base SHA that Phase 1 kept: `git show <base SHA>:CLAUDE.md`. A change can edit the commands that judge it. Each fix commit moves `HEAD`, so never use `HEAD` or a name that is relative to it. With no root file at the base SHA, read `.claude/CLAUDE.md` there. Also read at the base SHA each file that the base copy imports with `@`. If the base has no `CLAUDE.md`, go to step 2. For another target, read the file in the worktree. If the file documents a build command or a test command, use it.
2. If `CLAUDE.md` names no build command and no test command, detect a manifest in the repository. For every manifest type, use the same rule: **exactly one** file, use it. **None**, go to the next type. **Two or more**, **stop and ask the user** with the list of files before you continue.
   - `*.sln` (C# and .NET): with exactly one `.sln`, run `dotnet build <solution>` and `dotnet test <solution>`. With two or more, ask: "Multiple solutions found: `<list>`. Which solution does Phase 6 build and test?" Use the answer for both commands.
   - Other stacks (Node, Rust, Python, Go, and others): this skill has no detection rule of its own for them. If the language has a clear analogue of `.sln`, apply the same rule to it: `package.json`, `Cargo.toml`, `pyproject.toml` or `setup.py`, `go.mod`, and so on. Run the build and test commands from the folder of the chosen manifest, not from the repository root. Change into that folder, or use the matching option (`--prefix`, `--manifest-path`, or `-C`). **If the language or the command form for that folder is unclear, stop and ask the user for the build and test commands**. Do not guess, and do not fall back to a run from the repository root.
3. If no manifest matches: **Stop and ask the user**: "What is the build command for this repo?" Record the answer, and continue.

Run the lint command of the `CLAUDE.md` of step 1 after the tests, also after failed tests.

If the build, the tests, or the lint fail:

- Report the failures honestly. Do not call them "pre-existing".
- If the run uses `--no-verify-fix`, or the fix pass of this cycle changed no file, no fix of this cycle is on disk. Then the failure is in the existing code. Do not run the failure check. Do not fix the failure in this loop. End the loop with `stop-blocked`. In the Phase 9 summary, list the failure with its file and its error message.
- With `--no-commit`, no fix commit exists. Do not run the failure check. Report the failure in the Phase 9 summary, and end the loop with `stop-blocked`.
- Without `--no-commit`, after a fix pass, do not guess the cause of a failure. Do not use file names or a read of the code to decide whether the fix pass caused it. Decide with a run. Phase 7 first commits the fixes of this cycle. Then do the failure check below.

Failure check (after the Phase 7 commit of this cycle). In this check, `<fix-commit>` is the Phase 7 commit of the review fixes of this cycle. It is never a regression-fix commit. The script `scripts/failure_check.py` of this skill does the check. It needs Python 3, git, and bash. On Windows, run it in the Bash tool (Git Bash). Run it from the folder where Phase 6 ran the failed command:

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/failure_check.py" --fix-commit <fix-commit> --command "<failed command>" --ignore "<glob>"
```

- `--command` is the build, test, or lint command that failed, without the output filter of Phase 6. With more than one failed command, give the first one in the order build, tests, lint. If the test tool can run only the failing tests, give that command. The script runs it with bash.
- Give one `--ignore` for each kind of file that this loop wrote in this run, as a glob relative to the repository root: the cycle reports and the summary (`<reviews folder>/<target-slug>-*`) and any progress file of the loop. Leave out a file outside the repository.
- The script makes each temporary worktree in a folder outside the repository, and removes it in every case. It stops each run of the command after 280 seconds. So give the Bash call a `timeout` of 600000. If the failed Phase 6 run took longer than 4 minutes, run the script with the Bash option `run_in_background: true`. Then add `--timeout <seconds>` with the time limit of one run, and wait for the notification that the script ended.
- A `MADE <path>` line with no `REMOVED <path>` line names a worktree that is still there. Remove it with `git worktree remove --force <path>`. An `EXPORTED <path>` line with no `REMOVED <path>` line names a plain folder that is still there: delete it by hand, because `git worktree remove` does not apply to it.
- A `WARN:` line names a worktree or a folder that the script cannot delete, often because a process of the build still runs. After that process ends, delete the folder by hand. List each `WARN` line in the Phase 9 summary.
- If `python3` is not available, the script exits with code 2, or its output has no `VERDICT:` line, end the loop with `stop-blocked`. In the Phase 9 summary, list the failure and the error of the script.

Act on the `VERDICT:` line. The `RUN`, `ERROR`, `TAIL`, and `CHANGED` lines are the evidence:

- `UNCOMMITTED`: the command passes at `<fix-commit>`. So the state of the main worktree causes the failure: its uncommitted changes, or a `HEAD` that is not `<fix-commit>`. Do not fix it in this loop. End the loop with `stop-blocked`. In the Phase 9 summary, list the failure, its error message, the `MAIN WORKTREE` line, and the `CHANGED` files.
- `REGRESSION`: the command fails at `<fix-commit>` and passes at `<fix-commit>^`, so the fixes of this cycle caused the failure. Go back to Phase 5 with the failure and the diff of `<fix-commit>`, and try one more fix. Commit that fix (Phase 7), and run Phase 6 again. Do not run the failure check again in this cycle. If the fixer reports REJECT or PARTIAL, or Phase 6 fails again, end the loop with `stop-blocked`. In the Phase 9 summary, list each command that still fails. If its command still fails, put the regression in the deferred list. Report to the user.
- `SAME-AT-PARENT`: the command fails at `<fix-commit>` and at `<fix-commit>^` with the same error. So the failure is also in the code before the fixes of this cycle. Do not fix it in this loop, because the fix is outside the review target. End the loop with `stop-blocked`. In the Phase 9 summary, list the failure with its file and its error message. Add the evidence: the command, and the SHA of the commit where it also fails. The user decides how to fix it (`dev-essentials:engineering-discipline` Rule 1). A `RUN` line with the words `in temporary export` means that the command ran in a folder with no git data. A command that reads git data can fail at both commits, so read the `ERROR` and `TAIL` lines before you trust `SAME-AT-PARENT`. If one of them shows missing git data, for example `fatal: not a git repository`, treat the verdict as `OTHER`.
- `OTHER`: any other result, for example another error, a time-out, or a command that cannot run in the worktree. End the loop with `stop-blocked`. In the Phase 9 summary, list the failure and the `RUN`, `ERROR`, and `TAIL` lines of both runs.

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

- **Continue** only on these conditions, and each must hold. (a) The rounds used are fewer than `--rounds`. (b) The fixer applied at least one edit in this cycle, so new code is on disk.
  - If the fixer applied no edit in this cycle, **stop**, because there is no new code to re-review. Examples: all findings were REJECT, or the cycle ran with `--dry-run` or `--no-verify-fix`.
  - If the fixer applies no edit in a re-review cycle, skip Phase 6 in that cycle. There is no new code to build or test. Carry the build, test, and lint status of the previous cycle forward into Phase 9.
  - The re-review covers only the files that the fix commit changed, not the full original target. This is on purpose: a re-review of the whole target mixes new findings with old deferred ones. With `--no-commit`, no fix commit exists, so the re-review covers the whole target file.
  - The re-review in Round N+1 always uses one `general-purpose` agent, for any `--reviewer` value. Dispatch it on `--reviewer-model` at `--reviewer-effort`, so that the re-review has the same judgment as Round 1. The reviewer setup (`audit-team`, `dual`, `pair`, `quad`) applies to Round 1 only. The goal is the question "did the fix resolve the issue, with no new regression?", not a full architecture review. Give the re-review one line for each finding that went to the fix pass of Round N: `<severity> <verdict>: <fix plan>`, with the verdict APPLY, PARTIAL, or REJECT. A REJECT line also gives the reason of the fixer. Take the lines from the cycle report of Round N. With them, the re-review can judge each fix against its plan and find a wrong REJECT. Tell the re-review to report a wrong REJECT as a finding only with a primary source, also outside the files of the fix commit.
- **Stop** in every other case. Classify the stop verdict:
  - **stop-clean**: all three conditions hold. (1) No unresolved finding in the re-review scope is `blocking: true` or has the severity Blocker, Critical, or High. (2) No such finding is in the deferred list of the whole run. This covers each kind of deferral. The first is by `--skip`. The second is after the unproven part of a PARTIAL verdict of the fixer or a REJECT verdict whose reason is missing proof. The third is by the merit judgment of Phase 4. A REJECT that a primary source refutes (the code is shown to be correct) resolves the finding. It is not a deferral, and Phase 9 lists it under "Rejected findings". Both halves of the test matter. `blocking: true` is the judgment of Phase 4 on each finding, so a flagged Medium, Low, or Nit blocks `stop-clean` exactly as a High does. The severity half reads the label, so an unflagged Blocker, Critical, or High can never clear the gate in silence. (3) The `Not covered:` line of the Phase 9 summary is `none`. A reviewer, a role agent, or an Area Explorer with no report reviewed nothing. So no finding can show that its part of the target is clean. If condition 3 fails, use `stop-blocked`. If only condition 1 or 2 fails, use `stop-max-rounds` instead.
  - **stop-max-rounds**: the `--rounds` limit came before a re-review pass found the run clean. It covers each other case that prevents `stop-clean`. (a) Issues remain open in the re-review scope. (b) `--skip` deferred every finding. (c) The fixer fixed every finding, but no re-review round ran to prove it. (d) Merge-blocking work is still open somewhere in the run, although the rounds limit was not reached. That work is a deferred Blocker, Critical, or High, for example through `--skip critical` or `--skip high`. It is also any unresolved finding that Phase 4 marked `blocking: true`, at **any** severity label.
  - **stop-blocked**: the build, the tests, or the lint fail, and this session cannot fix them. Or a unit of the review is not covered (condition 3 of `stop-clean`). Escalate to the user.

### Phase 9 — Final summary

Aggregate across all cycles. Follow the "Report destination rules": write to `<target-slug>-summary.md` in the reviews folder in a run with more than one cycle or with `--save-reports`, and else print in chat. If the run format applies, the final chat report follows the "Run format" section. Whatever the destination, the chat output of the run holds the `Stop verdict:` line and the paths of the fixed files (see "Done test").

Fill the Phase 9 template of `references/output-formats.md`.

A `(blocking)` row, or a deferred Blocker, Critical, or High row, means that the run did not reach `stop-clean` (see Phase 8).

---

## Files and related skills

| File or skill | When to read it, or why this skill depends on it |
|---|---|
| `references/reviewer-briefs.md` | Phase 3, in every run: the Common Rules, the Full format, a brief for each target type, and the `--reviewer-focus` tokens. |
| `references/parameters.md` | Phase 1: the default and the meaning of each flag. Read it before Phase 1. |
| `references/output-formats.md` | The end of each cycle (Brief format), and Phase 9 (summary template). Also the Full format. |
| `references/orchestrated-review.md` | Phase 3, only in the large-target orchestrated mode. |
| `scripts/group_diff.py` | Phase 3, only in the large-target orchestrated mode: it groups the changed files into areas. |
| `references/audit-team-adapter.md` | Phase 2, only with `--reviewer audit-team`. |
| `references/triage-matrix.md` | Phase 4: the severity scale, the action for each severity, and the `blocking` flag. |
| `references/verify-fix-discipline.md` | Phase 5: the playbook of the fixer. Read it before the fix pass, and give its path to a fixer subagent. |
| `scripts/failure_check.py` | Phase 6, only after a failed build, test, or lint run that follows a fix pass: the failure check. Run it with `--help` for all flags. |
| `examples/branch-review.md` | A full review of a feature branch, with both report formats filled in with real numbers. |
| `examples/spec-review.md` | A review of a spec change document of any spec framework. The example uses a change folder of a spec framework as one case. It shows the `audit-team` adapter and the findings. |
| `dev-essentials:engineering-discipline` | Rule 1 (own every red signal) drives the build and test run of Phase 6. Rule 2 (no critical decision alone) drives the REJECT of a signature change that the triage did not allow, in Phase 5. Rule 5 (no claim without proof) drives the primary-source rule of the reviewer and the fixer. |
| `dev-essentials:subagent-orchestration` | Rule 1 for the choice of the fixer in Phase 5, step 5b. Rule 3 for the reviewer dispatch of Phase 3 and the fixer dispatch of Phase 5. Independent `Agent` calls go in one message. "Model selection" for Fable. `Trust but verify` and "Run format agreement" for the run format. |
| `dev-essentials:github-mcp-conventions` | For `target=pr <id>`: how to call `pull_request_read` with explicit `owner` and `repo`, and how to paginate (Rule 3). |
