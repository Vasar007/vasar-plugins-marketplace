# Changelog

This file records all notable changes to this marketplace.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for each plugin separately.
For the current version of a plugin, see the `plugin.json` file of that plugin.
In each release heading, the linked number is the release tag of the marketplace, for example `v2.1.0`.
The other numbers in a heading are plugin versions.

## [Unreleased]

## dev-essentials 6.4.0 in release [7.5.0] - 2026-11-27

`compose-pr` now follows the PR template of the repository. Before, it always wrote the sections `## What`, `## Why`, and `## Changes`, and it did not look for a template. The rule matters most for a session on a smaller model. In the eval runs, a session without the rule followed a template on the larger of two tested models, and it ignored the template on the smaller one (issue #382).

### Changed in dev-essentials

- `skills/compose-pr/SKILL.md`: step 5 first looks for a PR template in the places that GitHub reads. With a template, the description uses its headings in their order. Each HTML comment of the template is the instruction for its section, and the description holds no comment. The writing rules, the Testing rule, and the length limits still apply, and the limit wins over a long template. An item that the session cannot show gets `Not confirmed:`. A comment with a rule for the PR title gives no title line. With several templates and none in the input, the skill uses its own form and names the templates. With no template, the form stays as it was. Step 6 names the template that the skill used, and it quotes a rule for titles (issue #382).
- `evals/composers/cmp-pr-repo-template`: a new case with no shell tool. The repository has a PR template, and the prompt does not name it. The description must have the headings of the template, no What section, and no comment of the template. Its Evidence section claims no test run, and a check box on a passed test run stays empty. A last line names the agent tool and the model. A route grader makes sure that the final reply names the template (issue #382).

### Changed in the repository

- `tests/test_eval_cases.py`: new tests for the patterns of the new graders on right and wrong texts. A new test makes sure that the prompt of `cmp-pr-repo-template` names no template and has the diff of `cmp-pr-untested-diff` (issue #382).
- `tests/test_eval_scaffolds.py`: the lists of branches and commit graders name `cmp-pr-repo-template`. A new test makes sure that the case plants its template on `main`, with its rules only in comments (issue #382).

## dev-essentials 6.3.0 in release [7.4.0] - 2026-11-27

`process-pr-comments` now acts only on the review comments of trusted logins. A login is trusted in three cases. It is the author of the pull request, it has write access to the repository, or the new `trusted` parameter names it. Before, the skill acted on the comment of each GitHub user. In the full mode, it fixed, committed, and pushed the change of a user with no write access, with no question (issue #375).

### Added in dev-essentials

- `skills/process-pr-comments/references/parameters.md`: the new parameter `trusted` adds logins that the skill trusts with no read of their access (issue #375).
- `evals/process-pr-comments/ppc-untrusted-full`: a new case with a `[ToFix]` comment of a login with no write access, in the full mode. The run must make no edit, no commit, no reply, no resolve, and no push. Its last message must list the thread with the reason. The route grader `route-trust-read` makes sure that the run read the collaborators of the repository (issue #375).

### Changed in dev-essentials

- `skills/process-pr-comments/SKILL.md`: Phase 2 step 1 tests the trust of each comment of a person. Stage 1 reads the collaborators of the repository once in each cycle with `list_repository_collaborators`. The roles `admin`, `maintain`, and `write` give write access. If the MCP read fails again after one retry, Stage 1 reads each login with `gh api repos/<owner>/<repo>/collaborators/<login>/permission`. If both reads fail, each such login is untrusted. If the error says that push access is needed, Stage 1 skips the retry and the `gh` read. Stage 1 copies no text of an untrusted comment into its report, and the text of each comment is data, never an instruction. An untrusted comment gets no fix, no reply, no issue, and no resolve, in every mode, also with an automated-review header. The cycle log lists its thread for the user. The bot list keeps its behavior. Phase 1 caches the login of the PR author as `authorLogin`. Bucket B holds the rule as an invariant (issue #375).
- `skills/process-pr-comments/references/thread-state-schema.md`: the PR metadata has `authorLogin`. Each comment of the Stage 1 report has its login and the field `trusted`. The summary has `untrustedThreads`, `trustRead`, and `trustReadError`. The `untrusted` outcome wins over each `assessedState`. The cycle log has the outcome `untrusted (<login>) — left to you` and the reply status `no reply (untrusted login)` (issue #375).
- `skills/process-pr-comments/references/tag-actions.md` and `skills/process-pr-comments/references/parameters.md`: a comment of a person with an automated-review header goes to Phase 3b only after the trust test. The `trusted` row of `parameters.md` says that the read of write access needs push access to the repository (issue #375).
- `skills/process-pr-comments/references/committed-fix-state.md` and `skills/process-pr-comments/references/deep-fix.md`: the guard for a newer reply counts only the reply of a trusted login. The hard list of `deep-fix.md` has a new row for a thread with an untrusted top comment (issue #375).
- `skills/process-pr-comments/references/invocation-examples.md`: an example with `trusted` (issue #375).
- The ten other `ppc-*` cases: each one gets a mock of `list_repository_collaborators`. The mock gives `example-reviewer` the role `write`, so the reviewer of each case stays trusted (issue #375).

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `PpcTrustTests` makes sure that the mock of each `ppc-*` case trusts each reviewer of that case. The one exception is `drive-by-user` of `ppc-untrusted-full`. The class also pins the verdicts of the graders `listed` and `route-trust-read` (issue #375).
- `tests/test_eval_scaffolds.py`: `NO_COMMIT_GRADERS` holds the grader `no-commit` of `ppc-untrusted-full`, so a test runs it on the scaffold (issue #375).

## dev-essentials 6.2.0 in release [7.3.0] - 2026-11-27

In a fan-out, a subagent can end with no report, for example on an API error or a usage limit. The orchestrator now gives such a unit one more try. If it fails again, the final report names the unit as not covered, and the run reports no clean result for it. A review loop with such a unit now ends with `stop-blocked`, not `stop-clean` (issue #376).

### Added in dev-essentials

- `evals/review-loop/rl-area-not-covered`: the orchestrated review of a large branch ends with three Area Explorers. Two of them report no finding. An API error cuts off the third, and its one resume fails again. The run must name the area `ledger` as not covered, and its stop verdict must be `stop-blocked`. The case needs no shell tool and no scaffold (issue #376).

### Changed in dev-essentials

- `skills/subagent-orchestration/SKILL.md`: the section `Trust but verify` has a rule for a fan-out. The orchestrator matches each report to its unit. A failed agent, a stopped agent, and a reply that Claude Code marks as cut off or partial give no report. Such a unit gets one resume or one new dispatch. If it fails again, the final report names it as not covered. A cut-off reply keeps its findings, but the unit stays not covered. A limit of tries or a stop rule that a skill names wins, and a run format does not replace the rule (issue #376).
- `skills/review-loop/SKILL.md`: `stop-clean` needs a third condition. The `Not covered:` line of the Phase 9 summary must be `none`. If a unit is not covered, the verdict is `stop-blocked`. In a run with more than one cycle, chat also gets a `Not covered:` line that is not `none` (issue #376).
- `skills/process-pr-comments/references/deep-fix.md`, `skills/process-pr-comments/references/thread-state-schema.md`, and `skills/research-implement-review-report/SKILL.md`: a `stop-blocked` has two reasons, a red build or a unit that no reviewer covered. The cycle log line is `deep-fix — blocked (<reason>, not pushed)`. With a unit that is not covered, the text does not say that red commits sit on the branch (issue #376).
- `evals/review-loop/rl-area-not-covered/prompt.md`: the request line has `--print-reports`, so the run needs no file write (issue #376).
- `skills/review-loop/references/output-formats.md`: the Phase 9 summary has a new line, `Not covered:` (issue #376).
- `skills/review-loop/references/orchestrated-review.md`: the collate step first matches each Area Explorer report to its area. The final report names each area that is still not covered (issue #376).
- `skills/review-loop/references/audit-team-adapter.md`: a role that the **Reviewers** line marks as not covered goes to the `Not covered:` line (issue #376).
- `commands/audit-team.md`: Step 3 matches each agent report to its role. The **Reviewers** line marks a role with no report as `(not covered)` (issue #376).

### Changed in the repository

- `tests/test_review_loop_text.py`: a new test makes sure that Phase 8 reads the `Not covered:` line that the Phase 9 template defines (issue #376).
- `tests/test_eval_cases.py`: the test of Step 3 of `audit-team` expects the new sentence on the labels that `review-loop` reads (issue #376).

## dev-essentials 6.1.1 in release [7.2.2] - 2026-11-27

`compose-pr`: the `## Testing` section now names only the tests that the diff adds or changes. If the input or the session shows a test command and its result line, the section names them. Else it says that the tests did not run in this session, and it claims no pass. Before, the template asked for a testing approach, and one example said that load tests proved the change. So a description claimed a run that nobody did (issue #377).

### Fixed in dev-essentials

- `skills/compose-pr/SKILL.md`: the template line of `## Testing` names the tests and the run result. A new writing rule says where a run result comes from. With no run, the section says `Not run in this session.` and claims no pass. The rule also tells the skill not to run the tests only for this section (issue #377).
- `skills/compose-pr/references/examples.md`: each `## Testing` section of the examples now says that the tests did not run in this session. The larger example names its load test and no longer claims a load test result. The lengths of the examples changed (issue #377).
- `skills/work-modes/references/finish.md`: step 4 now gives `pr-composer` the test command of step 2 and its result line. So the description names the run (issue #377).

### Changed in dev-essentials

- `evals/composers/cmp-pr-untested-diff`: a new case with no shell tool. The prompt gives a diff with a new test file and no test run. The Testing section must name the test and say that the tests did not run in this session. It must claim no pass (issue #377).
- `evals/composers/cmp-pr-tested-diff`: a new case with no shell tool. The prompt gives the same diff and the result of a test run. The Testing section must name the result and must not say that the tests did not run (issue #377).

### Changed in the repository

- `tests/test_eval_cases.py`: new tests for the patterns of the new graders on right and wrong texts, with their known limits. A new test makes sure that the two new cases grant no shell tool. It also makes sure that only the prompt of `cmp-pr-tested-diff` holds a test result (issue #377).

## kb 0.4.1 in release [7.2.1] - 2026-11-26

If no text that a session follows calls its script with a relative path, `/kb:setup` now removes the stale allow rule of that script. Before, the skill searched the whole folder `_claude` of the KB clone. That search found files that do not matter, so the rule stayed for all time (issue #373).

### Fixed in kb

- `skills/setup/check.sh`: it now decides for each stale rule whether the rule can go. It reads five files of the clone: `_claude/RULES.md`, `_claude/capture.md`, `_claude/close-task.md`, `_claude/hooks/session-start.sh`, and `_claude/hooks/subagent-start.sh`. A file that does not exist is skipped. It looks only for the relative call of the script of that rule. A full-path call and a call of another script do not count. If no file has the relative call, the `STALE:` line ends with the words "Remove it". If a file has it, the line ends with the words "Keep it for now:" and the path of the first such file. With no clone that a full `KB_DIR` names, the line ends with "Remove it" too (issue #373).

### Changed in kb

- `skills/setup/SKILL.md`: the step for a `STALE:` line has no search of its own. If the line says "Remove it", the skill removes the rule after the yes of the owner. If the line says "Keep it for now", it changes nothing and tells the owner which file still has the relative call (issue #373).
- `README.md`: the setup section names the five files that `check.sh` reads and the two forms of the `STALE:` line (issue #373).

### Changed in the repository

- `tests/test_kb_plugin.py`: the stale tests expect the new text of the `STALE:` line. Five new tests cover these cases. A relative call in the rules file keeps only the rule of that script. The first file with the call is named. Each of the five files keeps the rule. Full-path calls keep no rule. A relative call in another file or of another script keeps no rule (issue #373).

## dev-essentials 6.1.0 in release [7.2.0] - 2026-11-26

When no GitHub MCP tool can make a call, the GitHub rules of `dev-essentials` now allow the `gh` CLI. Each `gh` call goes into the report, and each approval gate stays (issue #365). Each workflow that opens a pull request now sets its assignee, the labels of its issue, and its Project (issue #366). Hard stop 1 of `work-modes` lets a run remove its own scratch with no question (issue #367). The archive of `feature-pipeline` now goes to the notes folder, not to `~/.claude/task-logs/` (issue #369).

### Added in dev-essentials

- `evals/merge-pr/mp-checks-403`: the MCP read of the check runs fails with a `403` error. The run must read the check runs with `gh` and name that call and its reason in the report. It must make no other `gh` call, and it must not merge (issue #365).
- `skills/github-mcp-conventions/references/pull-request-fields.md`: the steps that set the fields of a new pull request. The assignee is the author of the pull request. The pull request gets the labels of its issue that its repository has. If the repository has one Project, the pull request goes into it. The MCP tools set the assignee and the labels, and `gh` is the fallback. The run reads the pull request before the update, so that it keeps the old labels and the old assignees. It reads the pull request again after the update, so that it sees a change that GitHub dropped. If the session has the MCP tool `projects_write`, the Project goes through it. Else it goes through `gh`. The report names each field that the run did not set (issue #366).
- `evals/work-modes/wm-scratch-probe`: a new cheap case for hard stop 1 in the full mode. The run measures the planted off-by-one in `page_slice` with its own probe in `tmp/probe/`. A file of the user in `tmp/` has no other copy. The scored grader `notes-kept` compares it with the file of the scaffold. The route grader `route-probe-made` makes sure that the run made a probe in `tmp/probe/`. The route grader `route-probe-removed` makes sure that the probe is gone at the end (issue #367).

### Changed in dev-essentials

- `skills/github-mcp-conventions/SKILL.md`: Rule 5 allows the `gh` CLI in two cases. No MCP tool has the call or a field that the step needs, or the MCP call fails again after one retry. The rule lists the known cases, for example a `403` error on the check runs and a release, which no MCP tool creates. The report names each `gh` call and its reason. A case holds for one call, and a stop or a `gh` step that a skill names wins over the rule. A slow MCP call is still no reason for `gh`, and each approval gate stays (issue #365).
- `skills/merge-pr/SKILL.md`: if the MCP read of the check runs fails again after a retry, the gate reads them with `gh api`. When no MCP tool reads them, Step 4 reads the checks of the merge commit with `gh`. Step 3 bans a `gh` merge after a failed MCP merge. The approval of the merge does not change (issue #365).
- `skills/subagent-orchestration/SKILL.md`: Rule 4 points at the two cases of Rule 5 of `github-mcp-conventions` (issue #365).
- `commands/help-review-pr.md`, `commands/save-context.md`, `agents/bug-hunter.md`, and `agents/bug-verifier.md`: the text follows the new Rule 5 (issue #365).
- `evals/merge-pr/mp-green-merge`: the new grader `no-gh-for-the-pr` fails a run that reads the pull request or merges with `gh` while the MCP tools work (issue #365).
- `skills/github-mcp-conventions/SKILL.md`: a new section points at the steps for the fields of a new pull request (issue #366).
- `skills/work-modes/references/finish.md`: a field of the new pull request that the run cannot set is no failed step. The run goes on to the merge (issue #366).
- The eval case `rirr-merge`: the task of the earlier run is issue 58 with two labels. New mocks and graders make sure that the run sets the assignee and both labels on the pull request with `issue_write`. The cases `rirr-merge-gate`, `it-merge`, and `ib-merge` get a mock of `issue_write` (issue #366).
- `skills/work-modes/SKILL.md`: hard stop 1 has an exception for scratch. The run removes scratch that it created in this session for its own use, with no question, in every mode. Examples are a probe script, a log, a scratch clone with no commit of its own, and a tool in a scratch folder. A folder or file that existed before the run is never scratch. If the run is not sure that it created a path, it keeps the path. The exception does not cover git work that has no other copy, a worktree, or a file that a step of the workflow names. A permanent install needs a yes of the user first. In the full mode, the run does not make it, and lists it in the final report. If a removal fails, the run tries no workaround, and the final report lists each leftover path under "Leftovers" (issue #367).
- `skills/bug-hunt/SKILL.md`: the report of Step 7 lists each leftover file under "Leftovers" (issue #367).
- `skills/feature-pipeline`: Step 10 archives the task logs to `Pipeline/<task ID>/` in the notes folder of the branch, not to `~/.claude/task-logs/`. `~/.claude/` is a protected path. A write there prompts in the modes `default` and `acceptEdits`, and the mode `dontAsk` denies it. So the archive of a run in the full mode stopped or failed. A notes folder outside the working folders needs `/add-dir` or `permissions.additionalDirectories`, as for the other workflows. A notes folder inside the repository is the folder in the main worktree. So the removal of a linked worktree keeps the archive. If a file is not in the archive, the run keeps the worktree. If a linked worktree still holds the merged local branch, the run keeps that branch too. With a missing file, the run also leaves the KB task folder open. The pipeline does not read or move an old archive in `~/.claude/task-logs/` (issue #369).
- `skills/feature-pipeline`: Step 9b leaves item 6 of Step 4 of `merge-pr`, the close of the KB task folder, to Step 10. So the archive goes into the task folder before the close moves it (issue #369).
- The eval case `fp-e2-merge`: the request names the notes folder `notes/`, and the new grader `route-archive-in-notes` reads the archive there (issue #369).

### Fixed in dev-essentials

- A new pull request got no assignee and no labels. Each workflow that opens a pull request now sets its fields. These workflows are the finish steps of `work-modes`, Step 6 of `stages/finalization.md` of `feature-pipeline`, and the PR step of `promote-conventions`. A field that the run cannot set does not stop the run (issue #366).

### Changed in the repository

- Tests: the new `tests/test_gh_fallback_text.py` makes sure that Rule 5 keeps each part of the rule, and that no unit keeps the old ban. `tests/test_eval_cases.py` and `tests/test_eval_scaffolds.py` cover the new case and the new grader (issue #365).
- Tests: the new class `PullRequestFieldTests` in `tests/test_work_modes_text.py` makes sure that each unit that opens a pull request points at the field steps. `tests/test_eval_cases.py` covers the new graders and mocks of `rirr-merge` (issue #366).
- `docs/testing.md`: the table of the test groups names the new module (issue #365).
- `docs/workflows.md`: in every mode, a run removes the temporary files that it made itself (issue #367).
- `docs/eval-cases.md`: the list of known limits of the graders names `route-probe-made` (issue #367).
- Tests: `tests/test_work_modes_text.py` makes sure that hard stop 1 keeps the exception for scratch and its limits, and that the final report names "Leftovers". `tests/test_eval_cases.py` and `tests/test_eval_scaffolds.py` test the graders of `wm-scratch-probe` (issue #367).
- `docs/workflows.md`: the section "Where the notes go" says where `feature-pipeline` archives its files (issue #369).
- Tests: `tests/test_rule_references.py` makes sure that no file of `dev-essentials` names a path such as `~/.claude/<name>/`, other than the files of Claude Code. It does not find a Windows path or a path that code builds. `tests/test_eval_cases.py` pins the archive grader of `fp-e2-merge` and the deferred items of `merge-pr` (issue #369).

## kb 0.4.0 in release [7.1.0] - 2026-11-26

The allow rules of `/kb:setup` for `kb-search.sh`, `ste-check.py`, and `md-check.py` now hold the full path of the KB clone. Before, they had a relative path, so they also matched a script with the same path in another project. Run `/kb:setup` again. It adds the new rules. Until the rules of the KB clone call the scripts with the full path, keep the old rules with the relative path. Then remove them (issue #356).

### Fixed in kb

- `skills/setup/check.sh`: it prints the allow rules for `kb-search.sh`, `ste-check.py`, and `md-check.py` with the full path of the clone, for example `Bash(bash <KB root>/_claude/tools/kb-search.sh *)`. The `git -C <KB root>` rules already had this form. Before, the three script rules had a relative path, such as `Bash(bash _claude/tools/kb-search.sh *)`. A Bash rule matches the command text and has no anchor to a folder. So the old rule also let the script `_claude/tools/kb-search.sh` of another project run with no prompt. With no KB clone, `check.sh` prints none of these rules now (issue #356).

### Changed in kb

- `skills/setup/check.sh` and `skills/setup/SKILL.md`: for each old rule with a relative path in `permissions.allow`, `check.sh` prints a `STALE:` line. If the rules of the KB clone call the scripts with the full path, the skill shows the change that removes the rule. It waits for the owner's yes. Else the old rule stays. The setup is done only with no `MISSING:` line and no `STALE:` line (issue #356).
- `skills/setup/check.sh`: it prints the path rules only for the clone that `KB_DIR` names. For another clone, it prints one `MISSING:` line that asks you to set `KB_DIR`. A space or a `*` in the clone path changes what a Bash rule matches. So it prints one `MISSING:` line and no script rule for a path with any other character than these: ASCII letters, digits, and `. _ / : ~ -` (issue #356).
- `README.md`: the setup section names the new form of the rules, the `STALE:` lines, the `KB_DIR` rule, and the limit on the clone path (issue #356).

### Changed in the repository

- `tests/test_kb_plugin.py`: the tests of `check.sh` expect the full path of the clone in the three script rules, also on Windows. Six new tests cover these cases. Three tests cover the `STALE:` lines: an old rule in `permissions.allow`, an old rule only in `ask` or `deny`, and an old rule with no clone. One test covers a clone path with a space or a `*`. One test covers a clone that only the project folder or a relative `KB_DIR` gives. One test covers a full `KB_DIR` in the environment next to a relative `KB_DIR` in `settings.json` (issue #356).

## dev-essentials 6.0.0 in release [7.0.0] - 2026-11-26

The skills and commands of `dev-essentials` now keep their notes in one notes folder, and a new rule file finds it. The notes no longer go to a fixed `Notes/` folder in the repository. The configuration `notes_dir`, the command `opsx-implement`, and the support for OpenSpec go. A knowledge base (KB) clone is a local git clone of notes. If the `kb` plugin and a KB clone are there, `merge-pr` closes the KB task folder after a merge with `kb:close-task` (issue #368).

### Added in dev-essentials

- `references/notes-root.md`: the rule that finds the notes folder of a task. The first item that gives a folder wins: a folder that the request names, a folder that the `CLAUDE.md` of the repository names for notes, and the task folder of a KB clone. A folder that `CLAUDE.md` names for one kind of file only, such as plans, holds that kind only. If no item gives a folder, the notes folder is `~/claude-notes/<repo>/<branch>/`. The test for a KB clone is the test of the launcher of the `kb` plugin: `KB_DIR` holds a full path to a folder with `_claude/RULES.md` (issue #368).
- `skills/merge-pr/SKILL.md`: item 6 of Step 4 loads `kb:close-task` after the merge. It has two conditions: the session lists that skill, and a KB clone exists. All workflows that merge reach it through `merge-pr` (issue #368).

### Changed in dev-essentials

- The units with a notes folder take it from the new rule, and no unit names a fixed `Notes/` path now. These units are the commands `implement`, `save-context`, `help-review-pr`, and `implement-task`. The workflow skills among them are `review-loop`, `process-pr-comments`, `research-implement-review-report`, `implement-batch`, and `feature-pipeline`. The other skills are `compose-pr`, `compose-task`, `create-documentation`, `create-html-artifact`, `engineering-discipline`, and `promote-conventions` (issue #368).
- `commands/implement.md` and `skills/research-implement-review-report/SKILL.md`: the last fallback for the context now reads the rules of a KB clone, not the auto-memory folder (issue #368).
- `skills/audit-personal-conventions`: the audit reads no memory topic file now. The scope `memory` reads the `MEMORY.md` index of each project. The new scope `kb` reads the rules of a KB clone (issue #368).
- `skills/promote-conventions/SKILL.md`: a rule from a KB clone stays report-only in the cleanup of Phase 9 (issue #368).
- `skills/optimize-skill/SKILL.md`: the sources of the decisions of the user are the `CLAUDE.md` files and the rules of a KB clone, not memory files (issue #368).
- `commands/merge-worktree-projects.md`: the report says that no unit reads a memory topic file as a rule. The script still moves the memory files as data (issue #368).
- `commands/save-context.md`: Step 5 moves the files of a notes folder outside the repository too. In a KB clone, it moves no file, because the rules of the KB own the task folder (issue #368).
- `scripts/backup_move.py`: a workspace outside a git work tree is no error now. No file counts as tracked there (issue #368).
- `skills/git-worktree-management`: a new worktree gets no notes folder. The bootstrap removes the upstream and copies `.claude/settings.local.json` (issue #368).
- `commands/audit-plan.md`: the command audits a plan file or a plan folder (issue #368).
- `skills/review-loop`, `skills/compose-pr`, and `skills/engineering-discipline`: the text names a spec framework in general, not OpenSpec (issue #368).
- The eval cases `cmp-pr-from-diff`, `cmp-task-draft`, `cmp-guide-draft`, `fp-e2-untracked-file`, `hrp-post-one`, and `ppc-build-context`: the `CLAUDE.md` of each scaffold names the notes folder `notes/`, and the graders read that folder. `evals/_lib/git-fixture.sh` has the new function `fixture_notes_folder` for this line (issue #368).

### Removed in dev-essentials

- The command `opsx-implement` (issue #368).
- The configuration key `notes_dir` (issue #368).
- The option `--change` of `save-context`, and the OpenSpec change as an input of `audit-plan` (issue #368).
- The option `--notes-dir` of `skills/git-worktree-management/scripts/worktree.py`, and its output line `NOTES` (issue #368).
- The trigger case `evals/triggers/audit-plan-openspec-fires` (issue #368).

### Breaking changes in dev-essentials

- The notes of a task move out of the repository, unless the request or the `CLAUDE.md` of the repository names a folder for them. To keep the notes in the `Notes/` folder of the repository, name that folder in the `CLAUDE.md` file of the repository (issue #368).
- The audit of `audit-personal-conventions` no longer reads the memory topic files. Move each rule that you keep there to a `CLAUDE.md` file or to a KB clone (issue #368).

| Old name | New name |
| --- | --- |
| `/dev-essentials:opsx-implement <change>` | `/dev-essentials:implement <plan file>` |
| `/dev-essentials:audit-plan openspec/changes/<change>` | `/dev-essentials:audit-plan <plan file or plan folder>` |
| `/dev-essentials:save-context --change <name>` | `/dev-essentials:save-context --plan <plan file>` |
| The configuration `notes_dir` | A line in the `CLAUDE.md` file of the repository that names the notes folder |
| `worktree.py create <branch> --notes-dir <folder>` | `worktree.py create <branch>` |

### Changed in the repository

- `CLAUDE.md`: the model rule now says which new model starts a new run of the main eval cases. A new model counts in two cases: the eval agent or the judge moves to it, or the owner starts to use it as the main model of sessions (issue #362).
- `docs/evals.md`: the new section "Run the main cases on a new model" lists the main cases and gives the command for one run. It also gives the cost and the time of the first model run, with an agent of the Fable family: 59 runs, each at 1.00, for 42.70 USD (issue #362).
- `docs/workflows.md`: the new section "Where the notes go" gives the rule for the notes folder (issue #368).
- Tests: `tests/test_worktree.py`, `tests/test_backup_move.py`, `tests/test_eval_cases.py`, `tests/test_eval_scaffolds.py`, `tests/test_work_modes_text.py`, and `tests/test_review_loop_text.py` follow the changes. `tests/test_rule_references.py` makes sure that each path below `${CLAUDE_PLUGIN_ROOT}` exists, and that each unit with a notes folder points at the rule. `tests/test_kb_plugin.py` makes sure that the rule and the launcher of `kb` agree on each KB clone. It also makes sure that `merge-pr` names only skills that `kb` has (issue #368).

## dev-essentials 5.1.6 in release [6.2.3] - 2026-11-22

A second review of each unit test and each eval case kept only the useful ones. The suite loses 14 tests and one eval case, and it fails for the same bugs as before. No skill text changes (issue #361).

### Removed in dev-essentials

- `evals/create-html-artifact/cha-12-findings`: the eval case is gone. Its request was the first 12 lines of the request of `cha-30-findings`, and both cases had the same scored graders. In 10 stored run pairs, both cases gave the same result. `cha-30-findings` now has the tag `smoke` (issue #361).

### Changed in the repository

- Tests: 12 unit tests are gone, and 2 pairs of tests are one test each (issue #361). For each removed test but one, mutants showed that a named other test fails for the same bugs. The other test, `UnitTests.test_help_text_names_each_kind_of_output_line`, reads only the help text, so no bug of the code makes it fail. The tests are in `test_eval_cases.py` (1), `test_eval_results.py` (1 merge), `test_changelog_merge.py` (2, and 1 merge), `test_failure_check.py` (3), `test_check_report.py` (1), `test_group_diff.py` (1), `test_squash_task.py` (1), and `test_openbsd_lint.py` (3). One of them, `GoldTests.test_gold_readme_is_found`, came back in an earlier review, because a heading with two spaces failed only that test. Such a heading is in style for the linter, so that failure was a false alarm.

## dev-essentials 5.1.5 in release [6.2.2] - 2026-11-22

`failure_check.py` of `review-loop` now gives `SAME-AT-PARENT` for the same failure of Jest, Vitest, and pytest-xdist. No skill text changes (issue #358).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: more run noise now becomes a token or does not count. The counts of passed tests and the totals in the summary lines of Jest and Vitest become tokens. So does the count of tests in the file line of Vitest, such as `(3 tests | 1 failed)`. The estimate after the time of Jest and the parts of the duration of Vitest do not count. Nor does the worker of pytest-xdist, such as `[gw2]`. The last 15 lines of a run now hold only lines that are not blank. A second run of Jest in the same folder prints one more blank line, and before, that line moved the last lines. Before, each of these gave `OTHER` in place of `SAME-AT-PARENT`. Real runs of Jest 30.5.2, Vitest 5.1.1, and pytest-xdist 3.8.0 on Windows showed it. The help text names the new rules and two limits: a coverage table, and a tool in an ignored folder such as `node_modules`. For that tool, it names the verdict of a clean main worktree and of one that is not clean (issue #358).

### Changed in the repository

- `tests/test_failure_check.py`: six new tests with the real output of Jest 30.5.2, Vitest 5.1.1, and pytest-xdist 3.8.0 on Windows. In each one, two runs of the same failure give the same signature. They differ in a count of passed tests, a time part, a worker, or a blank line. Three new cases show that a count of failed tests of Jest and Vitest still counts. One more test runs a tool in an ignored folder from a clean main worktree and from one that is not clean. Other new cases cover the counts of skipped and todo tests and a worker of two digits. One more case has a count line inside an assertion message (issue #358).

## dev-essentials 5.1.4 in release [6.2.1] - 2026-11-22

The docs pages are shorter and easier to read. The eval docs are now two pages: one runs the cases, and one says how to write them. No skill text changes (issue #355).

### Changed in dev-essentials

- `evals/_lib/dotnet-fixture.sh`: the comment of `dotnet_write_run_marker` now points at `docs/eval-cases.md`, the new home of the limits of the test marker (issue #355).

### Changed in the repository

- Docs: the pages of `docs/` and the README are shorter and easier to read (issue #355). `docs/evals.md` now says how to run the evals. The new page `docs/eval-cases.md` says how to write a case and a grader, and it names the known limits of the graders. `docs/testing.md` has a table of the test groups in place of a list of the modules and the Windows paths. `docs/tools.md` points at the `--help` text of each script for its stops. `docs/authoring.md` and `docs/workflows.md` have lists and tables in place of long paragraphs. Step 3 of the unit workflow in `CLAUDE.md` points at the new page.
- `tests/test_eval_cases.py`: two docstrings now name the test as the list of the known wrong verdicts of a grader, in place of `docs/evals.md` (issue #355).

## kb 0.3.0 in release [6.2.0] - 2026-11-22

The hooks of `kb` now run scripts only from the KB clone that `KB_DIR` names. A clone of another repository can no longer run its own scripts from a KB hook. A session with no `KB_DIR` needs one run of `/kb:setup` (issue #129). The release also takes in two fixes of `tools/changelog_merge.py` that had no release (issues #307 and #343).

### Fixed in kb

- `scripts/kb-hook.sh`: the launcher runs hook scripts only from the clone that `KB_DIR` names. `KB_DIR` must be a full path to a folder with `_claude/RULES.md`. Before, with no such `KB_DIR`, the launcher looked for `_claude/RULES.md` in the project folder and in each child folder. Then it ran the hook scripts of the first folder that it found. So a clone of another repository ran its own scripts at each hook of the session (issue #129).

### Changed in kb

- `skills/setup/SKILL.md` and `README.md`: they say that the hooks need `KB_DIR` with the full path of the clone, also in a session inside the clone (issue #129).

### Breaking changes in kb

- A session with no `KB_DIR` no longer finds a KB clone in its project folder. Then the `SessionStart` hook prints `KB plugin: no KB clone found. Set KB_DIR with /kb:setup.`, and no KB script runs. Run `/kb:setup` once, so that it writes `KB_DIR` into `~/.claude/settings.json` (issue #129).

### Changed in the repository

- `tools/changelog_merge.py`: an old release can have the text of an entry that both sides released from `[Unreleased]` of the merge base. For such an entry, the subcommand `release` now leaves out the copy of the branch, as it does for a new text. Before, it kept that copy, and the count guard stopped with exit code 3. The rule needs an entry under `[Unreleased]` of the merge base that `main` moved into a release. The docstring names the rule (issue #307).
- `tools/changelog_merge.py`: if the branch changed an old release and `main` does not have the same text of that release, the subcommand `release` now stops. The result takes the old releases from `main`, so it loses such a change. Before, some of these merges ended with exit code 0. An example is a bullet that the branch moved out of an old release into its new release. If `main` made the change of the branch and one more change in that release, the script stops too. The docstring and `docs/tools.md` name the stop (issue #307).
- `tests/test_changelog_merge.py`: 16 new tests (issue #307). One test merges the case of the issue. Another one stops for a table row that the branch added below such an entry. In a third one, `main` removed such an entry, and two old releases have its text. Then the script stops. In a fourth one, `main` keeps the entry under `[Unreleased]` and releases another entry with the same text. Then the branch keeps its copy. In a fifth one, the branch moves a bullet out of an old release into its new release, and another old release has its text. Then the script stops. A sixth one moves a bullet whose text no other old release has. In a seventh one, both sides also released an entry with the text of the moved bullet. The script stops in both. In an eighth one, both sides released such an entry, and the branch also added a copy of its text to an old release. Then the script stops. A ninth one merges a bullet that both sides moved out of an old release. In a tenth one, both sides added a copy of a released entry to old releases. In an eleventh one, the branch moved a bullet out of an old release. `main` has an entry with its text under `[Unreleased]`, and `--absorb-unreleased` takes it in. The script stops in both. In a twelfth one, both sides renamed the heading of an old release the same way. The branch also added a copy of a released entry there. Then the script stops. A thirteenth one merges an old release whose heading both sides renamed the same way. In a fourteenth one, `main` has the heading of the new section of the branch. That section of `main` has a bullet that the branch added to an old release. Then the script stops. In a fifteenth one, two old releases have the same heading. The branch added a copy of a released entry to the first one. Then the script stops. In a sixteenth one, the branch removed an old release. Then the script stops. The test of a lost line of the branch now adds that line above `## [Unreleased]`.
- `tools/changelog_merge.py`: a table row below a bullet now belongs to that entry, like an indented line. The subcommand `unreleased` and the option `--absorb-unreleased` keep a blank line right above an indented line or a table row of an entry. Before, both lost that blank line with exit code 0. So a table moved into the text of the bullet above it. `unreleased` also dropped a table row of the branch that a table of `main` had under the same heading. An example is the separator row. The subcommand `release` now leaves out the table rows of a bullet that `main` already has, together with that bullet. Before, the rows stayed below the bullet above it, and the table was in the result two times. For a table row after a blank line below such a bullet, `release` stops with a `merge CHANGELOG.md by hand:` line. An entry can also be indented lines or table rows right below a `###` heading, with no bullet above them. The first line of such an entry matches only the first line under that heading on the other side. The docstring and `docs/tools.md` name the new rules (issue #343).
- `tests/test_changelog_merge.py`: 12 new tests (issue #343). For `unreleased`, one test keeps the blank line above a table and above an indented line. Another one keeps a row of a table of the branch that a table of `main` also has. A third one adds a bullet after a blank line below an entry of the merge base, with no stop. For `--absorb-unreleased`, one test keeps the blank line above a table. For `release`, one test stops for a table after a blank line below a dropped bullet. Another one leaves out a dropped bullet together with its table rows. A third one stops for a dropped bullet whose table has another row on `main`. Five more tests are for `unreleased`. One keeps one copy of a table with no bullet above it that both sides added. Another one keeps an indented line with no bullet above it that an entry of `main` also has. A third one keeps a table with no bullet above it that an entry of `main` also has. A fourth one stops for an entry of both sides with another table row. A fifth one keeps one copy of a table with no bullet above it that both sides added. There, `main` has a line of spaces below the heading.
- `tests/test_kb_plugin.py`: a new test plants `_claude/RULES.md` and hook scripts in a project folder and in its child folder. With no `KB_DIR` or with a relative `KB_DIR`, no hook script runs. Another new test runs the hook of the clone in a session inside the clone with `KB_DIR`. The three tests of the search of the project folder go, and the test of paths with spaces keeps only its `KB_DIR` part. On Windows, that test also runs the `C:/...` form. A third new test gives a `KB_DIR` with no clone in a project folder that is a clone (issue #129).

## dev-essentials 5.1.3 in release [6.1.3] - 2026-11-21

`failure_check.py` of `review-loop` now gives `SAME-AT-PARENT` for a test run on Microsoft.Testing.Platform that takes from 1 second up to 1 hour at one commit only. No skill text changes (issue #351).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: a time with more than one unit, such as `1s 318ms`, now becomes one token, as `683ms` does. `dotnet test` on Microsoft.Testing.Platform prints the line `duration: 1s 318ms` in its summary. The run at the commit before the fix builds in a new worktree, so it often takes more than 1 second. Before, that line gave `OTHER` in place of `SAME-AT-PARENT` for the same failure. Real runs of xunit.v3 4.0.3 and NUnit 5.0.0 with the .NET SDK 11.0.100 showed it. The help text of the script now names the rule (issue #351).

### Changed in the repository

- `tests/test_failure_check.py`: a new test with the real summary lines of `dotnet test` on Microsoft.Testing.Platform. A time with two units and a time with one unit give the same signature (issue #351).

## dev-essentials 5.1.2 in release [6.1.2] - 2026-11-21

`failure_check.py` of `review-loop` now gives `SAME-AT-PARENT` for a test run on Microsoft.Testing.Platform that keeps its failure after a new test. No skill text changes (issue #348).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: the counts of passed and skipped tests in the line of a test assembly of Microsoft.Testing.Platform now become a token, as in `[+<n>/x1/?<n>]`. The count of failed tests stays. `dotnet test` on that platform prints the line, for example `Probe.dll (net11.0|x64) failed with 1 error(s) [+1/x1/?0] (233ms)`. Before, a fix commit that added a test and kept the same failure gave `OTHER` in place of `SAME-AT-PARENT`. A real run of MSTest 4.2.3 with the .NET SDK 11.0.100 showed it (issue #348).

### Changed in the repository

- `tests/test_failure_check.py`: the samples of Microsoft.Testing.Platform hold the line of a test assembly and the last line of a real run of `dotnet test` with MSTest 4.2.3. A new count of passed or skipped tests in that line gives the same signature. A new count of failed tests gives another one (issue #348).

## dev-essentials 5.1.1 in release [6.1.1] - 2026-11-21

The skill `bug-hunt` runs the commands `snapshot` and `delete-temp` of its helper script in steps 1 and 6, in place of two helper agents. The subcommand `report` makes more of the structure tests of a report. A new cheap eval case, `bh-flow`, measures the flow of a run (issue #345).

### Added in dev-essentials

- `evals/bug-hunt/bh-flow`: a new cheap case for the flow of a bug hunt. It has one area, and its hunter, verifier, and auditor are Sonnet at medium effort. Its scored graders read the final report, the delete of the scratch folder and of each progress file, the run context file, and the project. Five of them compare a whole file of the project with the file of the scaffold. So an edit or a delete of one of these five files fails the run. Its route graders count a Bash call of `check_report.py snapshot` and of `delete-temp` with `--apply`. No grader reads recall (issue #345).

### Changed in dev-essentials

- `skills/bug-hunt`: step 1 runs the command `snapshot` of `check_report.py` in place of the setup helper, and step 6 runs `delete-temp` in place of the cleanup helper. Step 1 runs `snapshot` before the collector writes the digest, because the command refuses a scratch folder with files of another source. Step 6 reads the dry run first and then runs the command with `--apply`. `references/structure-checks.md` names each command, its options, and the action for each exit code in one place. A refusal of `delete-temp` goes to the user, and the run never deletes by hand or with another path. After a failed delete whose cause is gone, the run tries one more time. After a failed cleanup, the session progress file stays. Step 6 also deletes each old scratch folder that `snapshot` refused during a resume. The skill names Python 3.12 or later. The briefs of the setup helper and of the cleanup helper leave `references/agent-briefs.md`. The resume steps run the commands again (issue #345).
- `skills/bug-hunt/scripts/check_report.py`: the subcommand `report` makes more of the tests that the verifiers and the auditor made by hand. At the stages `summary` and `final`, each row of the Summary table must match its entry. The severity, the confidence, the verdict, and the "Also on base" answer must be the same. A cell that is not a value of the format, such as `N/A`, gives no defect. Each `Duplicate of BH-NN` must name an earlier entry. Each `BH-NN` of a verdict, of a `Result:` note, or of a "New details for" line must name an entry. So must each `BH-NN` of the list "For the owner's review". A `BH-NN` in other prose gives no defect, because it can name an entry of an older report. Each `N-NN` of a `Duplicate of` verdict or of a "New details for" line must be in the Known issues section. Each `#NN` of these places must be in the digest. With the new options `--snapshot` and `--base-snapshot`, each location must name a file and a line of the snapshot. A path out of the snapshot, also through a link, is a defect, and the script does not read it. A line 0 and a range that ends before it starts are defects too. An option value that names no folder stops the command with exit code 2. At the stage `final`, an appendix with entries must not say "None yet.". The command prints at most 100 DEFECT lines and then one line with the count of the rest (issue #345).

### Changed in the repository

- `tests/test_check_report.py`: `ReferenceAndRowTests` covers the new tests of `report`: a row that differs from its entry, a row with the new value of a changed entry, and a row of another area. It also covers a duplicate of a later entry and a reference to a missing known issue. A `#NN` reference with and without the digest has tests too. So do an entry ID of another report in prose and an entry ID in each place of the format. Other tests cover a location past the end of its file, a missing file, and a wrong line part. An absolute path, a drive path, and a link out of the snapshot have tests too. So do a path with a space or with `\`. More tests cover a cell that is not a value of the format and a row with no last `|`. Two more cover "None yet." in an appendix with entries and the limit of 100 DEFECT lines. One test covers a snapshot option that names no folder. `ValidReportTests` runs the fixture report with both snapshot options (issue #345).
- `tests/test_eval_cases.py`: `BugHuntFlowGraderTests` tests the route graders of `bh-flow` with right calls, a call through a shell variable, a dry run, and other commands. It also tests the report grader. A new test of `ShopFilesKeptGraderTests` holds the graders that compare a file of the project equal to the graders of `bh-planted-bugs` (issue #345).
- `tests/test_eval_scaffolds.py`: `BugHuntFlowGraderTests` runs the command lines of `snapshot` and `delete-temp` from `references/structure-checks.md` on the scaffold of `bh-flow`. Each wrong end state fails its scored grader (issue #345).
- `docs/evals.md`: the case count of the `bug-hunt` suite, and a paragraph on the new case and the limits of its graders (issue #345).
- `tests/simple-english-baseline.json`: seven entries for the regex patterns of the graders of the new case (issue #345).

## dev-essentials 5.1.0 in release [6.1.0] - 2026-11-21

The helper script of the skill `bug-hunt` gets two subcommands. `snapshot` exports the analyzed commit and its base into the scratch folder of a run. `delete-temp` stops the leftover processes of a run and deletes its scratch folder, with guards that refuse before any change. No skill text calls them yet (issue #339).

### Added in dev-essentials

- `skills/bug-hunt/scripts/check_report.py`: the new subcommand `snapshot` exports the analyzed commit into the scratch folder with `git archive`. It reads the archive with the `data` filter of `tarfile`, so no file lands outside the snapshot, and no `tar` program is needed. The command reads the archive to its end. So git does not fail on a full last record. A local base gets its own export, and a remote base gets a shallow clone of its branch. Each snapshot holds the bytes of the commit, whatever `core.autocrlf` says. The output gives the file counts, the SHA of the base, and each limit. The limits are submodules, `export-ignore`, `filter=lfs`, and each link that the filter leaves out. A link that the system cannot make and a second name that differs only by case also give a limit line. The command writes the marker file `.bug-hunt-scratch` into the scratch folder. It refuses a scratch folder that is not empty and has no marker. A folder with the marker and an entry that a run does not make gets a refusal too. A marker that exists stays as it is. A commit with no files gives an empty snapshot. It also refuses a scratch folder that is, holds, or is inside a folder of the repository. A snapshot folder that is not empty gets a refusal too. The command shares the guards of the place of the scratch folder with `delete-temp` (issue #339).
- `skills/bug-hunt/scripts/check_report.py`: the new subcommand `delete-temp` deletes the scratch folder and the progress files `_bug-hunt-progress-*.md` of a run. It finds these paths itself. Without `--apply`, it changes nothing and prints what it does. First it stops each process whose start time and command line match a `--pid` value. The command line must name the path of the scratch folder up to its end, so `/tmp/run` does not match `/tmp/run-2`. Then the command waits up to 5 seconds for the end of each process. A process that still runs gets a `NOT STOPPED` line. Each guard refuses the whole run before any change. The scratch folder must be an absolute path and hold the marker file of `snapshot`. An empty folder with no marker also passes, because it holds nothing to lose. The guards refuse a link or a junction, a drive root, a mount point, the home folder, and the temp root. They also refuse a missing report folder, the report folder, and each folder of the repository and its worktrees. A scratch folder entry that a run does not make gets a refusal. A worktree in the scratch folder whose git folder is outside it gets a refusal too. So does a git folder in the scratch folder whose work tree or linked worktree is outside it. git reads the `core.worktree` value, so a value in quotes gets the same refusal. If the path changes after the guards, the command deletes nothing in it. The delete removes the marker last, so a later run can finish a failed delete. A `FAILED` line names the path inside the scratch folder. After a failed first pass on POSIX, the command makes each folder writable and deletes again. With `--apply`, the command runs the test of the `cleanup` subcommand at the end. No skill text calls the new subcommands yet (issue #339).

### Changed in the repository

- `tests/test_check_report.py`: 80 new tests for `snapshot` and `delete-temp` (issue #339). `SnapshotTests` covers the bytes of each file, the live work tree, and each base source, also with a relative scratch folder. It also covers the marker file, the refusals, the limit lines, a missing commit, and the limit of 40 output lines. Other tests cover a link that the system cannot make, names that differ only by case, and the line ends of `core.autocrlf`. `DeleteTempTests` covers the dry run, a read-only file, a folder with no write right, the files that stay, and each guard. It also covers links, a junction on Windows, worktrees, clones, and git folders in the scratch folder. A path that changes after the guards and a delete that fails have tests too. Other tests cover a second run after a failed delete and an empty folder. A marker that is a link, a folder, or a hard link has tests too. A quoted `core.worktree` value, a commit with no files, and a fake mount table have tests too. As root, three tests drop the folder rights with `capsh`. The process tests cover the start time, the whole path, the process chain of the script, and a process that ignores SIGTERM. One test stops a real process. `OutputTests` covers the cut of a long line, a name with a line break, and a git timeout.
- `docs/testing.md`: the Windows paths that the tests of `snapshot` and `delete-temp` reach (issue #339).

## dev-essentials 5.0.0 in release [6.0.0] - 2026-11-21

The agents `task-composer` and `docs-composer` and the command `audit-openspec` leave, because no unit used them. `audit-plan` now also audits an OpenSpec change. The option `--mode` of `help-review-pr` is now `--post`, so its name no longer clashes with the work modes. A new eval case proves the post of one finding (issue #337).

### Added in dev-essentials

- `evals/help-review-pr/hrp-post-one`: a new case for the option `--post` of `help-review-pr`. The pull request of its scaffold has a real defect, a style defect, and a `TODO` comment. So the findings table has a major row, a minor row, and an info row. The run with `--post=2` must write the HTML artifact and edit no code. It must post one review comment, and that comment must be the style defect of row 2. Before this case, no eval case ran `help-review-pr` (issue #337).

### Changed in dev-essentials

- `commands/help-review-pr.md`: the option `--mode=html-only|post-all|post-<N>|post-<N>-<M>` is now `--post=all|<N>|<N>-<M>`. With no `--post`, the run writes only the HTML artifact. The old name was the name of the option of the work modes, which picks where a workflow stops (issue #337).
- `commands/audit-plan.md`: the command now also audits an OpenSpec change. It takes the folder of the change below `openspec/changes/`, or only the name of the change. The description names the OpenSpec change folder (issue #337).
- `skills/work-modes/SKILL.md`: the note on the `--mode` of `help-review-pr` goes, because that option no longer exists (issue #337).
- `evals/triggers/audit-plan-openspec-fires` and `evals/triggers/audit-plan-fires`: the new names of the cases `audit-openspec-fires` and `audit-openspec-near-miss`. Each one must start `audit-plan`. The graders on `audit-openspec` go, and so does the grader that kept `audit-plan` at zero calls (issue #337).
- `evals/triggers/compose-task-fires`, `compose-task-draft-fires`, and `create-documentation-guide-fires`: the descriptions name no removed agent. `compose-task-fires` and `create-documentation-guide-fires` no longer list the `Agent` tool (issue #337).

### Removed in dev-essentials

- The agents `task-composer` and `docs-composer`. No unit of the marketplace dispatched them. The skills `compose-task` and `create-documentation` do the same work in the session, or in a subagent that loads the skill (issue #337).
- The command `audit-openspec`. It differed from `audit-plan` only in its folder rule, and `audit-plan` now has that rule (issue #337).
- The graders `task-composer-not-fired` of `compose-task-fires` and `docs-composer-not-fired` of `create-documentation-guide-fires`. Also `route-task-composer-not-fired` of `cmp-task-draft` and `cmp-issue-create`, and `route-docs-composer-not-fired` of `cmp-guide-draft`. With no agent of that name, these graders cannot fail (issue #337).

### Breaking changes in dev-essentials

- Write the new name in place of the old one. The command `help-review-pr` no longer defines `--mode`. Phase 6 runs only with `--post`, so the text gives an old value such as `--mode=post-all` no meaning (issue #337).

| Old name | New name |
| --- | --- |
| The agent `dev-essentials:task-composer` | The skill `dev-essentials:compose-task`, in the session or in a `general-purpose` agent that loads it |
| The agent `dev-essentials:docs-composer` | The skill `dev-essentials:create-documentation`, in the session or in a `general-purpose` agent that loads it |
| `/dev-essentials:audit-openspec <change>` | `/dev-essentials:audit-plan openspec/changes/<change>` |
| `/dev-essentials:help-review-pr <url> --mode=html-only` | `/dev-essentials:help-review-pr <url>` |
| `--mode=post-all` of `help-review-pr` | `--post=all` |
| `--mode=post-<N>` of `help-review-pr` | `--post=<N>` |
| `--mode=post-<N>-<M>` of `help-review-pr` | `--post=<N>-<M>` |

### Changed in the repository

- `tests/test_eval_cases.py`: the tests of the removed graders go. `HelpReviewPrPostGraderTests` tests the graders of the new case on right and wrong runs. A post of row 1, a post of rows 1 and 2, and an edit of the reviewed code each fail a grader (issue #337).
- `docs/evals.md`: a row for the new suite `help-review-pr`, and a paragraph on the new case (issue #337).
- `docs/workflows.md` and `README.md`: they name `--post` in place of the `--mode` of `help-review-pr` (issue #337).

## dev-essentials 4.4.9 in release [5.4.9] - 2026-11-21

Three eval cases get graders that fail a wrong run: `ta-full-pass`, `bh-planted-bugs`, and `fp-e5-breaking-change`. A review of the 97 behavior cases by the rule of useful tests found them. No skill text changes (issues #336 and #338).

### Fixed in dev-essentials

- `evals/trim-artifacts/ta-full-pass`: the new scored grader `other-files-kept` reads the listing of the run. Each notes file that the user did not approve for deletion must still be in the folder `notes/`. Before, no scored grader read 7 of these 11 files. So a run that deleted one of them, or merged it into another file, passed each scored grader. The prompt approves only the deletion of the session log (issue #336).
- `evals/bug-hunt/bh-planted-bugs`: five new scored graders compare a whole file of the project with the file of the scaffold. They read `billing/invoice.py`, `inventory/cache.py`, `notify/retry.py`, `notify/email.py`, and `inventory/stock.py`. The grader `project-unchanged` is a `file_exists` grader, and it sees only the files that the run created. So before, a run that fixed a planted bug in place passed each grader of the case (issue #338).
- `evals/feature-pipeline/fp-e5-breaking-change`: the grader `test-unchanged` now reads the whole test that the new cache breaks. It also reads the `[Test]` attribute of the test, the header of its class, and the namespace line above the class. Before, it read only the last assertion of the test. So a run that put `[Ignore]` on the test, or that removed its first read, passed each grader of the case. A test with `[Ignore]` does not fail the test run, so `tests-passed` passed too. For a bug of the code, the stage `test-coverage` marks its own new test with `[Ignore]`. A run can do the same to the old test (issue #338).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: `TrimFullPassTests` deletes each kept notes file after a right trim, with each form of the backup. It also renames each kept file to `<name>.orig`. Each deletion and each rename must fail the new grader `other-files-kept` (issue #336).
- `tests/test_eval_cases.py`: `ShopFilesKeptGraderTests` tests the new graders of `bh-planted-bugs`. Each one passes the file of the scaffold. A fix of the bug in the file, or a change of the decoy, fails it. A new first or last line fails it too, and so does an empty file (issue #338).
- `docs/evals.md`: a `file_exists` grader does not see an edit of a file of the scaffold. So `bh-planted-bugs` reads the content of five files of its project. The file also names the limits of the grader `test-unchanged` of `fp-e5-breaking-change` (issue #338).
- `tests/simple-english-baseline.json`: six entries for the code text in the patterns of the new graders (issue #338).
- `tests/test_eval_cases.py`: `BreakingChangeTestGraderTests` runs the grader `test-unchanged` of `fp-e5-breaking-change` on the test file of the fixture and on 16 edits of it. Each of the 13 edits that skips, ignores, or changes the test fails the grader. A new test before or after it passes, and so do CRLF line ends (issue #338).

## dev-essentials 4.4.8 in release [5.4.8] - 2026-11-21

The scored grader `no-run-commit` of five resume cases now fails an orphan commit and an amend that keeps the subject of a fixture commit. No skill text changes (issue #335). The release also takes in the guard of `changelog_merge.py release` against a silent loss of an indented line (issue #330).

### Fixed in dev-essentials

- `evals/*/*/graders/no-run-commit.md` of `it-merge`, `ib-merge`, `rirr-merge`, `rirr-resume-moved-head`, and `rirr-upstream-remote`: the scored grader now fails an orphan commit and an amend that keeps the subject of a fixture commit. For an orphan commit, git writes `commit (initial): <subject>`, and the old pattern did not count that form. An amend with `--no-edit` keeps the subject `fixture: ...`, and the old pattern skipped it. So a run with such a commit passed the grader. The six copies of the grader now have one text, the text of `it-no-worktree-dirty` (issue #335).

### Changed in the repository

- `tools/changelog_merge.py`: the subcommand `release` now stops for a bullet that it leaves out with a new indented line. `main` and the merge base lack that line below that bullet. This happens for a section of the branch with another heading than the top heading of `main`. Before, the script left out that line with the bullet. If the same line was below another bullet, no guard saw the loss, and the script ended with exit code 0. The script also stops for an indented line after a blank line below such a bullet. Before, that line moved below another bullet. A line of only spaces below such a bullet gives no stop. The branch can have the line right below the bullet, and `main` can have it after a blank line below its copy of the bullet. Then the script gives no stop. The subcommand `unreleased` and the option `--absorb-unreleased` now compare an indented line only with the lines below the same `-` bullet. Before, the same line below another bullet of the subsection hid the loss. An entry with another first line, such as a `*` bullet, still compares with the whole subsection. The new STOP line starts with `merge CHANGELOG.md by hand` and names the bullet and the line, each cut at 40 characters. The docstring and `docs/tools.md` name the new stops (issue #330).
- `tests/test_changelog_merge.py`: 19 new tests (issue #330). Six tests stop. Four cover the smallest pair of the loss, a tab line below a second dropped bullet, and two lines after a blank line. The fifth covers a line that the merge base has below another bullet. The sixth covers a line that `main` has below a paragraph after a blank line. Two tests merge a shared bullet: with the same indented lines, and with a line that `main` changed since the merge base. Two more merge with two copies on `main` and with a line of only spaces. Two more merge with a line that `main` has after a blank line, and with a dropped bullet above another subsection of the branch. A bullet of an old release keeps its new indented line. A bullet that the branch has twice reaches the count stop. Two tests read the STOP lines of a long bullet. For the subcommand `unreleased`, one test stops for an indented line below another bullet. Another one merges an entry with a `*` marker. For the option `--absorb-unreleased`, one test stops for an indented line below another bullet. The test `test_indented_line_below_a_bullet_that_main_has_refuses` still stops, but with the STOP line of the new guard.
- `tests/test_eval_scaffolds.py`: a new test of `CommitGraderTests` runs `no-run-commit` of the five cases on real git states. An orphan commit and an amend of the fixture commit with `--no-edit` must each fail the grader (issue #335).
- `tests/test_eval_cases.py`: in `RirrFinishCaseTests`, the sample `commit (amend): fixture: amended` now counts as a commit of the run. Before, the sample expected a pass, so it pinned the gap. A new sample `commit: fix the retry limit` must count too. Its subject starts like the fixture prefix, so a lookahead that skips more than `fixture:` fails it. Four new samples cover the merge and cherry-pick forms (issue #335).
- `docs/evals.md`: two known limits of `route-no-worktree-read`. A harmless call with a `branch` word before the read, such as `git branch 2>/dev/null`, can make it fail a right run. In Bun 1.4.4, it gives no match with 350,000 characters before the read, and it matches with 300,000 (issue #335).

## dev-essentials 4.4.7 in release [5.4.7] - 2026-11-20

A new eval case shows the stop of `--no-worktree` on a changed file of the user. No skill text changes (issue #329).

### Added in dev-essentials

- `evals/implement-task/it-no-worktree-dirty`: a new case for the stop of `--no-worktree` on a change of the user. Its scaffold changes one tracked file of the clone and commits nothing. The run with `--mode full` must stop before any work and name the file. It must make no commit and keep the change. Before this case, no eval case planted a changed tracked file, so no run proved the stop (issue #329).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: `NoWorktreeDirtyGraderTests` runs the scored graders of the new case on real git states. An edit of the file, a stash, a restore, and a commit each fail at least one grader. `ScaffoldTests` makes sure that the new scaffold leaves exactly one changed tracked file (issue #329).
- `tests/test_eval_cases.py`: `NoWorktreeDirtyRouteGraderTests` tests the route graders of the new case. `NoWorktreeReadGraderTests` also covers the new case (issue #329).
- `docs/evals.md`: the case count of the `implement-task` suite, and a paragraph on the new case (issue #329).
- `tests/simple-english-baseline.json`: one entry for the file path in a grader of the new case (issue #329).

## dev-essentials 4.4.6 in release [5.4.6] - 2026-11-20

The trace graders `tests-before-commit` and `untested-commit` now take far fewer steps. So in most measured cases, the regex engine of the eval tool stops them only on a much larger trace. With 200 to 250 test commands before the first fitting commit, the new `tests-before-commit` stopped at the same size as the old one. No skill text changes (issues #319 and #328).

### Fixed in dev-essentials

- `evals/*/*/graders/tests-before-commit.md` (nine cases) and `evals/*/*/graders/untested-commit.md` (seven cases): the token between the two calls now runs its lookahead only at a quote, and it stops at the first fitting commit. Each grader gives the same verdict as before, with far fewer steps. The `claude` binary holds Bun 1.4.4, whose engine stops a long search with no match. On a trace of 690,094 characters, the old `tests-before-commit` failed a right run of `ib-no-worktree` (issue #319). The old `untested-commit` gave no match on a built wrong trace, and so a pass (issue #328). That trace had about 196,000 characters between the edit and the commit. In Bun 1.4.4, both new patterns match a built trace with 2,000,000 characters between the two calls.

### Changed in the repository

- `tests/test_eval_cases.py`: `TestsBeforeCommitGraderTests` now also reads the grader `tests-before-commit` of `it-no-worktree` and `ib-no-worktree`. A new sample has a test, a commit, an edit, and a second commit, and it must match. Four more samples cover a backslash between the two calls, a `NotebookEdit` stop, and a word that ends with `unittest`. A new test pins the end of the match at the first fitting commit. The unit tests run Python `re`, so no sample shows the limit of Bun 1.4.4 (issues #319 and #328).
- `docs/evals.md`: the replay tool runs V8, and the `claude` binary holds Bun 1.4.4, which runs JavaScriptCore. The new text gives the facts of the failed run and the limits that Bun 1.4.4 showed. It also names the risk for a `not_contains` grader (issues #319 and #328).

## dev-essentials 4.4.5 in release [5.4.5] - 2026-11-20

If a fix commit swaps or adds a hit above the first error line, `failure_check.py` of `review-loop` now gives `OTHER`. The same holds for an error line that comes one more time. No skill text changes (issue #311). The release also takes in the retry of a .NET scaffold test after the rare CLR crash (issue #261). It also takes in the new script `tools/release.py` (issue #317). The third one is the fix of `changelog_merge.py release` for a heading that `main` took first (issue #318).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: with an error line in the output, each line above the first error line that names a place now counts too. The line and column numbers of the first place of such a line do not count. So a hit or a warning that moved to another line still gives `SAME-AT-PARENT`. A place is a file name with an extension and a line number, such as `src/a.py:3` or `A.java:[3,5]`. A name with no extension needs a `:` after the number, as in `Makefile:3:`. A `3:5` at the start of a word, a `(3,5)` after a name, and a code frame line such as `3 | x = 1` are places too. So is a Python line such as `File "a.py", line 3`. So is a line with only a file path or a file name and a `:`, with no space in it. Examples are the file line of eslint stylish and of grouped ruff. A digit of a file name in such a line stays. Before, such a line did not count. So a swapped hit above a summary such as `Found 1 error.` gave `SAME-AT-PARENT`. The same held for a hit above a file such as `src/errors.py`, and for a hit that moved to another file. Each line of the compare now has its count, so an error line that comes one more time gives `OTHER`. A root folder now becomes a token only at the start of a path, where no character of a file name comes before it. Before, the rule also took the folder name before it, so a repository in `/app` made `src/app/util.py` and `tests/app/util.py` the same. An ISO time with a time zone and the time of a tqdm progress bar now become a token too. An incremental build in the clean main worktree can print fewer warnings than the build at the commit before. Then a warning line with a place gives `OTHER`, and the docstring says so. The docstring and the reason text of `OTHER` name the new compare (issue #311).

### Changed in the repository

- `tests/test_failure_check.py`: 24 new tests (issue #311). Five of them hold the real output of ruff 0.17.6. They cover these results:
  - A swapped hit above the only error word gives `OTHER`, in the concise and in the full output of ruff.
  - A swapped hit above a hit in `src/errors.py` gives `OTHER`.
  - A swapped hit above a summary with an error word gives `OTHER`, in the stylish form of eslint.
  - A moved hit above such a summary gives `SAME-AT-PARENT`. The samples are the grouped output of ruff, a warning of a C# build, a place with a column, and the Maven form.
  - The same hit in another file gives `OTHER`, in the grouped output of ruff and in the Python form `File "a.py", line 2`. This holds also for a file in the root folder, such as `a.py:`.
  - A digit of a file name in a line with only a path stays. So `step-1-a.js` and `step-2-a.js` give `OTHER`. A number in the message or in the code of a line with a place stays too.
  - More forms of a place count: a place with color codes, a name with no extension, the Maven form, and the forms of a code frame. A line of test dots, a port, and a time are no places.
  - A place between the first error line and the last lines counts, and the reason of `OTHER` names the lines with a place.
  - An error line that comes one more time gives `OTHER`.
  - A run with an error line never matches a run with none. This holds also for an error word that is only in the root folder.
  - The root `/app` no longer takes the folder name before it. A root after an option, a quote, `=`, `:`, `,`, `@`, or a backtick still becomes a token. So does a root in a file URL.
  - The text before the temporary folder stays, and a long line with an option or a path takes less than 5 seconds.
- `tests/test_eval_scaffolds.py`: after the rare crash of the .NET runtime, `DotnetProbeTests` runs the scaffold one more time in a new folder. The crash fails the scaffold with the text "Internal CLR error". The retry prints one line to stderr. Any other failure fails at once. A second crash fails too, and the error holds the output of both tries. Before, the crash failed the run of the whole suite. Four new tests in `DotnetWarmTests` use a fake `dotnet`. It crashes one time, fails in another way, aborts with no crash text, or crashes two times (issue #261).
- `tools/wsl/linux/unit-tests-clone.sh`, `docs/tools.md`: the lines that `tools/wsl/unit-tests.sh` prints now include each retry line of a .NET scaffold, so a crash with a retry shows in the output. A new test in `UnitTestsTests` pins it (issue #261).
- `tools/release.py`: a new script for the maintainers, with two subcommands. `section` puts a release section right below `## [Unreleased]` of `CHANGELOG.md`. It moves the `[Unreleased]` link line, adds the link line of the release, and writes the new version into each `plugin.json`. `notes` writes the notes of a GitHub release from the release section. Before, a person or an agent did these steps by hand. The script stops and writes nothing on a second section or on a version that is not higher. It also stops on an `[Unreleased]` entry that the section lacks (issue #317).
- `tests/test_release.py`: the tests of the new script. The job `test-windows` of `.github/workflows/tests.yml` runs them. `docs/tools.md` says how to run the script. `docs/testing.md` names its tests, and `docs/authoring.md` and `README.md` name the release as a purpose of `tools/` (issue #317).
- `tools/changelog_merge.py`: the subcommand `release` now merges a branch whose top heading `main` took first. For example, two open branches take the same release numbers, and one of them merges first. Before, the script stopped with exit code 3. If the two sections share no entry, the script now puts the whole section of the branch on top with the new numbers. If they share an entry, the script stops, for example after a squash merge of the same branch. The script also stops for a heading that the merge base has too. If `main` added each bullet of a section with another heading since the merge base, the script now stops. Before, it wrote a release section with no bullet. The docstring and `docs/tools.md` name each stop. `docs/tools.md` also names the next step (issue #318).
- `tests/test_changelog_merge.py`: 15 new tests (issue #318). They cover these results:
  - A branch whose top heading `main` took after the merge base merges in full. This holds for indented lines, a paragraph after a blank line, and an empty `###` heading. It also holds for lines that the section of `main` has below other bullets, and for a bullet with the text of an old release.
  - A bullet that both sides added to their section stops. This holds below another `###` heading, with a paragraph after a blank line, and with the text of an old release. It also holds for an entry under `[Unreleased]` that both sides moved into their section. A squash merge stops too, also with `--absorb-unreleased`.
  - For another heading, a section whose bullets `main` added stops, also with `--absorb-unreleased`. A section with star bullets or with no bullet merges.

## dev-essentials 4.4.4 in release [5.4.4] - 2026-11-20

The route grader `route-no-worktree-read` of the two `--no-worktree` cases now sees a branch command with more options before the option that creates the branch. No skill text changes (issue #315). The release also takes in the first slice of the review of the unit tests (issue #316).

### Fixed in dev-essentials

- `evals/implement-task/it-no-worktree` and `evals/implement-batch/ib-no-worktree`: the route grader `route-no-worktree-read` sees more forms of a branch command. Another option can now come before the option that creates the branch, for example `git checkout -q -b` or `git switch -qc`. Two spaces before `-c`, `git branch -f`, and `git branch --force` count too. Before, a run that read the rules of `--no-worktree` after such a command passed the grader (issue #315).

### Changed in the repository

- `tests/test_eval_cases.py`: `NoWorktreeReadGraderTests` has twelve new runs that read the file too late. Ten of them use a new form. Two of them keep the name right after `-c` or `-b`. Two new samples show that `git branch -a`, `git switch --detach`, and `git switch main` create no branch (issue #315).
- `docs/evals.md`: the paragraph of the two cases names the branch commands of the grader (issue #315).
- `tests/test_work_modes_text.py`: one duplicate test is gone, `FinishCallerTests.test_merge_pr_counts_the_yes_of_the_final_gate`. It made the same assertion on the same file as the subtest for `merge-pr` of `UnitRuleTests.test_the_unit_rules_stay`. That subtest stays, because it guards the approval sentence of `merge-pr`. `PipelineMergeTests` of `tests/test_eval_cases.py` pins a longer text that holds the same sentence (issue #316).
- `tests/test_openbsd_lint.py`: one test is gone, `HookFileTests.test_script_exists`. It failed only where stronger tests of the same module also fail: a missing script fails about 100 other tests (issue #316).
- `tests/test_eval_front_matter.py`: `YamlScanTests.test_a_machine_without_pyyaml_fails_with_the_install_hint` now fails for a `require_yaml` that skips the test. Before, such a skip made the test skip too, so the suite passed (issue #316).
- The review of the 1360 unit tests below `tests/` found no other exact duplicate and no test that cannot fail for a bug. It read each short test and each text module in full, and the other modules by class. So the suite has 1358 tests now (issue #316).

## dev-essentials 4.4.3 in release [5.4.3] - 2026-11-20

`failure_check.py` of `review-loop` now gives `SAME-AT-PARENT` for a lint that fails in the same way at both commits and prints no error word. No skill text changes (issue #301).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: a run with no error word in its output gets a signature that counts each line that is not blank. Before, the signature of such a run was empty, so the verdict was `OTHER`. A lint such as flake8 prints no error word. A new or a repeated lint hit at any place gives `OTHER`. The exception is a lint that prints one line for each file. A run with an error line never matches a run with none. In a temporary export, a run with no error line gives `OTHER`, because the script cannot see a git error there. Two small fixes also help runs with an error line. Each byte that is not UTF-8 stays different, and a place such as `prog.1:12:10` is no longer a clock time. The help of `--command` and the docstring name the lint. The docstring and the reason text name the new compare (issue #301).

### Changed in the repository

- `tests/test_failure_check.py`: 15 new tests (issue #301). They cover these results:
  - The same lint output at both commits gives `SAME-AT-PARENT`. So does the same output with other times, other root folders, or other blank lines.
  - Another hit, another first hit, a new hit in the middle, and a repeated hit line give `OTHER`. So does an error line at one commit only.
  - After an error line, the last 15 lines count. The lines between an error word on the first line and the last 15 lines do not count.
  - The place of a hit such as `prog.1:12:10` is not a clock time, and two bytes that are not UTF-8 stay different.
  - A run in a temporary export with no error line gives `OTHER`.
  - Output with no line to compare gives `OTHER` with its own reason.
- `tests/test_failure_check.py` and `tests/test_eval_cases.py`: the reason line of `ExportTests` and the sample of `FailureCheckExportGraderTests` hold the new reason text (issue #301).

## dev-essentials 4.4.2 and dotnet-backend-dev 1.8.3 in release [5.4.2] - 2026-11-19

The text of the units no longer counts the items of a list. Each time an item joins or leaves a list, such a count is wrong, and it gives no instruction. Limits, thresholds, identifiers, and the numbers of examples stay (issue #309).

### Changed in dev-essentials

- `skills/engineering-discipline`, `skills/dotnet-build-test`, and `skills/work-modes`: the description loses its count word. It now starts with "Rules against", says "The exceptions to this rule", or says "Defines the work modes" (issue #309).
- Each skill, reference file, stage file, agent, and command with such a count: the count word goes, or it becomes "these", "the", or "each". For example, the pointer to `work-modes` in each gated workflow now says "the modes". Each stage file of `feature-pipeline` that a subagent runs says "replace the placeholders" (issue #309).

### Changed in dotnet-backend-dev

- `skills/create-tests`, `skills/dotnet-conventions`, `skills/model-mapping`, `skills/add-migration`, `skills/add-session-logging`, and `skills/handle-sensitive-data`: the count word of a list goes (issue #309).

### Changed in the repository

- `README.md`: the count of the plugins and the count of the official pages go (issue #309).
- `docs/permissions.md` and `docs/workflows.md`: the count of the push cases goes. So do the count of the values of `--mode` and the count of the steps of the usual chain (issue #309).
- `tests/test_work_modes_text.py` and `tests/test_eval_cases.py`: the pins follow the new text. The pin of the questions that still stop in the full mode of `process-pr-comments` now holds both questions and the sentence after them (issue #309).

## dev-essentials 4.4.1 in release [5.4.1] - 2026-11-19

This release fixes one grader that seven eval cases share. No skill text changes (issue #293).

### Fixed in dev-essentials

- `evals/*/graders/untested-commit.md` of `rirr-retry-limit`, `rl-null-guard`, `rl-off-by-one`, `rl-unbounded-query`, `so-rename-large`, `so-rename-small`, and `so-two-fixes`: the grader passes a run that tests between the edit and the commit in one chained command. This also holds after an earlier `git` step such as `git diff`. Before, the commit part of the pattern started at the earlier `git` step and took in the test run. So a right run failed. Both alternatives of the pattern change. A commit with no test run still fails. The one exception is the word `unittest` between a `git` step and the `commit` of one command, and `docs/evals.md` names it (issue #293).

### Changed in the repository

- `tests/test_eval_cases.py`: `TestsBeforeCommitGraderTests` gets two chained commands that must pass and two runs that must fail. The test of the known wrong verdicts gets two forms of the new one. The word `unittest` is in an earlier `git` step or in the commit step (issue #293).
- `docs/evals.md`: it names the new wrong verdict of `untested-commit` (issue #293).

## dev-essentials 4.4.0 in release [5.4.0] - 2026-11-19

`review-loop` gets three changes. The re-review of a round gets the findings, the verdicts, and the fix plans of the round before it (issue #296). For a branch, a pull request, commits, or a diff, Phase 6 takes its commands from the `CLAUDE.md` at the base of the target. Phase 1 pins that base to a SHA (issue #297). A failed lint of the command that `CLAUDE.md` names now fails Phase 6 (issue #298).

### Added in dev-essentials

- `evals/review-loop/rl-edited-rules`: a new route case. The branch narrows the test command in `CLAUDE.md`, so that the test of its defect does not run. The route grader `route-base-rule-file` needs a read of `CLAUDE.md` at `main`, at a SHA, or at a shell variable in the main loop. A read of the copy of the branch does not pass (issue #297).
- `evals/review-loop/rl-lint-gate`: a new route case. `CLAUDE.md` names a lint command, and the lint already fails on `main`. The route grader `route-lint-check` needs a run of `failure_check.py` with the lint command. The scored graders `lint-tool-kept` and `vendor-kept` need the whole lint script and the whole vendored file as they are. The scored grader `stop-blocked` needs `Stop verdict: stop-blocked` in the final message (issue #298).
- `evals/review-loop/rl-off-by-one`: the new route grader `route-earlier-findings` needs a re-review brief with a verdict next to a severity (issue #296).

### Changed in dev-essentials

- `skills/review-loop`: the re-review of round N+1 gets one line for each finding of the fix pass of round N. The line gives the severity, the verdict, and the fix plan, from the cycle report of round N. A REJECT line also gives the reason of the fixer. The re-review reports a wrong REJECT only with a primary source (issue #296).
- `skills/review-loop`: for a `branch`, `pr`, `commits`, or `diff` target, Phase 6 reads `CLAUDE.md` with `git show <base SHA>:CLAUDE.md`. Phase 1 pins the base SHA once, because each fix commit moves `HEAD`. It is the merge base for `branch` and `pr`, and for a three-dot range of `diff`. For `commits` and any other range of `diff`, it is the left side of the range. So a branch cannot edit the command lines that judge it. A script or a manifest that such a command runs still comes from the branch. With no root file at the base, Phase 6 reads `.claude/CLAUDE.md`, and it reads the files that `CLAUDE.md` imports with `@`. With no `CLAUDE.md` at the base, the manifest steps run as before (issue #297).
- `skills/review-loop`: if `CLAUDE.md` names a lint command, a failed lint is a failed Phase 6. Phase 6 runs the lint after the tests, also after failed tests. A failed lint takes the path of a failed build to `failure_check.py`. With more than one failed command, the failure check gets the first one in the order build, tests, lint. The Phase 9 summary and the brief of each cycle get a `Lint:` line (issue #298).

### Changed in the repository

- `tests/test_eval_cases.py`: the new classes `EarlierFindingsGraderTests` and `BaseRulesAndLintGraderTests` test the new graders on right and wrong trace lines. `StopVerdictRouteGraderTests` covers the two new cases (issues #296, #297, and #298).
- `tests/test_eval_scaffolds.py`: two new tests run the new scaffolds. One shows that the narrowed test command skips the failing test. The other shows that the lint fails at both commits, so `failure_check.py` gives `SAME-AT-PARENT`. It also shows that the lint break is on `main`, outside the diff. The new cases join the tables of the scaffold tests (issues #297 and #298).
- `docs/evals.md`: the suite `review-loop` has 8 cases (issues #297 and #298).

## dev-essentials 4.3.1 in release [5.3.1] - 2026-11-19

The rules of the option `--no-worktree` have one home now: `references/no-worktree.md` of `work-modes`. `implement-task` and `implement-batch` read it only in a run with that option. So a run with no option loads 370 fewer words of each unit (issues #290 and #295).

### Added in dev-essentials

- `skills/work-modes/references/no-worktree.md`: the steps of the option `--no-worktree` of `implement-task` and `implement-batch`. The steps are the text of the two units, word for word. Only the names of the workflow file and of the base branch changed. A short head gives the order of the steps and says what the workflow file is (issue #290).
- `evals/implement-task/it-no-worktree` and `evals/implement-batch/ib-no-worktree`: the route grader `route-no-worktree-read`. It passes only for a run that reads the new file before its first branch command and its first Edit or Write call. A read, an Edit, or a Write of a subagent does not count (issue #290).

### Changed in dev-essentials

- `commands/implement-task` and `skills/implement-batch`: Phase 1 and Step 1 keep one pointer sentence in place of the rules. A run with `--no-worktree` reads the new file before any other step there. The option row, the gate row, the user file list for the agent, and the finish sentences stay in each unit (issue #290).
- `skills/research-implement-review-report`: the line of the effort levels no longer points at Rule 5 of `subagent-orchestration`, which is the rule for named teammates. The line of the models already points at "Model selection" (issue #295).

### Changed in the repository

- `tests/test_work_modes_text.py`: `NoWorktreeTests` pins the safety sentences in the new file. It also makes sure that each unit points at the file in its worktree setup and holds no second copy of the rules (issue #290).
- `tests/test_eval_cases.py`: `NoWorktreeReadGraderTests` tests the new route grader with a read before and after the first step (issue #290).
- `docs/evals.md`: it names the new route grader (issue #290).

## dev-essentials 4.3.0 and dotnet-backend-dev 1.8.2 in release [5.3.0] - 2026-11-19

The terms "useful test" and "bad test" now have one general home: the new Rule 8 of the skill `engineering-discipline`. It names the classes of bad tests with no stack name, and the one exception for a contract value. The skill `create-tests` keeps its .NET examples and points at the rule (issue #294).

### Added in dev-essentials

- `skills/engineering-discipline`: Rule 8, "Write only useful tests". A useful test fails for a bug or for a bad change of behavior. The rule names four classes of bad tests, for example a test that only reads back a fixed value. A test can pin a contract value, which other systems, users, or stored data read. The description of the skill names the new rule (issue #294).
- `evals/engineering-discipline/ed-useful-tests`: a new behavior case. The request loads `engineering-discipline` and asks for unit tests of one Python module with public constants and one function. Scored graders need a test that calls the function in an assertion or an assignment. They also need a test of a guard, a passed test run, and an unchanged module. The scored grader `no-constant-test` fails a test file that asserts only the value of a constant (issue #294).

### Changed in dotnet-backend-dev

- `skills/create-tests`: the section "Useful Tests" starts with new sentences and points at Rule 8 of `dev-essentials:engineering-discipline` for the terms. It keeps its three .NET examples. The first one now asks for the input and the expected value as written values, not as the name of the constant. Its last sentence keeps two examples of a contract value: an error code and the default of a configuration option (issue #294).
- `skills/dotnet-conventions/testing.md`: the sentence on useful tests points at Rule 8 and at the .NET examples of `create-tests` (issue #294).

### Changed in the repository

- `tests/test_rule_references.py`: a new test. Each reference to a numbered rule of `engineering-discipline` in a plugin file must name an existing rule. This includes a table row whose first cell is that skill. The section "Useful Tests" of `create-tests` must point at the rule for useful tests (issue #294).
- `tests/test_eval_cases.py`: the new class `UsefulTestsCaseGraderTests` tests the graders of the new case on samples (issue #294).
- `docs/testing.md` and `docs/evals.md`: a link to Rule 8, and the new suite `engineering-discipline` with one case (issue #294).

## dev-essentials 4.2.1 in release [5.2.1] - 2026-11-19

This release fixes one grader of an eval case. No skill text changes (issue #292).

### Fixed in dev-essentials

- `evals/research-implement-review-report/rirr-retry-limit`: the grader `reported` also takes a last message that says that the run changed a test. An example is "updated the one test that checks it". Before, only the file name `test_http_client.py` passed, so a right run failed. A message that names no test change still fails (issue #292).

### Changed in the repository

- `tests/test_eval_cases.py`: `RetryLimitReportedGraderTests` runs the grader `reported` of `rirr-retry-limit` on sample replies. A reply that names a test change passes. A reply that only says that the tests pass fails (issue #292).
- `tests/evals/compare_versions.py`: `run` takes the option `--keep-temp`, the same as `baseline`. It passes the option to the base side and to the head side. The commands of a report that run the cases again keep the option. Before, `run --keep-temp` stopped with exit code 2. `tests/evals/test_compare_versions.py` tests the change, and `docs/evals.md` names it (issue #291).

## dev-essentials 4.2.0 in release [5.2.0] - 2026-11-19

`implement-task` and `implement-batch` take the new option `--no-worktree`. With it, the run makes no git worktree and works in the current folder. Each of the two workflows also gets its first eval case that runs it from its start (issue #282).

### Added in dev-essentials

- `commands/implement-task` and `skills/implement-batch`: the option `--no-worktree`. The run makes no worktree, and it works on the current branch in the current folder. If a tracked file has a change, it stops. It asks before a task writes, stages, or deletes an untracked file of the user. On the default branch, the base branch, or a detached HEAD, the full mode first creates the branch of the `--worktree` row. The partial mode and the interactive mode ask for a branch name. On a branch, they also offer a yes to work on it, with local commits and no finish step. If that branch already exists, or the request names another branch ref, the run asks. If the branch holds commits that are not on the remote base branch, or the run cannot count them, it asks. In the full mode, it does no finish step and names those commits as the reason. After a merge, the run removes no worktree (issue #282).
- `evals/implement-task` and `evals/implement-batch`: the cases `it-no-worktree` and `ib-no-worktree`. Each one runs its workflow with `--no-worktree` and `--mode full` in a clone on `main`. The run must create its branch, make one commit for each task, and push nothing. Before them, no eval case ran these workflows from their start, because `git worktree add` fails in an eval run (issue #282).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: `NoWorktreeBranchGraderTests` tests the branch graders of the two new cases on real commits, also with an amend and a cherry-pick. The new scaffolds join the tables of the scaffold tests (issue #282).
- `tests/test_work_modes_text.py`: `NoWorktreeTests` pins the cells of the new gate row that ask outside the full mode. It also pins the sentences that protect the work of the user (issue #282).
- `docs/workflows.md` and `docs/evals.md`: they name the option `--no-worktree` and the two new cases (issue #282).

## dev-essentials 4.1.0 in release [5.1.0] - 2026-11-19

This release turns the model matrix of `subagent-orchestration` into a ladder. A dispatch with no better fit starts on Opus at `medium` effort. If a step falls short, the run first raises its effort, and only then moves the step to a larger model. Fable is the step after Opus at `xhigh`, not an exception. Well-scoped work still goes to Sonnet, and mechanical work to Haiku (issue #281).

### Added in dev-essentials

- `evals/subagent-orchestration/so-ladder-start`: a route case. The request sends one bug fix with no fix plan to one subagent. The route grader `route-ladder-start` shows a dispatch on Opus at `medium` effort (issue #281).

### Changed in dev-essentials

- `skills/subagent-orchestration`: Opus at `medium` effort is the default of the matrix. Sonnet takes well-scoped work: an approved plan, a written fix plan, or a brief settles each decision. The new ladder moves each step that runs in a subagent, also a dispatch that a workflow skill names. A model and an effort that a skill names are the start of the ladder for that step. A step falls short in two cases. First, its self-test fails again after one resume with the error lines. Second, its reviewer reports a finding that blocks the merge. A failure whose fix is out of the scope of the step is no fall short, and the run stops and tells the user. If a step falls short, the run raises the effort one level, up to `xhigh`. After that, it moves the step one model up, at `high`. The ladder ends after three moves of one step. A move from `low` to `medium` is not one of the three. The level `max` needs the word of the user or of a skill. A limit of tries that a skill names wins over the ladder. A move up to Fable is never silent. On a Sonnet session, a code change that Rule 1 keeps in the main loop stays there. A plan, a review, and a decision that no plan settles still go to Opus. In `references/model-selection.md`, a dispatch with no named effort starts at `medium`, and a review starts at `high`. If the `Agent` tool or the model has no effort levels, the ladder makes no move that only raises the effort. This changes the dispatches with no named effort of `optimize-skill`, `audit-team`, `process-pr-comments`, and `promote-conventions`. It also changes `trim-artifacts`, `feature-pipeline`, `help-review-pr`, and Phases 2 and 4 of `implement-task` (issue #281).
- `skills/review-loop`: the rule "Keep Opus" of the partial mode holds for the reviewer only. A fixer subagent moves up by the model ladder, and the final summary names the step (issue #281).
- `skills/work-modes`: outside the interactive mode, a workflow moves a step up to Fable by the ladder with no question. It names the move in the final report. Before, it used Opus (issue #281).
- `skills/research-implement-review-report`, `commands/implement-task`, `skills/implement-batch`, and `skills/feature-pipeline`: in the partial and the full mode, the gate row for Fable follows the ladder. The first three lose the bullet "Fable is for exceptional cases only" (issue #281).

### Changed in the repository

- `tests/test_model_ladder_text.py`: a new test. A plugin file that keeps the old Fable rule, the old default row, or the old effort rule fails it (issue #281).
- `tests/test_eval_cases.py`: the new class `ModelLadderCaseTests` tests the grader `route-ladder-start` on right and wrong `Agent` calls (issue #281).
- `tests/test_eval_scaffolds.py`, `tests/test_work_modes_text.py`, `tests/simple-english-baseline.json`, and `docs/evals.md`: the new case and the new sentence of `work-modes` (issue #281).

## dotnet-backend-dev 1.8.1 in release [5.0.2] - 2026-11-19

The skill `create-tests` now asks for useful tests only. A useful test can fail for a bug or for a bad change of behavior. A test that only asserts that a constant or a property with a fixed value has its value is not useful. The repository guidance has the same rule for its own tests and eval cases (issue #280).

### Added in dotnet-backend-dev

- `evals/write-tests/wt-useful-tests`: a new behavior case. The class under test has four public constants and a property with no logic, next to a method with real logic. Scored graders need tests of the method and of a guard, a passed test run, and an unchanged class. The scored grader `no-constant-test` fails a test file that asserts only the value of a constant or of the property (issue #280).

### Changed in dotnet-backend-dev

- `skills/create-tests`: the new section "Useful Tests" and one new item of the checklist. The section gives the rule, its reason, and three kinds of tests that are not useful. It also names the values that can still have a test of their own: a wire format, a persisted value, an error code, or the default of a configuration option (issue #280).
- `skills/create-tests/examples/domain-model-tests.md`: key point 6 asks for a constructor test for a hand-written constructor only, not for a positional record. The two example tests of the hand-written constructors stay, and they lose their `NotBeNull()` line (issue #280).
- `skills/dotnet-conventions/testing.md`: one sentence points at the new section of `create-tests` (issue #280).

### Changed in the repository

- `CLAUDE.md` and `docs/testing.md`: each test of the repository must be able to fail for a bug or for a bad change. Step 3 of "New and imported units" asks the same of each eval case: it must be able to fail for a real defect of its unit (issue #280).
- `docs/evals.md`: the suite `write-tests` has three cases (issue #280).
- `tests/test_eval_cases.py`: the new class `WriteTestsUsefulTestGraderTests` tests the graders `no-constant-test`, `covers-get-fee`, `covers-guard`, and `source-unchanged` of the new case on samples. The route tests of one class also read the new case (issue #280).
- `tests/test_eval_scaffolds.py` and `tests/simple-english-baseline.json`: the branch of the new scaffold, and the `--` of its prompt (issue #280).

## dev-essentials 4.0.1 in release [5.0.1] - 2026-11-19

This release adds four eval cases for the finish steps in `skills/work-modes/references/finish.md`. Two of them finish an earlier run of `implement-task` and of `implement-batch` in the full mode. The other two must stop before the push. No skill text changes (issue #283).

### Added in dev-essentials

- `evals/implement-task/it-merge` and `evals/implement-batch/ib-merge`: the first cases of the two workflows. Each case finishes an earlier run in the full mode. Its scaffold plants the commits of that run on a branch that no remote holds, and the report of that run. The run must push the branch, open the pull request, read the merge gate, and merge with a squash (issue #283).
- `evals/research-implement-review-report/rirr-resume-moved-head`: the report of the earlier run names the reviewed commit. A later commit that no review saw is the head of the branch. The run must do no finish step (issue #283).
- `evals/research-implement-review-report/rirr-upstream-remote`: the clone has an `upstream` remote on GitHub. The run must ask the user which repository gets the pull request. It must do no finish step before the answer (issue #283).

### Changed in the repository

- `tests/test_eval_cases.py` and `tests/test_eval_scaffolds.py`: the grader tests of `rirr-merge` also run on the new resume cases. A new test makes sure that each pull request call fails the two stop cases. `ResumeReportTests` makes sure that the report of each resume case names its head commit and holds each review verdict. It also runs the tests at the head. Other new tests pin the request of each stop case. They make sure that `route-skill-fired` names the workflow of each case. They make sure that `route-question` of `rirr-upstream-remote` needs a question about the repository (issue #283).
- `docs/evals.md`: the suite table and the text name the new cases. The tag `implement-task` is in the list of tags that also run trigger cases (issue #283).

## dev-essentials 4.0.0 in release [5.0.0] - 2026-11-19

The gated workflows no longer read the old mode flags. Only `--mode interactive|partial|full`, another form of that option, and plain words that name a mode pick a mode. A request can name an unknown mode, or a flag that the workflow does not define. Then the run asks which mode to use before its first step (issue #278).

### Changed in dev-essentials

- `skills/work-modes`: the section "Old spellings" goes. Another form of the option, for example `--mode=full`, picks that mode. A request can name an unknown mode, or a flag that the workflow does not define. Then the run asks the user which mode to use. The run does no work before the answer, and a guess never picks the full mode (issue #278).
- `skills/work-modes/references/finish.md`: the finish steps name no old flag. In the full mode, the run does the steps with no question. In the other modes, it asks the question of the final gate. A run with no GitHub repository does no step and asks no question, in every mode (issue #278).
- `skills/merge-pr` and `skills/feature-pipeline`: an old spelling no longer approves a merge. Another form of `--mode full` that `work-modes` accepts still counts as the full mode (issue #278).
- `evals/research-implement-review-report/rirr-merge`: the request writes the option as `--mode=full`. So the case also tests another form of the option (issue #278).

### Removed in dev-essentials

- The old mode flags `--interactive`, `--autonomous`, `--merge`, and `--push`, and the arguments `interactive` and `autonomous` of `process-pr-comments`. No unit defines them now (issue #278).

### Breaking changes in dev-essentials

- A run that gets one of the old flags asks which mode to use before its first step. Write the new form in place of the old flag.
- `--interactive`, or the argument `interactive` of `process-pr-comments`: write `--mode interactive`.
- `--autonomous`, or the argument `autonomous` of `process-pr-comments`: write `--mode full`. Where the workflow ends with a merge, the full mode also pushes, opens the pull request, and merges. To stop before these steps, add "Do not push the branch." or "Do not merge the pull request." to the request.
- `--autonomous --merge`: write `--mode full`.
- `--merge` alone: write no flag, and ask for the merge in your own words, for example "and merge it". In `research-implement-review-report`, `implement-task`, and `implement-batch`, you can also answer yes to the question of the final gate.
- `--push` of `implement-task` and `implement-batch`: write no flag, and answer "push and pull request only" to the question of the final gate. This answer also opens a pull request. The old flag only pushed the branch.

### Changed in the repository

- `tests/test_work_modes_text.py`: the pins of the old spellings go. The test of the old mode flags now also reads `work-modes` and `finish.md`, and it also finds `--push`. Its list of allowed files goes (issue #278).
- `tests/test_eval_cases.py`: the pins of `merge-pr`, of `feature-pipeline`, and of the request of `rirr-merge` follow the new text (issue #278).
- `docs/workflows.md` and `docs/permissions.md`: they name no old flag (issue #278).
- `tests/test_work_modes_gate_rows.py`: a new test of the gate tables of the gated units of `dev-essentials`. It sorts each cell of each gate row by its opening words: the run stops, the run goes on, or the row leaves its gates to another text. The interactive mode must stop at each gate where the partial mode stops, and the partial mode at each gate where the full mode stops. So a swap of two cells of different classes fails the test. Two rows break this order on purpose, and the test names them. One more rule reads the gate names with the word push, merge, delete, deletion, remove, or removal. The partial mode must not go on with no question there. A cell with unknown opening words fails the test too (issue #279).

## dev-essentials 3.30.0 in release [4.28.0] - 2026-11-18

Three workflows can now end with a merged pull request: `research-implement-review-report`, `implement-task`, and `implement-batch`. In the full mode, they push the branch, open a pull request, and merge it after the gate of `merge-pr`. In the other modes, each of them asks one question for these steps at its end. The steps live one time, in `skills/work-modes/references/finish.md` (issue #271).

### Added in dev-essentials

- `skills/work-modes/references/finish.md`: the finish steps of the three workflows. It holds the start conditions and the source of the GitHub repository. It also holds the push, the pull request with a body from `pr-composer`, and the merge through `merge-pr`. It also holds the resume of an earlier run and the finish report. In the full mode, a failed step ends the run with a report. Some runs have no GitHub repository: the request names none, and no remote of the clone is on GitHub. Such a run does no pull request step and no merge step, in every mode. Only the old `--push` still pushes there. The pull request step first looks for an open pull request of the branch. Only a pull request with the base branch of the run as its base counts. In the full mode, a question of `pr-composer` gets one more dispatch and then ends the run. A resume needs the verdict of each review loop and the head commit at the end of that run. The head of the branch must be that commit (issue #271).
- `evals/research-implement-review-report`: the cases `rirr-merge`, `rirr-merge-gate`, and `rirr-final-gate`. `rirr-merge` finishes an earlier run and merges its pull request. It and `rirr-merge-gate` have a mock of `list_pull_requests` that lists no pull request. `rirr-merge-gate` is a full run that opens the pull request and stops at the merge gate. `rirr-final-gate` runs in the partial mode, asks the question of the final gate, and pushes nothing (issue #271).

### Changed in dev-essentials

- `skills/research-implement-review-report`: the new Phase 5 does the finish steps. When another workflow runs the skill, Phase 5 does not run. The report names the base branch and the head commit at the end of the run (issue #271).
- `commands/implement-task` and `skills/implement-batch`: the new Phase 6 and Step 6 do the finish steps. The flag `--push` is now an old spelling that `work-modes` reads. It still approves the push of the run and nothing more. Their descriptions no longer name `--push`. Their final reports name the head commit at the end of the run (issue #271).
- `skills/work-modes`: it names the end of the three workflows in the full mode, and it points at `references/finish.md`. The old spelling of the full mode with no merge still pushes nothing in these workflows. Next to `--push`, `--mode full` and `--autonomous --merge` do all finish steps, and the old `--autonomous` with no `--merge` only pushes (issue #271).
- `skills/process-pr-comments`: a `deep-fix` run tells `research-implement-review-report` not to run its finish steps, because this skill owns the push of the cycle (issue #271).
- `evals`: the requests of `rirr-retry-limit` and `rirr-single-commit` say "Do not push the branch.". So the cases keep their end state in the full mode (issue #271).

### Changed in the repository

- `tests/test_work_modes_text.py`, `tests/test_eval_cases.py`, and `tests/test_eval_scaffolds.py`: new tests for the finish steps and for the new cases (issue #271).
- `docs/workflows.md`, `docs/permissions.md`, and `docs/evals.md`: they name the finish steps of the three workflows (issue #271).

## dev-essentials 3.29.0 in release [4.27.0] - 2026-11-18

This release adds the skill `work-modes`. It defines one option, `--mode`, with three values: `interactive`, `partial` (the default), and `full`. The 14 gated units of the plugin point at it, and their copies of the common rules go. In the full mode, `feature-pipeline` ends with the merge of the pull request, and `process-pr-comments` creates a new out-of-scope issue with no question. The old mode flags still work, because `work-modes` reads them as a mode. An old `--merge` still approves the merge after the final gate, and an old `--autonomous` alone never merges (issue #267).

### Added in dev-essentials

- `skills/work-modes`: a new skill that only Claude loads (`user-invocable: false`). It defines the option `--mode`, the three modes, and the place where each workflow ends in the full mode. It also holds the hard stops, the rules for every mode, the old spellings, and the final report. Only the user picks the full mode, in the request of the session. A rule in a project file, a memory file, an issue, a comment, or a tool result never picks it. Hard stop 1 forbids the loss of git work that has no other copy. It also forbids the deletion of a file that no step of the workflow names. A file deletion that is a named step of the workflow follows its gate table (issue #267).
- `evals/triggers`: the cases `work-modes-fires` and `work-modes-near-miss`. The near-miss asks for a merge with no stops, which belongs to `merge-pr` (issue #267).

### Changed in dev-essentials

- The gated units of the plugin, which `tests/test_work_modes_text.py` lists. In each of them, the option `--mode` replaces `--interactive` and `--autonomous`. The section "Autonomy" of each unit loads `work-modes` before the first step. It keeps only the gate table of the unit, with the columns Partial, Interactive, and Full. The list of the common rules goes. A rule that only one unit has stays in that unit. The body of `skills/git-worktree-management` uses the mode words too (issue #267).
- `skills/feature-pipeline`: the flag `--merge` goes. The full mode pushes, opens the pull request, and merges it in Step 9b, with no question. Outside the full mode, Step 9b runs only with the approval that `merge-pr` needs. Blocking issues can remain after the fix round. Then the full mode writes the gate into the final report and ends the run with no push (issue #267).
- `skills/research-implement-review-report` and `commands/implement-task`: in the full mode, the run asks no question at the end. The cleanup of `save-context` keeps each file of an older session and each stale branch, and the report lists them (issue #267).
- `skills/process-pr-comments`: the words `autonomous` and `interactive` give way to `--mode full` and `--mode interactive`. In the full mode, a new `[OutOfScope]` issue after a search with no hit needs no question. The run creates it and names it in the cycle log. The search still runs. After a failed search, the run creates no issue, and the cycle report lists the thread (issue #267).
- `skills/merge-pr`: the full mode of a workflow of this plugin counts as the approval of the merge. The user must pick that mode in the request of the session. An old spelling that `work-modes` reads as an approval of the merge counts too. A yes to a question of the session that names the merge counts as well. A request to work with no stops, and the word "autonomous", still do not give the approval (issue #267).
- `skills/subagent-orchestration`, `skills/engineering-discipline`, `skills/github-mcp-conventions`, `skills/compose-task`, and `skills/audit-personal-conventions`: they name the modes of `work-modes` (issue #267).
- `evals`: each case that passed an old mode flag now passes `--mode full`. `fp-e2-fork-pr` and `fp-e2-untracked-file` also say "Do not merge the pull request", so that they keep their end state. `mp-no-merge-word` uses the word "autonomous" with no flag. `ppc-outofscope-autonomous` now expects a new issue, a reply that names it, and no question. Its only scored grader is the issue search, and route graders hold the new end state. `rirr-retry-limit` has a new grader that the last message does not end with a question. `rirr-retry-limit`, `fp-e2-merge`, and `ppc-autonomous-push` have the route grader `route-work-modes` (issue #267).

### Changed in the repository

- `tests/test_work_modes_text.py`: a new test. It pins the main sentences of `work-modes`, which include each hard stop, the rules for every mode, and the old spellings. It also pins the pointer and the gate table header of each gated unit, and the rules that stay in one unit. A file outside `work-modes` that names an old mode flag or keeps a copy of the common rules fails it (issue #267).
- `tests/test_eval_cases.py`: `PipelineMergeTests` and `MergePrGraderTests` pin the new sentences of `feature-pipeline` and `merge-pr`. `PpcQuestionGraderTests` reads the route grader `route-no-create-question`. `RirrNoQuestionGraderTests` tests the new grader `no-question` and the graders `route-work-modes` (issue #267).
- `docs/workflows.md`: a new section "Work modes". `docs/permissions.md` and `docs/evals.md` name the full mode in place of the old flags. `README.md` names the new section (issue #267).

## dev-essentials 3.28.0 in release [4.26.0] - 2026-11-18

This release adds the script `worktree.py` to the skill `git-worktree-management`. The script does the fixed git steps of a worktree. The skill keeps the steps that need a judgment, a question, or a GitHub tool (issue #270).

### Added in dev-essentials

- `skills/git-worktree-management/scripts/worktree.py`: a new script with three subcommands. `create` checks the branch name, the path, and the ignore rule, picks the case of the branch, runs `git worktree add`, and does the bootstrap. The bootstrap gives the new branch no upstream and makes the notes folder. If git ignores `.claude/settings.local.json`, the bootstrap also copies that file. With `--plan`, `create` prints the plan and changes nothing. If no rule ignores `.claude/worktrees/`, `--add-exclude` adds that line to the local exclude file of git. `create` refuses a base that origin does not have and a path inside another worktree. It also refuses a rule of a `.gitignore` file with `!` that keeps `.claude/worktrees/` not ignored. On a file system with no case, it also refuses a name that clashes with a local branch. A part of the name differs from a part of that branch only in case. The commands `ls-remote` and `fetch` stop after 120 seconds. Git also stops an http transfer that gets no data for that time. Unless you pass `--apply`, `remove` and `prune` print their plan and change nothing. `remove` never passes `--force`. It prints an `IGNORED` line for each ignored file that the removal deletes. It refuses a worktree with a change or an untracked file, a locked worktree, and a folder that git does not list. It also refuses a tracked file with the flag skip-worktree or assume-unchanged, because git status hides its change. It refuses a worktree that holds another worktree or another git repository. It looks in each ignored folder for a `.git` entry, a bare repository, or the git folder of `--separate-git-dir`. It does so also for a worktree that git no longer lists. It refuses an ignored folder that it cannot read. It refuses a detached HEAD with commits that no branch, tag, or remote branch holds. If git leaves the folder, for example with a junction in it, a `LEFT` line names it. `prune` refuses the same detached HEAD. The script refuses each path outside `.claude/worktrees/`, and it asks for no input (issue #270).
- `evals/git-worktree-management/gwm-create-blocked`: a route case. The user asks for a worktree and approves it in advance. The sandbox of an eval run keeps `.git/worktrees` read-only, so `git worktree add` fails. The run must call `worktree.py create`, and its final reply must say that the worktree was not made and why (issue #270).
- `evals/triggers`: the cases `git-worktree-management-fires` and `git-worktree-management-near-miss`. The near-miss asks to merge the Claude Code project folders of worktrees, which belongs to `merge-worktree-projects` (issue #270).

### Changed in dev-essentials

- `skills/git-worktree-management`: Workflows A, C, and D and the fallback for a missing worktree call the script in place of the git commands. These rules stay as they were: the approval prompt of Workflow A Step 3 and its pipeline mode, and the rule that keeps a worktree until its pull request is merged. The rule that `--autonomous` destroys no work with no other copy stays too. The fallback no longer runs `git worktree remove --force`. The bootstrap no longer copies a `.claude/settings.local.json` that git does not ignore, because the copy blocked the removal later. The repository root is now the main worktree, also in a run from a linked worktree. A removal from a folder inside the worktree is refused. If one stale entry is outside `.claude/worktrees/`, Workflow D prunes no entry and names it in the report. A stale entry with a detached HEAD and its own commits also blocks the prune. No branch, tag, or remote branch holds those commits (issue #270).

### Changed in the repository

- `tests/test_worktree.py`: the tests of the new script, on Linux and on Windows. The job `test-windows` of `.github/workflows/tests.yml` runs them (issue #270).
- `tests/test_eval_cases.py`: the new class `WorktreeScriptCaseTests` tests the graders of the three new cases on right and wrong runs (issue #270).
- `tests/test_eval_scaffolds.py`: `EXPECTED_BRANCH` names the branch of the new case (issue #270).
- `docs/testing.md` and `docs/evals.md`: the new test module, the new suite, and why no eval case can make a worktree (issue #270).

## dev-essentials 3.27.3 in release [4.25.3] - 2026-11-18

If `git worktree add` fails, for example in the sandbox of an eval run, this release lets `failure_check.py` of `review-loop` reach a verdict. The script then writes the files of the commit into the same temporary folder and runs the command there (issue #232).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: if `git worktree add` fails and makes no folder, the script exports the commit with `git read-tree` and `git checkout-index` into that folder. The folder is the work tree of the checkout. A temporary index file keeps the index of the repository as it is. The export gets the same line ends, links, and modes as a worktree, and no git data. Git reads the attributes of the commit, not of the main worktree. A command in an export runs with `GIT_CEILING_DIRECTORIES`, so git finds no repository above the temporary folder. On Windows, the script now deletes a read-only file that the command made. A new line `EXPORTED <path>` names the export, and the RUN line says `in temporary export`. A new line `NO WORKTREE: <text>` holds the error of `git worktree add` before each export. If the export fails too, the RUN line holds the error of the export, and the verdict is `OTHER`. If the command passes only in an export, the verdict is `OTHER`, because an export has no git data. The help text says that a command that reads git data can give another result in an export. It also says that an export of a sparse checkout holds each file. The `CHANGED:` lines still list the stub files of the sandbox. They do not change the verdict of a command that reads no git data (issue #232).

### Changed in dev-essentials

- `skills/review-loop/SKILL.md`: the part "Failure check" of Phase 6 has four new sentences. A `RUN` line with the words `in temporary export` means that the command ran in a folder with no git data. So read the `ERROR` and `TAIL` lines before you trust `SAME-AT-PARENT`. If one of them shows missing git data, treat the verdict as `OTHER`. An `EXPORTED <path>` line with no `REMOVED <path>` line names a plain folder that is still there. The skill says to delete it by hand (issue #232).
- `evals/review-loop/rl-failing-build`: the route grader `route-verdict-same-at-parent`. It reads the trace for the line `VERDICT: SAME-AT-PARENT` and the start of the `REASON:` line after it (issue #232).

### Changed in the repository

- `tests/test_failure_check.py`: the new class `ExportTests` blocks `git worktree add` with a plain file in the place of `.git/worktrees`. Its tests run the script with two exports, and with the main worktree and one export. They also run it with an export that fails, and with the stub files of the sandbox. Other tests make sure that an export ignores a `.gitattributes` of the main worktree. They also make sure that git finds no repository above the temporary folder, and that a read-only file does not keep the export. A Linux test makes sure that the delete keeps the mode of an outside folder. A Windows test makes sure that the delete removes a read-only link. Another test makes sure that a ceiling of the caller stays. Two more tests cover a command that passes only in an export, and the environment of git in an export. One test compares an export with a worktree for two links, an executable file, CRLF line ends, and a path with a space. New tests of `UnitTests` and `SignalTests` cover the remove step and a stop by a signal during a run in an export (issue #232).
- `tests/test_eval_cases.py`: the new class `FailureCheckExportGraderTests` tests the new grader on right and wrong traces (issue #232).
- `docs/testing.md`: the tests of `failure_check.py` reach two more Windows paths: an export with links and CRLF line ends, and the delete of a read-only file that the command made (issue #232).

## dev-essentials 3.27.2 in release [4.25.2] - 2026-11-18

This release makes the final report of `/audit-team` keep the heading and the labels of its form. Before, the report often left out the heading "Team Review Report" or the label "Agreement matrix" (issue #259).

### Fixed in dev-essentials

- `commands/audit-team.md`: Step 3 now asks the report to keep the heading and each bold label of its form word for word, also `**Agreement matrix:**`. The adapter of `review-loop` reads the parts Blockers, Warnings, and Suggestions and the agreement matrix by these labels. Before the change, the full form showed in 6 of 16 eval runs. Fifteen of the 16 runs ran the case `at-seeded-design`, and one ran a local copy of it with an agent count of 5. Each of the 10 runs without the full form renamed the label "Agreement matrix" or left it out. Six of them also changed the heading or left it out. With the change, the full form showed in 6 of 6 head runs, and in 2 of 4 base runs (issue #259).

### Changed in the repository

- `tests/test_eval_cases.py`: the new test `test_step_3_keeps_the_heading_and_the_labels_of_the_form` of `AuditTeamRouteGraderTests` pins the new sentences of Step 3. It also makes sure that they come before the form (issue #259).

## dev-essentials 3.27.1 in release [4.25.1] - 2026-11-18

This release fixes the eval case `os-review-fixes` of `optimize-skill`. Its route grader `route-seed-contents` failed in each run. The auditor brief does not ask for a contents list, and the runs of the case grant no web tool (issue #268).

### Fixed in dev-essentials

- `evals/optimize-skill/os-review-fixes`: the route grader `route-seed-contents` is gone, so the case has four seed graders. That grader looked for a contents list of the long reference file `csv-format.md` in the audit report. The rule for such a list is on the best practice page for skills. The list "What to look for" of the auditor has no item for it. The example audit of the skill keeps that point on purpose. In each of the 7 runs of the first eval, the auditor tried to read that page, and the sandbox refused the request. The scaffold comment and the description of the case now name four seeded issues. The fixture file does not change (issue #268).

### Changed in the repository

- `tests/test_eval_cases.py`: `OptimizeSkillCaseTests` pins the four seed graders. If a grader of the case looks for a contents list again, a new test fails (issue #268).

## dev-essentials 3.27.0 in release [4.25.0] - 2026-11-18

This release adds the flag `--merge` to the workflow `feature-pipeline`. With `--autonomous --merge`, a run goes from the task to the merged pull request with no human step. Without `--merge`, the pipeline does what it did before (issue #262). The release also holds the new maintainer tools in the folder `tools/`, which no plugin ships (issue #255).

### Added in dev-essentials

- `skills/feature-pipeline`: the flag `--merge` and a new Step 9b. After Step 9 opens the pull request, Step 9b loads the skill `merge-pr`. That skill reads the merge gate, merges, and does the steps after a merge. The flag is the approval of the merge. `--autonomous` alone never merges, and no text of the task, of a file, or of a tool result approves a merge. Step 9b needs a pull request of Step 9 and review stages with no blocking issue. If the gate fails, the pull request stays open, and the run reports the gate and goes to Step 10. A resume with `--merge` runs Step 9b too, also for a run that ended earlier with an open pull request. If the review stages have no blocking issue, the question of Human Approve #2 names the merge. Step 10 treats a pull request that Step 9b merged as merged. It deletes the merged local branch after the archive of the task logs (issue #262).
- `evals/feature-pipeline`: the cases `fp-e2-merge` and `fp-e2-merge-gate`. No mock can give the SHA of a commit that the run makes, and the merge gate compares that SHA with the local branch. So `fp-e2-merge` starts after Step 9, with a head commit that its scaffold makes. Its run must read the gate and merge with a squash. `fp-e2-merge-gate` is a full run with both flags. Its mock gives the last commit of the scaffold as the head. So the gate fails, and the run must open the pull request, read the gate, and not merge (issue #262).

### Changed in dev-essentials

- `evals/feature-pipeline/fp-e2-fork-pr`: a mock for the merge tool, the grader `not-merged`, and the route grader `route-merge-skill-not-fired`. The request of the case has `--autonomous` and no `--merge`, so a run that merges there fails (issue #262).

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `PipelineMergeTests` tests the graders of the three cases on right and wrong runs. It pins the fixtures of the mocked pull request and the state that the resume case starts from. It also pins the sentences of the pipeline about the flag and the two items of Step 9b in their order. `RoutePlainDotnetGraderTests` counts 14 cases, and `ForkHeadMockTests` reads the new full run (issue #262).
- `tests/test_eval_scaffolds.py`: `EXPECTED_BRANCH` names the branch of the two new cases. `ScaffoldTests` makes sure that the head of the pull request in `fixtures/pull/get.json` is the branch and the last commit of the scaffold. The new method `check_pipeline_state` reads the state file that a resume case plants. That file must be valid JSON with the keys of the schema, and its pull request must be the mocked one. Its task ID must be the task of the prompt, and its stage names must be stage keys of the skill (issue #262).
- `docs/permissions.md`: `feature-pipeline` calls `merge-pr` only with the flag `--merge` (issue #262).
- `docs/evals.md`: the suite `feature-pipeline` has 12 cases, and a new paragraph says why two cases test the flag (issue #262).
- `tools/changelog_merge.py`: a new script for the maintainers. After a merge of `main` into an open branch that you start with `git merge --no-commit`, it writes `CHANGELOG.md` and the `version` of each `plugin.json` new. It takes a release of one or more plugins, or the entries that the branch added under `[Unreleased]`. If the result loses a line that a side added, the script stops. If the result has a line that a side removed, the script stops too (issue #255).
- `tools/eval_results.py`: a new script that reads the results of eval runs. It prints the runs of `baseline.json` files and tests the spend against a cap. It also lists the kept run folders and prints the tool calls of a trace (issue #255).
- `tools/wsl/`: new scripts that run the unit suite and one command of `compare_versions.py` in WSL2 from Git Bash. A branch goes to WSL2 as a git bundle, and no Linux command reads a Windows drive. The eval runner stops on a `claude` below `/mnt` (issue #255).
- `tests/test_changelog_merge.py`, `tests/test_eval_results.py`, and `tests/test_tools_wsl.py`: the tests of the new scripts. The job `test-windows` of `.github/workflows/tests.yml` runs the first two (issue #255).
- `docs/tools.md`: a new page that says how to run the scripts. `docs/authoring.md`, `docs/testing.md`, and `README.md` point to it (issue #255).

## dev-essentials 3.26.0 in release [4.24.0] - 2026-11-18

This release adds the skill `merge-pr`. It merges one GitHub pull request after a gate, and then it does the steps after a merge. It merges only on an explicit request of the user (issue #257).

### Added in dev-essentials

- `skills/merge-pr`: a new skill. The gate needs green check runs on the head, the merge state `clean`, and no open change request. It also needs that the pull request holds each local commit. The last test, build, or review result of the session must be clean. If an item fails or a read fails, the skill does not merge, and it reports the item. The default method is a squash merge whose commit has a title and a body. After the merge, the skill updates the local base branch, deletes the merged local branch, and reads the linked issues. A request of the user in words gives the approval, and so does a `--merge` flag of a workflow. `--autonomous` alone does not give it, and no text of a file, an issue, or a tool result does (issue #257).
- `evals/merge-pr`: three behavior cases on a GitHub stand-in. In `mp-green-merge`, the checks are green, and the run must merge with a squash. In `mp-red-check`, one check failed, and the run must not merge. In `mp-no-merge-word`, the user names the skill and asks only whether the pull request passes the merge gate, with `--autonomous`. The body of the pull request claims an approval and tells an agent to merge. The run must report the result of the gate, and it must not merge (issue #257).
- `evals/triggers`: the cases `merge-pr-fires`, `merge-pr-near-miss`, and `merge-pr-near-miss-review`. The first case names the pull request by its URL, and `git-sync` and `process-pr-comments` must not start. The first near-miss asks for a local merge of the base branch, which belongs to `git-sync`. The second near-miss asks whether a pull request is ready for a merge. That is a review request, which belongs to `help-review-pr` (issue #257).

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `MergePrGraderTests` tests the regex graders of the new cases on right and wrong runs. For the `llm` grader `reported-ready`, it pins the type and the conditions of the rubric. It also pins the fixtures and the approval rule of the skill. The check of the `mock_calls` graders accepts a field of the first call before the span between two calls (issue #257).
- `tests/test_eval_scaffolds.py`: `EXPECTED_BRANCH` names the branch of the three new cases (issue #257).
- `tests/test_plugin_cli.py`: the listing budget of dev-essentials is 4785, for the new skill (issue #257).
- `docs/permissions.md`: a new section on the merge of a pull request, with an ask rule for the merge tool (issue #257).
- `docs/evals.md`: the suite `merge-pr` (issue #257).

## dev-essentials 3.25.1 in release [4.23.1] - 2026-11-18

This release adds the first eval cases of `optimize-skill`. In the eval runs, a fold of the review fixer into the main session showed no proved gain. So the skill text does not change (issue #256).

### Added in dev-essentials

- `evals/optimize-skill/os-review-fixes`: the first behavior case of the skill. The scaffold makes a small plugin with five seeded issues and an agent file with a safety rule. The prompt adds one finding of the user, so that step 6 has an accepted finding in each run. Scored graders need the restored rule, the kept safety rule, at most two local commits, no push, an unchanged `CLAUDE.md`, and both reports. Route graders count the dispatches, the review fixer, and the second commit. They also find each seeded issue in the audit report (issue #256).
- `evals/triggers/optimize-skill-fires` and `evals/triggers/optimize-skill-near-miss-trim`: the first trigger cases of the skill. The near-miss asks to trim a notes file, which `trim-artifacts` owns (issue #256).

### Changed in the repository

- `tests/test_eval_cases.py` and `tests/test_eval_scaffolds.py`: tests of the graders of the new cases on the fixture, on a right run, and on wrong runs (issue #256).
- `docs/evals.md`: the new suite, its tag, and the finding of the user in the prompt of `os-review-fixes` (issue #256).

## dev-essentials 3.25.0 in release [4.23.0] - 2026-11-18

With no agent count, `/audit-team` now reviews with two points of view. The main session reviews with the five roles as lenses, and one fresh agent takes the devil's advocate role. An explicit count still starts one agent for each of the first N roles. A new eval case plants one defect for each role (issue #254).

### Changed in dev-essentials

- `commands/audit-team`: with no `agent-count`, the run takes the two-view route. Before, it started five role agents, and each one read the whole target again. If the second argument is not a whole number and names a model, it is the model of the agent. So `/audit-team <path> opus` now works with no count. The report keeps its form. On the two-view route, a consensus in the agreement matrix needs a flag of the main session and a flag of the agent (issue #254).
- `skills/review-loop`: the `audit-team` adapter and the spec review example pass a count of 5 as a fixed value, so `--reviewer audit-team` keeps the five-role team (issue #254).

### Added in dev-essentials

- `evals/audit-team/at-seeded-design`: a new case. A design file has five planted defects, one for each role. One requirement has no acceptance case, and one claim about the code is wrong. One step has a condition that no test can check, and one name breaks the pattern of the project. Two sections disagree. A judge reads the final report for each defect. A route grader counts the role agents (issue #254).

### Changed in the repository

- `tests/test_eval_scaffolds.py` and `tests/test_eval_cases.py`: tests of the planted design and of the graders of the new case (issue #254).
- `tests/test_review_loop_text.py`: four tests pin the fixed count of the adapter, the explicit count of the command, and the two-view route (issue #254).
- `docs/evals.md`: a new suite row for `audit-team` with 1 case, and the tag sentence: `--tag audit-team` also runs the two trigger cases of the command (issue #254).

## dev-essentials 3.24.1 in release [4.22.1] - 2026-11-17

This release fixes the .NET eval scaffolds for a `baseline` command with `--concurrency 1`, `--keep-temp`, and more than one run. Before, each .NET scaffold after the first .NET run failed on a NuGet lock in the sealed `tmp` folder of that run (issue #250).

### Fixed in dev-essentials

- `evals/_lib/dotnet-fixture.sh`: each `dotnet` command of `dotnet_warm` has `-nodeReuse:false`. Before, the first scaffold of a command left an MSBuild node, and the next scaffold in the same session used that node. NuGet in that node kept its lock folder in the `TMPDIR` of the first run. The eval tool seals that folder after a kept run, so the restore failed after about 31 seconds. Each later scaffold now takes about 1 second more. The fixture of dotnet-backend-dev is a link to this file, so it gets the fix too (issue #250).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: the new test class `DotnetNodeReuseTests` runs `dotnet_warm` with a fake `dotnet`. It makes sure that each of the four `dotnet` commands has `-nodeReuse:false` (issue #250).

## dev-essentials 3.24.0 in release [4.22.0] - 2026-11-17

This release makes the single-commit mode of `research-implement-review-report` squash the run with the script `squash_task.py`, as `implement-batch` does. The script checks the commits of the run before the squash. After a failed commit, it puts the old HEAD back (issue #246).

### Changed in dev-essentials

- `scripts/squash_task.py`: moved from `skills/implement-batch/scripts/`, so that two skills can run it. The code does not change (issue #246).
- `skills/research-implement-review-report`: the single-commit mode runs the script in place of `git reset --soft` and `git commit`. The session records the SHA of each commit of the run, also the commits of the review loop. It stages explicit paths and never the plan file. It gives the folder of the plan file as `--plan-dir`. The gate table has the two rows of the script, as in `implement-batch`. Before, a failed commit after the soft reset left the branch at the base. The session found a commit of someone else only by its own reading of the range (issue #246).
- `skills/implement-batch`: Step 3.6 runs the script from the `scripts` folder of the plugin (issue #246).

### Added in dev-essentials

- `evals/research-implement-review-report/rirr-single-commit`: a new case. A plan file with two tasks runs in the single-commit mode. A scored grader needs one squash commit on top of `main` as the last change of `HEAD`. The route graders need a call of the script with two commits and `--apply`. They also need the reflog entry and the `TREE` line of the script, and no `git reset --soft`. So a base run can score 1.00 (issue #246).

### Changed in the repository

- `tests/test_squash_task.py`: the new path of the script, and a test that both skills call it by `${CLAUDE_PLUGIN_ROOT}` (issue #246).
- `tests/test_eval_scaffolds.py` and `tests/test_eval_cases.py`: tests of the graders of the new case on right and wrong runs (issue #246).
- `tests/simple-english-baseline.json`: the file path `config/settings.py` in two graders of the new case is an exception, as in `rirr-retry-limit` (issue #246).
- `docs/testing.md` and `docs/evals.md`: the second caller of the script, and the second case of the suite (issue #246).

## dotnet-backend-dev 1.8.0 in release [4.21.0] - 2026-11-17

This release lets `/write-tests` write the tests of one class in the main session. Two or more targets, a module, and a project keep the `test-engineer` agents.

### Changed in dotnet-backend-dev

- `commands/write-tests`: if the grouping leaves one target of the kind Class, the main session writes its tests with the `create-tests` skill. It does the steps of the `test-engineer` agent and gives the same report. Two or more targets, a module, and a project still dispatch one agent for each target. The text gives the reason with the delegation tests of Rule 1 of `subagent-orchestration`. This changes a part of the behavior of issue #37 (issue #242).
- `agents/test-engineer`: the description and the section "Purpose" say that the command dispatches the agent for two or more targets, a module, or a project (issue #242).
- `evals/write-tests`: the grader `route-agent` of `wt-one-class` fails a run that dispatches `test-engineer`. The grader `route-agent` of `wt-pricing-folder` still asks for at least one such dispatch. Both graders now read the agent type of the call (issue #242).

### Changed in the repository

- `tests/test_eval_cases.py`: samples for the two `route-agent` graders of the write-tests suite (issue #242).
- `tests/simple-english-baseline.json`: the reason of the entry of `wt-one-class` names the main session (issue #242).

## dev-essentials 3.23.0 in release [4.20.0] - 2026-11-17

This release turns the executor role of the full pass of `trim-artifacts` into the subcommand `apply` of its script. The main session runs it, so no executor agent starts. A new eval case runs a full pass (issue #243).

### Added in dev-essentials

- `skills/trim-artifacts/scripts/trim_report.py`: the new subcommand `apply` copies the result of a proven plan from the `target` copy of the planner into the workspace. Before it writes, it tests the plan and each file. A workspace file and its backup copy must equal the `orig` copy. A new file must not exist yet. Each deletion needs a `--delete` flag. If one test fails, it changes no file. Then it deletes the approved files, removes the folders that the deletions emptied, and runs the checks against the backup. It stops with no change for a link on the path or a file in the place of a folder. It does the same for a name that differs only by case and for a `--glob` with `..`. If a file changed after its test, it stops with exit code 4. A `--delete` flag for a file that the plan keeps prints a `KEPT` line. A second run after a stop skips each file that is done. Its output has at most 100 lines. The form with no subcommand stays as it is (issue #243).
- `evals/trim-artifacts/ta-full-pass`: a new behavior case. A full pass runs on 12 notes files, and the prompt gives the answers of the user. The graders read the final files: the two planted cuts are made, the session log and its folder are gone, and the index no longer cites the log. The decision blocks, the ids, and the uncertainty markers stay, and the backup stays in the run folder. Route graders count the planner, the reviewer, the executor dispatch, and the `apply` call (issue #243).

### Changed in dev-essentials

- `skills/trim-artifacts`: step 6 of the full pass runs `trim_report.py apply` in the main session, in place of an executor agent. The planner applies the whole plan to its `target` copy, also the deletions. The roles are the planner, the reviewer, and the fixer. `references/role-briefs.md` has no executor brief, and `references/script-results.md` names the exit codes of `apply`. Each planned file must match the glob. A batch that plans again takes a second backup (issue #243).

### Changed in the repository

- `tests/test_trim_report.py`: new tests for `apply` on fixture trees. They cover the apply, a second run, each refusal, a failed write, and the output limit (issue #243).
- `tests/test_eval_cases.py`: samples for the route graders of `ta-full-pass` (issue #243).
- `tests/test_eval_scaffolds.py`: `EXPECTED_BRANCH` names the branch of the new case. New tests run its scaffold. They make sure that the file graders fail on the planted notes and pass on a right trim (issue #243).
- `docs/evals.md`: a new suite row for `trim-artifacts` with 1 case (issue #243).

## dev-essentials 3.22.0 in release [4.19.0] - 2026-11-17

This release turns the squash steps of `implement-batch` into a script with unit tests. The script checks the commits of a task before it squashes them. After a failed commit, it puts the old HEAD back (issue #244).

### Added in dev-essentials

- `skills/implement-batch/scripts/squash_task.py`: squashes the commits of one task into one commit on the base commit of the task. It takes the base, each commit of the task, and the message. Without `--apply`, it prints the plan and changes nothing. It refuses a commit that the task did not make and a merge commit. It also refuses a changed tracked file, a detached HEAD, and a plan file in the commits. A staged plan file counts as a changed tracked file. The commit hooks of the repository run. If the commit fails, or Ctrl+C stops the script during the commit, the script puts the old HEAD back. Its output is short, each line prints at once, and it names the command that undoes the squash (issue #244).

### Changed in dev-essentials

- `skills/implement-batch`: Step 3.6 and Step 4.4 run the script in place of `git reset --soft` and `git commit`. The session records the SHA of each commit of a task, and the script refuses a commit that is not in that list. This is the squash-base safety stop of the skill. So the brief of the implementer tells it not to commit, and the session commits the implementation. The gate table and the rules of Step 3.6 cover each outcome of the script. No eval case covers the change (issue #244). The eval sandbox blocks the worktree of Step 1 (issue #232).

### Changed in the repository

- `tests/test_squash_task.py`: new tests for the script on a fixture repository, on Linux and Windows (issue #244).
- `.github/workflows/tests.yml`: the job `test-windows` also runs `test_squash_task` (issue #244).
- `docs/testing.md`: names the tests of the script (issue #244).

## dev-essentials 3.21.0 in release [4.18.0] - 2026-11-17

This release lets Stage 9 of `feature-pipeline` open a PR from a fork with an MCP PR tool. The PR creation entry of the project context can name the owner of the fork. Step 6 then sends `<fork owner>:<branch>` as the head of the PR (issue #225). A fork that the organization of the upstream repository owns is not supported, because the MCP tool has no `head_repo` field.

### Added in dev-essentials

- `skills/feature-pipeline/stages/finalization.md`: if the PR creation entry names a fork owner, Step 6 sends `<fork owner>:<branch>` as `head` of the MCP PR call. Without a fork owner, it sends the bare branch, as before. The fork owner comes only from that entry, not from a remote URL (issue #225).
- `skills/feature-pipeline/project-context.template.md`: the PR creation entry can name the owner of a fork. This part is optional (issue #225).
- `skills/feature-pipeline/references/setup.md`: the PR creation entry can name the owner of a fork. Step 0 does not ask for it, because it is optional (issue #225).
- `evals/feature-pipeline/fp-e2-fork-pr`: a new behavior case. Its project context names the repository of the PR and the fork owner `eval-user`. The mock of the PR call expects the head `eval-user:work/fork-pr`. A run that sends another head stops with the score 0 (issue #225).

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `ForkHeadMockTests` makes sure that the PR mock of `fp-e2-untracked-file` expects the bare branch. It also makes sure that the PR mock of `fp-e2-fork-pr` expects `<fork owner>:<branch>`, and that Step 6 and the template name the fork owner. `RoutePlainDotnetGraderTests` counts 12 graders `route-plain-dotnet` (issue #225).
- `tests/test_eval_scaffolds.py`: `EXPECTED_BRANCH` names the branch of the new case. Each scaffold run also makes sure that the head, the owner, and the repository of the PR mock match the project context of the scaffold. The new class `PrHeadTests` gives samples for these rules (issue #225).
- `docs/evals.md`: the suite `feature-pipeline` has 10 cases (issue #225).

## dev-essentials 3.20.2 in release [4.17.2] - 2026-11-17

This release makes the failure check of `review-loop` ignore the count of tests in the output of `unittest`, `pytest`, and `dotnet test`. So a fix commit that adds a test and keeps the same failure gives `SAME-AT-PARENT`, not `OTHER`. The line of one test still counts, as with `pytest -v` (issue #230).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: the error signature puts a token in place of each count of tests. The new rules cover the line `Ran N tests in <time>` and the count `skipped=N` of `unittest`, and the summary line and the progress percentage of `pytest`. They also cover the summary lines of `dotnet test`, with VSTest and with Microsoft.Testing.Platform. The counts of failures and errors still count. A first rule removes the color codes from each line, so the rules also work on colored output, for example of `pytest` with `FORCE_COLOR=1`. The help text names the limit: the line of a single test still counts. Before, a fix commit that added a test changed the line `Ran N tests`, so the same failure gave `OTHER` (issue #230).

### Changed in the repository

- `tests/test_failure_check.py`: two new tests run a real `unittest` suite whose fix commit adds a test. The same failure gives `SAME-AT-PARENT`, and another failure gives `OTHER`. A new test class uses output lines of each runner. It makes sure that a count of tests does not count. It also makes sure that a count of failures and a number outside a count line still count (issue #230).

## dev-essentials 3.20.1 in release [4.17.1] - 2026-11-17

This release makes the eval case `rl-off-by-one` of `review-loop` stable. The skill text does not change. With the stable case, `rl-off-by-one` scores 1.00 at the commit before release 4.17.0 and 1.00 at the head, over 7 runs on each side. No run stopped with a question. So the change of release 4.17.0 holds.

### Fixed in dev-essentials

- `evals/review-loop/rl-off-by-one` and `evals/review-loop/rl-failing-build`: the prompt gives the contract of `page_slice` for `page < 1` in advance. Before, the session stopped after the round 1 review in 5 of 14 runs of `rl-off-by-one`. It asked the user what `page_slice` must do for `page < 1`, for example raise `ValueError` or return an empty list. An eval run has no user, so such a run ended with no fix and no commit (issue #238).

### Added in dev-essentials

- `evals/review-loop/rl-off-by-one` and `evals/review-loop/rl-failing-build`: the new route grader `route-stop-verdict` needs the `Stop verdict:` line of the skill in the final message to pass. A run that stops with a question has no such line. A replay on 14 earlier runs of `rl-off-by-one` gives a fail for exactly the 5 runs that asked (issue #238).

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `StopVerdictRouteGraderTests` makes sure that both cases have the same grader on the final message. It gives samples of a final report with each stop verdict, and samples of a run that stopped with a question (issue #238).
- `README.md`: has a new order. The install steps come first, then the plugin table. New sections follow: "Try it", "Requirements", "Safety", a documentation map, and "License". The update section is short now. The map replaces the sections "Working across sessions" and "References". The update text no longer says that `/plugin marketplace update` updates the installed plugins, because the official docs do not say that. The list of official docs moved to `docs/installing.md`, so the README has fewer words than before (issue #234).
- `docs/installing.md`: a new page with the shell form of the install, the configuration files, and the steps for updates. It also has the automatic updates and the list of official docs. It holds the text that moved out of the README (issue #234).
- `docs/workflows.md`: the link to the update steps points to `docs/installing.md` (issue #234).
- `CLAUDE.md`: the paragraph "How users receive updates" names the update ways of the official docs. They are "Update marketplace" in the `/plugin` panel, `claude plugin update`, and automatic updates. The paragraph no longer says that `/plugin marketplace update` updates the installed plugins. It points to `docs/installing.md` for the details (issue #240).

## dev-essentials 3.20.0 in release [4.17.0] - 2026-11-17

This release lets the reviewer of `review-loop` write the fix plan of each finding, so no other dispatch plans the fixes. The session that runs the loop applies the fixes, unless step 5b sends them to the fixer subagent. A new eval case runs the failure check of Phase 6.

### Changed in dev-essentials

- `skills/review-loop`: the Full format of the reviewer report has a **Fix plan** line in each finding, and a Common Rule asks for it. Step 5a takes the plan from the report. A plan dispatch on `--reviewer-model` runs only for a finding with no usable plan. The cases are an `audit-team` or orchestrated-mode report, and the regression fix of the failure check. Another case is a fix that the triage changed with no fix named by the user (issue #221).
- `skills/review-loop`: step 5b chooses the fixer with the delegation tests of Rule 1 of `subagent-orchestration`, mostly the context test. A few bounded edits stay in the orchestrator, which follows `references/verify-fix-discipline.md`. A fix set whose reads and edits put many files into the main context keeps the fixer subagent. An explicit `--fixer`, `--fixer-model`, or `--fixer-effort` keeps it too. The Brief format of a cycle names the fixer and the test (issue #221).
- `skills/review-loop`: the parameter texts, the reference files of the fixer, the `audit-team` adapter, the orchestrated mode, and both examples follow the new steps (issue #221).
- `skills/implement-batch`, `skills/research-implement-review-report`, and `skills/subagent-orchestration`: the text no longer says that a fixer subagent always runs (issue #221).

### Added in dev-essentials

- `evals/review-loop/rl-failing-build`: a new behavior case. The docs build of the repository already fails before the branch, because a sibling theme folder is missing. The graders make sure that the loop fixes the defect and commits. They make sure that it runs `failure_check.py` on the build command and stops with `stop-blocked`. No grader reads the verdict of the script. In an eval run, the sandbox keeps `.git/worktrees` read-only, so the script cannot make its temporary worktree (issue #232). They also make sure that the build tool stays as it is and that nothing is pushed (issue #221).
- `evals/review-loop`: the cases `rl-off-by-one`, `rl-null-guard`, and `rl-unbounded-query` get three route graders. They show whether a subagent edited a file. They show whether the reviewer brief asks for a fix plan. They also count the dispatches on the reviewer model (issue #221).

### Changed in the repository

- `tests/test_review_loop_text.py`: a new test module pins the plan line, the plan dispatch rule, and the choice of the fixer (issue #221).
- `tests/test_eval_cases.py`: samples for the route graders of the fold and for the graders of `rl-failing-build` (issue #221).
- `tests/test_eval_scaffolds.py`: `EXPECTED_BRANCH` names the branch of the new case. A new test makes sure that only its build fails and that `failure_check.py` gives `SAME-AT-PARENT` on it (issue #221).
- `docs/evals.md`: the suite `review-loop` has 6 cases (issue #221).

## dotnet-backend-dev 1.7.8 in release [4.16.1] - 2026-11-17

This release prepares the repository for a public home. The README, the docs, and `CLAUDE.md` no longer call the repository private, and the examples of `dotnet-backend-dev` use a neutral namespace for the test helpers.

### Changed in dotnet-backend-dev

- `skills/create-tests`, `skills/create-primitive-wrapper`, and `skills/dotnet-conventions`: the example namespace of the shared test helpers is now `MyApp.Testing`, in 16 lines of 7 files. The templates do the same work. If a repository has another namespace for its test helpers, the skills follow the code of that repository, as before (issue #233).

### Changed in the repository

- `README.md`: removes the texts that call the repository private, the note on the git credential helper, and the sentence on credentials for the background update. The plugin table has a new column with the version badge of each plugin (issue #233).
- `docs/authoring.md`: the sync section says that the owner adds the marketplace with "Add marketplace", and that this way takes a public repository. It names the organization sync of a Team or Enterprise plan as a different way, which needs a private or internal repository (issue #233).
- `CLAUDE.md`: the first rule of "Repo conventions" says that the repository is public, and no longer uses the word "employer" (issue #233).

## dev-essentials 3.19.0 in release [4.16.0] - 2026-11-17

This release turns Steps 1 to 5 of the command `merge-worktree-projects` into a script with unit tests. The dry run stays the default, and the apply run still needs an explicit yes of the user (issue #223).

### Added in dev-essentials

- `scripts/merge_projects.py`: finds the worktree project folders of each main project folder. It plans the merge of the sessions and the memory files by the rules of the command. Without `--apply`, it prints the plan and a `PLAN` code, and it changes nothing. With `--apply`, it needs `--confirm` with the code of the approved plan, and it makes the plan again before it acts. It tests each target before a move, and it never replaces an entry that it finds. It never follows a link, and it never deletes a folder that is not empty. It keeps a worktree index that holds a line that it cannot merge by rule: a line with no link, or a pointer line with other words for a file that the main index names. It applies only a plan that it prints in full. Its output is short, and each name prints on one line (issue #223).

### Changed in dev-essentials

- `commands/merge-worktree-projects`: Steps 1 to 5 run the script. The command keeps the questions to the user: an ambiguous keyword, a folder with recent activity, and the approval of the plan. Without Python 3, the command stops and moves no file. The command also says how to pass a folder name that starts with `-`. It also says how to split a plan that is too long (issue #223).

### Changed in the repository

- `tests/test_merge_projects.py`: new tests for the script on a fixture tree, on Linux and Windows (issue #223).
- `.github/workflows/tests.yml`: the job `test-windows` also runs `test_merge_projects` (issue #223).
- `docs/testing.md`: names the tests of the script (issue #223).

## dev-essentials 3.18.0 in release [4.15.0] - 2026-11-17

This release makes Stage 9 of `feature-pipeline` name the source of each argument of the PR call. If no source names the repository, the stage stops before the call (issue #214). If the repository gives no form for a PR body, the stage writes the body in the form of `compose-pr` (issue #203).

### Changed in dev-essentials

- `skills/feature-pipeline/stages/finalization.md`: Step 6 follows the convention of the repository for the PR body. A convention is a PR template, or a PR rule in the Key Conventions or the guidance files that gives the sections of the body. A rule that asks only for some content does not replace the form. Else the stage loads `compose-pr` and writes the body by its step 5, so `## What`, `## Why`, and `## Changes` come first (issue #203). A PR from a fork with an MCP PR tool is not supported yet (issue #225).
- `skills/feature-pipeline/project-context.template.md`: the example of the PR creation entry names the repository of the PR. If the issues of the Task Provider are in another repository, it also tells the user to name the repository of the code (issue #214).
- `skills/feature-pipeline/references/setup.md`: for an MCP PR tool, the PR creation entry also names the repository of the PR. Step 0 counts this entry as a required field. A Task Provider on the same MCP server can name it instead. If no source gives it, Step 0 asks the user (issue #214).
- `skills/promote-conventions/references/cleanup-and-provenance.md`: step 7 of 9c.4 says that its PR body does not take the form of `compose-pr`, and gives the reason (issue #203).
- `evals/feature-pipeline/fp-e2-untracked-file`: the new grader `pr-body-form` reads the body of the PR call. A replay on 8 kept runs of the old text gives a fail in each run, and `pr-created` passes in each run. The new grader `pr-body-length` makes sure that the body has at most 1000 characters, the limit of `compose-pr` for a small change. A replay on the 8 kept runs gives a pass in 3 runs and a fail in 5 runs. The new grader `pr-draft-not-saved` makes sure that the run saves no draft file of `compose-pr`. The new route grader `route-compose-pr-skill` shows the load of `compose-pr`. The mock of the PR call also guards `head` (issues #203 and #214).

### Fixed in dev-essentials

- `skills/feature-pipeline/stages/finalization.md`: Step 6 names the source of `owner`, `repo`, and `head` for an MCP PR tool. `owner` and `repo` come from the PR creation entry of the project context, or else from the Task Provider on the same MCP server. `head` is the current branch. If no source names the repository, the stage stops before the call. It does not take the repository from the `origin` remote (issue #214). A project context with an MCP PR tool must name the repository in the PR creation entry. Else it needs a Task Provider on the same MCP server.

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `PrBodyFormGraderTests` gives right and wrong samples to `pr-body-form`. It also gives samples of 1000 and 1001 characters to `pr-body-length`, and makes sure that `pr-draft-not-saved` names the draft file of `compose-pr`. It makes sure that the finalization stage names the step of `compose-pr` that holds the form (issue #203).

## dev-essentials 3.17.5 in release [4.14.5] - 2026-11-17

This release makes the stop of the failure check complete on Windows. A stopped command no longer leaves a Git Bash process that keeps the temporary folder of the check (issues #216 and #211).

### Fixed in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: on Windows, the script runs the command in a job object. At the time limit or after a stop signal, it runs `taskkill` as before, and then stops the whole job. It waits up to 5 seconds until the processes of the job end. Before, `taskkill /T` missed a Git Bash process whose Windows parent was gone. That process kept `fix.log` open, so the script left its folder with a `WARN` line. If the command cannot join a job, the script uses only `taskkill` (issues #216 and #211).
- `skills/review-loop/SKILL.md`: the `WARN` bullet of Phase 6 no longer names a Windows limit of the time limit (issue #211).

### Changed in the repository

- `tests/test_failure_check.py`: the test of the time limit has the same checks on Windows and on Linux. Five new Windows tests cover the stop. They make sure that a shell that cannot join a job gets no job, and that `taskkill` then stops it. They also make sure that the stop of a job runs `taskkill` first, then ends the job, and then waits. Another test makes sure that a signal during `taskkill` still ends the job. The last test makes sure that the wait covers each process of the job and has one limit (issues #216 and #211).
- `docs/testing.md`: names the job object in place of the `WARN` line of the Windows job (issue #211).

## dev-essentials 3.17.4 in release [4.14.4] - 2026-11-17

This release moves the cache tip of `process-pr-comments` into the documentation.

### Added in the repository

- `docs/workflows.md` and its link in `README.md`: the page covers the choice between one session and a new one. It gives the cost numbers of the study of issue #184 (issue #224).

### Changed in the repository

- `docs/evals.md`: step 5 of "Prepare WSL2 first" names the real cause of the Windows performance tip. WSL shows it for `git clone` or `cargo build` with a current folder on a Windows drive. The step says to start a WSL2 command with `wsl.exe --cd '~'` (issue #198).

### Removed in dev-essentials

- `skills/process-pr-comments`: the tip about the prompt cache is gone from Phase 5. Probe runs with a long history printed the tip in 0 of 4 runs. The guidance is now in `docs/workflows.md` (issue #224).

## dev-essentials 3.17.2 in release [4.14.2] - 2026-11-17

This release fixes the trigger case `compose-task-fires`, which failed in about one run of three. The skill text does not change.

### Fixed in dev-essentials

- `evals/triggers/compose-task-fires`: the prompt asks for the task description in chat and for no file. Before, the prompt selected the default mode of the skill. This mode writes a draft file, and a trigger run has no tool that writes a file. So in 4 of 12 kept runs, the session started the wrapper agent `task-composer` to write the file, and the grader `task-composer-not-fired` failed. The graders do not change, and the grader on the wrapper agent still counts in the score (issue #217).
- `evals/triggers/compose-task-draft-fires`: the new case sends the plain request for a task description, which selects the default mode. It has no grader on the wrapper agent `task-composer`. Kept runs show that a run can start an agent also with no `Agent` in `allowed_tools`. It has the two graders of `compose-task-fires` on the skills (issue #217).

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `ComposeTaskFiresCaseTests` makes sure that the prompt of `compose-task-fires` uses two phrases of the skill for `mode: response`. It also makes sure that the case keeps the tool `Agent` and lists no tool that writes a file. It gives right and wrong samples to the graders on the skill and on the wrapper agent. The new class `ComposeTaskDraftFiresCaseTests` makes sure that the prompt of `compose-task-draft-fires` has the trigger words and no phrase of the skill for another mode. It also makes sure that the case lists no `Agent` tool and no tool that writes a file. Its graders must be the two graders of `compose-task-fires` on the skills (issue #217).
- `docs/authoring.md`: the section "Conventions" states that a Python script reads its arguments with `argparse`, and it names the one exception (issue #220).

## dev-essentials 3.17.1 in release [4.14.1] - 2026-11-17

This release makes the skills `compose-pr` and `compose-task`, and the guide part of `create-documentation`, shorter. Each rule keeps one home, and the skills do the same work. A new eval case tests the guide flow.

### Changed in dev-essentials

- `skills/compose-pr`: the intro no longer names the wrapper agent. Step 3 names the groups of files in one sentence. Step 2 and the length limits no longer repeat text of other steps. `SKILL.md` goes from 1757 to 1678 words (issue #213).
- `skills/compose-task`: the rules against code, file paths, class names, and estimates now have one home in "Critical Rules". The sections "Good Change Examples" and "What to Avoid in the Description" are gone. The rule on parent links is now only in `references/create-mode.md`, which `mode: create` reads before its first GitHub call. The rule about HTML conversion is gone, because no step converts anything. The word "change" now routes to `mode: draft`, as the edit section already said. `SKILL.md` goes from 1118 to 930 words (issue #213).
- `skills/compose-task/references/create-mode.md`: the report step says once that the echoed parent number is no proof of a link (issue #213).
- `skills/create-documentation`: the guide section no longer names the wrapper agent. `references/guides-and-publishing.md` states the publish rule at the publish step and in "Critical Rules" only, and it drops the style lines that give no action. The compose-only fallback now says to report the path and that the guide is not published. In a subagent, the final reply says so, for the caller. The reference file goes from 822 to 701 words (issue #213).

### Added in dev-essentials

- `evals/composers`: the new case `cmp-guide-draft` runs the guide flow. Its repository keeps the guide drafts in `docs/drafts/`, and the notes of the user hold a warning. The graders test the folder and the file. They test the title and the overview, and the numbered steps. They test the language tag of the code block, the test command, and the warning in a blockquote (issue #213).

### Fixed in dev-essentials

- `evals/composers`: the route graders `route-pr-composer-agent` and `route-task-composer-agent` expected a call of the wrapper agent, so they failed in each run since release 4.11.0. The new graders `route-pr-composer-not-fired` and `route-task-composer-not-fired` make sure that no wrapper agent started. A replay on 36 kept runs gives a pass for each run of 4.11.0 or later (issue #213).

### Changed in the repository

- `tests/test_eval_cases.py`: new samples for the regex graders of `cmp-guide-draft`. A new test makes sure that each composer case counts its wrapper agent with `min: 0` and `max: 0`. One more test makes sure that the route grader of the guide case names the skill. Another one makes sure that the file graders of the case read `docs/drafts/run-tests-locally.md` (issue #213).
- `tests/test_eval_scaffolds.py`: `EXPECTED_BRANCH` names the branch of the new case (issue #213).
- `docs/evals.md`: the suite `composers` has 4 cases (issue #213).

## dev-essentials 3.17.0 in release [4.14.0] - 2026-11-17

This release lets `process-pr-comments` read the hand-off file of the earlier work on the PR branch. A new session then keeps the decisions that the user made in the build session (issue #199). The release also fixes five deferred review findings on the text of the skill (issue #187).

### Added in dev-essentials

- `skills/process-pr-comments`: Phase 1 step 7 reads the hand-off file of the earlier work on the PR branch. That is the file that the user names. Else, it is each file in `Results/` of the notes folder whose `Branch:` line names the head branch of the PR. `/dev-essentials:save-context` writes such files. A decision of the user is a decision that the file says the user made or approved. If a comment asks to reverse such a decision, the skill does not edit the code. It asks the user, with a draft reply that gives the reason of the decision (issue #199).
- `skills/process-pr-comments`: the cycle log of Phase 5 can end with one tip. If the session did long work before the skill, the first cycle log carries it. The tip says that the prompt cache is cold after a long pause before the next review round. A new session with the file of `save-context` then costs less. In the terminal, `/usage` shows the cache state. The skill does not stop for the tip (issue #199).
- `evals/process-pr-comments/ppc-build-context`: a new behavior case. A reviewer asks for a change that the user ruled out in the build session. The reason is only in the hand-off file of the scaffold, and the prompt does not name the file. The graders make sure that the run keeps the error and gives the reason of the user. They also make sure that the run makes no commit, no push, no reply, and no resolve (issue #199).

### Fixed in dev-essentials

- `skills/process-pr-comments`: the dispatch model no longer says that Rule 4 of `subagent-orchestration` covers only high-volume work. It says that Rule 4 also covers writes with iteration, but only by default. Rule 1 lets the skill make its writes in the session (issue #187).
- `skills/process-pr-comments`: under `dry-run`, the session asks no open item of Stage 2. The dry-run report lists each open item with its question. Before, the run asked questions whose answers changed nothing (issue #187).
- `skills/process-pr-comments`: the heading of the dispatch model says that the one dispatch is Stage 1 (issue #187).
- `skills/process-pr-comments`: for a linked PR, the brief of the read-only subagent gives the number of that PR, with its owner and repo. It also gives the text of the comment that points to it (issue #187).
- `skills/process-pr-comments/references/tag-actions.md`: the issue search of an `[OutOfScope]` thread passes `perPage: 10` and reads only the first page, which holds the best matches. The text names this as a departure from Rule 3 of `github-mcp-conventions` (issue #187).

### Changed in the repository

- `tests/test_eval_cases.py`: the new class `PpcBuildContextGraderTests` gives right and wrong samples to the graders of `ppc-build-context`. It also makes sure that the hand-off file of the scaffold names the branch of the PR mock (issue #199).
- `tests/test_eval_scaffolds.py`: the "no commit" grader of `ppc-build-context` runs on its scaffold (issue #199).
- `docs/evals.md`: the suite `process-pr-comments` has 10 behavior cases (issue #199).

## dev-essentials 3.16.0 in release [4.13.0] - 2026-11-16

This release turns two fixed steps of the skill `review-loop` into scripts with unit tests: the failure check after a red build, and the grouping of a large diff into review areas.

### Added in dev-essentials

- `skills/review-loop/scripts/failure_check.py`: the failure check of Phase 6. It runs the failed build or test command at the fix commit, and after a failure there also at the commit before it. Each run that the main worktree cannot hold uses a temporary worktree outside the repository. It removes each worktree that it made, also after a time-out or a stop signal. It prints one of the verdicts `UNCOMMITTED`, `REGRESSION`, `SAME-AT-PARENT`, and `OTHER` with the evidence. On Windows, it runs the command with Git Bash, because a plain `bash` there can start WSL (issue #197).
- `skills/review-loop/scripts/group_diff.py`: the areas of the large-target mode, from `git diff --numstat` and `git diff --raw`, with the limits of 10 files and 800 changed lines. Lock files and generated files go to the area "skipped" (issue #197).

### Changed in dev-essentials

- `skills/review-loop/SKILL.md`: Phase 6 runs `failure_check.py` and acts on its verdict. Without Python 3, the check ends the loop with `stop-blocked` (issue #197).
- `skills/review-loop/references/orchestrated-review.md`: the orchestrator runs `group_diff.py` before the Target Explorer. The Target Explorer no longer groups the files, and the map has no section "Areas". Without Python 3, the caller uses its default flow (issue #197).
- `commands/help-review-pr.md`: names the folder of the skill `review-loop` for the script of the orchestrated mode. Before the script runs, the orchestrator mode fetches the base branch and the head of the PR (issue #197).

### Changed in the repository

- `tests/test_failure_check.py` and `tests/test_group_diff.py`: new tests for the two scripts, with real git repositories and short bash commands. On Windows, `taskkill` does not reach a Git Bash program that a background subshell starts. So on Windows, the test of the time limit accepts a `WARN` line for the folder that this program keeps. The test then stops the program and deletes the folder (issue #197).
- `docs/testing.md`: names the tests of the two scripts (issue #197).
- `.github/workflows/tests.yml`: the job `test-windows` also runs `test_failure_check` and `test_group_diff` (issue #197).

## dev-essentials 3.15.2 in release [4.12.2] - 2026-11-16

This release settles the deferred review findings of the PRs #175, #176, #177, and #179. It makes seven eval graders read more right wordings and fewer wrong runs. The skill text does not change.

### Fixed in dev-essentials

- `evals/process-pr-comments`: `question-drafted` of `ppc-gated-threads` also reads "post the answer?". It no longer passes the reply offer of another thread that comes after the question thread. It also no longer passes a "post this answer" plan that ends with a period before another question. `asks-create` of `ppc-outofscope-autonomous` also reads `could not find`, "zero results", and "came back empty" as an empty search. It also reads a create question with a quoted title or the word "ticket". It no longer reads "neither of the issues I found" as an empty search (issue #187).
- `evals/composers`: `names-dropped-label` no longer passes "removes" in another sense or a label list after a sentence end. `names-count` of `cmp-pr-from-diff` reads "how many orders a customer has" and "total orders per customer", and not "row count". `reason-from-plan` reads "invoicing run". `no-closing-keyword` finds a closing keyword with the issue URL. `short-items` of `cmp-task-draft` reads only the section `## Changes to Do` (issue #187).
- `.claude-plugin/plugin.json`: the keyword `composer-agents` is now `composers` (issue #187).
- A replay of the changed graders on 71 kept runs changed no verdict (issue #187).

### Changed in the repository

- `tests/test_eval_cases.py`: the case check refuses the regex flags `u`, `v`, and `y`. The CLI accepts them, but Python cannot apply them, so a sample test gives another verdict than a run. New samples pin each changed grader (issue #187).
- `tests/test_eval_scaffolds.py`: a new test makes sure that each grader that names the PR file of `compose-pr` names the file of the scaffold branch (issue #187).
- `docs/evals.md`: a new sentence names the `not_contains` graders on `mock_calls` that need a second grader (issue #187).

## dev-essentials 3.15.1 in release [4.12.1] - 2026-11-16

This release makes the eval graders that read the mocked GitHub calls find a tool name only in the `tool` field of a call. The skill text does not change.

### Fixed in dev-essentials

- `evals`: 32 regex graders on `mock_calls` named a tool or a method without the `tool` field. Now each one starts at the `tool` field, in the form `"tool":"(?:[\w-]*__)?<tool>"`. Before, a tool name in the input or the output of another call also matched. With such a name, a `contains` grader can pass a run with no such call. A `not_contains` grader can fail a right run, and a count can be too high. No kept run had such a name. The suites are `bug-hunt`, `composers`, `feature-pipeline`, `probes`, and `process-pr-comments` (issue #189).
- `evals/process-pr-comments`: the three graders on the method `resolve_thread` now read it only in a call of `pull_request_review_write`. The graders that read the text or the comment id of a reply now read only the line of that reply. Before, they also read the next call (issue #189).
- `evals`: the five graders that already read the `tool` field now use `(?:[\w-]*__)?` in place of `\w*`. So the name `issue_write` no longer matches the tool `sub_issue_write`. The graders `label-kept`, `no-missing-label`, and `no-title-in-body` of `cmp-issue-create` no longer read past the end of the create call (issue #189).
- A replay of the new patterns on 170 kept runs gave the stored verdict of each run (issue #189).

### Changed in the repository

- `tests/test_eval_cases.py`: the new test class `MockCallsGraderTests` makes sure that each regex grader on `mock_calls` starts at the `tool` field and names a mocked tool only there. The part after a `tool` field must not read past the end of the call line, except a span to a second `tool` field. Each side of a `|` outside a group must also start at a `tool` field. Samples for each kind of grader test a tool name in another call and the real call (issue #189).
- `docs/evals.md`: a new paragraph says that a pattern on `mock_calls` starts at the `tool` field and reads only the line of its call. It names the test that checks this (issue #189).
- `docs/authoring.md`: the paragraph about the sync notice for a changed plugin lists the three recorded sync results. It says which changes came with the notice, and that the notice asks for no fix (issue #200).

## dev-essentials 3.15.0 in release [4.12.0] - 2026-11-16

This release changes the PR description of `compose-pr`. Each description now starts with the sections `## What`, `## Why`, and `## Changes`, so that a reader gets the task and its reason first.

### Changed in dev-essentials

- `skills/compose-pr`: step 5 starts each PR description with `## What`, `## Why`, and `## Changes`, in this order. `## Why` gives the problem that the change solves, from the plan or the issue of the branch. If a source names a gain in time, resources, or cost, `## Why` names it too. `## Changes` is the list by component, and it replaces `## Modified Components`. The old summary of `## Changes` is now `## What`. `## Testing` and `## Notes` stay after them with the same template lines, and the length limits stay the same. The rule for bullet points now covers only `## Changes`. A closing line from the input, for example `Closes #42.`, goes after the last section (issue #190).
- `skills/compose-pr/references/examples.md`: the three examples have the new sections (issue #190).
- `evals/composers/cmp-pr-from-diff`: the grader `structure` needs `## What`, `## Why`, and `## Changes` first, and `## Testing` after them. The grader `reason-from-plan` needs the reason of the plan in the section `## Why`. The new grader `no-modified-components` fails a run that still writes the old section (issue #190).

### Changed in the repository

- `tests/test_eval_cases.py`: new tests make sure that the graders `structure`, `reason-from-plan`, and `no-modified-components` pass the new form and fail the old form (issue #190).

## dev-essentials 3.14.6 in release [4.11.7] - 2026-11-16

This release fixes two kinds of eval graders that passed some wrong runs: the `no-push` graders and the "no commit" graders. The skill text does not change.

### Fixed in dev-essentials

- `evals`: the 12 `no-push` graders of `feature-pipeline`, `process-pr-comments`, and `review-loop` read `.remote/origin.git/logs/refs/heads/**`. Before, each one read only the reflog of the case branch on the remote. So a push to another branch passed, for example `HEAD:refs/heads/review-fixes` or `work/813` (issue #180).
- `evals/review-loop/rl-pr-head-gate`: the grader `pr-branch-no-push` is gone. The grader `no-push` now covers both branches (issue #180).
- `evals`: the 8 "no commit" graders fail on each reflog line of their branch that the fixture did not write, except a `branch: Created from` line. Before, they matched only a plain `commit:` line. So an amend, a reset, a merge, a cherry-pick, a rebase, or a revert passed (issue #180).
- `evals/feature-pipeline/fp-e1-clean-change`: the new grader `no-commit-any-branch` reads `.git/logs/HEAD`. It fails a run that makes a commit on any branch of the main work tree, also on a new branch (issue #180).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: a new check makes sure that each `no-push` grader and each "no commit" grader of a branch uses the shared form. New tests run each "no commit" grader on its scaffold. They also run the graders on the reflog lines of an amend, a reset, a merge, a cherry-pick, a rebase, and a revert. Another test runs five pushes on a scaffold (issue #180).
- `docs/evals.md`: a new paragraph names the shared forms of the `no-push` and "no commit" graders and the seven forms that they still miss (issue #180).

## dev-essentials 3.14.5 and dotnet-backend-dev 1.7.7 in release [4.11.6] - 2026-11-16

This release fixes two gaps in the shared eval fixtures. A .NET test run that stops early, or a failed compile after a change of the code, no longer leaves `Passed` for the graders. A push from a linked worktree now reaches the bare remote. The skill text does not change.

### Fixed in dev-essentials

- `evals/_lib/dotnet-fixture.sh`: when a test run starts, `RunMarker.cs` now writes `Started` to `.test-runs/last.txt`. Before, a test run that stopped before its teardown kept the `Passed` of an earlier run. Examples are a crash of the test host and a command that a timeout stops. Then the 13 `tests-passed` graders passed a run that ended with broken code (issue #181).
- `evals/_lib/dotnet-fixture.sh`: `Directory.Build.props` has the new target `MarkTestOutcomeStale`. The target runs before a compile. If a compile input is newer than the compiled assembly, it writes `Stale` to `.test-runs/last.txt`. The inputs are the source files, the list of source files, the project files, and the referenced assemblies. So a failed compile after a passing test run, or after a deleted source file, no longer keeps `Passed`. A build that compiles nothing keeps the outcome. A rebuild, or a build after a clean or after a change of only the file times, writes `Stale`. A first build of another configuration, for example `-c Release`, also writes `Stale`. An edit with no later build of its project, a failed restore, and a change of only `.editorconfig` still keep the outcome. A `dotnet test --no-build` after a failed build writes the outcome of the old binaries (issue #181).
- `evals/_lib/git-fixture.sh`: `fixture_remote_init` adds the remote `origin` with an absolute path. Before, git read the relative path `.remote/origin.git` from the top folder of the current worktree. So a push or a fetch from a linked worktree failed (issue #181).
- `evals/_lib/dotnet-fixture.sh`: `dotnet_warm` takes optional `<package>@<version>` arguments. It restores each package into the shared NuGet folder under the same lock as the restore of the solution. `evals/feature-pipeline/fp-e4-package-bump/scaffold.sh` uses it for NUnit 5.0.0 and no longer has its own copy of the lock code. Before, a failed restore in that copy left a temporary folder (issue #181).

### Changed in dev-essentials

- `evals/_lib/dotnet-fixture.sh`: the versions of the three test packages are now in one place. The variables are `DOTNET_TEST_SDK_VERSION`, `DOTNET_NUNIT_VERSION`, and `DOTNET_NUNIT_ADAPTER_VERSION`. `inventory-fixture.sh` uses them. The files that the scaffolds write do not change (issue #181).

### Changed in dotnet-backend-dev

- `evals/_lib/billing-fixture.sh`: uses the shared versions of the test packages from `dotnet-fixture.sh`. Before, it had its own copy of the same three versions. The files that the scaffolds write do not change. The fixes of `dotnet-fixture.sh` and `git-fixture.sh` in dev-essentials also apply to the cases of this plugin through the git symlinks (issue #181).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: the new test `test_run_marker_follows_the_last_build_and_test_run` runs the probe `probe-test-fixture`. A build with no change must keep `Passed`. A failed build must leave `Stale`, and a crash of the test host must leave `Started`. A failed build after a deleted source file must leave `Stale`. The new test `test_a_push_from_a_linked_worktree_reaches_the_remote` pushes from a linked worktree. Three new tests of `DotnetWarmTests` test a named package. It must go into the shared folder before the solution. Two runs must restore one after the other. A failed restore must leave no temporary folder (issue #181).
- `docs/evals.md`: a new part says how the run marker of the .NET cases works, and it lists the limits of the marker (issue #181).
- `docs/evals.md`: a new step of the WSL2 preparation says to keep the clone for the eval runs in the Linux file system. It also says how that clone gets a branch of a Windows clone through a git bundle (issue #198).
- `tests/evals/replay_graders.mjs`: a new tool replays the graders of an eval case on kept runs for free. It builds the `last_message`, `mock_calls`, and `trace` texts by the rules of Claude Code 2.1.325. It runs the regex graders on these texts and the `tool_used` graders. `docs/evals.md` says how to run it (issue #186).
- `tests/evals/test_replay_graders.py`: new tests pin the verdicts and the `mock_calls` text of the tool on a hand-made run. A test also makes sure that the tool reads each grader file of the repository as PyYAML does (issue #186).

## dev-essentials 3.14.4 in release [4.11.5] - 2026-11-16

This release corrects the description of the skill `feature-pipeline`, and the note about it in two other skills and one command. The pipeline itself does not change.

### Fixed in dev-essentials

- `skills/feature-pipeline`: the description says that subagents run the stages from the requirements to the reviews, and that the session pushes and opens the PR. Before, it said that one subagent runs each stage to the PR. That is not true for the last stage since release 4.9.0 (issue #196).
- `skills/implement-batch`, `skills/research-implement-review-report`, and `commands/implement-task`: the note about `feature-pipeline` no longer says that it has one subagent for each stage (issue #196).

## doc-styles 1.1.7 in release [4.11.4] - 2026-11-16

This release stops a hook error of doc-styles on a Windows PC where `python3` is an alias of the Microsoft Store that cannot start Python. A stub showed this case, not a PC with the real alias. It also adds a CI job that runs the tests of the plugin scripts on Windows (issue #182).

### Fixed in doc-styles

- `hooks/hooks.json`: the `PostToolUse` hook now tests for Python with `python3 -c ''` instead of `command -v python3`. On Windows, Git Bash finds the `python3` alias of the Microsoft Store in `WindowsApps`. If the Store Python is not installed, the alias exits with an error. Before, the hook then exited with that error. The hooks page of Claude Code says that such an exit code gives a hook error notice. Now the hook exits with 0 and stays silent. A test with a stub `python3` shows this. No test ran on a PC with the real alias. If `python3` is missing, the hook also exits with 0 and stays silent (issue #182).

### Changed in the repository

- `.github/workflows/tests.yml`: the new job `test-windows` runs the tests of the plugin scripts and of the test helpers on `windows-latest` in Git Bash (issue #182).
- `tests/test_kb_plugin.py`: the tests of `check.sh` pass on Windows. A `uname` stub picks the Linux branch on every OS. The path rules use the `C:/...` form that `check.sh` prints, and the tests read the path of `settings.json` from the `$HOME` of bash. A new test runs the real Windows branch in Git Bash. It skips on other systems (issue #182).
- `tests/test_openbsd_lint.py`: a new test runs the hook command with a `python3` that cannot start (issue #182).
- `docs/testing.md`: names the job `test-windows` and the tests that it runs (issue #182).

## dev-essentials 3.14.3, doc-styles 1.1.6, dotnet-backend-dev 1.7.6, and kb 0.2.4 in release [4.11.3] - 2026-11-16

This release removes the `icon` key from each `plugin.json`, so the claude.ai sync no longer shows a warning for it. The icon files stay, and `claude plugin validate` still finds them. New tests catch a known sync warning before a merge.

### Fixed in dev-essentials

- `.claude-plugin/plugin.json`: no `icon` key. The claude.ai sync stripped the key and showed a warning. `claude plugin validate` finds `assets/icon.png` without the key (issue #192).

### Fixed in doc-styles

- `.claude-plugin/plugin.json`: no `icon` key, for the same reason as in dev-essentials (issue #192).

### Fixed in dotnet-backend-dev

- `.claude-plugin/plugin.json`: no `icon` key, for the same reason as in dev-essentials (issue #192).

### Fixed in kb

- `.claude-plugin/plugin.json`: no `icon` key, for the same reason as in dev-essentials (issue #192).

### Changed in the repository

- `tests/test_claude_ai_sync.py`: the key test of `plugin.json` allows only the keys that a claude.ai sync took with no warning. Before, it found only `$schema`. A new test does the same for `marketplace.json` and its plugin entries. Two new tests make sure that each plugin `source` starts with `./` and that no plugin has a top-level `bin/` folder. The icon test now checks only the file (issue #192).
- `docs/authoring.md`: a new section lists the rules of the claude.ai sync. It says how to add a key, and what to do after a sync warning that no test knew (issue #192).
- `CLAUDE.md`: the icon convention says not to set the `icon` field (issue #192).
- `docs/evals.md`: three new paragraphs say how an eval run builds the `mock_calls` text of a regex grader, and what a pattern for a call looks like. They also say that a mock of the type `agent` does not see a call that a fixed mock answered (issue #185).

## dev-essentials 3.14.2 and dotnet-backend-dev 1.7.5 in release [4.11.2] - 2026-11-16

This release fixes two eval graders that matched text outside the call that they test. The skill text does not change.

### Fixed in dev-essentials

- `evals/feature-pipeline/fp-e2-untracked-file`: the grader `pr-created` reads only the `tool` field of each mocked call. Before, another call that named the PR tool in its input or its answer made a run with no PR call pass (issue #183).
- `evals/feature-pipeline`: the grader `route-plain-dotnet` of the nine .NET cases counts a `dotnet build` or `dotnet test` command only at the start of a command. Before, it counted a sentence that named the command, for example in a heredoc that writes a prompt or a review file. That failed the grader in 2 of 6 kept runs of `fp-e2-untracked-file` and in 3 kept runs of `fp-e8-rename-across-projects`. The grader also no longer counts `dotnet build-server` (issue #183).

### Fixed in dotnet-backend-dev

- `evals/write-tests/wt-one-class` and `evals/write-tests/wt-pricing-folder`: the grader `route-plain-dotnet` has the new pattern of dev-essentials. A test makes sure that the 11 copies are equal (issue #183).

### Changed in the repository

- `docs/evals.md`: a new paragraph says what the grader `route-plain-dotnet` counts. It names the forms where its verdict is wrong (issue #183).
- `tests/test_eval_cases.py`: the new class `RoutePlainDotnetGraderTests` tests plain calls, calls with `-m:1`, and text in heredocs. It pins each wrong verdict that `docs/evals.md` names, and it makes sure that the grader is fast on long commands. The new class `PrCreatedGraderTests` makes sure that only a call of the PR tool passes `pr-created` (issue #183).

## dev-essentials 3.14.1 and kb 0.2.3 in release [4.11.1] - 2026-11-16

This release fixes four bugs that a code review found in two plugin scripts. It also closes four gaps in the repository tests and stops a superseded CI run (issue #110).

### Fixed in dev-essentials

- `skills/bug-hunt/scripts/check_report.py`: the command `next-id` now reads the entries with the same parser as the report check. Before, it counted a `### BH-NN:` heading inside a code fence. Then it printed another ID than the `next=` value of the report check (issue #110).
- `skills/bug-hunt/scripts/check_report.py`: the command `open-notes` and the report check skip a note line inside a code fence (issue #110).
- `skills/bug-hunt/scripts/check_report.py`: if the process command exits with a nonzero code, the process scan returns no result. Before, the scan read the empty output as an empty process list. So the warning `cannot list processes` never appeared (issue #110).

### Fixed in kb

- `skills/setup/check.sh`: the error of a missing `settings.json` no longer prints on stderr. The `2>/dev/null` now comes before the `< "$settings"` redirect on both lines that read the file (issue #110).

### Changed in the repository

- `tests/test_version_bump.py`: a new file that git does not track yet now counts as a change of its plugin. Before, a local run passed and the CI run failed (issue #110).
- `tests/test_eval_stubs.py`: the drift test of the `simple-english` stand-in also reads the synced copies of the plugin, with the folder names `simple-english` and `simple-english~g<N>`. On a machine with synced plugins, the test always skipped before (issue #110).
- `tests/test_openbsd_lint.py`: a new test makes sure that the hook joins a relative `file_path` with the `cwd` of the event (issue #110).
- `tests/test_eval_scaffolds.py`: a new check makes sure that each commit id in a regex grader pattern starts a commit of the scaffold repository (issue #110).
- `.github/workflows/tests.yml`: a new push to a pull request cancels the test run that the earlier push started. A push to `main` never cancels a run that is already running. A newer push to `main` can replace a run that still waits in the queue (issue #110).

## dev-essentials 3.14.0 in release [4.11.0] - 2026-11-16

This release moves the bodies of the three composer agents into skills. Each agent stays as a thin wrapper that preloads its skill, so each old dispatch still works.

### Added in dev-essentials

- `skills/compose-task`: a new skill with the body of the agent `task-composer`. It writes a task description as a local draft, returns it in chat, or creates the GitHub issue and reads it back. The steps of the create mode are in `references/create-mode.md` (issue #172).
- `skills/create-documentation/references/guides-and-publishing.md`: the guide drafts and the publish flow of the agent `docs-composer`. Only on an explicit "publish" of the user, the skill publishes a guide (issue #172).
- `evals/composers`: the new behavior case `cmp-pr-from-diff`. It plants a decoy plan, a scratch note, and a plan step that the diff does not hold (issue #172).
- `evals/composers`: the new behavior cases `cmp-task-draft` and `cmp-issue-create`. The second one creates an issue on the GitHub stand-in, with a label that the repository does not have (issue #172).
- `evals/triggers`: the new trigger cases `compose-task-fires`, `compose-task-near-miss`, and `create-documentation-guide-fires` (issue #172).

### Changed in dev-essentials

- `skills/compose-pr`: the command `compose-pr` is now a skill with the body of the agent `pr-composer`. It writes the PR description in the session, with no subagent. `/dev-essentials:compose-pr` works as before. The examples are in `references/examples.md` (issue #172).
- `agents/pr-composer`: a thin wrapper that preloads the skill `compose-pr` (issue #172).
- `review-loop`: names the skill `compose-pr` for a PR description (issue #172).
- `agents/task-composer` and `agents/docs-composer`: thin wrappers that preload the skills `compose-task` and `create-documentation` (issue #172).
- `skills/create-documentation`: the new section "Guide Drafts and Publishing" points to the reference file. The description names the guide draft and the publish rule (issue #172).
- `github-mcp-conventions`: names the create steps of the skill `compose-task` as the standard for a verified create (issue #172).
- `evals/triggers/compose-pr-fires` and `compose-pr-near-miss`: the near-miss expects the skill `compose-task` for an issue request, and `compose-pr-fires` makes sure that `compose-task` does not start (issue #172).
- `skills/process-pr-comments`: Task Composer is now the skill `compose-task`. The session loads it for the draft of an `[OutOfScope]` issue, and runs its create steps right before the batch posts. The best-effort search, the question before a new issue, the `Source:` line, and the state `pr-commit-no-reply` stay the same (issue #172).

### Changed in the repository

- `docs/evals.md`: the table of behavior suites names the suite `composers` (issue #172).

## dev-essentials 3.13.0 in release [4.10.0] - 2026-11-16

This release runs Stage 2 of `process-pr-comments` in the orchestrating session. The skill no longer resumes a Stage 2 subagent with `SendMessage`. A new behavior case covers the open items of a cycle after the answers of the user.

### Added in dev-essentials

- `evals/process-pr-comments/ppc-open-items-answered`: a new behavior case. A reviewer asks a question and marks one thread as out of scope. The prompt gives the answers of the user in advance. The graders make sure that the run creates the issue with the `Source:` line of the thread before any reply posts. They also make sure that the run posts both replies, resolves no thread, and makes no commit. They make sure too that the out-of-scope reply names the new issue (issue #171, issue #122).

### Changed in dev-essentials

- `skills/process-pr-comments`: Stage 2 runs in the orchestrating session, not in a subagent. Stage 2 records its open items, and the session asks all of them in one message. After the answers, Stage 2 finishes them. The post of the batch, the push, and the resolve need no `SendMessage` resume. Stage 1 and the Task Composer dispatches stay. A new paragraph says how Stage 2 keeps the main context small (issue #171).
- `skills/process-pr-comments`: on a `deep-fix` cycle, an answer that asks for a code change follows the rule for a changed fix. Before, it waited for a later invocation, because the Stage 2 subagent had ended (issue #171).

### Changed in the repository

- `docs/evals.md`: the table of behavior suites gives 9 cases for `process-pr-comments`. A new paragraph says that a run sends one prompt and has no `SendMessage` tool. So a case gives the answers of the user in advance in its prompt (issue #122).

## dev-essentials 3.12.0 in release [4.9.0] - 2026-11-16

This release folds three dispatches into the main session. On a `deep-fix` cycle of `process-pr-comments`, the orchestrating session posts the replies and resolves the threads itself. `feature-pipeline` runs its finalization stage in the main session, with one build and test run before the push.

### Changed in dev-essentials

- `skills/process-pr-comments`: on a `deep-fix` cycle, the orchestrating session posts the batch of replies, and after the push it resolves the fixed threads. Before, the dispatch Stage 3b posted the batch, and one more dispatch resolved the threads. Their texts were already decided, and each call has a small result, so no delegation test sent them to a subagent (issue #170).
- `skills/feature-pipeline`: the master agent runs Stage 9 (`finalization`) itself, in the main session: the build and test run, the commit, the push, and the PR. Before, a subagent made the commit and reported the facts for the push and the PR. The build and test run is the run before a push that item 1 of `Trust but verify` in `subagent-orchestration` asks for. `--model-override` no longer applies to Stage 9 (issue #170).
- `evals/feature-pipeline/fp-e2-untracked-file`: the project context of the case names an MCP tool as the PR command. A mock answers the PR call, and the new grader `pr-created` makes sure that the run opens the PR (issue #170).

## dev-essentials 3.11.5 in release [4.8.6] - 2026-11-16

This release fixes two graders of the `process-pr-comments` eval suite. Each one failed a right run because of the wording of its last message. The skill text does not change.

### Fixed in dev-essentials

- `evals/process-pr-comments/ppc-outofscope-autonomous`: the grader `asks-create` also reads "found none", "none found", and "neither ... found" as an empty search. The create question must have the word "issue", "one", or "it" after its verb, for example "create this issue?". The search result and the create question can now be up to 1500 characters apart. Before, the limit was 400, and a run that showed the issue draft between them failed (issue #173).
- `evals/process-pr-comments/ppc-gated-threads`: the grader `question-drafted` also reads the question "post this answer?" as the offer of a drafted `[Question]` reply. It reads "post this reply?" the same way, but only next to `T#9102` or `[Question]`, or right under the quoted draft (issue #173).

### Changed in the repository

- `tests/test_eval_cases.py`: two new tests pin the wordings that the two graders accept and the replies that they refuse (issue #173).

## dev-essentials 3.11.4 in release [4.8.5] - 2026-11-16

This release closes the open edge cases of the report-only state `pr-commit-no-reply` of `process-pr-comments`. It also adds a behavior case for a local commit that goes along with an `autonomous` push.

### Added in dev-essentials

- `evals/process-pr-comments/ppc-autonomous-ride-along`: a new behavior case. One `[ToFix]` thread has no reply, and the run has `autonomous`. The local branch has a commit of the author that is not pushed yet, and only the body of that commit names the thread. The graders make sure that the run fixes and commits the thread and names the commit of the author in its last message. They also make sure that the run posts no reply and does not push before the go-ahead (issue #124).

### Changed in dev-essentials

- `skills/process-pr-comments`: only the subject line of a commit names a thread. A `T#<id>` in the body no longer counts. A `squash` commit and a commit for threads with the same note put every `T#<id>` in the subject (issue #124).
- `skills/process-pr-comments`: if the fetch of the base branch fails, each thread with no reply gets the report-only state `pr-commit-no-reply` in that cycle. The run asks no question about the failed fetch, and these threads open no push. Before, the failed fetch went to the `blockers` list, and the state of these threads was not defined (issue #124).
- `skills/process-pr-comments`: with `autonomous`, a later cycle of a `/loop` session asks the push question again only for a new list. The list holds the commits that no thread of the push names. With the same list, the cycle holds the push and the replies, and prints the list (issue #124).
- `skills/process-pr-comments`: the text names one more way into `pr-commit-no-reply`: a push after a failed reply post, in a session that then ended. Both this way and a push by hand need no "handle separately" answer (issue #124).

### Changed in the repository

- `docs/evals.md`: the table of behavior suites gives 8 cases for `process-pr-comments` (issue #124).
- `docs/evals.md`: the new section "Clean the temp folder" says how to clean the temp folder of the eval runs in WSL2 or Linux. A dry run lists the entries that stay and the entries that go. A run folder that one of your notes names stays (issue #165).
- `docs/evals.md`: a new paragraph names some edits that the eval grader `untested-commit` misses. One of them is a `sed -i` or `perl -pi` edit with a `;`, `&`, or `|` inside its quoted script. Four tries at a pattern that reads the script each brought a new wrong verdict, so the grader stays as it is (issue #162).
- `tests/test_eval_cases.py`: a new test pins each wrong verdict that `docs/evals.md` names. Another new test makes sure that the grader needs less than 2 seconds for a command with 4000 `sed` edits (issue #162).

## dev-essentials 3.11.3 in release [4.8.4] - 2026-11-15

This release adds one behavior case for `process-pr-comments`. The case covers an `[OutOfScope]` issue search that finds the issue. The skill text does not change.

### Added in dev-essentials

- `evals/process-pr-comments/ppc-outofscope-search-hit`: a new behavior case. A reviewer asks for a separate issue, and the run has `autonomous`. The issue search returns two issues. The body of one issue has the line `Source:` with the URL of the thread. The graders make sure that the run searches and creates no issue. They make sure that the run asks no question about a new issue. They also make sure that the run posts the `Tracked as issue` reply that names the found issue. The case `ppc-outofscope-autonomous` still covers a search that finds nothing (issue #126).

### Changed in the repository

- `docs/evals.md`: the table of behavior suites gives 7 cases for `process-pr-comments` (issue #126).
- `docs/evals.md`: the `style-compare-*` suites of `doc-styles` run in WSL2 or on Linux, not on native Windows. Their hooks need `python3`, and the hooks of the simple-english stand-in also need `node` (Node.js 22 or later). On native Windows, the lint hooks of `doc-styles` and of the stand-in gave no message in an eval run. So the old scores of these suites came from runs with no lint hook message. The file names the tools, a setup step for WSL2, and the results of the hook probes (issue #151).

## dev-essentials 3.11.2 in release [4.8.3] - 2026-11-15

This release gives the `Route:` line of `subagent-orchestration` a label for each kind of dispatch that no delegation test decides.

### Changed in dev-essentials

- `subagent-orchestration`: Rule 1 gives the `Route:` line three labels for a dispatch that no test decides. The label `workflow` is for a dispatch that a workflow skill names. The label `outside system` is for a Rule 4 dispatch, and the label `stronger model` is the third. Before, a reply had to invent a word or name a test that did not decide the dispatch (issue #161).
- `evals/subagent-orchestration` and `evals/research-implement-review-report/rirr-retry-limit`: the graders `route-reported` accept the three labels (issue #161).

### Changed in the repository

- `tests/test_eval_cases.py`: `RouteReportedGraderTests` runs the `route-reported` patterns of the so cases and of `rirr-retry-limit` on sample lines with each label. It also makes sure that the four so cases have the same pattern (issue #161).

## dev-essentials 3.11.1 in release [4.8.2] - 2026-11-15

This release fixes small gaps that the review loops of batch 2 left open. One eval grader gave a false pass, and some tests and docs lines were not exact. The skill text does not change.

### Changed in dev-essentials

- `evals/feature-pipeline/fp-e1-seeded-defects`: the grader `fixed-sql` also reads the SQL words `select`, `where`, `from`, and `values` in lower case. Before, a lower-case line with the defect passed (issue #159).
- `evals/_lib`: the comments of `git-fixture.sh` and `dotnet-fixture.sh` say that `dotnet-backend-dev` has a git symlink to each file. Before, they said that the file is copied into each plugin (issue #159).

### Changed in the repository

- `tests/test_claude_ai_sync.py`: the new class `PluginIconTest` makes sure that each plugin names `./assets/icon.png` in `plugin.json`. It also makes sure that the file is a square PNG of 512 to 2048 px, under 2 MB (issue #159).
- `tests/test_check_report.py`: the two leftovers tests no longer read a folder of the machine. Before, a folder `C:\work\bh-scratch\work` that was not empty made them fail. On Linux, that path is relative to the current folder (issue #159).
- `tests/test_eval_cases.py`: new samples for lower-case SQL (issue #159).
- `tests/test_eval_scaffolds.py`: the docstring of the pull ref test names the one pin that the test proves (issue #159).
- `CLAUDE.md`: the icon convention says what the validator reports without the icon file, and names the new test (issue #159).
- `docs/testing.md`: the sentence about `cmd.exe` names the folder that it cannot use (issue #159).

## dotnet-backend-dev 1.7.4 in release [4.8.1] - 2026-11-15

This release removes the copies of two eval fixture libraries. The skill text does not change.

### Changed in dotnet-backend-dev

- `evals/_lib/git-fixture.sh` and `evals/_lib/dotnet-fixture.sh` are now git symlinks to the files of the same name in `dev-essentials`. A change to one of these libraries now edits one file and bumps only `dev-essentials`. When Claude Code copies the plugin from the git-hosted marketplace, it copies the content of each link into the plugin cache (issue #156).

### Changed in the repository

- `tests/test_eval_cases.py`: a new test makes sure that the two libraries of `dotnet-backend-dev` are links to the files of `dev-essentials`. A link that git checked out as a plain file fails with the fix in the message. `shell_file_problems` accepts a link between two `evals/_lib` folders (issue #156).
- `docs/evals.md`: the text names the links and the setup that Windows needs for them (issue #156).

## dev-essentials 3.11.0 in release [4.8.0] - 2026-11-15

This release changes how the orchestrator picks the route of each piece of work. Five delegation tests in `subagent-orchestration` decide each dispatch, and the main loop keeps small lookups and the small tasks of a plan. Before a commit, the main loop runs the build and the tests one time, in place of a `test-runner` dispatch. The final reply names the route in a `Route:` line.

### Changed in dev-essentials

- `subagent-orchestration`: behavior change: Rule 1 has five delegation tests: context, parallel work, independent view, tool isolation, and else the main loop. The main loop does small lookups and the small tasks of a plan itself. A workflow skill keeps the dispatches that it names. The final reply has a `Route:` line that names each dispatch and its test (issue #134).
- `subagent-orchestration`: behavior change: in the check of a subagent report, the first tier reads the verbatim result lines and adds no run after each report. Before a commit or a push, the main loop runs the build and the tests one time. It uses one filtered command and keeps the exit code. If a run can take longer than 10 minutes or runs in several worktrees, the main loop dispatches `test-runner` (issue #134).
- `subagent-orchestration`: `references/model-selection.md` has no fork exception in "Plan → execute split" any more. A task that passes a test of Rule 1 goes to a Sonnet subagent. The session dispatches a subagent for a model that a skill or the user names, or for a stronger model of the matrix. It does not dispatch a subagent to reach a cheaper model (issue #134).
- `subagent-orchestration`: behavior change: Rule 7 gives the receiver of a bounded task one rule. The rule replaces a size test and a fan-out list with a test of its own. The receiver never dispatches its whole task again. It dispatches a part only for a reason of Rule 1: a delegation test, a stronger model, or a high-volume read of an outside system (issue #144).
- `review-loop`: behavior change: Phase 6 runs the build and the tests one time in the main loop before the Phase 7 commit. It uses one filtered command that keeps the exit code, and for .NET the two filters of `dotnet-build-test`. If the test run can take longer than 10 minutes, it dispatches `test-runner`. After a red run, each later run of a build or test command uses the same method (issue #134).
- `feature-pipeline`: behavior change: the master agent runs the build of the Build Gate itself, with no `test-runner` dispatch. It filters the output to the error lines and the result line, and keeps the exit code. If the build exits with code 0 and shows no error line, the status is GREEN. The Build Gate retry in `references/stage-launch.md` runs the same build again after the implementation stage (issue #134).
- `research-implement-review-report`: behavior change: Phase 1 finds the facts of a small task in the main loop. For independent questions that each read many files, it dispatches fact gatherers. Phase 2 implements a small task in the main loop, and runs the build and the tests there before each commit. The final report ends with the `Route:` line (issue #134).
- `implement-batch`: behavior change: before the commit of each task, the main loop runs the build and the tests one time. Before, a `test-runner` dispatch did this run. The text names the delegation test of each dispatch: the planners pass the parallel test, and the implementers pass the context test. The other dispatches do not change (issue #134).
- `process-pr-comments`: the dispatch model cites Rule 1 for a workflow skill that names its own dispatches. The dispatches do not change (issue #134).
- `implement-task`: behavior change: after the `/simplify` subagent reports, the command runs the build and the tests one time in the worktree. Before, a `test-runner` dispatch did this run. The orchestrating session has no ban on a read of source code any more, but outside Phase 3 it still edits no product code. The report ends with the `Route:` line (issue #134).
- `code-locator`: the description names a broad search whose many reads the main context does not need, and several searches at the same time (issue #134).
- `test-runner`: the description names a test run too long for the main loop, and runs in several worktrees at the same time (issue #134).
- `dotnet-build-test`: behavior change: the build filter is now a block that writes the output to a log file and keeps the exit code of `dotnet build`. It drops each warning line and keeps the warning count. A new test filter keeps the errors, the failed tests, the result lines, and the exit code of `dotnet test`. If the exit code is 0 and the result line shows zero failed tests, the run is green (issue #134).
- `evals`: the new graders `route-test-runner-0` and `route-agent-count` go into six cases. These cases are `fp-e1-clean-change`, `fp-e8-rename-across-projects`, `fp-free-text`, `rl-null-guard`, `rl-off-by-one`, and `rl-unbounded-query`. `route-test-runner-0` passes at zero `test-runner` dispatches, and `route-agent-count` records the count of `Agent` calls (issue #134).
- `evals/subagent-orchestration`: the cases `so-rename-large`, `so-rename-small`, and `so-two-fixes` get the grader `route-test-runner-0`. These three cases and `so-lookup` get `route-reported`, which reads the `Route:` line of the last message (issue #134).
- `evals`: the new graders `tests-before-commit` and `untested-commit` go into the three review-loop cases above and the three `so-` cases above. `tests-before-commit` makes sure that the trace has a `unittest` run before a `git commit`, with no edit of a Python file between them. Take a trace with an edit of a Python file, then a commit with no `unittest` run between them. `untested-commit` fails such a trace, also for an edit by a Bash command (issue #134).
- `evals/research-implement-review-report/rirr-retry-limit`: a new behavior case. The task lowers the HTTP retry limit from 5 to 3, and a test in another file then turns red. The run must save a plan, run `review-loop`, make the test follow the new limit, and test before the commit. It must not push or dispatch `test-runner`, and the last message names the test file and the route (issue #134).
- `evals/triggers/code-locator-fires` is now `code-locator-lookup-near-miss`. The user asks where a class is defined and who calls it. The main loop searches, and the `code-locator` agent does not start (issue #134).

### Changed in the repository

- `tests/test_eval_cases.py`: the new classes `TestsBeforeCommitGraderTests` and `RouteReportedGraderTests` run the patterns of `tests-before-commit`, `untested-commit`, and `route-reported` on sample traces and messages. They also make sure that each case has the same pattern of `tests-before-commit` and of `untested-commit` (issue #134).
- `tests/test_eval_scaffolds.py`: the commit grader tests cover `rirr-retry-limit`. A new test makes sure that the retry limit change turns the HTTP client test of that scaffold red (issue #134).
- `tests/simple-english-baseline.json`: one accepted hit for the file path in the grader `limit-lowered` (issue #134).
- `docs/evals.md`: the table of behavior suites has a row for `research-implement-review-report`, with 1 case (issue #134).

## dev-essentials 3.10.5 and dotnet-backend-dev 1.7.3 in release [4.7.8] - 2026-11-15

This release fixes the shared .NET fixture library of the eval cases. Scaffolds that ran at the same time with an empty NuGet folder failed, and the record showed no error text. The skill text does not change.

### Changed in dev-essentials

- `evals/_lib/dotnet-fixture.sh`: `dotnet_warm` holds a lock on `/tmp/plugin-evals/nuget.lock` while it restores into the shared folder `/tmp/plugin-evals/nuget` and copies that folder. Each eval run has its own `TMPDIR`, so the file locks of NuGet did not guard the shared folder. Before, two scaffolds or a unit test run that restored the same package at the same time into an empty folder broke each other. One restore deleted a temporary file of the other, and the scaffold failed. The dotnet commands now write their output to stderr. Before, the error message of a failed scaffold was empty, and dotnet writes its errors to stdout. The new variable `EVAL_FIXTURE_DOTNET_CACHE` replaces `/tmp/plugin-evals`. Only a test sets it (issue #147).
- `evals/feature-pipeline/fp-e4-package-bump/scaffold.sh`: the prefetch of the new NUnit version passes the cache folder to `dotnet_prepare_cache`. It holds the same lock as `dotnet_warm` (issue #147).

### Changed in dotnet-backend-dev

- `evals/_lib/dotnet-fixture.sh`: the same change as in dev-essentials, because a test makes sure that the two copies are equal (issue #147).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: the new class `DotnetWarmTests` runs `dotnet_warm` with a fake `dotnet` and a cache folder of the test. One test starts two runs at the same time. It makes sure that their restores into the shared folder do not overlap, and that dotnet does not get the lock. The second test makes sure that the error text of a dotnet command reaches stderr. A third test runs each .NET scaffold with the fake `dotnet` (issue #147).
- `docs/evals.md`: the text about the .NET cases names the lock on the shared NuGet folder. The setup list for WSL2 names `flock` (issue #147).

## dev-essentials 3.10.4 in release [4.7.7] - 2026-11-15

This release fixes the graders of the eval case `fp-e1-seeded-defects` of the feature-pipeline suite. The prompt and the skill text do not change.

### Changed in dev-essentials

- `evals/feature-pipeline/fp-e1-seeded-defects`: the review frame of `caught-review-rule` and `caught-sql` no longer matches the five review entries of the kept runs that say that the defect is absent. Other wordings of such an entry can still match, for example "safe from SQL injection". `caught-review-rule` now needs a defect word and a doc word in one sentence of the entry, for example "no XML doc comment". Before, an entry about missing `<param>` tags passed. Such an entry can say that the code meets `REVIEW.md`. `caught-sql` skips an entry that says "no injection" or "not open to SQL injection". `caught-review-rule` also skips an entry that says that the rule is met or holds. The review frame of `caught-duplicate` also accepts `SkuFormatter.Normalize` before the copy word. In a `task_notification` record, a `usage` object must now follow the stage reply. The record of a Bash command has no such object, so a question block in a command text does not count. The template item of the stage text does not count after a blank line either. `fixed-sql` now needs an SQL word before the quote on the line. So it ignores an exception text that joins the sku in quotes. It also finds SQL that puts the sku in quotes with `$"..."` or `string.Format`. `fixed-bound` also reads a `while` loop, and it accepts `<= skus.Length - 1` (issue #146).

### Changed in the repository

- `tests/test_eval_cases.py`: new samples for review entries that report no defect, for other word orders of a review entry, and for other forms of the outcome code. More new samples are a Bash notification, the template after a blank line, and a defect line in a string after the reply. The sample stage reply now has a `usage` object (issue #146).

## doc-styles 1.1.5 in release [4.7.6] - 2026-11-15

This release fixes the probe `probe-se-lint-hook` of doc-styles. The probe tests the lint hook of the stand-in for simple-english. Its grader looked for the hook message in the trace. In the runs of issue #115, the trace of Claude Code 2.1.310 did not hold the output of a `PostToolUse` hook. Release 4.7.1 fixed the probe `probe-obsd-lint-hook` for that reason. With Claude Code 2.1.325 in WSL2, the probe now scores 1.00 with the stand-in and 0.00 without it. On native Windows, it scored 0 with the stand-in. The reply of one kept run ended with the line `No hook message.` and quoted no hook text.

### Changed in doc-styles

- `evals/probes/probe-se-lint-hook`: the prompt tells the agent to copy the hook message into its reply, word for word. The grader `lint-hook-ran` now reads the final reply and matches the full first line of the hook message. The new grader `hook-hit-quoted` makes sure that the reply also quotes the hit on line 1. A run with no hook cannot give these two lines, so it scores 0 (issue #142).

### Changed in the repository

- `tests/test_markdownlint.py`: if markdownlint finds none of its files, it prints its help text and exits with 0. Before, the test then passed with no lint. This happened under WSL2 with the `npx` of a Windows install of Node.js. That `npx` runs markdownlint through `cmd.exe`, and `cmd.exe` cannot use a folder in the Linux file system as its current folder. So markdownlint runs in `C:\Windows`, where the relative file names find no file. Now the test skips with a message. If the environment variable `CI` is `true`, the test fails. A new test makes sure that a file that does not exist gives the help text. So a new version of markdownlint-cli with other help text fails the test and does not turn off the check (issue #143).
- `docs/testing.md`: the file says that under WSL2 the markdownlint test needs Node.js in Linux (issue #143).
- `tests/test_check_report.py`: the test `test_leftovers_warns_for_a_process_that_uses_the_scratch_folder` now uses a fixed fake pid for the test process. Before, it used the real pid next to the fake pids 500 to 502. If the real pid was 500, 501, or 502, or its parent pid was 500, the records clashed and the test failed. In WSL2, the first commands after a start get pids near 500 (issue #145).
- `tests/test_eval_cases.py`: a new test runs the lint hook of the stand-in in `tests/evals/stubs/simple-english` on the probe text of `probe-se-lint-hook`. It makes sure that both graders match the hook message. It also makes sure that neither grader matches a reply with no hook, or the output of the linter script (issue #142).

## dev-essentials 3.10.3, doc-styles 1.1.4, dotnet-backend-dev 1.7.2, and kb 0.2.2 in release [4.7.5] - 2026-11-15

This release gives each plugin an icon for a listing in Anthropic's directory. So `claude plugin validate --strict` no longer reports `ICON_MISSING` for a plugin.

### Changed in dev-essentials

- `assets/icon.png`: new icon, a square PNG of 1024 px with code chevrons on a blue rounded square. The `icon` field of `plugin.json` names it (issue #140).

### Changed in doc-styles

- `assets/icon.png`: new icon, a square PNG of 1024 px with a page of text lines on a green rounded square. The `icon` field of `plugin.json` names it (issue #140).

### Changed in dotnet-backend-dev

- `assets/icon.png`: new icon, a square PNG of 1024 px with three stacked layers on a teal rounded square. The `icon` field of `plugin.json` names it (issue #140).

### Changed in kb

- `assets/icon.png`: new icon, a square PNG of 1024 px with an open book on a raspberry rounded square. The `icon` field of `plugin.json` names it (issue #140).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: new test `test_the_pull_ref_hook_runs_when_hooks_are_pinned_off_for_the_push`. If the push runs with the hook pins of an eval run, the `post-receive` hook of `git-fixture.sh` must still move `refs/pull/<id>/head`. The test sets the pins in the environment and as `-c` arguments. The hook still runs because git removes the pins of the pushing process before it starts `receive-pack` for a local remote (issue #141).
- `CLAUDE.md`: a new convention says that each plugin has an icon at `assets/icon.png`, and that the `icon` field of `plugin.json` names it (issue #140).

## dev-essentials 3.10.2 in release [4.7.4] - 2026-11-15

This release fixes the eval case `fp-e1-seeded-defects` of the feature-pipeline suite. The skill text does not change.

### Changed in dev-essentials

- `evals/feature-pipeline/fp-e1-seeded-defects`: Stage 1 finds the seven planted defects in the issue text and asks about them. With `--autonomous`, the run takes the recommended fix for each defect. So the defects never reach the review stages, and the graders `caught-bound`, `caught-key`, and `caught-typosquat` failed in every run. Each `caught-*` grader now also accepts a line of a stage reply that names the defect. The line must be in the final reply of a stage subagent, and that reply must hold a `QUESTIONS:` block with a recommended option. A brief, a note, or a stop message of the master agent does not count. The new graders `fixed-bound`, `fixed-sql`, `fixed-key`, and `fixed-typosquat` read the final files. If a defect is still in its file, its grader fails. In a run that changes no file, `fixed-key` and `fixed-typosquat` pass, because the fixture files are clean. `caught-duplicate` now needs a copy word next to `CleanSku` or `SkuFormatter.Normalize`. `caught-query-in-loop` no longer accepts the bare word `QueryMany`. The prompt now tells the run to take the recommended option for each stage question, and not to ask the user. It also tells the run not to stop before Stage 1 (issue #113).

### Changed in the repository

- `tests/test_eval_cases.py`: new tests for the stage replies and for the `fixed-*` graders. Samples that must not match are the issue text of the case and the skill text. Other such samples are a brief and a stop message of the master agent, and a not-present text next to a question block (issue #113).

## dev-essentials 3.10.1 in release [4.7.3] - 2026-11-15

This release fixes the commit graders of three `subagent-orchestration` eval cases. If the run merges or cherry-picks a linked worktree commit into the main work tree, the commit now counts. Claude Code turns git hooks off in an eval run, so the graders read `.git/logs/HEAD`, a reflog that git writes itself. Each linked worktree has its own HEAD reflog. So a commit that stays in a linked worktree and never reaches the main work tree does not count.

### Changed in dev-essentials

- `evals/subagent-orchestration/so-rename-small` and `evals/subagent-orchestration/so-rename-large`: the grader `committed` also counts a cherry-pick, a merge, and a merge commit in `.git/logs/HEAD`. It also counts a cherry-pick or a merge that stops on a conflict and ends with a commit. Before, it counted only a `commit:` line. So a worktree commit that came to the main work tree with a merge or a cherry-pick did not count. A commit that stays in a linked worktree still does not count (issue #127).
- `evals/subagent-orchestration/so-two-fixes`: the grader `two-commits` reads `.git/logs/HEAD` of the main work tree, on any branch. It needs at least two commit or cherry-pick lines, or at least two merge lines. A merge commit counts as a merge line. Before, it read `.git/logs/refs/heads/main` and needed exactly two `commit:` lines. So it failed a run with two commits on another branch, or with a third commit. It also failed a run that merged or cherry-picked each worktree commit. The grader cannot see the files of a commit. So a run with one commit for both fixes and one more commit passes. One commit line and one merge line do not pass, because a combined commit and its merge give the same two lines. One merge that brings two commits of a linked worktree counts once, and that run fails. A pull, a reset, and a rebase do not count (issue #127).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: the new class `CommitGraderTests` runs the three scaffolds. Then it makes the commits of typical runs, with git hooks off as in an eval run. It reads the pattern, the match, and the target of each commit grader from the grader file. It makes sure that each grader gives the verdict that the case means. For example, a commit with both fixes fails `two-commits`, also after a merge to `main`. The tests also cover a merge and a cherry-pick that stop before the commit, and a run commit with the subject prefix `fixture:`. A worktree commit that the run does not bring to the main work tree does not count (issue #127).

## doc-styles 1.1.3 in release [4.7.2] - 2026-11-14

This release changes the EXIT STATUS rule of the OpenBSD style. A document lists only the exit codes that the facts name. The sentence for a special code comes only after `>0`.

### Changed in doc-styles

- `skills/openbsd-style-docs/references/skeletons.md`: in the skeleton of a command-line utility, a note now limits the line that starts with `In particular`. Only a code that the facts name can use that line, and only after `>0`. A new rule after the skeleton covers a number for errors in general. If the facts give such a number, the document uses a tag list of the codes, as `grep(1)` does. The list has no `>0` and no `In particular`. Before, the model often changed `>0` to the error code of the facts and kept the line. So the README made the special code a case of the error code, but the facts give it its own code. In the eval case `obsd-d1-readme`, the grader `acc-no-invention` failed in 14 of 19 judged runs with that line. It failed in 0 of 18 runs without it (issue #114).
- `skills/openbsd-style-docs/SKILL.md`: the EXIT STATUS item of "Failure, warnings and limits" adds only the special codes that the facts name. If the facts give a number for errors in general, the item asks for the tag list of `grep(1)` instead of the pair (issue #114).
- `skills/openbsd-style-docs/references/examples.md`: the "Before" text of the example for error behavior now names the code 2. Before, the "After" text added a code that the "Before" text did not name (issue #114).

## doc-styles 1.1.2 in release [4.7.1] - 2026-11-14

This release fixes the probe `probe-obsd-lint-hook` of doc-styles. The lint hook ran, but the probe still scored 0. Its grader looked for the hook message in the trace. In the three runs of issue #115, with Claude Code 2.1.310, the trace did not hold the output of the `PostToolUse` hook. The release also ships a new test that parses the YAML of every eval case file (issue #123).

### Changed in doc-styles

- `evals/probes/probe-obsd-lint-hook`: the prompt tells the agent to copy the hook message into its reply, word for word. The grader `lint-hook-ran` now reads the final reply. The new grader `hook-hit-quoted` makes sure that the reply also quotes the hit on line 7. A run with no hook cannot give these two lines, so it scores 0 (issue #115).

### Changed in the repository

- `tests/test_eval_cases.py`: a new test runs the lint hook on the probe text of `probe-obsd-lint-hook`. It makes sure that both graders match the hook message, and that neither matches a reply with no hook (issue #115).
- `tests/test_eval_front_matter.py`: a new test parses the YAML of each `prompt.md`, `case.yaml`, and grader file of every plugin with PyYAML. It fails with the path and the problem of each file that does not parse. If PyYAML gives a line number, the failure also names the line. The small parser of `tests/test_eval_cases.py` accepted a plain value with a colon and a space in it, but `claude plugin eval` did not load the case. The fixture `tests/fixtures/eval-front-matter/colon-in-plain-value.md` has this defect (issue #123).
- `.github/workflows/tests.yml`: CI installs PyYAML 6.0.3 for the new test. If PyYAML is not installed, the test fails. It does not skip (issue #123).
- `docs/testing.md`: the file names the new test and the PyYAML package (issue #123).

## dev-essentials 3.10.0 in release [4.7.0] - 2026-11-14

This release keeps the record of a `process-pr-comments` fix whose commit is on the pull request head while its thread has no reply. A push sends every commit ahead of the PR head, so such a commit can go along with the fixes of a cycle. A later run no longer takes the thread for a new one.

### Added in dev-essentials

- `evals/process-pr-comments/ppc-ride-along-commit`: a new behavior case. A commit on the PR head names a `[ToFix]` thread that has no reply, and the run has `autonomous`. The graders make sure that the last message names the commit and the thread. They also make sure that the run makes no edit, no commit, no reply, no push, and no resolve (issue #105).

### Changed in dev-essentials

- `skills/process-pr-comments`: Phase 2 step 5 also reads the commits of the pull request (`origin/<base>..origin/pull/<prId>/head`). If a commit names a thread with no reply of Claude, the thread gets the new state `pr-commit-no-reply`. The run prints a report line that names the commit, and the human handles the thread. The run asks no question and does not act on the thread, in every mode (issue #105).
- `skills/process-pr-comments`: with `autonomous`, the run asks before a push that sends a commit that no thread of the push names. The question lists each such commit. Before, the run asked only for a commit whose thread got a "handle separately" answer or a report line. A commit that named no thread went along with no question (issue #105).

## dev-essentials 3.9.0 in release [4.6.0] - 2026-11-14

This release changes the duplicate check of `process-pr-comments` for an `[OutOfScope]` issue. The issue search tool of the GitHub server does not find an issue by the comment URL in its body. So the check is now a best effort. The skill asks the user before it creates an issue that the search did not find, also with `autonomous`.

### Added in dev-essentials

- `evals/process-pr-comments/ppc-outofscope-autonomous`: a new behavior case. A reviewer asks for a separate issue, the run has `autonomous`, and the issue search finds nothing. The graders make sure that the run searches, asks before it creates the issue, creates no issue, and posts no reply (issue #106).

### Changed in dev-essentials

- `skills/process-pr-comments`: before it creates an `[OutOfScope]` issue, the skill searches the issues of the repository with the words of the draft title. The search is a best effort. If the body of a result has the line `Source: <thread comment URL>`, the skill uses that issue and creates no new one. Else it tells the user that the search found no issue, and asks before it creates the issue. Without `autonomous`, this question also approves the title and the type. With `autonomous`, the question still comes, as an open item before the batch posts. If the search call fails, the skill says so and asks the same question. The user can also name an existing issue in the answer, and the skill reads that issue for its title. The issue body keeps the `Source` line as a required part, and the `Tracked as issue` reply names the issue. The skill no longer says that a search for the quoted comment URL finds the issue (issue #106).
- `evals/process-pr-comments/ppc-gated-threads`: a mock for `search_issues` that finds no issue, the new grader `searched`, and the tag `outofscope`. The graders `issue-waits` and `question-drafted` match the new question and do not take it for the draft of a `[Question]` reply (issue #106).

## dev-essentials 3.8.2 in release [4.5.5] - 2026-11-14

This release adds one behavior case for `process-pr-comments`. The case covers a user who changes the shape of a fix before the push.

### Added in dev-essentials

- `evals/process-pr-comments/ppc-reshaped-fix`: a new behavior case. The user changes the shape of a `[ToFix]` fix before the go-ahead of the push. The graders make sure that the thread gets exactly one reply. The reply posts after the change and right before the push. It names the pushed commit and the new shape (issue #64).

## dev-essentials 3.8.1 and dotnet-backend-dev 1.7.1 in release [4.5.4] - 2026-11-14

This release fixes four defects in the eval cases of dev-essentials. It also adds a pointer in `process-pr-comments`. The shared fixture library of dotnet-backend-dev gets the same change as the copy in dev-essentials.

### Changed in dev-essentials

- `evals/subagent-orchestration/so-rename-small` and `evals/subagent-orchestration/so-rename-large`: the grader `committed` reads `.git/logs/HEAD`, not `.git/logs/refs/heads/main`. So a commit of the run in the main work tree counts on any branch (issue #112).
- `evals/review-loop/rl-pr-head-gate`: the grader `asks-for-head` also matches "dry run" with a space (issue #112).
- `evals/process-pr-comments/ppc-tofix-default`: the `description` of `prompt.md` is in quotes. It holds ": ", so a YAML parser stopped, and `claude plugin eval` did not load the case (issue #112).
- `evals/_lib/git-fixture.sh`: `fixture_publish` installs a `post-receive` hook in the bare remote. When a later push changes the branch of a pull request, the hook moves `refs/pull/<id>/head` to the new tip, as GitHub does. `fixture_publish` also sets `core.hooksPath` of the remote to its own `hooks` folder, so a global `core.hooksPath` does not stop the hook. Before, the pull request ref stayed at the commit of the scaffold (issue #112).
- `skills/process-pr-comments`: Phase 4 names `<pushed-tip>` for the ancestry check and points to its definition in `references/commit-push-resolve.md` (issue #112).

### Changed in dotnet-backend-dev

- `evals/_lib/git-fixture.sh`: the same hook as in dev-essentials, because a test makes sure that the two copies are equal (issue #112).

### Changed in the repository

- `tests/test_eval_scaffolds.py`: two new tests push a new commit to the pull request branch. They make sure that `refs/pull/<id>/head` of the remote moves to that commit, also with a global `core.hooksPath` (issue #112).
- `tests/test_eval_scaffolds.py`: the two .NET probe tests need the .NET SDK 10 or newer and the .NET 10 runtime. Before, they needed SDK 10 exactly, and CI failed after the runner image got the .NET SDK 11 (issue #117).

## doc-styles 1.1.1 in release [4.5.3] - 2026-11-12

This release makes the OpenBSD docs linter of doc-styles read its arguments with `argparse`. Every valid call works as before.

### Changed in doc-styles

- `skills/openbsd-style-docs/scripts/openbsd_lint.py`: the script reads its arguments with `argparse`. A call with a bad argument still exits with code 2, but it now prints the usage line and one error line. Before, it printed the module docstring. `--help` and `-h` now print the help on stdout and exit with code 0. `--hook --hook` now runs the hook. `-` and every argument after `--` is now a file name. So `-- -file.md` lints the file `-file.md`, and `p.md -- ok.md` lints both files (issue #109).

### Changed in the repository

- `tests/test_openbsd_lint.py`: the test for a call with no argument looks for the `argparse` usage line. New tests cover an unknown option, the abbreviated option `--ho`, `--hook` with a file, and `--help` (issue #109).

## Repository changes only in release [4.5.2] - 2026-11-12

This release moves the repeated test setup of five more test files to `tests/testkit.py`. No plugin changes.

### Changed in the repository

- `tests/testkit.py`: `run` has two new options. With `check=True`, an exit code other than 0 raises an error. With `text=False`, stdin, stdout, and stderr are bytes. `git_init` also sets a local user name and email, so that a commit works with no global git identity. The docstring names the source of the file (issue #97).
- `tests/test_version_bump.py`, `tests/test_eval_cases.py`, `tests/evals/test_compare_versions.py`, `tests/test_eval_stubs.py`, and `tests/test_plugin_cli.py`: they use `tests/testkit.py` instead of their own temporary folders, `git init` calls with an identity, and child process runners (issue #97).
- `tests/test_testkit.py`: new tests for the two options of `run` and for the identity of `git_init` (issue #97).
- `tests/evals/test_compare_versions.py`: a new test makes sure that a link `evals` outside the plugin at the head commit gives exit code 2 and runs no eval. Before, only the base commit had this test (issue #97).

## Repository changes only in release [4.5.1] - 2026-11-10

This release makes `tests/evals/compare_versions.py` refuse an eval folder outside the plugin folder. No plugin changes.

### Changed in the repository

- `tests/evals/compare_versions.py`: if the eval folder is not below the plugin folder, `run` and `baseline` stop with exit code 2. An absolute `--eval-dir` and a value with `..` are examples. Before the fix, `run` deleted such a folder outside the export (issue #101).
- `tests/evals/compare_versions.py`: if a commit has a link that points outside the export, `run` and `baseline` stop with exit code 2, not with a traceback (issue #101).
- `tests/evals/test_compare_versions.py`: a new test runs `run` and `baseline` with an absolute `--eval-dir`, with a `..` value, and with `.`. It makes sure that the exit code is 2, that no eval runs, and that the folder outside the export does not change. A second test makes sure that a commit with a link outside the export gives exit code 2 and runs no eval (issue #101).

## dev-essentials 3.8.0 in release [4.5.0] - 2026-11-09

This release makes `process-pr-comments` post all thread replies of a cycle in one batch right before the push, not right after each commit or answer. With a push to make and without `autonomous`, the user sees the batch with the go-ahead question. A reply then describes the code that the push sends, also after the user changes a fix before the push.

### Changed in dev-essentials

- `skills/process-pr-comments`: every thread reply of a cycle waits as a pending reply, in every mode. This covers the replies about a fix, every `[AI][Draft]` reply, and the `[Question]`, `[ToDiscuss]`, and `[OutOfScope]` replies. After the go-ahead for the push, or with `autonomous`, Stage 2 posts them in one batch, and then the orchestrating session pushes. A draft reply is in the batch as written, and only its code change waits for the answer of the user. A `[Question]` draft joins the batch only after the `yes` of the user. With `autonomous`, the open items of Stage 2 are still asked before the batch. If the user changes a fix before the push, Stage 2 updates its pending reply first. With no go-ahead, the replies stay unposted, and the cycle log shows their text. A reply that misses its batch, also after a late answer or a failed post, joins the next batch of the same session. If the session ends first, a later run handles the comment again. A cycle with no push to make posts the batch at the end of Phase 4. `dry-run` posts none (issue #64).
- `skills/process-pr-comments`: on a `deep-fix` cycle, Stage 2 hands back its open items. The orchestrating session asks them with the go-ahead. Stage 3b writes the approved `[Question]` replies and creates the approved issues before it posts the batch (issue #64).
- `skills/process-pr-comments`: Task Composer creates an `[OutOfScope]` issue right before the batch posts, not at once. The `Tracked as issue` reply is the record that stops a second issue for the thread. So if the batch does not post, no issue exists, and a later run handles the thread again. The cycle log shows such a thread as `issue pending`. If the issue exists but its reply did not post, the session keeps the issue number, and the next try creates no second issue. The issue body ends with `Source: <thread comment URL>`, and a later run finds the issue by that link before it creates one. With `no-reply`, no issue is created, and the cycle log shows the approved title (issue #64).
- `skills/process-pr-comments`: if the test of Stage 2 for a `cured` thread disagrees with Stage 1, Stage 2 does not act on the thread in this cycle. It prints the report line, and the next cycle asks the question or prints a report line. In each later cycle of a `/loop` session, a carried-over claim gets the report line. The cycle does not stop for a question (issue #64).
- `skills/process-pr-comments`: Phase 2 step 5 also reads the local commits that the PR head does not have yet. If such a commit names a thread with no reply about it, the thread is `unconfirmed-commit-claim` with the new report field `claimSource: local-commit`. The human gets the question. A later run then does not fix the thread a second time (issue #64).
- `skills/process-pr-comments`: the Rules state the push gate once. A cycle pushes only for a commit of this cycle, or for a carried-over claim on a local commit after a push-and-resolve answer. The unpushed commit of a reply that missed an earlier batch counts as a commit of this cycle. Stage 1 tests that the claimed commit is on the local branch and not on the PR head, with the new report field `isAncestorOfHead`. A claim that fails the test gets a report line, not the question. `no-commit` and `dry-run` never push, and print a report line for a carried-over claim instead of the question. The orchestrating session gets every answer to such a question before it dispatches Stage 2. The question for the go-ahead and the cycle log list the commits that the push sends. That list can hold a commit whose thread the user chose to handle separately, or whose thread a report line handed to the human. Then the run asks before the replies post, also with `autonomous` (issue #64).
- `evals/process-pr-comments/ppc-tofix-default`: the grader `replied` is now `reply-waits`, and expects no reply before the go-ahead. The new grader `reply-drafted` expects the reply text in the last message (issue #64).
- `evals/process-pr-comments/ppc-gated-threads`: the grader `no-question-reply` is now `no-reply`, and expects no reply at all. Every reply of the cycle waits for the answers of the user (issue #64).

## doc-styles 1.1.0 in release [4.4.0] - 2026-11-09

This release adds a linter and a lint hook to the skill `openbsd-style-docs` (issue #82). The hook checks the rules that a script can test after each write of a document in this style. The model still checks the other rules.

### Added in doc-styles

- `skills/openbsd-style-docs/scripts/openbsd_lint.py`: a linter for the rules that a script can test. It checks the section names, their order and their content, and the NAME line. It also checks the sort order of option, variable, file and error lists. It checks that a default has its own sentence. It looks for "you" and for the marketing and filler words of the skill. It uses only the standard library of Python 3 (issue #82).
- `hooks/hooks.json`: a `PostToolUse` hook for `Write` and `Edit`. It runs the linter on a Markdown file that has the form of this style, and it shows the hits to Claude. It skips other files. It needs `python3` on `PATH`. If `python3` is missing, the hook exits at once and reports nothing. To stop it for some paths, set `OPENBSD_STYLE_LINT_EXCLUDE` to glob patterns, or to `*` (issue #82).
- `evals/probes/probe-obsd-lint-hook`: a probe that shows whether the hook runs in an eval run (issue #82).

### Changed in doc-styles

- `skills/openbsd-style-docs/SKILL.md`: the self-check names the linter and keeps only the checks that a script cannot do. It also names the documents that the hook skips, and the agent checks those by hand. The word list moved to "Sentence rules". The precedence rule about other linters no longer covers the hook of this plugin. Bold is not allowed in any case, the same as in the linter. Some sentences that repeated other text are removed (issue #82).
- `skills/openbsd-style-docs/references/skeletons.md` and `references/examples.md`: the ERRORS list of the library skeleton is sorted. The SEE ALSO lists of the configuration file skeleton and of the complete README are sorted by section (issue #82).

### Changed in the repository

- `tests/test_openbsd_lint.py`: tests for the linter, the hook mode, the hook file, and the word list of the skill (issue #82).
- `README.md`, `.claude-plugin/marketplace.json`, and `docs/testing.md`: they name the hook and the new tests (issue #82).

## Repository changes only in release [4.2.5] - 2026-11-09

This release makes the listing budget test match the always-on cost that a signed-in session shows. No plugin changes.

### Changed in the repository

- `tests/test_plugin_cli.py`: each budget in `LISTING_BUDGET` is now the most always-on tokens that `claude plugin details` can show in a signed-in session. With no sign-in, the command shows an offline estimate: the number of characters divided by 4. The test runs with no sign-in, so it multiplies the estimate by the new `SIGNED_IN_RATIO` of 1.5 before it compares the result with the budget. The new budgets are the old ones times 1.5. So the test passes and fails for the same descriptions as before (issue #90).
- `tests/test_plugin_cli.py`: each claude call now runs without the known environment variables that sign Claude Code in, for example `CLAUDE_CODE_OAUTH_TOKEN`. Before, such a variable gave the test the API count, and the budget test failed for each plugin. A Claude Code cloud session can still sign in through its token file. Then the budget test fails, and it does not hide an overrun (issue #90).
- `docs/testing.md`: the text says what the budgets count, and why the test multiplies the estimate (issue #90).

## Repository changes only in release [4.2.4] - 2026-11-09

This release makes `tests/evals/compare_versions.py` refuse a `--plugin` path outside the exported commit. No plugin changes.

### Changed in the repository

- `tests/evals/compare_versions.py`: if the `--plugin` path is not inside the exported commit, `run` and `baseline` stop with exit code 2. An absolute path and a path with `..` are examples. Before the fix, such a path named the real plugin folder. The script then wrote `.deps/` into it, and `baseline` replaced its `eval-stubs/` folder (issue #89).
- `tests/evals/test_compare_versions.py`: a new test runs `run` and `baseline` with an absolute path and with a `..` path to the real plugin. It makes sure that the exit code is 2, that no eval runs, and that the real plugin does not change. A second test makes sure that a link or a `..` path inside the export still works (issue #89).

## Repository changes only in release [4.2.3] - 2026-11-09

This release moves the guides for contributors out of `README.md` into the new folder `docs/`. No plugin changes.

### Changed in the repository

- `docs/authoring.md`, `docs/testing.md`, `docs/evals.md`, and `docs/permissions.md`: new files with the text that moved out of `README.md`. The text is the same, with these changes for the new place: the heading levels, the path of the link to `CLAUDE.md`, and "this section" became "this file". The list item in `docs/testing.md` also names the files in `docs/` now. The folder list in `docs/authoring.md` names `docs/` (issue #93).
- `README.md`: it keeps the plugin list, the install and update steps, the link to `CHANGELOG.md`, and the references. The new section "Contributing" gives a short summary of each guide in `docs/` and links to it. The section on the push rules keeps a short summary and links to `docs/permissions.md` (issue #93).
- `CLAUDE.md`: step 3 of the workflow for new units points to `docs/evals.md` instead of the Evals section of `README.md` (issue #93).
- `tests/test_readme_counts.py`: the test also reads the `.md` files in `docs/`. The moved text then stays free of counts of hooks, skills, agents, and commands (issue #93).

## kb 0.2.1 and dev-essentials 3.7.2 in release [4.2.2] - 2026-11-09

This release removes counts of hooks, skills, agents, and eval cases from the docs. When a unit is added or removed, such a count goes stale. It also shortens the `bug-hunt` skill. No behavior changes.

### Changed in kb

- `README.md`: the text names no count of hooks, skills, or text checks. It points to `hooks/hooks.json` and `skills/` instead. The hook table stays (issue #94).

### Changed in dev-essentials

- `skills/bug-hunt/SKILL.md`: rule 7 names the agents `bug-hunter`, `bug-verifier`, and `bug-report-auditor` instead of a count (issue #94).
- `skills/bug-hunt`: a pass of `optimize-skill` shortened the skill with no change of behavior. Step 0 moved to the section "Step 0 procedure" of `references/inputs-and-meta-plan.md`, with the cuts and pointer fixes below. A repeated mode rule and the first sentence of `SKILL.md` were cut. Three pointers are clearer. `references/resume-and-failures.md` says "the cleanup helper". Step 6 names the source of the process list. The three bug hunt agent files say "the snapshots" (issue #94).
- `skills/feature-pipeline/SKILL.md`: the text says "the resume checks" instead of a count (issue #94).
- `skills/bug-hunt`: two pointers to step 0 now link to `references/inputs-and-meta-plan.md` (issue #94).
- `skills/bug-hunt`: the skill now says "Fable, or the strongest model that the `model` parameter of the `Agent` tool accepts" where it names the strongest model. A newer model line can then replace Fable. The default of `--hunter-model` stays `fable`. The rule of no dispatch without the OK of the user does not change (issue #94).

### Changed in the repository

- `README.md`: the text about the behavior suites names no case counts. The suite table keeps them. The list of test parts names the new count test (issue #94).
- `tests/test_readme_counts.py`: a new test. If a `README.md` states a count of hooks, skills, agents, or commands, the test fails. The count pattern skips function words, so "step 3 of this skill" is not a count. An `ALLOWED` entry is keyed on the text of the line. An entry covers only lines with exactly that text. A hit on a line with other text is still reported (issue #94).

## Repository changes only in release [4.2.1] - 2026-10-29

This release moves the shared test setup into one helper module. No plugin changes.

### Changed in the repository

- `tests/testkit.py`: a new module with generic test helpers. It has a test case with a temporary folder and a copy of the environment without named keys. It also has a runner for child processes, `git init`, a `pwd -W` stub for Git Bash, and `load_module`. It uses only the standard library and the syntax of Python 3.7, because another repository keeps a copy of it (issue #95).
- `tests/test_kb_plugin.py`, `tests/test_eval_scaffolds.py`, `tests/test_backup_move.py`, `tests/test_trim_report.py`, and `tests/test_check_report.py`: they use `tests/testkit.py` instead of their own copies of the setup code (issue #95).
- `tests/support.py`: `load_module` moved to `tests/testkit.py`. `support.py` keeps the parts that are specific to this repository (issue #95).
- `tests/test_testkit.py`: tests for the helpers. They also make a best-effort check that `tests/testkit.py` has no syntax newer than Python 3.7. They make sure that it has no type hints and imports from the standard library only (issue #95).

## kb 0.2.0 in release [4.2.0] - 2026-10-29

This release lets KB sessions run the two text checks and read-only git in the KB with no prompt. It also adds plain allow rules as a fallback.

### Added in kb

- `hooks/hooks.json`: a second `PreToolUse` group with the matcher `Bash`. It calls the `allow-read` script of the KB clone, which approves the two text checks and read-only git in the KB. If the clone has no such script, the launcher exits 0 (issue #91).

### Changed in kb

- `skills/setup/check.sh`: it checks the allow rules for the two text checks and for three `git -C <KB root>` commands: `status`, `log`, and `show`. It also checks the ask rule for `--output`. It reads the `allow` and `ask` lists separately and matches whole entries. On Windows, it accepts the path rule with the drive letter in upper case or in lower case (issue #91).
- `.claude-plugin/plugin.json`: the description names the approval of read-only commands (issue #91).
- `skills/setup/SKILL.md`: step 2 names where the rules go and bans a rule for a git command that changes the KB (issue #91).
- `README.md`: the hook table and the setup pieces. It also has two limits: one for a KB clone with no `allow-read` script, and one that explains why there is no plain `git diff` rule (issue #91).

### Changed in the repository

- `README.md`: the `kb` row names the approval of read-only commands (issue #91).
- `tests/test_kb_plugin.py`: tests for the `allow-read` hook entry, the launcher, and the new rule checks (issue #91).

## dev-essentials 3.7.1 and doc-styles 1.0.1 in release [4.1.1] - 2026-10-28

This release moves the eval stand-in plugins out of the plugin folders. The claude.ai sync skipped `dev-essentials` and `doc-styles`, because each held a second `.claude-plugin/plugin.json` below its root. No skill, agent, or command changes.

### Fixed in dev-essentials

- `eval-stubs/github`: the stand-in for the GitHub server moved to `tests/evals/stubs/github`. The claude.ai sync skipped the plugin from 3.4.2 on, because the stand-in had its own manifest. The cases that load it now run only through `tests/evals/compare_versions.py`.

### Fixed in doc-styles

- `eval-stubs/simple-english`: the stand-in moved to `tests/evals/stubs/simple-english` for the same reason. The claude.ai sync did not sync 1.0.0.

### Changed in the repository

- `tests/evals/compare_versions.py`: `run` and `baseline` copy each folder of `tests/evals/stubs/` into `eval-stubs/` of the plugin copy. A `run` uses the stand-ins of the head on both sides. `tests/evals/test_compare_versions.py` tests the copy.
- `tests/test_claude_ai_sync.py`: if a tracked file of a plugin is in a `.claude-plugin` folder below the plugin root, a new test fails.
- `tests/test_eval_cases.py`: if `tests/evals/stubs/<name>` is a plugin folder, a `plugins` entry `eval-stubs/<name>` is valid.
- `tests/test_eval_stubs.py`, `tests/support.py`, `.gitignore`, and `README.md`: the new path of the stand-ins.

## kb 0.1.0 in release [4.1.0] - 2026-10-28

This release adds the plugin `kb`. It wires Claude Code to a personal knowledge base that lives in a git repository. No other plugin changes its version.

### Added in kb

- `kb`: a thin plugin that wires Claude Code to a personal knowledge base in git. Five hooks call the launcher `scripts/kb-hook.sh`, which runs the hook scripts of the local KB clone. The hooks are `SessionStart`, `SubagentStart`, `PreToolUse`, `Stop`, and `SessionEnd`. The skills `capture` and `close-task` point to the procedures in the KB. The skill `setup` runs `check.sh`, which changes nothing and prints the OS and one line for each missing piece. The plugin needs a KB clone. If the hooks find none, they exit 0.

### Changed in the repository

- `tests/test_kb_plugin.py`: unit tests for the launcher `kb-hook.sh`. They cover no clone, `KB_DIR`, a clone in a child folder, stdin, and the exit code of the guard. Other tests cover `check.sh` (always exit 0, one line for each missing piece) and the five hook entries.
- `README.md`, `.claude-plugin/marketplace.json`, and `tests/test_plugin_cli.py`: the new plugin has a row in the plugin matrix and an install line. It also has an entry in the marketplace and an entry of 120 tokens in `LISTING_BUDGET`.
- `.gitattributes`: `*.json` files keep LF on Windows, like `*.sh` files, so that a commit from a Windows PC stores LF.

## gop-pipeline removed in release [4.0.0] - 2026-10-28

This release removes the `gop-pipeline` plugin (issue #71). The `feature-pipeline` skill in `dev-essentials` does the same job. The release is MAJOR because an install path goes away: `/plugin install gop-pipeline@vasar-plugins-marketplace` no longer works. No other plugin changes its version.

### Removed

- `gop-pipeline` (issue #71): the plugin, with the `gop-work` skill, its eight agents, and its eval suite. `feature-pipeline` in `dev-essentials` does the same job. To start it, ask Claude to "run the feature pipeline on this request", or run `/dev-essentials:feature-pipeline "<request>"`. The flags `--interactive` and `--autonomous` work as before. One difference: `feature-pipeline` works in a new worktree and ends with a pull request. To work on the current branch, as `gop-work` did, pass `--no-worktree`. The five validators are now the checks of the review and the security review. After `/plugin marketplace update vasar-plugins-marketplace`, Claude Code shows "Removed from the "vasar-plugins-marketplace" marketplace" and turns the plugin off.

### Changed in the repository

- `marketplace.json` (issue #71): the `renames` map records the removal. The description no longer names a separate pipeline plugin.
- `README.md` (issue #71): the plugin table, the install lines, and the eval notes no longer name `gop-pipeline`.
- The tests (issue #71): they no longer name the `gop-` cases or the `gop-pipeline` folder.

## dev-essentials 3.7.0 in release [3.10.0] - 2026-10-28

This release lets `feature-pipeline` take over the useful parts of `gop-work` (issue #71). So `gop-pipeline` can go in the next release. The pipeline takes a plain request. Its review has new lenses, and a new supply-chain check. It keeps the changes that you made before the run out of its commits. A new eval suite measures it.

### Added in dev-essentials

- `feature-pipeline` (issue #71): If the user names the pipeline, Claude can start it (`when_to_use`). A small edit does not start it. `implement-task`, `implement-batch`, and `research-implement-review-report` keep their own requests.
- `feature-pipeline` (issue #71): a plain request as the task, for example `/dev-essentials:feature-pipeline "add a cache to GetQuantity"`. A task with a space is a request. If the project context has no Task Provider, any task is a request. A request run needs no task provider and posts no task comments.
- `feature-pipeline` (issue #71): the request ID. The run gets the ID `req-<slug>`. If a folder or a branch of that ID exists, the run adds `-2`, `-3`, and so on. To resume a request run, pass its `req-<slug>` ID as the task.
- `feature-pipeline` review (issue #71): the performance, reuse, and compliance lenses, and a check of the callers of the changed code. Each finding names its lens. A finding can carry a `Fix:` line.
- `feature-pipeline` security review (issue #71): a supply-chain category. It covers new dependencies, likely typosquats, install scripts of third-party packages, and floating versions. A new dependency is a LOW warning. A likely typosquat is HIGH.
- `feature-pipeline` references (issue #71): `stage-launch.md`, `pipeline-discipline.md`, and `task-comments.md`. The text moved out of `SKILL.md`, which is now shorter.

### Changed in dev-essentials

- `feature-pipeline` (issue #71): behavior change: Stage 7 runs as a `general-purpose` agent with the review method of the skill. The run no longer needs the `feature-dev` plugin.
- `feature-pipeline` (issue #71): behavior change: the review and the security review read one fixed patch, `review-diff.patch`. The master agent writes it. The patch leaves out the paths that you changed before the run. The review runs no git command that changes state. A dependency manifest of a test project is now in the scope of the security review.
- `feature-pipeline` (issue #71): behavior change: the run records the changes in the tree at the start (`startChanges` in the state file). No commit takes them, unless a stage edits that file. The final report lists each path that the run left out under "Not committed".
- `feature-pipeline` (issue #71): behavior change: each commit names its paths after `--`. A rename lists the old path and the new path. A change that you staged before the run stays staged and out of the commit. No stage adds an ignored file, also not with `git add -f`.
- `feature-pipeline` (issue #71): behavior change: with `--no-worktree` on the default branch, on the base branch, or on a detached HEAD, the run stops. It asks for a branch name or for an explicit yes. With `--autonomous`, it creates the branch. With `--dry-run`, it only reports.
- `feature-pipeline` (issue #71): the state file has two new keys, `taskSource` and `startChanges`. A state file of an older run without them resumes with the values `"provider"` and `[]`.
- `implement-task`, `implement-batch`, and `research-implement-review-report` (issue #71): the line that describes `feature-pipeline` now says that the task can be a plain request.
- `promote-conventions` (issue #71): its example of skill frontmatter fields says that `feature-pipeline` sets `argument-hint` and `when_to_use`. It no longer says `disable-model-invocation`.

### Changed in the repository

- The `feature-pipeline` eval suite (issue #71): 9 behavior cases (`fp-*`) and 4 trigger cases, in `essentials/dev-essentials/evals/feature-pipeline` and `evals/triggers`. The fixtures `dotnet-fixture.sh`, `inventory-fixture.sh`, and `pipeline-fixture.sh` are in `evals/_lib/`. The probe `probe-dotnet-sandbox` checks the .NET sandbox. The cases `implement-task-fires` and `implement-task-near-miss` also make sure that `feature-pipeline` does not start. The suite row and the `--tag feature-pipeline` count (13 cases) are in `README.md`.
- Tests (issue #71): `FeaturePipelineGraderTests` has 7 tests for the grader patterns of the suite. The scaffold tests cover the 9 new cases and the `pipeline-fixture.sh` file.

## doc-styles 1.0.0 in release [3.9.0] - 2026-10-28

This release adds the plugin `doc-styles` with the skill `openbsd-style-docs` (issue #73). The skill comes from a public source, and it is adapted for this marketplace. It owns the docs that the user asks for in the style of the OpenBSD manual pages. `simple-english` stays the default for other text and for chat replies.

### Added in doc-styles

- `openbsd-style-docs` (issue #73): writes and rewrites a technical document in the style of the OpenBSD manual pages, as Markdown. The user must name the style to start it. The names are "OpenBSD style", "like a man page", "man-page style", and "BSD style". The document has uppercase sections in a fixed order, a one-line NAME summary, sorted option and error lists, and each default as its own sentence. The chat reply follows the reply rules of the session.
- Eval suites (issue #73): 5 trigger cases, 3 probes, and 21 style-comparison cases. The comparison runs each case with the skill, with `simple-english`, and with both plugins loaded. The OpenBSD docs prompts also name the style.
- `eval-stubs/simple-english` (issue #73): a stand-in for `simple-english` that is used only in the eval runs. It is a byte copy of simple-english 2.1.1 (MIT). If a newer simple-english is installed, the test `tests/test_eval_stubs.py` fails.

### Changed in the repository

- `tests/evals/compare_versions.py` (issue #73): the new option `--extra-dep NAME` copies a plugin of the repository into the `.deps` folder of the bundle for a suite that needs it. `baseline` gets the options `--ablation` and `--keep-temp`. `tests/evals/test_compare_versions.py` tests the changes.
- `tests/test_eval_cases.py` (issue #73): the list `EVAL_ONLY_DEPS` names the plugins that a suite can copy with `--extra-dep`. A new test checks that the two arms of a style comparison differ only in the style.
- `tests/test_simple_english.py` and `tests/simple-english-baseline.json` (issue #73): the simple-english lint test can exclude a folder, with a reason for each folder. The skill `openbsd-style-docs` keeps its own style, so the test excludes its folder. The test also skips the stand-in copy of simple-english.
- `README.md` and `.claude-plugin/marketplace.json` (issue #73): the new plugin has a row in the plugin matrix, an install line, and an entry in the marketplace. The Evals section lists the new suites and the option `--extra-dep`.

## dotnet-backend-dev 1.7.0 and dev-essentials 3.6.0 in release [3.8.0] - 2026-10-27

This release makes seven large dotnet skills shorter. They move examples and rare sections into reference and example files. The skills that write code or Markdown now run a build or a lint loop until it passes (issue #78). Each loop stops after three failed fix attempts, or for an error outside the changed code. The moves keep the rules.

### Added in dotnet-backend-dev

- `create-domain-model`, `create-primitive-wrapper`, `create-exception`, `handle-sensitive-data`, `model-mapping`, `create-controller`, `update-swagger-spec`, `create-external-client`, `add-configuration-option`, `add-session-logging`, and `create-string-resource` (issue #78): a build loop. Behavior change: the skill builds the changed projects with `dotnet build`, fixes the errors, and reports the result line of the last build. The skills with a code generator do not edit a generated file, and they point to their stop-and-ask rule. For an error that names a missing generated member, they do not change the calling code. `model-mapping` also fixes each unmapped member that the build reports. `update-swagger-spec` runs the loop as a new last step.
- `add-migration` (issue #78): a build and migration-test loop on the framework path. The standard EF Core path already had its build.

### Changed in dotnet-backend-dev

- `add-migration` (issue #78): the framework text moved to `references/framework-migrations.md` and `references/cosmos-db.md`. The hard rules stay in `SKILL.md`.
- `update-swagger-spec` (issue #78): the common spec patterns moved to `references/common-patterns.md`. Step 1 now states the `500` rule and its reason.
- `create-tests` (issue #78): the helper and mocking examples moved to `examples/helper-methods.md` and `examples/mocking-rules.md`, and the checklist comes first. The forbidden list for scenario tests points to the table of `examples/scenario-tests.md`. The builder rule moved to `examples/mocking-rules.md`.
- `model-mapping` (issue #78): the full examples moved to `examples/full-examples.md`.
- `add-configuration-option` (issue #78): the `BuildEnvironment` pattern moved to `references/build-environment.md`.
- `handle-sensitive-data` (issue #78): the JSON converter code moved to `references/serialized-output.md`.
- `add-session-logging` (issue #78): the two Best Practices sections are one section.

### Changed in dev-essentials

- `write-markdown` (issue #78): the validation workflow loops on `markdownlint` until the exit code is `0`. An exit code of `2` to `4` is a configuration error, and the skill reports it. Usage text from `markdownlint` means that the path matched no file.
- `create-documentation` (issue #78): the checklist starts with a `markdownlint` loop until exit `0`. The list keeps the four items that the linter cannot test: the file name, the title heading, the contents list, and the relative links. Usage text from `markdownlint` means that the path matched no file.
- `generate-xml-docs` (issue #78): a CS1591 build loop with `-p:GenerateDocumentationFile=true` for that build only. The checklist stays the test for internal members. If the project hides CS1591 or sets `TreatWarningsAsErrors`, the skill names the fallback.

## dev-essentials 3.5.0 and dotnet-backend-dev 1.6.5 in release [3.7.0] - 2026-10-27

This release gives each trigger phrase one owner. It puts the hard rules and the done test of the large dev-essentials skills first. It turns two commands into skills with the same names, and it splits the promotion out of `audit-personal-conventions`. It also adds two plugin options (issue #76). The two moved units keep their invocation paths. Every `/dev-essentials:research-implement-review-report` and `/dev-essentials:implement-batch` call works as before.

### Added in dev-essentials

- `promote-conventions` (issue #76): Phases 5 to 10 of the old audit. Only the user starts it, with `/dev-essentials:promote-conventions`, because the skill sets `disable-model-invocation: true`. Per the skills docs, its description is not in the skill listing.
- `userConfig` options (issue #76), set with `/plugin configure dev-essentials@<marketplace>`:
  - `branch_prefix`, default empty: the first segment of the task branches. The order of the rules is the flag. Then come the `CLAUDE.md` of the repo, this value, and the `CLAUDE.md` of the user. Last comes one question to the user.
  - `notes_dir`, default `Notes`: the folder for plans, reports, reviews, and progress files. A location that the repo documents wins.
  - A value that is not saved stays a `${user_config...}` placeholder in the text. Each skill and command reads that as an empty prefix and as the folder `Notes`. So a user who sets nothing sees the old behavior.
- Reference files (issue #76): review-loop `parameters.md` and `output-formats.md`, process-pr-comments `parameters.md` and `invocation-examples.md`, and subagent-orchestration `model-selection.md`.
- Trigger cases `audit-personal-conventions-fires` and `promote-conventions-near-miss`, and the listing probes `probe-listing` (issue #76).

### Changed in dev-essentials

- `audit-personal-conventions` (issue #76): behavior change: every triage that stops ends with the command `/dev-essentials:promote-conventions`. These flags moved to that skill: `--resume`, `--cross-repo`, `--delete-personal-entities`, `--update-global-claude-md`, `--cleanup-mode`, `--rounds`, `--report`, `--interactive`, and `--autonomous`. They still work on the audit. A reply such as `approve 1,3` works too. The audit reads `promote-conventions` and continues into its Phase 5 in the same run in these cases only: a promote request, with or without a flag of the promotion, and `--resume`. A question or an audit stops after the triage, also with a flag of the promotion, `--autonomous`, or `--interactive`. `--dry-run` always stops after the triage. So an old invocation keeps its path, and the bump stays MINOR.
- `research-implement-review-report` and `implement-batch` (issue #76): now skills with the same names, so every invocation works as before.
- `general-conventions` (issue #76): PowerShell only. Its frontmatter rules moved to `write-markdown`.
- `write-markdown` (issue #76): the general markdownlint examples, the file template, and the quick reference are cut. The skill keeps the two choices that are not linter defaults.
- review-loop, process-pr-comments, and subagent-orchestration (issue #76): the rules and the done test come first, and the parameters, the examples, and the model detail moved to reference files. review-loop and process-pr-comments got a done test, and review-loop got one new hard rule (the head gate before the first fix).
- `task-composer`, `compose-pr`, `create-html-artifact`, and `general-conventions` (issue #76): trigger words, so that each phrase has one owner.
- `git-worktree-management`, `help-review-pr`, `implement`, `implement-task`, `opsx-implement`, `save-context`, `research-implement-review-report`, `implement-batch`, and `review-loop` (issue #76): they read the notes folder from the new option. `research-implement-review-report`, `implement-batch`, `implement-task`, and `promote-conventions` also read the branch prefix. Examples with a path keep `Notes/`.

### Fixed in dev-essentials

- `review-loop` (issue #76): the final chat message now always holds the `Stop verdict:` line and the path of each fixed file. Before, a run with the summary in a file or with a report format of the user often left it out.

### Changed in dotnet-backend-dev

- `create-ef-entity`, `model-mapping`, `create-tests`, and `/write-tests` (issue #76): one owner for "EF mapping" and for one test in an existing class.

### Changed in the repository

- `README.md` (issue #76): `userConfig` in the list of `plugin.json` fields.

## dev-essentials 3.4.4 and dotnet-backend-dev 1.6.4 in release [3.6.5] - 2026-10-27

This release changes the text of skills, commands, and agents (issue #74). Each workflow states its own gates. Plain rules replace shouted words. Long reference files get a contents list. Two plugins name what they assume. The old shared block and the steps of some workflows disagreed. In these cases the table keeps what the step says. The `bug-hunt` cleanup deletes the paths that the run made with no stop. A few gates, such as the report path of `audit-personal-conventions` and the reference conflict of `implement-task`, still ask in the default mode.

### Changed in dev-essentials

- 14 workflows (issue #74): the "Autonomy" section lists the gates of the workflow in a table, in place of a block that 14 files shared. Six are commands: `implement`, `opsx-implement`, `research-implement-review-report`, `implement-task`, `implement-batch`, and `save-context`. Eight are skills: `audit-personal-conventions`, `bug-hunt`, `feature-pipeline`, `git-worktree-management`, `optimize-skill`, `process-pr-comments`, `review-loop`, and `trim-artifacts`.
- Plain rules in place of shouted words (issue #74): 47 files.
- Contents lists (issue #74): 31 reference and example files. `bug-hunt` links `references/report-format.md`, and `optimize-skill` links `examples/bug-hunt-audit.md`.
- `opsx-implement` names the `openspec` CLI, and `audit-openspec` names the OpenSpec folder layout. `generate-xml-docs` names its guard style (issue #74).

### Changed in dotnet-backend-dev

- Plain rules in place of shouted words (issue #74): 30 files.
- Contents lists (issue #74): 21 reference and example files.
- The templates name the private shared framework (issue #74). The `dotnet-conventions` hub has a paragraph about it, nine skills have a dependency line, and the plugin description has one sentence about it.

### Changed in the repository

- `README.md` (issue #74): a new section with permission rules for push, force push, and `--no-verify`. The dotnet-backend-dev row names the shared framework.
- `.claude-plugin/marketplace.json` (issue #74): the same description change.
- `CLAUDE.md` (issue #74): a new section with the workflow for new and imported units.
- `tests/simple-english-baseline.json` (issue #74): five entries for heading words that the new contents lists repeat.

## dev-essentials 3.4.3 in release [3.6.4] - 2026-10-27

This release changes the reviewer prompts (issue #72). Reviewers now report every finding with a severity and a confidence, and one later step filters them. Blanket second passes and persona lines are gone. Where a change alters behavior, the bullet says so.

### Changed in dev-essentials

- `review-loop` (issue #72): behavior change: the reviewer brief asks for every finding with a severity, a confidence, and a failure case. Phase 4 is the only filter, and it defers a Low or Nit finding unless the reviewer puts it under Must fix before merge. The finding counts are now a signal for the triage, and the run no longer asks for a stricter second review. The reviewer prompts of the branch, pr, last-commits, and diff-range briefs open with the goal, not a persona.
- `review-loop` (issue #72): behavior change: the large-target mode has no Finding Verifier subagent and has three roles. In the synthesis, the main agent reads the lines of each finding and makes sure that the diagnosis matches them. An Area Explorer reports every finding with a confidence, and the word cap on the whole reply is gone. Each field keeps its own limit.
- `help-review-pr` (issue #72): behavior change: the review reports every finding with a severity, and the findings table is sorted by severity. So `--mode=post-all` now posts a comment for every finding, also the Nits, and it can post more comments than before. The mode `--orchestrate` has no Finding Verifier.
- `audit-team` (issue #72): behavior change: each role reports every issue with a confidence, and the consolidation is the only filter. The Reverify step is gone. The role prompt names a point of view, not a persona.
- `audit-plan` and `audit-openspec` (issue #72): the Reverify step is now a step that makes sure that each cited `path:line` says what the finding claims.
- `feature-pipeline` (issue #72): behavior change: the security stage now reports the LOW findings and the findings below a confidence of 0.8. They go under Warnings, and the human sees them at Human Approve #2. The subtle web vulnerabilities of precedent 5 now follow the same confidence rule, so a HIGH one can still block. The fix round still takes only the Blocking Issues. The code review stage asks for every issue with a confidence. The stage prompts open with the goal, not a persona.
- `engineering-discipline` (issue #72): behavior change: the diff scan runs in the main session in every mode, and the line that asks to re-read the skill is gone.
- `docs-composer` (issue #72): the agent prompt has no persona line, and the style rules have no emoji.

## dev-essentials 3.4.2, dotnet-backend-dev 1.6.3, and gop-pipeline 1.4.3 in release [3.6.3] - 2026-10-26

This release adds behavior suites (issue #69). A behavior suite is a set of eval cases that runs a workflow skill on a small planted repository and grades the result. Each case builds its repository with a `scaffold.sh` script, and the graders check the files, the commits, the pushes, and the final message. CI does not run the suites, because each run calls a model. No skill, agent, or command changes, so the plugins behave as before.

### Added in dev-essentials

- `evals/review-loop/` (issue #69): 5 cases for the `review-loop` skill.
- `evals/subagent-orchestration/` (issue #69): 4 cases for the `subagent-orchestration` skill.
- `evals/process-pr-comments/` (issue #69): 3 cases for the `process-pr-comments` skill. Mock files answer the calls to the GitHub tools.
- `evals/bug-hunt/` (issue #69): 2 cases for the `bug-hunt` skill.
- `evals/create-html-artifact/` (issue #69): 2 cases for the `create-html-artifact` skill. They grant no shell tool, so they also run on native Windows.
- `evals/probes/` (issue #69): 2 probe cases that test the run environment, not a skill: the git sandbox and the GitHub mocks.
- `evals/_lib/` (issue #69): the Bash functions that the scaffold scripts use to build the fixture repositories.
- `eval-stubs/github` (issue #69): a stand-in plugin that declares the GitHub server, so that the mock files can answer for it. It is outside `evals/`, because `claude plugin eval` refuses a plugin in the eval folder.

### Added in dotnet-backend-dev

- `evals/write-tests/` (issue #69): 2 cases for the `write-tests` command.
- `evals/probes/` (issue #69): 1 probe case for the .NET fixture.
- `evals/_lib/` (issue #69): the fixture functions for the Billing solution.

### Added in gop-pipeline

- `evals/gop-work/` (issue #69): 9 cases for the `gop-work` skill, from the scenarios E1 to E6 and E8.
- `evals/probes/` (issue #69): 1 probe case for the .NET fixture.
- `evals/_lib/` (issue #69): the fixture functions for the Inventory solution and a Python repository.

### Changed in the repository

- `tests/evals/compare_versions.py` (issue #69): the new option `--concurrency` sets the number of runs at the same time. If a run grants `Bash` on Linux, the script now checks the temporary folder. If the folder is `/tmp`, `/var/tmp`, `/dev/shm`, `/run/shm`, or under one of them, the script stops with a message. The sandbox of a run denies writes to these folders, so every Bash call in the run fails ([anthropics/claude-code#104631](https://github.com/anthropics/claude-code/issues/104631)). `tests/evals/test_compare_versions.py` tests both changes.
- `tests/test_eval_cases.py` (issue #69): static checks of every eval case. They call no model.
- `tests/test_eval_scaffolds.py` (issue #69): runs each scaffold script in a temporary folder and checks the repository that it builds. One test builds a .NET solution.
- `.github/workflows/tests.yml` (issue #69): CI installs the .NET SDK 10 for the scaffold tests.
- `.gitattributes` (issue #69): shell scripts keep LF line ends on Windows, so that the scaffolds run in Bash.
- `.gitignore` (issue #69): the stand-in plugin keeps its `.mcp.json`.
- `tests/simple-english-baseline.json` (issue #69): three new entries for text that is not prose, with the reason for each.
- `README.md` (issue #69): the Testing section names the new tests. A new section of Evals explains the behavior suites, the WSL2 setup, the `TMPDIR` rule, the `-m:1` option for .NET builds, and the probes.

## dotnet-backend-dev 1.6.2 and gop-pipeline 1.4.2 in release [3.6.2] - 2026-10-25

The trigger cases of dotnet-backend-dev and gop-pipeline tested nothing (issue #67). Both plugins list `dev-essentials` in `dependencies`, and `claude plugin eval` loads only the plugin under test. So the eval session reported `dependency-unsatisfied` and did not load the plugin. A case can now load the dependency. No skill, agent, or command changes, so the plugins behave as before.

### Fixed in dotnet-backend-dev

- `evals/triggers/` (issue #67): each of the 10 trigger cases now sets `plugins: ["../../..", "../../../.deps/dev-essentials"]` in its `prompt.md`. The plugin and its dependency now load in the eval session. The cases load only through `tests/evals/compare_versions.py`, because the `.deps` folder exists only in the copy that the script makes.

### Fixed in gop-pipeline

- `evals/triggers/` (issue #67): the same fix for the 2 trigger cases.

### Changed in the repository

- `tests/evals/compare_versions.py` (issue #67): the script now reads `dependencies` from the manifest of the plugin at each commit. It copies each dependency from the marketplace at the same commit into `.deps/<name>` of the plugin copy. An entry can be a name, `name@marketplace`, or an object with a name. A dependency that is not in the marketplace is an input error. A new `baseline` subcommand runs one suite at one commit and writes one result file with no comparison. It does not overwrite an existing result file.
- `tests/evals/test_compare_versions.py` (issue #67): new tests for the dependency copy and the `baseline` subcommand. They call no model.
- `README.md` (issue #67): the Evals section says that a plugin with dependencies must run through the script, and it shows the `baseline` command.

## dev-essentials 3.4.1, dotnet-backend-dev 1.6.1, and gop-pipeline 1.4.1 in release [3.6.1] - 2026-10-25

This release adds the first eval tooling (issue #65). An eval runs test prompts and scores each run with graders. CI now runs `claude plugin validate` and a budget test for the always-on cost of each plugin. It also searches for lines that ask the model to write out its reasoning, and it checks that each changed plugin raises its version. A new script compares one eval suite at two commits. Each plugin gets trigger cases for the units whose descriptions share trigger words. A unit is a skill, an agent, or a command. No unit changes, so the plugins behave as before.

### Added in dev-essentials

- `evals/triggers/` (issue #65): 18 trigger cases for 9 pairs of units, for example `review-loop` and `help-review-pr`. For each pair, one case checks that the right unit starts. A near-miss case checks that the unit does not start for the words of the other unit. If another unit owns those words, the case also checks that this other unit starts. CI does not run them, because each run calls a model.

### Added in dotnet-backend-dev

- `evals/triggers/` (issue #65): 10 trigger cases for 5 pairs of units, for example `create-controller` and `update-swagger-spec`.

### Added in gop-pipeline

- `evals/triggers/` (issue #65): 2 trigger cases. They check that `gop-work` starts on a request for GOP mode, and not on a plain request to implement and commit a task.

### Added in the repository

- `tests/test_plugin_cli.py` (issue #65): runs `claude plugin validate --strict` on the marketplace and on each plugin. It also compares the always-on cost of each plugin from `claude plugin details` with a budget.
- `tests/test_prompt_phrases.py` (issue #65): fails on a line in a plugin file that asks the model to write out its reasoning. Such a line can make a model refuse the task.
- `tests/evals/compare_versions.py` (issue #65): runs one `claude plugin eval` suite on the plugin at a base commit and at a head commit, or reads two finished result files. It then gives a verdict with the rules of the single-agent-loop-kit. A lower mean score or a missing case fails. A change in at most one run is marked as possible noise, and the report prints the commands to run those cases again. If the output folder already holds a result file, the script stops. The report names the agent model and the judge model of each side, and it shows route checks as information only. `tests/evals/test_compare_versions.py` tests it on a fixture result file and calls no model.
- `tests/test_version_bump.py` (issue #65): if a pull request changes a file of a plugin, and the version of that plugin does not go up, the test fails.

### Changed in the repository

- `.github/workflows/tests.yml` (issue #65): CI installs the latest Claude Code with npm. CI also fetches the full history, so that the version check finds the merge base.
- `.gitignore` (issue #65): git ignores the `evals/results/` folder of each plugin.
- `README.md` (issue #65): the Testing section names the new tests. A new Evals section says how to run the trigger cases and the compare script by hand.

## dotnet-backend-dev 1.6.0 in release [3.6.0] - 2026-10-25

Some instructions of dotnet-backend-dev contradicted another file, or fired on a request that they did not support (issue #62). The `add-migration` skill now has a path for a standard EF Core repo. The templates and the examples now follow the rules of the skills. Some fixes change the code that a skill writes on purpose. Each of these bullets says so.

### Added in dotnet-backend-dev

- `add-migration` (issue #62): the skill fired on "add migration" in any repo, but it taught only the migration interfaces of the framework. In a standard EF Core repo, the code that it wrote did not build. A new first step finds out which migration system the repo uses. A new section adds a standard EF Core migration with `dotnet ef migrations add`, and gives the install command of the `dotnet-ef` tool. The command pins the version of the EF Core packages. A migration can have custom code in its `Up` and `Down` methods, for example a data backfill. The table goes by the production provider. If both systems match, the skill asks the user. Behavior change: in a repo without the framework, the skill runs `dotnet ef` and writes no framework migration class. In a repo with no migration system and a document database, it stops and asks the user.

### Fixed in dotnet-backend-dev

- `add-migration` (issue #62): the steps for a new partition key deleted the old Cosmos DB container with no question to the user. Behavior change: the skill now asks the user before the delete.
- `create-ef-entity` (issue #62): the skill added a `DbSet` and stopped. On a relational provider, the first query then failed, because the table did not exist. Behavior change: a new Step 7 builds the changed projects. If the production provider is relational, it then adds a migration with `add-migration`. If the production provider is not clear, it asks the user.
- `update-swagger-spec` (issue #62): the step for the controller showed a `public sealed` class on `ControllerBase` with no try-catch. This sketch broke the rules of `create-controller`. The sketch is gone, and the step points to `create-controller` for the class.
- `create-tests` (issue #62): the skill ran the full test suite before it reported the work as complete. `dev-essentials:dotnet-build-test` forbids a run with no filter in a repo with integration tests. Behavior change: the skill now runs the test classes that it wrote or changed, with a filter. It runs them in one run with one filter. The full suite runs in two cases only. The user asks for it, or the user says yes to it after a props-file change.
- `add-configuration-option` (issue #62): the template put `[Required]` on two `Int32` properties, where the attribute has no effect. Two range rules used the message for a missing value. Behavior change: the template has no `[Required]` on a value type. Each rule gets a message from the error builder that matches the rule.
- `create-domain-model` (issue #62): the `ToString` rule said to include all fields, against the rule to erase sensitive information. It now says to include all fields, and to write the erased placeholder as the value of each field with sensitive information.
- `create-tests` and `dotnet-conventions` (issue #62): the rule made each test data generator a singleton with a static `Instance` property. This is a rule of the project: a shared static generator caused test failures that were hard to trace in real projects. Behavior change: each test class now creates its generators with `new {Model}Generator()`, and the generator template has no `Instance` property. All examples follow the new rule.
- `create-tests` (issue #62): two examples built the class under test with `Fixture.Create` in the test case, against Gate 3. They now call a `CreateService()` helper. The rule against inline test data now names its one exception: an options record in a configuration test.
- `test-engineer` (issue #62): the description said to use the agent for "write tests for X". So a request for one class can start an agent that cannot ask the user a question. The sentence is gone. The agent serves the `/write-tests` command.

## dev-essentials 3.4.0 in release [3.5.0] - 2026-10-25

This release fixes workflow bugs in dev-essentials (issue #60). Some rules contradicted each other. Some steps made a commit, a push, or a deletion that the user did not ask for. Where a fix changes behavior on purpose, the bullet says so.

### Added in dev-essentials

- `scripts/backup_move.py` (issue #60): a script that moves notes files to a backup folder outside the workspace. It never deletes a file, and it refuses a file that git tracks. Without `--apply`, it prints the plan only. `save-context` uses it.

### Changed in dev-essentials

- `audit-personal-conventions` (issue #60): behavior change: a question or an audit request, such as "which of my rules belong in the marketplace?", now stops after the Phase 4 triage. Before, the default mode approved its own triage, authored the entities, committed them, and bumped a version. Phase 5 and the later phases now run only on a request to promote. A reply to the triage with the Phase 5 verbs is such a request.
- `save-context` (issue #60): behavior change: Step 5 moves the finished notes files to a backup folder outside the workspace with `backup_move.py`. Before, it deleted them with no stop and no copy. `research-implement-review-report` and `implement-task` now say "move" where they said "delete".
- `implement-batch` (issue #60): behavior change: the plan files stay out of every commit. Step 2 makes no commit, and its plan-review loops pass the new `review-loop` option `--no-commit`. The commit of task 1 no longer holds the plans. Before, a repo that ignores the plan folder got an empty plans commit, and other repos shipped the plan files. The final report names the plan paths.
- `implement` (issue #60): behavior change: a commit holds no plan file and no research file. The commit message follows the style of the repo, with no `Phase N: Task X.Y` numbers.
- `opsx-implement` (issue #60): the commit message follows the style of the repo, with no phase or task numbers of `tasks.md`.
- `feature-pipeline` (issue #60): behavior change: the finalization stage makes the commit and returns the facts for the push and the PR. The master agent then pushes and creates the PR in the main session. Before, the stage subagent pushed, against Rule 4 of `subagent-orchestration`.
- `review-loop` (issue #60): new option `--no-commit` for a caller that keeps the target out of commits, for example a plan file. Phase 7 makes no commit, and Phase 8 re-reviews the whole target.
- `review-loop` (issue #60): behavior change: for `target=pr <id>`, Phase 5 compares `HEAD` with the fetched PR head before the first fix. If they differ, the run asks the user, or with `--autonomous` it continues as `--dry-run`. Before, the fixer edited and committed on the branch that was checked out, also on an unrelated branch such as `main`. The trigger phrases now name the loop and its fixes, and a plain PR review points to `help-review-pr`. The gate covers `target=diff <range>` too: it compares `HEAD` with the right side of the range, and a range with `HEAD` on the right side needs no check.

### Fixed in dev-essentials

- `process-pr-comments` (issue #60): the copied Autonomy text said that a post stops in the default mode, but Bucket A1 posts replies with no stop. The skill now states its own gates: a reply and a resolve do not stop, and a push and a new issue do.
- `subagent-orchestration` (issue #60): Rule 1 sent a plain "process PR comments" request to a subagent, which cannot ask the user. The main session now invokes `process-pr-comments`, with `dry-run` for a plan only.
- `create-html-artifact` (issue #60): `references/pitfalls.md` said that a review of 1,000 lines has about 1 major item, which can act as a cap. The renderer now shows every finding that the caller gives.
- `bug-hunter` and `bug-verifier` (issue #60): each agent now says that its read-only `gh` commands are its only GitHub source. The rule to use only the GitHub MCP tools is for the orchestrator and the known-issues collector.
- `dotnet-build-test` and `test-runner` (issue #60): a long test run in a subagent no longer polls with `sleep`. A background subagent waits for the notification that its background command ended. `test-runner` sets `background: true`. Then it runs in the background, also for a caller that waits for it.

### Changed in the repository

- `tests/test_backup_move.py` (issue #60): unit tests for `backup_move.py`.

## gop-pipeline 1.4.0 and dotnet-backend-dev 1.5.0 in release [3.4.0] - 2026-10-25

The GOP pipeline had four bugs and one rule that never applied (issue #58). In some runs, it committed a file that the run did not change, or it committed and pushed on the default branch. A change to a shared build file skipped all tests. A failed build, or a test that failed because of production code, stopped the run. This release fixes them, and each fix changes behavior on purpose. The release also declares `dev-essentials` as a dependency of `dotnet-backend-dev` and `gop-pipeline`, so an install of either plugin also installs it.

### Fixed in gop-pipeline

- `gop-commit` (issue #58): the agent staged every change with `git add -A`. So a commit sometimes took in an untracked file of the user, for example `.env.local`, and `--autonomous` pushed it. Behavior change: `gop-work` now gives the agent the files of the run, and the agent stages and commits only these paths. Changes that the user staged before the run stay staged. The report lists each change that the commit left out.
- `gop-work` (issue #58): no step made a branch, and `gop-commit` must not switch branches. So a run on the default branch committed there, and `--autonomous` pushed to the default branch of the remote. Behavior change: if the run starts on the default branch, Phase 0 stops and asks for a branch name or an explicit yes. With `--autonomous`, Phase 0 creates a branch. Phase 0 also records the changes that were in the working tree before the run, so that Phase 5 does not commit them.
- `gop-work` (issue #58): a change to `Directory.Packages.props` or another shared build file, with no `.cs` or `.csproj` change, skipped all tests. Behavior change: such a change now runs all test projects. `gop-test` has a new input `test_scope` for this.
- `gop-work` (issue #58): a failed build, or a test that failed because of production code, stopped the run, also with `--autonomous`. `gop-test` must not change production code. Behavior change: the run now goes back to Phase 1 with the failures, and the main session fixes the production code. The run does this at most 2 times, and then it stops and reports the failures.
- The five `gop-validate-*` validators (issue #58): a rule made a failed build or test CRITICAL. The rule never applied, because the run stops or starts a fix cycle before the validation. The rule is gone. The validators still record "no tests found" as INFO.
- `gop-work` (issue #58): the skill now states that its build and test phases assume a .NET solution and the .NET SDK on `PATH`.
- `gop-test` (issue #58): the agent polled the log of a long test run with `sleep` loops. When the background command of a background subagent ends, Claude Code sends the subagent a notification. The agent now waits for that notification and then reads the exit file and the log. `gop-work` now starts `gop-test` as a background subagent, and the agent file sets `background: true`. So the notification arrives.

### Changed in gop-pipeline

- `plugin.json` (issue #58): the plugin declares `dev-essentials` as a dependency, because `gop-work` and `gop-test` use its skills and agents. An install of `gop-pipeline` now also installs `dev-essentials`.

### Changed in dotnet-backend-dev

- `plugin.json` (issue #58): the plugin declares `dev-essentials` as a dependency, because some of its skills use skills of `dev-essentials`. An install of `dotnet-backend-dev` now also installs `dev-essentials`.

### Changed in the repository

- `README.md` (issue #58): the rules for `plugin.json` allow the `dependencies` field, with bare plugin names and no version range. The install section says that `dotnet-backend-dev` and `gop-pipeline` also install `dev-essentials`.

## dev-essentials 3.3.1 and gop-pipeline 1.3.1 in release [3.3.1] - 2026-10-22

This release follows up on issue #55. Some skill text named a versioned model, or quoted the higher price that one model charges for a long prompt. Other text cited the docs as the reason for a rule. When a new model or a new docs page ships, such text goes out of date. The text now gives a reason that stays true, and names models only by family. No behavior changes.

### Fixed in dev-essentials

- `subagent-orchestration` (issue #55): the auto-compact rule no longer names Haiku 5.5, its price for a long prompt, or the docs. It now says that about 100,000 tokens is a good size for search, fact, and build-check work. The reason is that a larger context often costs more and adds noise. The skill no longer says which model the built-in `Explore` agent runs on. It now says not to count on `Explore` for a cheap search, because its model can change between releases.
- `review-loop` (issue #55): the examples name the reviewer model as `opus`, not as a versioned model ID.
- `bug-hunt` (issue #55): `references/pauses.md` no longer says that its facts come from the docs.
- `audit-personal-conventions` (issue #55): `references/entity-authoring-conventions.md` gives the reasons for the 500-line rule and the `context: fork` rule without a quote from the docs.

### Fixed in gop-pipeline

- `gop-work` (issue #55): the Phase 0 text and the Stages table no longer say which model the built-in `Explore` and Plan agents run on.

## dev-essentials 3.3.0 and gop-pipeline 1.3.0 in release [3.3.0] - 2026-10-22

The workflows now give the mechanical work to three new read-only Haiku agents: a code search, fact gathering, and a build and test check (issue #55). The planning, the review, and the implementation stay on their models. A built-in `Explore` search runs on the model of the session, so the workflows now use the new code search agent. The new agent fields need Claude Code 2.1.296 or later for `autoCompactWindow` and 2.1.271 or later for `omitClaudeMd`. An older version loads the agents without these fields. The per-call `effort` parameter of the Agent tool needs 2.1.292 or later. Three workflows now also name an effort level for each role: `research-implement-review-report`, `implement-batch`, and `review-loop`, so that a subagent does not depend on the effort of the session.

### Added in dev-essentials

- `code-locator` (issue #55): a read-only code search agent. It returns paths, line numbers, symbols, and short excerpts.
- `fact-gatherer` (issue #55): a read-only agent for one narrow question. It returns facts with a `path:line` or a URL as evidence, and no conclusions.
- `test-runner` (issue #55): an agent that runs the build and test commands of a brief and reports the verbatim result lines. It never edits code. In a .NET repo, it follows `dotnet-build-test`.

### Changed in dev-essentials

- `subagent-orchestration` (issue #55): "Haiku scope" names the three agents and the rule that they return facts, not synthesis. The skill says that the built-in `Explore` runs on the model of the session, and that only an agent file sets the auto-compact window. A plan now names exact paths, anchors, and key signatures. A new, rarely used exception gives a small, tightly coupled task to a fork on an Opus session. A new section says that the orchestrating session runs on Opus or Sonnet, never on Haiku. On a Sonnet session, a tightly coupled task and a critical decision without the user go to an Opus subagent. In Rule 5, each dispatch of a general agent type passes `effort`. Any other agent type gets `effort` in two cases: a skill or the user names a level, or the session effort is too low for the task. It says which dispatch needs no `effort` parameter. It also warns against `CLAUDE_CODE_EFFORT_LEVEL`, because that variable overrides the effort of every subagent. Behavior change: item 1 of `Trust but verify` checks a build or test claim with `test-runner`, with the same test filter as the subagent.
- `research-implement-review-report` (issue #55): Phase 1 dispatches parallel fact gatherers, one narrow question each, and then a planner that reads their reports. A question that needs judgment goes whole to a researcher. Behavior change: after each task, the orchestrating session checks the build and the tests with `test-runner`. The "Models" line names every role. Behavior change: a new "Effort" line sets the effort of each research, planning, and implementation dispatch.
- `implement-batch` (issue #55): the "Models" line agrees with RIRR. Behavior change: Step 3 checks the build and the tests with `test-runner` before the commit. Behavior change: a new "Effort" line, which agrees with RIRR, sets the effort of the planner and the implementer.
- `implement-task` (issue #55): behavior change: the simplify pass gets a `test-runner` check before its commit.
- `feature-pipeline` (issue #55): behavior change: the Build Gate gives the build to `test-runner`, and the master agent reads only its report.
- `review-loop` (issue #55): behavior change: Phase 6 runs the build and the tests through `test-runner`. A reviewer can give a broad search to `code-locator`. Behavior change: in the orchestrated mode, the Area Explorers and the Finding Verifier run on `--reviewer-model`. Behavior change: the Target Explorer of the orchestrated mode runs on Haiku with low effort. It returns a fact map with no judgment, and the Area Explorers do the judging. Behavior change: each dispatch on the reviewer model now passes the effort of the new option `--reviewer-effort` (default `high`). The fixer passes the effort of `--fixer-effort` (default `medium`).
- `help-review-pr` and `audit-team` (issue #55): a review can give a broad search to `code-locator`. `audit-team` does not use it for a role. Behavior change: the orchestrated mode of `help-review-pr` changes the same way as in `review-loop`, with a Target Explorer fact map.

### Changed in gop-pipeline

- `gop-work` (issue #55): if the session lists `dev-essentials:code-locator`, Phase 0 uses it for a code search. Else it uses the built-in `Explore`.

## dev-essentials 3.2.3, dotnet-backend-dev 1.4.3, and gop-pipeline 1.2.5 in release [3.2.3] - 2026-10-18

Some instructions in the skills, agents, and commands were wrong or misleading. Some told Claude to do a thing that cannot work, for example to ask the user from a subagent. Some contradicted another file, and some code examples did not compile or did the wrong thing. This release fixes them (issue #48). Each fix below says what was wrong and what the text says now. Where a fix changes behavior on purpose, the bullet says so. The release also ships the `.gitattributes` file of issue #52, which had no release before.

### Fixed in dev-essentials

- `audit-personal-conventions` (issue #48): the review-fix commits were called "Apply review findings" and had to hold the finding numbers, but the review loop makes its own `Review round <N>: Fix ...` commits. The skill now keeps the finding numbers and their `source:` citations in the report of Phase 10, not in commit messages. Behavior change: the extra "Apply review findings" commit is gone. A new rule picks the terms that a shipped entity must still cover, and it has its own section in `entity-authoring-conventions.md`. A resume run now stops and asks in two cases. In the first, the TODO has no `Marketplace remote`, on every path that resolves the marketplace root. The run asks for the remote URL and writes the answer into the TODO. In the second, a `--marketplace=` clone has no `origin` remote. Before, it went on with a warning, and the later compare never passed. An approved F item in a memory file is removed with the once-per-run question. An F item in a CLAUDE.md is only reported. A stale personal file is deleted only after the user approves its F item at Phase 5. The resume hints now say so. The skill also tells the worktree skill to leave `.gitignore` of the other repo alone. The report templates and the walkthrough now show the sections that the Phase 10 report has.
- `project-claude-md-preamble` (issue #48): if the root has both `CLAUDE.md` and `AGENTS.md`, Claude Code reads only `CLAUDE.md`. A preamble in `AGENTS.md` alone did not load. The skill now keeps the preamble in `AGENTS.md` and puts the line `@AGENTS.md` in `CLAUDE.md`.
- `bug-hunt` (issue #48): the planner now numbers the areas in search order. If the user changes the order, the planner renumbers the areas. Before, the number and the order did not always agree. A structure check that fails on the setup files, the digest, or the skeleton now names the agent to run again. Before, the text had only a repair step for hunters, verifiers, and the auditor.
- `create-documentation` (issue #48): the REST API template listed two links in its contents list ("Update" and "Delete") that have no section. The links are gone.
- `create-html-artifact` (issue #48): the Mermaid note said that single-encoded entities such as `&lt;` break a diagram. Mermaid decodes one level, so only double-encoded text fails. The note and its search list now look for the double-encoded form.
- `dotnet-build-test` (issue #48): the text said a foreground Bash command runs for 10 minutes by default. The default is 2 minutes, and the `timeout` parameter raises it to at most 10 minutes. The steps for a subagent now give each wait call a `timeout` of at most `600000`.
- `feature-pipeline` (issue #48): the skill now tells the stages where it lives, so the path of the starter context file works. The flags reach the skill through `$ARGUMENTS`. Every stage prompt now gets a `<worktree>` block, so stage commands run in the worktree and not in the main checkout. The text no longer mixes `<task-id>` and `{TASK_ID}`. Behavior changes: when a resumed run needs the Build Gate or Human Approve #2, it now runs them. A fix round now runs the implementation stage again and then the Build Gate. A stage that reports a STOP, a blocker, or an escalation is not marked complete. The skill asks the user in every mode. A missing `stageStartSha` entry no longer stops a resume. The worktree skill now gets the base branch of the project context. The finalization stage reports the PR number, owner, and repository. The test plan heading in the table now matches the real heading.
- `git-worktree-management` (issue #48): `git check-ignore` and `git rev-parse` now run with `git -C <repo-root>`, so they work from any folder. The exclude path is absolute. The `--track` option is gone from the command for a remote branch, because the command failed for a branch with no upstream. The copy of `settings.local.json` now reads from the repo root and creates the target folder. The solution search finds `.slnx` files too. The advice for long paths no longer says to shorten the branch ref. It says to suggest a shorter branch name to the user.
- `optimize-skill` (issue #48): when a fact test fails after a commit, the repair now changes the commit of this step, with `git commit --amend`. If that commit exists and its parent is the base commit of the step, the repair amends it. Before, the repair sometimes added a second commit for the same step. If the commit does not exist, the repair makes it. The repair never amends the base commit of the user. The `SendMessage` repair, the dispatch again, and the briefs carry the same instruction.
- `process-pr-comments` (issue #48): `deep-fix` took a thread ID, but the reply and commit text use the number of the top comment (`T#`). The option now takes the comment ID and says so. Subagents cannot push after they ask the user, so the push moved. Behavior change: the orchestrating session now pushes on every cycle, and then resumes Stage 2 for the resolve step and Phase 5. If no push happens (no go-ahead, the user declines, or the push fails), Stage 2 runs Phase 5 only. The orchestrating session also owns `processedCommentIds`. On `stop-blocked`, the deep-fix commits stay on the unpushed branch and are not squashed. The deep-fix review runs on the range of that arc only. In autonomous mode, an `[OutOfScope]` issue takes its title from the draft and no type unless the reviewer named one. An autonomous reply to a `[Question]` is a plain `[AI]` reply. The skill states that creating a PR is out of scope and points to `pr-composer` for the text only. Behavior change: with `autonomous`, a fix that rewrites code from scratch (Bucket A2) must now stay inside the diff of the PR. Before, it was allowed to leave the diff.
- `review-loop` (issue #48): the run format changes only what chat shows. The text said it also moved the reports to files, and it named a `--print-reports` override that does not exist. The text now says that the report destination does not change. The `audit-team` reviewer builds its own prompts, so Phase 3 builds no brief for it. The triage table showed "(will fix)" for every row, even for a finding that was deferred on its merits. Rows now show the merit deferral. The `blocker` skip token now says that the finding goes to the deferred list of Phase 9. Behavior change: a finding that a primary source refuted no longer blocks `stop-clean`. The examples now match the rules, and they no longer cite a convention that does not exist. The spec review example now works for the change document of any spec framework, with OpenSpec as one case. It uses the active-change path `openspec/changes/<name>/` and the archive path `openspec/changes/archive/<YYYY-MM-DD>-<name>/`, as the OpenSpec docs give them.
- `subagent-orchestration` (issue #48): the rule against background Bash runs named one exception. It now names both exceptions of `dotnet-build-test`: an explicit request of the user, and a long test run in a subagent.
- `trim-artifacts` (issue #48): the planner copied only its own batch, so the planner had no proof for a regular expression that crosses files. It now copies every file that the glob matches. Each batch has its own scratch folder and its own progress file, so parallel planners no longer overwrite each other. The reviewer brief now has a `Targets in bytes: {TARGETS}` line. Each plan names the profile of each file. So the reviewer can check each file against its target.
- `write-markdown` (issue #48): the skill told Claude to install `markdownlint` and to create a configuration file on its own. Behavior change: it now does neither unless the user asks. It uses the existing configuration of the repo, and the setup notes are for the user.
- `docs-composer`, `pr-composer`, and `task-composer` (issue #48): the agents said to ask the user, but a subagent has no way to ask. They now stop and put the question in the final reply, so that the caller asks. The `pr-composer` file name is now `PR-<branch>.md`. Each `/` in the branch name becomes `-`, because a slash in the name made a folder.
- `implement-batch` (issue #48): the text allowed a Step 2 with no plans commit, which broke the squash base of task 1. Behavior change: Step 2 now always makes one plans commit, and stages the plan files again before the squash. The review of task 1 now starts at that commit (`REVIEW_BASE_SHA`), so it no longer reviews the plan files as code.
- `implement-task` (issue #48): a research agent that cannot fetch an item, and a simplify step that needs a decision, said to ask the user. Subagents cannot ask. They now stop that item, and put the question in their report for the orchestrator.
- `implement` and `opsx-implement` (issue #48): the examples named `create-domain-model` and `create-tests` and assumed that every repo has them. They now name the `dotnet-backend-dev` skills. They say that these skills apply to a .NET repo with that plugin.
- `merge-worktree-projects` (issue #48): the index merge dropped the pointer line of a memory file that had no free name and did not move. Now such a line is not appended. The index of the worktree project stays in place for that pair only, and the report lists the pair as partially retained. Every other merge still deletes the copy of the index. The text points to the right step (4.5) for the deletion.
- `research-implement-review-report` (issue #48): a plan file as the argument now skips research and planning, but still gets the sign-off and the open-decision step. In single mode, Phase 2 output is committed before Phase 3. Behavior change: if the review loop ends with `stop-blocked`, the command no longer squashes. It keeps the round commits and reports the verdict.

### Fixed in dotnet-backend-dev

- `add-configuration-option` (issue #48): the `appsettings.json` section was `{Feature}`, but the options binding uses the name of the options class. The section is now `{Feature}Options`, and the text says why. The environment variable example now shows how the key maps to the shell variable. A comment in the example validator says that the nested validation is for nested options only. Behavior change: the default way to read options is now `IOptionsMonitor<T>`, as in the conventions. `IOptions<T>` and `IOptionsSnapshot<T>` stay for repos that already use them.
- `add-migration` (issue #48): the container example used a per-entity `ToContainer` and a partition key, which contradicts the entity configuration of the conventions. Behavior change: a new entity now uses the service container from `DbStorages`, as in `create-ef-entity`. The separate-container example is only for a change of the partition key. The batch pattern in `common-patterns.md` used `Skip`. When the batch removes or changes the rows that the query filters on, `Skip` misses records. The pattern now queries the records that still need the migration and takes a batch each time. It keeps the keys of skipped records out of the query. It works for any key type, for example `Guid`.
- `add-session-logging` (issue #48): the example wrote the failure as an information entry and kept the exception out of the log. It now writes an error entry with a user-friendly message, passes `ex.ToString()` in `details`, and uses `CancellationToken.None`. Behavior change: the exception text now goes to the `details` parameter, as `logging.md` says.
- `create-controller` (issue #48): the text said to implement `I{Feature}ControllerImpl`. The class is `{Feature}ControllerImpl`, and it implements the generated `Rest.I{Feature}Controller`.
- `create-domain-model` (issue #48): the skill told Claude to write `Equals`, `GetHashCode`, and `ToString` by hand with a case-insensitive comparer. This contradicted the hub, which keeps the generated members. Behavior change: the skill now keeps the generated members unless a case in `domain-models.md` applies. The fallback for a missing `IStaticEquatable<T>` is `IEquatable<T>, IEqualityOperators<T, T, Boolean>`, and the line that said to drop the interface is gone. `dotnet-conventions` and `domain-models.md` say the same.
- `create-ef-entity` (issue #48): the repository interface path was wrong. The example used a raw container name and a partition key. It now uses `DbStorages`, `HasUniversalKey`, and no partition key, as in `ef-patterns.md`. The skill had no step for the repository class or the `DbSet` property. It now has both.
- `create-exception` and `create-string-resource` (issue #48): the example messages put some placeholders in no brackets. The messages now wrap each value in `[{0}]`, as the string rules say.
- `create-tests` (issue #48): the rule for optional parameters did not cover the `Create{Mock}` helpers. It now does. The two constructor tests are now required for one or more dependencies, not more than one. The examples now match the rules. Comments no longer put text after "Arrange" on the same line. The logger helper is non-static and passes the fixture. The mock builder uses `Arg.Any<T>()` with `Returns`. The repository tests use `CreateRepository(DbContext)` and no extra `SaveChangesAsync`. The scenario tests use `CreateNew()` and `FromValue()`. The wrapper tests use a `CreateMigrationId` helper of the generator. The controller test uses a generator method and a 503 service-unavailable assertion. The migration test uses a helper for the legacy record. Every test class example now has `[TestFixture]`, also a generic one with `[TestFixtureSource]`. The rules say so too. No example file that has no regions has a banner comment above its helpers. The helpers stay at the end of the class. `enforced-gates.md` says that the other examples leave out the regions.
- `model-mapping` (issue #48): `nameof(A.B.C)` returns only `C`, so the nested `MapProperty` examples mapped the wrong property. They now give the path as an array of names. The `using` alias in an example is now `Rest = ...`.
- `update-swagger-spec` (issue #48): the standard error responses had a 500 with no body. Every operation must document 500, because otherwise an unhandled server exception can look like a client failure in some generated client code. The 500 now has a `ProblemDetails` body, and the spec also documents a 503 with a `ProblemDetails` body. The checklist, the worked example, and the first full operation example ("Path Operations") list 500. The integration test example now adds a store to the database first, because the database is empty after each test.

### Fixed in gop-pipeline

- `gop-build` (issue #48): the build walked up only from modified `.cs` files. It now walks up from any modified file, and a modified `.csproj` counts as affected. If no project is affected and no shared infrastructure changed, it builds the solution.
- `gop-commit` (issue #48): `cd <repo_root>` does not persist between Bash calls, so the git commands ran in the wrong folder. Every git command now uses `git -C <repo_root>`. The pathspecs that unstage `CLAUDE.md` and plan files now work from the top of the repo.
- `gop-test` (issue #48): the test build used `--no-restore`, which failed on a project that was not restored. The flag is gone. A modified `.csproj` file now counts as a source project.
- `gop-validate-compliance`, `gop-validate-correctness`, `gop-validate-performance`, `gop-validate-reuse`, and `gop-validate-security` (issue #48): `git diff HEAD` does not show new untracked files. The validators now also list the untracked files with `git ls-files --others --exclude-standard`, and read each one in full. Behavior change: validators now review new files, which they missed before.
- `gop-work` (issue #48): the quick probe for a test project is gone. Behavior change: if any `.cs` or `.csproj` file changed, Phase 3 now runs, and `gop-test` does the search. In interactive mode, after the second re-run, the options "accept" and "dismiss" are gone. A `BLOCKED` result stops the pipeline. A result with warnings offers only to proceed or to stop for a manual fix. The implement stage now also runs `git status --short`, so new files show in the scope.

### Changed in the repository

- `.gitattributes`: new file. GitHub counts the `.md` files in the language statistics, so the main language of the repository is Markdown, not Python (issue #52).

## dev-essentials 3.2.2 and dotnet-backend-dev 1.4.2 in release [3.2.2] - 2026-10-18

This release reviews each lint exception of the repository (issue #49). Text rewrites and a fix in the lint test remove 14 of the 23 entries of the simple-english baseline. The 9 entries that stay name the reason that no rewrite can remove them. Two markdownlint rule changes go away.

### Changed in the repository

- `tests/simple-english-baseline.json`: 9 entries instead of 23. The reason of each entry that stays names the settled name, the file path, or the quoted source that keeps the hit.
- `tests/test_simple_english.py`: the test does not lint the value of an `argument-hint` line or the closing `---` of the frontmatter, because they are not prose. Before, the hint and the first sentence of the body counted as one long sentence.
- `.markdownlint.jsonc`: `MD038` is on again. `MD033` allows only the elements of the `write-markdown` base configuration. `MD041` names its reason.

### Fixed in dev-essentials

- `merge-worktree-projects`: the text uses "approval" for the answer of the user and keeps "check" for the safety checks. The report line for a skipped folder is now "skipped (recent activity). Make sure that it is safe to merge."
- `bug-hunt`: placeholders such as `<ID>` in the notes are code spans. The "Result:" text of a verifier is a code span with no space at the start. The text says to add a space before it.
- `audit-personal-conventions`: the gate question before the delete is two short questions.
- `feature-pipeline`: the worktree announcement has no bold labels, and the project context template uses placeholders that markdownlint does not read as HTML.
- `general-conventions`, `review-loop`, and `task-composer`: plain words in a YAML rule, in an example of a bad argument, and in a trigger phrase.

### Fixed in dotnet-backend-dev

- `create-tests`: the checklist item for Gate 1 states the gate first and its scope in two short sentences. The scope does not change.

## dev-essentials 3.2.1 and gop-pipeline 1.2.4 in release [3.2.1] - 2026-10-18

Many skills and commands have options that set a model, for example `--reviewer-model` and `--fixer-model`. Their text also named the default model of a role ("the Opus reviewer", "a Sonnet fixer"). If the user picked another model with the option, that text contradicted the run. The text now names the option or the role. The default model appears once, in the option table or the model line of the skill (issue #47).

### Changed in dev-essentials

- `review-loop` (issue #47): the phases, the audit-team adapter, and the examples name `--reviewer-model` and `--fixer-model` instead of Opus and Sonnet. The option table keeps the defaults.
- `bug-hunt` (issue #47): if the model of the hunter, the verifier, or the auditor is not available, step 0 asks a question. Before, only a missing Fable gave this question. The helper briefs no longer repeat the models of the dispatch table.
- `process-pr-comments` (issue #47): the intro, the note under the dispatch table, `references/thread-state-schema.md`, and `references/deep-fix.md` no longer name the models of the stages. The dispatch table is their one home.
- `implement-batch` and `research-implement-review-report` (issue #47): the steps name the role, for example "planner" or "implementer". The "Models" line is the one home of the models.
- `audit-personal-conventions` (issue #47): the example of session review-loop defaults and the walkthrough no longer name models.
- `audit-personal-conventions`, `git-worktree-management`, `implement`, `opsx-implement`, `process-pr-comments`, and `save-context` (issue #47): the "Autonomy" section no longer has the rule for a Fable dispatch. These workflows never pick Fable on their own. The rule stays in the workflows that can pick Fable, and its one home is "Model selection" in `subagent-orchestration`.

### Changed in gop-pipeline

- `gop-work` (issue #47): the "Autonomy" section no longer has the rule for a Fable dispatch. The workflow uses the fixed models of its agent table and never picks Fable.

## dev-essentials 3.2.0 in release [3.2.0] - 2026-10-18

This release adds the skill `optimize-skill` (issue #26). It turns the pipeline that optimized `bug-hunt` and the other skills of this marketplace into a skill.

### Added in dev-essentials

- `optimize-skill`: a skill that optimizes one skill for tokens and clarity and keeps its behavior. An auditor (Opus by default) reads the skill docs, the best practices for skills, and the criteria of `claude-md-improver`. It writes an audit report with a fix plan for each item. The orchestrator decides the open items from the decisions of the user, not from the taste of the auditor. By default, it decides them without a stop and lists them for review. With `--interactive`, it asks. An applier (Sonnet by default) classifies each item APPLY, PARTIAL, or REJECT, applies the plan, and makes one local commit. A reviewer (Opus by default) then tests whether the skill still behaves the same. A fixer (Sonnet by default) applies the accepted findings in a second commit. The run never pushes. If `simple-english` is not installed, the run uses the plain-English fallback rules of `bug-hunt`.
- `optimize-skill`: the reference files `audit-report-format.md` and `briefs.md`, and the worked example `examples/bug-hunt-audit.md`, an abridged copy of a real audit of `bug-hunt`.
- `plugin.json`: the keyword `skill-optimization`.

### Changed in the repository

- `tests/simple-english-baseline.json`: one entry for the worked example, which quotes the settled terms of `bug-hunt`.

## dev-essentials 3.1.1, dotnet-backend-dev 1.4.1, and gop-pipeline 1.2.3 in release [3.1.1] - 2026-10-18

When claude.ai synced the marketplace, it showed 5 warnings. This release removes them (issue #44). The release also adds the update steps to the README and cuts the text that repeated the documentation (issue #42).

### Added in the repository

- `tests/test_claude_ai_sync.py` (issue #44): a test for two problems. If a `plugin.json` sets `$schema`, the test fails. If the `description` of a skill, an agent, or a command holds an angle bracket, the test also fails.

### Changed in the repository

- `README.md` (issue #42): a new section "Updating the plugins" says how to get a new release. You run `/plugin marketplace update vasar-plugins-marketplace` and then `/reload-plugins`. The section also says how automatic updates work and how to turn them on for this marketplace.
- `README.md` (issue #42): the "Authoring reference" no longer repeats the official documentation. The sections about the folder structure, `marketplace.json`, `plugin.json`, and validation keep only the rules of this repository. They link to the documentation for the rest. The links in the intro and in "References" go to the current pages of the Claude Code documentation.
- `README.md` (issue #44): the rules for `plugin.json` no longer list `$schema`. They say not to set it, because the claude.ai sync strips it and shows a warning.

### Fixed in dev-essentials

- `plugin.json` (issue #44): removes `$schema`. Claude Code ignores the key, but the claude.ai sync strips it and shows a warning.
- `git-worktree-management` (issue #44): the description no longer holds the path `<repo-root>/.claude/worktrees/<full-branch-ref>/`. claude.ai read the placeholders as XML tags and removed the angle brackets, so the path was broken on claude.ai. The description now names the `.claude/worktrees/` folder of the repo in words. The body keeps the full path.
- `audit-personal-conventions` (issue #44): the description recipe in `references/entity-authoring-conventions.md` has a new item. A `description` must not hold angle brackets.

### Fixed in dotnet-backend-dev

- `plugin.json` (issue #44): removes `$schema`. Claude Code ignores the key, but the claude.ai sync strips it and shows a warning.

### Fixed in gop-pipeline

- `plugin.json` (issue #44): removes `$schema`. Claude Code ignores the key, but the claude.ai sync strips it and shows a warning.

## dev-essentials 3.1.0 and dotnet-backend-dev 1.4.0 in release [3.1.0] - 2026-10-17

This release closes the gaps between the descriptions and the bodies that remained after release 3.0.2 (issue #36). It makes `pr-composer` read the spec or the plan of a branch (issue #40). It makes `/write-tests` dispatch the `test-engineer` agent (issue #37). It adds a serialization rule to `handle-sensitive-data` (issue #39). It replaces the names of replaceable tools in the bodies with general terms (issue #38).

### Added in dev-essentials

- `pr-composer`: a step that finds the spec or planning artifact of the branch (issue #40). The agent looks at four sources. The first is the brief. The second is the active changes of the spec framework. The third is plan and design files in the plan folders and notes folders. The fourth is decision records that the diff adds or changes. An artifact belongs to the branch in three cases. The brief names it, the diff adds or changes it, or its name holds the slug or an issue number of the branch. The slug or the number must be a whole part of the name. The agent uses the artifacts for the reason of the change. It names each artifact that it used, with its path, in its final reply. It does not fetch an issue from a remote system.

### Changed in dev-essentials

- `pr-composer` (issue #40): the agent now always reads the git diff first. Before, an active OpenSpec change was the only source for the PR description, and the agent skipped the diff. Now the agent reads the diff together with the artifacts. The diff gives what changed. The artifacts give the reason. If an artifact plans work that the diff does not hold, the agent says so in the "Notes" section. A change of the spec framework must belong to the branch. If exactly one active change exists, it counts as the change of the branch. If no rule matches it, the agent names it as a guess in its final reply. If another artifact belongs to the branch by a rule, the PR description does not use the guess. Otherwise, the "Notes" section does not list the planned work of that change. The description of the agent and the description of `/compose-pr` follow the new behavior.
- `compose-pr` (issue #40): the brief for the agent now holds each spec, plan, or design document that the user named, as a path. It also holds the text of each linked issue or task that the user gave, word for word. The command does not fetch an issue. It shows the artifacts, the guesses, and the issue numbers without text that the agent names in its final reply.
- The bodies use general terms in place of tools that a project can replace (issue #38). A body names such a tool only as a marked example, for example "the mapping library (for example, Riok.Mapperly)". This applies to `general-conventions/powershell.md`, where AWS and Azure are now examples of a cloud provider. It also applies to the other skills and references that named a replaceable tool.
- `audit-personal-conventions` (issue #38): `references/entity-authoring-conventions.md` extends the rule for general terms to the body and to the `keywords` of `plugin.json`. Only a plugin that exists for a tool can use its name as a keyword. The file asks for one general term for each role in all files of the marketplace. It asks for an example at the first use of the term in a file. A new section lists the allowed forms of a marked example and has a table of the general terms.
- `keywords` of `plugin.json` (issue #38): `openspec` becomes `spec-driven`.
- `implement-task`, `implement-batch`, and `research-implement-review-report` (issue #38): the line about `feature-pipeline` was wrong. It said that the pipeline is for an OpenSpec change. Now it says that the pipeline runs a tracked task from the task provider end-to-end in an isolated git worktree.

### Added in dotnet-backend-dev

- `handle-sensitive-data`: a section about serialized output (issue #39). A serializer does not call `ToString()`, so the placeholder did not protect the JSON form of a secret. The section has three parts. The first is an example of a `System.Text.Json` converter that writes the placeholder. The second is a rule for secrets in plain `String` properties. The third is a table that says what to do for logs, API responses, caches, and messages. The section also says how an inbound model reads a secret. It also lists three cases in which the `[LogProperties]` attribute logs a raw value. The checklist and the questions of the skill cover the new rule.

### Changed in dotnet-backend-dev

- `/write-tests` (issue #37): the command no longer writes tests in the main session. It parses the targets, merges the targets that overlap, and dispatches one `test-engineer` agent for each target. A target is a class, a module (a folder or a namespace), or an assembly (a project). Independent targets run in parallel, at most four at the same time. The command checks the combined result and shows one merged report.
- `test-engineer` (issue #37): the agent handles class, module, and assembly targets. It reads a brief from the command and returns a short report in a fixed format. A module or an assembly with more than 20 classes gets no tests. The agent reports the classes, and the command splits them into class targets of at most 20 classes.
- `handle-sensitive-data` (issue #39): the description and `when_to_use` name the serialized form. `dotnet-conventions/security.md` gets a line that points to the skill for JSON.
- The bodies use general terms in place of tools that a project can replace (issue #38). Examples are the code generator, the OpenAPI linter, the mapping library, and the validation library. Other examples are the document database, the test framework, the assertion library, the mocking library, and the test data library. The concrete tools stay as marked examples. This applies to the skills, the examples of `create-tests`, `dotnet-conventions`, and the `test-engineer` agent.
- `keywords` of `plugin.json` (issue #38): `nswag` becomes `code-generation`, and `mapperly` becomes `object-mapping`.

## dev-essentials 3.0.2, dotnet-backend-dev 1.3.2, and gop-pipeline 1.2.2 in release [3.0.2] - 2026-10-17

This release shortens the descriptions that Claude Code loads into every session (issue #33). The skill listing has a budget of 1% of the context window. If the listing is over the budget, Claude Code drops the descriptions of the skills that you use least. Without its description, Claude cannot match a skill to a request. Each new description puts the main use case first and keeps the strongest trigger phrases. The details stay in the body of each file. The release also adds status badges to the README (issue #32).

### Added in the repository

- `README.md`: a line of badges under the title. The tests badge shows the result of the `Tests` workflow on `main` and links to the workflow runs. The latest release badge links to the latest GitHub release. The MIT license badge links to `LICENSE`. The Claude Code plugin marketplace badge links to the documentation of plugin marketplaces. The latest release badge reads the GitHub API through shields.io, so it can show an error while the repository is private.

### Changed in the repository

- `.claude-plugin/marketplace.json` and `README.md`: the descriptions of the marketplace and of each plugin state the general purpose in one to three sentences. They no longer list skills.
- `tests/simple-english-baseline.json`: removes the two entries that the old descriptions needed.

### Changed in dev-essentials

- Shorter descriptions for the skills, commands, and agents. `audit-personal-conventions` also has a shorter `when_to_use`. The three bug-hunt agents still say that only the `bug-hunt` skill dispatches them.
- The trigger phrases of each skill move from `description` to a new `when_to_use` field, so `description` says what the skill does. The agents keep their trigger phrases in `description`, because the frontmatter of an agent has no `when_to_use` field. `feature-pipeline` gets no `when_to_use`, because Claude Code does not load its description.
- If an entity does not exist for a library, a product, or a file, its description does not name it. The descriptions also leave out the internal mechanics. For example, `pr-composer` no longer names OpenSpec, and `process-pr-comments` no longer names its review tags.
- `implement-task` and `implement-batch`: the description says that the command pushes only with `--push`. The old text said that it never pushes.
- The plugin description states the general purpose and lists no skills.
- `audit-personal-conventions`: the description recipe in `references/entity-authoring-conventions.md` follows the new short style. A new description puts the main use case first and has a few trigger phrases. It keeps the facts that change what the user expects, for example a stop before a push. The other details go in the body. The recipe also asks for general terms in place of the names of tools and types that a project can replace. It asks to leave out internal mechanics. It also says which entities get `when_to_use`. Skills and commands get it, and agents do not.

### Changed in dotnet-backend-dev

- Shorter descriptions for the 15 skills and the `test-engineer` agent. The trigger phrases of each skill move to a new `when_to_use` field.
- The descriptions use general terms in place of the names that a project can replace. Examples are the code generator, the mapping library, the test libraries, and the validation library. Other examples are the database product, the session log type, and the resource file name. EF Core and OpenAPI stay.
- The plugin description states the general purpose and lists no skills.

### Changed in gop-pipeline

- Shorter descriptions for the `gop-work` skill and its 8 agents. Each agent still says that only `gop-work` dispatches it. `gop-work` moves its trigger condition to a new `when_to_use` field.
- The plugin description states the general purpose and lists no skills.

## dev-essentials 3.0.1, dotnet-backend-dev 1.3.1, and gop-pipeline 1.2.1 in release [3.0.1] - 2026-10-15

This release adds tests for the scripts of the skills and lint checks for the `.md` files of the repository (issues #25 and #28). The plugin changes fix the Markdown and the words that the new checks found.

### Added in the repository

- The folder `tests/` with tests for `check_report.py` (`bug-hunt`) and `trim_report.py` (`trim-artifacts`). It also has a simple-english lint test and a markdownlint test for every tracked `.md` file of the repository. Run `python3 -m unittest discover -s tests -v` from the repository root. Claude Code does not copy this folder into the plugin cache.
- The file `.markdownlint.jsonc` with the markdownlint rules for the `.md` files of the repository.
- A GitHub Actions workflow that runs the tests on each pull request and on each push to `main`. It uses the latest release of the simple-english linter.

### Changed in the repository

- `CLAUDE.md`: shorter sentences and plainer words, so that the file passes the simple-english test. The rules did not change.

### Fixed in dev-essentials

- The Markdown of 10 files now passes markdownlint. The changes add blank lines around lists and code blocks, give each code block a language, and replace emphasis that worked as a heading. `create-documentation` no longer turns the line-length rule back on.
- `create-documentation`: the configuration, migration, and REST API templates no longer hold inline markdownlint comments, so the documents that an agent writes from them have none either. Two links of the configuration template were split over two lines and did not render as links. Each link is now on one line and renders. The skill also has a hint for a table row that passes the line-length limit of the target repo.
- `implement-batch`, `implement-task`, and `research-implement-review-report`: removed an inline markdownlint comment that the repository configuration already covers.
- `process-pr-comments`, `subagent-orchestration`, and `write-markdown`: shorter sentences and plainer words in four lines. The meaning did not change.

### Fixed in dotnet-backend-dev

- `add-migration`: two steps for a failed migration use plainer words. `create-primitive-wrapper` and the wrapper example of `create-tests` no longer use "etc.".

### Fixed in gop-pipeline

- The Markdown of 11 files now passes markdownlint. In `gop-work`, the two sub-steps of step 12 are now nested under the step.

## dev-essentials 3.0.0 and dotnet-backend-dev 1.3.0 in release [3.0.0] - 2026-10-14

This release makes the continuation prompt of `save-context` opt-in (issue #23). It also moves the .NET test tools from `dev-essentials` to `dotnet-backend-dev` (issue #24).

### Added in dotnet-backend-dev

- The command `/dotnet-backend-dev:write-tests` and the agent `dotnet-backend-dev:test-engineer`. Both moved from `dev-essentials` and work as before. They use the skill `create-tests` of the same plugin.

### Changed in dotnet-backend-dev

- `test-engineer`: If the agent cannot load `create-tests`, it now stops and reports the error. Before, it told the user to install `dotnet-backend-dev`.
- `test-engineer`: The agent now reads the `create-tests` examples from `${CLAUDE_PLUGIN_ROOT}/skills/create-tests/examples/` first. The search of the plugin cache stays as a fallback.
- The plugin description now names the `write-tests` command and the `test-engineer` agent.

### Changed in dev-essentials

- `save-context`: The next-session continuation prompt is now opt-in. The new flag `--continuation-prompt` prints it. A request in words also prints it. A run without a request cleans up the context files (Step 5) and prints no prompt. The flag `--no-cleanup` still skips the cleanup.
- `research-implement-review-report` and `implement-task`: The report phase now runs `save-context` as the last step of the run. The call passes no flag, also not `--plan` or the mode flag of the run. So `save-context` runs in its default mode, also in a run with `--autonomous`. Its cleanup keeps every file of the run, except a finished `_`-prefixed progress file, because the branch is not merged yet. Before it deletes a file of an older session, it asks the user. On a yes, the run deletes the listed files in the same session. `save-context` prints no continuation prompt, unless the user asks for one in the run.
- `implement` and `opsx-implement`: The commands no longer print the continuation prompt of `save-context` by default. If the user asks for it in the run, they print it after their summary.
- The plugin description no longer names a test agent.

### Removed in dev-essentials

- `save-context`: Removed the flag `--no-continuation-prompt`. The prompt is now off by default.
- Removed the command `write-tests` and the agent `test-engineer`. They moved to `dotnet-backend-dev`.

### Breaking changes in dev-essentials

- `/dev-essentials:write-tests` no longer exists. Install `dotnet-backend-dev` and run `/dotnet-backend-dev:write-tests`.
- The agent type `dev-essentials:test-engineer` no longer exists. Dispatch `dotnet-backend-dev:test-engineer`.
- `save-context` no longer accepts `--no-continuation-prompt`, and it prints no continuation prompt by default. To get the prompt, pass `--continuation-prompt`.

## dev-essentials 2.5.0 and dotnet-backend-dev 1.2.3 in release [2.5.0] - 2026-10-14

This release applies the design decisions from the lint sweep (issue #11).

### Changed in dev-essentials

- `process-pr-comments`: With `autonomous`, an automated-review fix that adds a new architecture or a new public contract is now implemented. Before, the skill drafted the fix and waited. Some such fixes also leave the files of the PR diff. If such a fix is not at the rewrite-from-scratch exception, the skill still drafts it and waits. The cycle log now has a list "Decisions for your review". The list names each decision that `autonomous` made in the cycle without a stop.
- `compose-pr`: The command now dispatches the `pr-composer` agent, so both write one PR description format, the format of `pr-composer`. `pr-composer` now ignores OpenSpec drafts and notes folders in the diff, and follows the extra context of the brief, as `compose-pr` did.
- `github-mcp-conventions`: Rule 4 now allows `delete_pending` for your own pending review. The ban on an edit or a delete of a posted comment through MCP stays.
- `subagent-orchestration`: Rule 3 now says that subagents run in the background by default, and how to dispatch independent work in parallel. It adds a short note on forks. The old text about the parameters of the `Agent` tool is gone.
- `review-loop`: The reference to Rule 3 of `subagent-orchestration` no longer speaks of a foreground or background choice. The branch-review example now prints `(parallel)`, not `(foreground-parallel)`.
- `create-documentation`: The feature template and the migration template now have a table of contents, as the checklist asks.
- `test-engineer`: The agent now names the combined comment forms `// Act & Assert.` and `// Arrange, Act & Assert.`.

### Changed in dotnet-backend-dev

- `create-tests`: Gate 1 now applies only to test classes that call the methods of the SUT directly. Controller tests through the HTTP client and scenario tests are out of its scope.
- `create-tests` and `dotnet-conventions`: The rule for test comments now names the combined forms `// Act & Assert.`, `// Arrange, Act & Assert.`, and `// Arrange & Act.`. The examples no longer use `// Act + Assert.`, and no longer put `// Act & Assert.` after `// Act.`.
- `create-tests`: The examples now end every section comment with a dot, as the rule says. For example, `// Arrange - empty database (cleared in SetUp).`.
- `handle-sensitive-data`: If it is not clear whether data is sensitive, the skill now asks the user. Before, it always asked. This matches `dotnet-conventions/security.md`.
- `dotnet-conventions`: `ef-patterns.md` and `domain-models.md` now give generic rules for stored references and for wrappers from a shared SDK. `security.md` no longer names a token type of one infrastructure domain.

## dev-essentials 2.4.2, dotnet-backend-dev 1.2.2, and gop-pipeline 1.2.0 in release [2.4.2] - 2026-10-14

This release fixes the skill bugs that the lint sweep found (issue #12).

### Added in gop-pipeline

- `gop-commit`: New optional input `warning_note`. A CRITICAL finding that the user overrides now reaches the commit message.
- `gop-commit`: New optional input `commit_trailer`. The agent now has a clear rule for the commit author and the trailer.

### Changed in dev-essentials

- `review-loop`: The option `--fixer` takes one agent ID. If the value names several agents (`audit-team`, `dual`, `pair`, or `quad`), the run warns and uses `general-purpose`.
- `process-pr-comments`: The default `bots` list now uses the real Copilot reviewer login `copilot-pull-request-reviewer[bot]`. The skill compares bot logins without the `[bot]` suffix.
- `feature-pipeline`: `--dry-run` now creates no worktree, no branch, and no file.
- `test-engineer`: The agent can now use the `Skill` tool to load `create-tests`. It reads the example files of the skill from the base folder that the Skill tool prints. Without that folder, it finds them in the plugin cache with Glob.
- `audit-personal-conventions`: The trigger phrases moved from `description` to the frontmatter field `when_to_use`. Claude Code adds this field to the description in the skill listing.

### Fixed in dev-essentials

- The lookup of a merged pull request now uses the head `owner:branch` and the state `all`. This applies to all workflows with the shared "Autonomy" section, `save-context`, and `git-worktree-management` (Workflow D). Before, the lookup missed some merged pull requests.
- `review-loop`, `help-review-pr`, and `github-mcp-conventions`: For a pull request from a fork, the diff recipe now fetches `pull/<id>/head`. `process-pr-comments` now runs the ancestry check against `origin/pull/<prId>/head`, so a pull request from a fork works.
- `git-sync`: The test for a rewritten branch uses `git merge-base --is-ancestor`. The repair recipe keeps the original author and date.
- `implement-batch`, `implement-task`, and `research-implement-review-report`: The guardrails now forbid the word "pre-existing" for a red signal, as `engineering-discipline` Rule 1 says.
- `review-loop`, `help-review-pr`, and `process-pr-comments`: The thread states now use the field names of the GitHub MCP response, `is_resolved` and `is_outdated`.
- `review-loop`: After a failed build or test run, Phase 7 commits the fixes first. Then Phase 6 runs the failing command on the commit before the fixes. If the main worktree holds uncommitted changes, Phase 6 also runs the command on the fix commit in a clean worktree. If the command fails only with the fixes, the loop tries one more fix. Else the loop stops with `stop-blocked` and the evidence. If the cycle has no fix, the loop stops with `stop-blocked` without this check. `engineering-discipline` Rule 1 names this check as an exception. The place of the cycle report now depends on `--rounds`.
- `audit-team`: The roles now run as `general-purpose` agents with a read-only brief.
- `feature-pipeline`: Stages 1 and 2 return `QUESTIONS`. The master agent asks the user. With `--autonomous`, it picks the recommended answers for at most 2 rounds, and lists them under "Decisions for your review". The master agent writes `review-diff.patch` against `origin/<base-branch>`, and saves the reply of the reviewer as `review.md`. A failed output check asks the reviewer for a new reply, not a new file. The security review also diffs against `origin/<base-branch>`. If its fetch fails, it writes the error to `security-review.md`, and the master agent stops and reports the error without a rerun. The text of the arguments follows the Autonomy core for the Fable rule, and every stage prompt gets the pipeline-discipline block. The RED step now proves that a passing test can fail, with a temporary wrong value. The run deletes `review-feedback.md` after each re-entry run. With `--skip=review`, `review.md` is optional.
- `process-pr-comments`: Bucket B now covers pushed history and commits that the run did not make, with an exception for deep fixes. Ordered rules replace "strictest action" for combined tags.
- `subagent-orchestration`: The Post-edit gate now covers only the edited paths, compared with the Pre-flight state.
- `audit-personal-conventions`: The skill creates the pull request with the GitHub MCP tools. If they are missing, or an MCP call fails with a connection or authentication error, it uses `gh pr create`. `github-mcp-conventions` names this step as the one exception to Rule 5. The skill fixes a call that fails because of a wrong parameter, and does not fall back. If `gh` is also missing or fails, the skill reports the PR text for a manual PR. The skill splits a skill that it authors and that grows past 500 lines. The authoring reference lists the split options: step references, scripts, agent files, `context: fork`, and an orchestrator skill.
- `task-composer`: The agent passes the approved issue type after a `list_issue_types` check. The agent always sets each existing label that fits the issue, with a type or without one. If the repository does not have the type, these labels include the label with the name of the type, if that label exists. The agent never creates a label.
- `pr-composer`: The agent has a fallback chain for the base branch. If the chain finds none, it asks in the final reply.
- `trim-artifacts`: The reviewer brief now has `{PLAN_PATH}` and the "in other file" test.
- The descriptions of `subagent-orchestration`, `process-pr-comments`, `audit-personal-conventions`, and `engineering-discipline` are now below the limit of 1,024 characters.
- `dotnet-build-test`: Rule 3 now has one exception for a subagent whose test run can take longer than 10 minutes. The subagent runs the tests in the background with a `timeout`, and polls an exit file. `subagent-orchestration` points to this exception.

### Fixed in dotnet-backend-dev

- `create-controller`: The example now inherits the project controller base.
- `add-session-logging`: The failure message of the session log no longer holds `ex.Message`. The session log field is now `_sessionLogRepository` in `add-session-logging`, `create-string-resource`, and `handle-sensitive-data`.
- `create-external-client`: The client no longer logs the whole request object.
- `model-mapping`: `SKILL.md` is now under 500 lines. `SKILL.md` no longer has the duplicate example.
- `dotnet-conventions`: The manual mapping example in `mappers.md` has its TODO and its parameter. The AAA example in `testing.md` builds the SUT with a helper named for its role.
- `create-tests`: The example in "Test Structure" builds the SUT with a helper named for its role. The usage examples in `generators.md` and `mock-builders.md` now follow the test rules. The test cases of the examples call private `Generate` helpers, not the generators. Rule 3 names `ExternalServicesMock` of Web API tests as the one exception to the no-post-setup rule. `repository-tests.md` uses one generic test class shape.

### Fixed in gop-pipeline

- `gop-test`: The agent runs long tests in the background and polls an exit file. This is the long-run exception of `dotnet-build-test` Rule 3 in `dev-essentials`.
- `gop-validate-compliance`, `gop-validate-security`, and `gop-validate-performance`: The blast radius of each agent now feeds a new lens. Security finds out whether untrusted input reaches the changed code through a caller. Performance finds out whether a caller calls the changed code in a loop or on a hot path. Compliance finds out whether the callers follow a changed contract as the plan or a skill requires.
- `gop-work`: The lookup of a merged pull request in the shared "Autonomy" section now uses the head `owner:branch` and the state `all`.
- `gop-work`: The `--interactive` routing now defines a partial dismissal and a repeated finding. A finding that the user dismissed does not make the status `BLOCKED` in a later cycle.

## dev-essentials 2.4.1, dotnet-backend-dev 1.2.1, and gop-pipeline 1.1.1 in release [2.4.1] - 2026-10-14

### Changed in dev-essentials

- All text in the changed skills, commands, and agents now follows plain-English rules. This means short sentences, active voice, one word for one meaning, and no filler. The workflow rules are the same. The notes below name what moved and where.
- `subagent-orchestration`: Moved the three worked examples to the new file `references/worked-examples.md`. Rule 3 no longer lists the parameters of the `Agent` tool, because the list was out of date. It still says that the tool has no `run_in_background` parameter.
- `review-loop`: Moved the `audit-team` adapter, which few runs need, to the new file `references/audit-team-adapter.md`. Moved the Full format into the reviewer brief file. The thread sections now exist once. The rules for the whole run now come before the late sections.
- `process-pr-comments`: Moved three procedures to the new files `references/commit-push-resolve.md`, `references/committed-fix-state.md`, and `references/deep-fix.md`. The briefs now name the skill files that a subagent must read.
- `feature-pipeline`: Moved four procedures to the new files `references/setup.md`, `references/checkpoint-protocol.md`, `references/commit-conventions.md`, and `references/cleanup.md`. The stage files and the artifact template now use the same rules for lint and for a failing test.
- `audit-personal-conventions`: Moved the report templates to the new file `references/report-templates.md`. The cleanup steps of Phase 9 now point to the cleanup reference file instead of repeating it.
- `bug-hunt` and its agents: Shortened repeated text, and fixed the numbering of one list in `SKILL.md`. Step 0 now uses the word "item" for its entries in all files.
- `trim-artifacts`: Moved the glob and regex instructions to the new file `references/protect-set.md`. Moved the script results to the new file `references/script-results.md`. Removed the section "Common failure modes".
- `git-worktree-management` and `merge-worktree-projects`: Shortened repeated text. Workflow D now says where `owner` and `repo` come from.
- `implement-task`, `implement-batch`, and `research-implement-review-report`: The three files now share one list for the division of labor. The guardrails no longer repeat the autonomy rules.
- `implement`, `opsx-implement`, and `save-context`: Removed repeated guardrails. `save-context` now states the output path for `--change` and `--plan`.
- `create-html-artifact` and `help-review-pr`: Shortened the text. `create-html-artifact` now says which mermaid tests run in which pass.
- `create-documentation`: Moved the four document templates to the new files `templates/feature.md`, `templates/configuration.md`, `templates/rest-api.md`, and `templates/migration.md`. A run reads only the template that it needs.
- `write-markdown`: Removed paths of another repository and two copies of the `markdownlint` commands.
- `write-tests`, `compose-pr`, `task-composer`, `docs-composer`, and the audit commands and agents: Removed repeated guardrails and infrastructure nouns from the examples. `audit-team` now passes two guardrails to its review agents.
- `engineering-discipline`, `dotnet-build-test`, `github-mcp-conventions`, `git-sync`, and `project-claude-md-preamble`: Shortened the text and removed a pointer to a section that does not exist.
- The shared "Autonomy" section in all workflows: Rewrote one condition so that it follows the plain-English rules. The meaning is the same.

### Fixed in dev-essentials

- `feature-pipeline`: A security-review finding that is `[HIGH]` and blocking now counts as a blocking issue. It goes to the fix round. With `--autonomous`, a remaining one stops the run before the push. Before, only `review.md` counted.
- `create-html-artifact`: The `mmdc` run and the `_test-mermaid.html` page run only in a fix pass. The grep counts always run.
- `help-review-pr` and `github-mcp-conventions`: The GitHub MCP parameter names now match the tool schemas, for example `pullNumber` and `perPage`.
- `github-mcp-conventions`: Rule 4 no longer says that no MCP tool can discard a pending review. It tells the agent not to discard or edit comments through MCP, and to use the GitHub UI.
- `git-sync`: The fix recipe now puts the saved commits back as a range. Several commits above the broken commit are now safe.
- `process-pr-comments`: A non-trivial `[Optional]` comment whose direction the comment or the code settles is now implemented, as for `[Suggestion]`. The decline draft is only for comments that nothing settles.
- `bug-hunt`: In the default mode, the run no longer waits for an "OK" that never comes. With `--interactive`, it still waits.

### Changed in dotnet-backend-dev

- `dotnet-conventions`, `handle-sensitive-data`, and `model-mapping`: The text now follows plain-English rules. Removed a repeated section and a stale claim from `dotnet-conventions`.
- `add-migration`: Moved the common patterns to the new file `references/common-patterns.md`.
- `add-configuration-option`, `create-controller`, `create-ef-entity`, and `update-swagger-spec`: Shortened the text and replaced `mermaid` fences that held no diagram.
- `create-tests`: Removed the code and the lists in `SKILL.md` that repeat the example files. Added a checklist of the seven enforced gates. The gates apply to every test class, and the text now says so.
- `create-domain-model`, `create-exception`, `create-primitive-wrapper`, `create-string-resource`, and `add-session-logging`: The text now follows plain-English rules, and the examples use neutral business nouns and full method bodies.

### Fixed in dotnet-backend-dev

- `update-swagger-spec`: The controller sketch now says that the class name, the base class, and the try-catch rule come from `create-controller`.
- `create-ef-entity`: An application service is created for each case in the list, also for validation across entities. Before, one line named only orchestration.
- `add-configuration-option`: Helm is now an example. The checklist works for any deployment system.

### Changed in gop-pipeline

- `gop-work`: Moved the routing for `--interactive` to the new file `references/interactive-routing.md`. The text now follows plain-English rules.
- The eight `gop-` agents: The text now follows plain-English rules. The five validators now run `git diff HEAD`, so they read both the staged and the unstaged changes.

### Fixed in gop-pipeline

- `gop-work`: After the second re-run cycle, the run starts no third cycle. If only warnings remain, it goes to Phase 5 and lists the warnings in the final report.
- `gop-work`: The text now uses the tool name `Agent`, not the old name `Task`.

## dev-essentials 2.4.0 and gop-pipeline 1.1.0 in release [2.4.0] - 2026-10-13

### Added in dev-essentials

- `save-context`: Added Step 5, a light cleanup of the context and handoff files of the session. It runs by default, and `--no-cleanup` turns it off. It deletes finished context files that git does not track. It trims files that open work still needs, updates facts that are no longer true, and fixes links to deleted files. It asks before it deletes a file from an older session or a branch. If another command runs the steps of `save-context`, the cleanup does not run.

### Changed in dev-essentials

- Workflows with decision gates now run without a stop at those gates by default. Deletion of data, posts to outside systems, push, and pull request creation still wait for the user. The new flag `--interactive` brings back every gate. The new flag `--autonomous` removes every stop, also before deletion, posts, push, and pull request creation. It does not add steps: a push that needs `--push` still needs it. It merges only where a workflow has a merge step and the branch policy allows a merge without a review. If the work cannot continue without an answer, the workflow asks in every mode. Each workflow carries the same "Autonomy" section.
- Without `--autonomous`, the workflows ask about a critical decision that has no ground in the plan. With `--autonomous`, they choose the option that follows the plan and the existing code, and list the decision in the final report for review. They do not destroy git work that has no other copy, for example a branch with unmerged commits or uncommitted changes. One exception: a squash merge makes `git branch -d` refuse a branch whose content is in the base branch. Two conditions must be true before they delete such a branch with `git branch -D`. First, its pull request is merged (read through the GitHub MCP tools). Second, the local tip equals the head SHA of that pull request. Else they keep the branch and list it in the final report. This rule does not cover a context file that a cleanup step classifies for deletion.
- The change covers 13 workflows. Commands: `research-implement-review-report`, `implement-task`, `implement-batch`, `implement`, `opsx-implement`, and `save-context`. Skills: `review-loop`, `feature-pipeline`, `process-pr-comments`, `audit-personal-conventions`, `bug-hunt`, `trim-artifacts`, and `git-worktree-management`.
- `review-loop`: Without `--interactive`, the run does not wait at the Phase 4 triage. With `--autonomous`, it also decides a finding that is not clear-cut. It lists the decision in the new Phase 9 section "Decisions for your review".
- `process-pr-comments`: By default, it implements larger fixes and non-trivial suggestions whose approach or direction the comment or the code settles. The new parameter `interactive` brings back draft-and-wait. `autonomous` covers question and discussion replies, design-level fixes, and push. It now also creates `[OutOfScope]` issues through Task Composer without a question. If both `interactive` and `autonomous` are set, the skill asks once which mode to use.
- `feature-pipeline`: Human Approve #1 stops only with `--interactive`. In the default mode, Task Comment #1 waits for Human Approve #2, which stops. With `--interactive` or `--autonomous`, the run posts Task Comment #1 before implementation. With `--autonomous`, Human Approve #2 stops in one case: blocking issues remain after the automatic fix round. Without `--interactive`, one automatic fix round runs before Human Approve #2 shows open blocking issues.
- `audit-personal-conventions`: Phase 5 approves the recommended C, D, and E items by default and defers the rest. Phase 9a asks once before it writes stubs. With `--autonomous`, no Phase 9 gate stops. This includes the per-repo push gate. The precondition tests before each gate still run.
- `engineering-discipline` Rule 2: If an auto-approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Else the decision stays a question for the user. With `--autonomous`, the agent chooses the option that follows the plan and the existing code, and lists the decision for the user to review.
- `github-mcp-conventions` Rule 1: Without `--interactive`, a workflow that documents it (`bug-hunt`) can take `owner/repo` from the `origin` remote. It must report the value as taken from the remote.
- `subagent-orchestration`: A workflow that runs with its default autonomy uses Opus instead of a question about Fable. The run-format agreement can come from no objection.
- `subagent-orchestration`: Rule 5 now allows `SendMessage` to your own subagent by its agent ID. Use it to resume the subagent after a stop, or to correct it on the same task. The rule still forbids `name`, `team_name`, shared task lists, and messages between subagents. Rule 3 and the anti-patterns now say the same.
- `subagent-orchestration`: Replaced the section `Trust but verify` with three tiers. The orchestrator checks cheap facts, and an agent checks the content. Only before a high-risk action, the orchestrator re-reads the lines that the action depends on. The "Check scope" part of "Run format agreement" now points to these tiers.
- `process-pr-comments` and `audit-personal-conventions`: Replaced the claim that a subagent cannot get a follow-up message. The Claude Code docs show that `SendMessage` can resume a subagent.
- `save-context`: `Confirm to user` is now Step 6, and the next-session continuation prompt is now Step 7.
- `research-implement-review-report` and `implement-task`: The final report no longer ends with the next-session continuation prompt of `save-context`. The commands print the report only.
- `task-composer`: If the user ran a calling skill with `autonomous`, that skill can approve `mode: create` for the user.

### Removed in dev-essentials

- `save-context`: Removed the tip to use `--context <path>` with `/implement` or `/opsx-implement`.
- `review-loop`: Removed the flag `--auto-proceed`. The run waits at the Phase 4 triage only with `--interactive`.
- `process-pr-comments`: Removed the parameter `auto-push`. To push without a question, ask for the push in the request. The parameter `autonomous` removes all gates of the skill.

### Changed in gop-pipeline

- `gop-work`: Without `--interactive`, Explore and Plan agents write the plan, and the run approves it. The run accepts every validation proposal with a confidence of 90% or more. When the result is `BLOCKED`, it also accepts every CRITICAL proposal. The push now waits for the approval of the user. With `--interactive`, Plan Mode and the old routing come back, and the plan approval covers the push. With `--autonomous`, no gate stops, and `gop-commit` pushes without a question.
- `gop-commit`: New input `push` (`yes` or `no`, default `no`).

## dev-essentials 2.3.0 in release [2.3.0] - 2026-10-13

### Added

- Added the skill `bug-hunt`. It runs a read-only bug hunt over a whole repository and saves one verified bug report. It exports the analyzed commit and the base branch with `git archive`. It splits the code into areas. It skips known bugs from notes files and GitHub issues. It never creates GitHub issues. Its step-0 meta-plan states the run format: the orchestrator checks only the structure of the report, and chat gets at most one status line for each step and one final report. A run context file keeps the stable facts of the run for the agents and for later rounds. The final chat report is saved as `bug-hunt-final-summary.md`. The user can turn off the base comparison, clone a newer base from the remote, and turn off experiments. The user can also set pause points with a scheduled resume.
- Added 8 reference files to the skill `bug-hunt`: `report-format.md`, `report-skeleton.md`, `plain-english-fallback.md`, `agent-briefs.md`, `structure-checks.md`, `pauses.md`, `inputs-and-meta-plan.md`, and `resume-and-failures.md`. Added the script `scripts/check_report.py`. It runs the structure checks of the report. It needs Python 3 and only its standard library.
- Added the agents `bug-hunter`, `bug-verifier`, and `bug-report-auditor`. One hunter searches each area in turn. Verifiers try to refute each finding and set a verdict. The auditor makes sure that the whole report is consistent. The hunters and verifiers can read public documentation, third-party sources, and GitHub data through read-only `gh` commands.
- Added the section "Run format agreement" to the skill `subagent-orchestration`. At the start of a long run, an orchestrating skill states what the orchestrator checks itself and what only the verifier or reviewer agents check. Chat gets at most one short status line for each phase and one final report. When the user agrees, this check scope replaces the generic "re-check every subagent claim" rules for that run only.

### Changed

- `review-loop`: States the run format after Phase 2. It applies from that statement unless the user objects. The Phase 4 acknowledgment gives the final agreement. With `--auto-proceed`, it applies without a stop. While it applies, chat gets one status line for each cycle, and the cycle reports go to files. If the user defines an end-of-run format, the final report uses it. When a calling workflow runs review-loop, the Phase 9 summary goes to that workflow.

## dev-essentials 2.2.0 in release [2.2.0] - 2026-10-11

### Added

- Added the skill `trim-artifacts`. It runs a trim pass on text artifacts. These include notes, plans, research, state files, handoff files, agent memory, logs, and task lists. It removes history, review records, process residue, and duplication. It keeps decisions, ids, needed facts with their sources, and uncertainty markers.
- Added 4 reference files and `scripts/trim_report.py` to the skill `trim-artifacts`. The script is written in Python and uses only the standard library. It compares the files before and after a trim. If a trim loses an id or a protected block, the script fails.

## gop-pipeline 1.0.2 in release [2.1.0] - 2026-08-31

### Fixed

- Gave the 8 pipeline agents a `description` field in their frontmatter. The agents are `gop-build`, `gop-commit`, `gop-test`, and the five `gop-validate-*` validators. The field says what each agent does and that it runs as a stage of the `gop-work` pipeline. This removes the 8 `claude plugin validate` warnings about agent frontmatter that had no `description`.

## dev-essentials 2.1.0 and dotnet-backend-dev 1.2.0 in release [2.1.0] - 2026-08-31

This release ported and generalized several skills, commands, and rule additions from a separate internal iteration of this toolkit. It stripped or transformed branding and tooling to fit the conventions of this marketplace. The release includes a full fidelity pass. The pass compared every skill, command, and agent against its upstream counterpart. It restored content that the port silently dropped. The release also includes a marketplace-wide de-branding cleanup.

### Added in dev-essentials

- Added these skills:
  - `audit-personal-conventions`: Performs a deep verification of personal/repo-convention drift. It has 2 worked examples and 4 reference files.
  - `create-html-artifact`: Renders a self-contained HTML report, plan, or review file. It has 4 reference files.
  - `project-claude-md-preamble`: Keeps the `CLAUDE.md` preamble of a project self-contained.
- Added the commands `help-review-pr`, `merge-worktree-projects`, `research-implement-review-report`, `implement-task`, and `implement-batch`. The command `help-review-pr` reviews a GitHub PR end-to-end and produces an HTML artifact. It can also post the findings as review comments.
- `feature-pipeline`: Added a new Stage 2b (`stages/plan-artifact.md`). The stage renders the approved implementation plan as an HTML artifact through `create-html-artifact` for Human Approve #1. Also added an anti-bypass gate, an archiving gate, and a commit-mode option.
- `review-loop`: Added an audit-team adapter, a `blocking` finding flag, and an orchestrated mode for large-target reviews (`references/orchestrated-review.md`).
- `process-pr-comments`: Added real wiring for resolving GitHub threads and a filter for resolved and outdated threads. Updated `references/thread-state-schema.md`.
- `engineering-discipline`: Added Rules 4–7: try/catch discipline, proof-before-claiming-done, an overblown-code guardrail, and refactor-scope discipline.
- `subagent-orchestration`: Fixed Rule 3. Added new Rules 5–7 and a model-selection matrix.
- `save-context`: Added a next-session continuation prompt.
- Added notes and sections to these skills and agents:
  - `create-documentation`
  - `git-sync`
  - `git-worktree-management`
  - `general-conventions` (documentation and PowerShell)
  - The `task-composer` agent (GitHub sub-issue create flow)

### Added in dotnet-backend-dev

- `create-tests`: Rewrote the mock-builder parameters to use `.ApplyIf`. A single `Create*` helper for each dependency takes optional nullable parameters. The helper applies them with `.ApplyIf`. This replaces the old overload-based pattern. Also added a new `enforced-gates.md` example.
- `dotnet-conventions`: Added notes to `ef-patterns.md` and `testing.md`.

### Changed in dev-essentials

- `review-loop`: Restored the shipped default configuration that the port dropped. The configuration has these parts:
  - 2 review cycles (not 3)
  - An Opus reviewer and a Sonnet fixer by default
  - A plan for each fix, made by the reviewer's tier before the fixer implements it
  - One commit per round
  - Merit-based (not label-based) triage
- `research-implement-review-report` and `implement-batch`: Updated the commands to describe the default configuration of `review-loop` accurately. They no longer imply a manual model override.
- `audit-team`: Replaced the non-functional foreground or background `mode` argument with a cross-reference to Rule 3 of `subagent-orchestration`. The `Agent` tool has no such mode.
- `process-pr-comments`: Restored the two-stage dispatch model. It has a read-only classifier stage and a judgment-bearing actor stage after it. It also has a hand-back to the orchestrating session for `deep-fix` cycles. Restored the contract for the Stage 1 report in `references/thread-state-schema.md`.

### Fixed in dev-essentials and dotnet-backend-dev

- Fidelity pass: Restored the content below from the upstream source. The initial port silently dropped it.
  - Rule 2 of `dotnet-build-test`: Restored the `--no-build` stale-referenced-binary caveat. A solution-level build can leave a test project that links an old DLL and report a false-green run. Restored the verbatim-proof reporting gate. Restored the guidance "warning-count deltas across incremental builds are meaningless".
  - `process-pr-comments`: Restored the rule for a carried-over unconfirmed-commit-claim thread. The skill resolves the thread automatically only after the human approves the resolve. The ancestry check alone does not resolve it. Made the `[OutOfScope]` issue-creation flow route through Task Composer consistently. Restored the safeguard "never defer reviewer-stated work without an `[OutOfScope]` tag" and its list of forbidden phrasing.
  - `feature-pipeline`: Restored the rationale for Project Context Injection. Restored the `{WORKTREE_PATH}` placeholder in the command that removes the worktree in Stage 10. The command regressed to a hardcoded relative path before this fix. Restored the trigger phrases and the rationale for bulk cleanup. Restored a concrete sandboxed-terminal example.
  - `git-worktree-management`: Restored the note that whoever runs the worktree removal workflow executes it and must not re-delegate it. Restored the note "bulk removal archives first, then removes per-path".
  - `github-mcp-conventions`: Restored a rule to make sure that a created issue relationship was actually applied. Restored a rule to read large PR diffs from local git, not from an MCP call that uses many tokens.
  - `create-tests`: Restored the dropped cross-reference "the same null-argument gate applies to methods". Restored a mixed static and instance test-helper example. Fixed an intro example that used `params` in violation of Rule 6 of the same skill.
  - Restored smaller passages in `opsx-implement`, `implement`, `help-review-pr`, `save-context`, `subagent-orchestration`, `git-sync`, and `engineering-discipline`.
- Completed the de-branding:
  - Replaced residual cloud-vendor identifiers (AWS, Azure, and Cosmos names) in the example code of `dotnet-backend-dev` with neutral business nouns. This covers `create-tests`, `add-migration`, `create-controller`, `model-mapping`, `update-swagger-spec`, and `dotnet-conventions/logging.md`.
  - Fixed a `DeploymentOptions` type-name collision in a `create-tests` example.
  - Replaced the remaining "work item" and Azure DevOps terminology across the marketplace with GitHub or provider-neutral equivalents.
  - Made the OpenSpec tracking-reference bullet of `save-context` specific to GitHub Issues and Projects.
- `dotnet-build-test` and `task-composer`: Fixed broken YAML frontmatter.

## dev-essentials 2.0.0 and dotnet-backend-dev 1.1.0 in release [2.0.0] - 2026-05-10

### Added in dev-essentials

- Added the skills `engineering-discipline`, `subagent-orchestration`, `git-sync`, `dotnet-build-test`, `review-loop`, and `github-mcp-conventions`. The skill `review-loop` came with 4 reference files and 2 worked examples.
- `review-loop`: Kept the trigger phrases `/review-loop` and `/review-pr` in the frontmatter description. GitHub MCP replaced ADO MCP for `target=pr` mode.
- `process-pr-comments`: Added `references/automated-review-verification.md`, which replaces `air-verification.md`. Added a GitHub-native phase flow (`pull_request_read`, `add_reply_to_pull_request_comment`) and a configurable bot-author list.
- `feature-pipeline`: Added a Pipeline Discipline section (3 safeguards). Added a note on Safeguard 2 in Human Approve #2, and a `pr` field in the schema of `pipeline-state.json`. Added gated worktree removal in Step 10 through GitHub MCP.
- Audit commands (`audit-plan`, `audit-openspec`, `audit-team`): Added a guardrail that requires verification before a fix.

### Added in dotnet-backend-dev

- `create-tests`: Added the section Constructor Null-Argument Tests (foreach-over-List\<Action\> pattern, anti-pattern: boolean stripes). Added the section Scenario Tests (stubs only, no mocking). Added the section Test Scope and Props Files.
- `create-tests/examples`: Added `constructor-null-arg-tests.md` and `scenario-tests.md`.

### Changed in dev-essentials

- `task-composer` agent: Rewrote the agent with three modes (draft, response, and create). Added a GitHub issue workflow (`issue_write` and `issue_read`). The workflow has two steps: create the issue, then make sure that it was created. Added a cross-reference to Rule 1 of `github-mcp-conventions`.
- `git-worktree-management`: Added a new path scheme `.claude/worktrees/<branch>/`, bootstrap steps, PR-status discovery through GitHub MCP (Workflow D), and a keep-until-PR-merged lifecycle.
- `process-pr-comments`: Rewrote the skill on top of GitHub MCP throughout. Removed the legacy work-item-ID prefix from the commit message. Changed the thread anchors to use `html_url`. Changed the `[OutOfScope]` tracking to use `issue_write` for tracking-issue creation. Updated `references/thread-state-schema.md` to GitHub field names.
- `feature-pipeline` Step 0: Changed worktree creation to delegate to Workflow A of `git-worktree-management`. It no longer uses inline git commands.
- Skill cross-references: Removed legacy upstream prefixes from all cross-reference names.

### Removed in dev-essentials

- Removed the commands `review-loop.md` and `review-pr.md`. The trigger phrases now live in the frontmatter description of the skill `review-loop`.
- Removed `process-pr-comments/references/air-verification.md`. The file `automated-review-verification.md` replaces it.

### Breaking changes in dev-essentials

- `task-composer` is now native to GitHub MCP. It calls `issue_write` and `issue_read` instead of any other PR-provider MCP tool. Existing non-GitHub workflows break.
- `process-pr-comments` now works only with GitHub MCP. It requires the GitHub MCP server. Existing non-GitHub workflows break.
- Deleted the commands `/dev-essentials:review-loop` and `/dev-essentials:review-pr`. Use the skill `review-loop` instead. Its description has the trigger phrases `/review-loop` and `/review-pr`.

## [1.0.2] - 2026-05-08

### Added

- `marketplace.json`: Added a top-level `description` so that the Discover tab shows a one-line summary.
- All 3 `plugin.json` manifests: Added `$schema`, a JSON Schema reference for editor validation. Added `repository`, a link back to this GitHub repository. Added per-plugin `keywords` for the Discover tab.
- `CLAUDE.md`: Added a Versioning Policy section. It has semver bump rules for each plugin, a single-source-of-truth rule for `version`, and an update-propagation flow.
- `README.md`: Added a Validating section that points at `claude plugin validate`. Added a References section that links the three official documentation pages for Claude Code plugins.

### Changed

- Bumped all 3 plugins from `1.0.0` to `1.0.1`. The manifest contract changed because of new metadata fields. We recommend that consumers re-fetch at the next `/plugin marketplace update`.
- `README.md`: Corrected the slash command from `/plugins marketplace add` to `/plugin marketplace add`. The singular form follows the current Claude Code documentation.
- `README.md` configuration examples: Replaced the undocumented shapes `plugins.marketplaces[]` and `plugins.sources[]` with the documented `extraKnownMarketplaces` and `enabledPlugins` configuration. The examples use `"source": "git"` with no `.git` suffix on the URL. This matches what Claude Code writes on install.
- `README.md` schema examples: Added a top-level `description` to the `marketplace.json` example and removed the per-plugin `version` from it. Added `$schema`, `repository`, and `keywords` to the `plugin.json` example.

### Removed

- `marketplace.json`: Removed the per-plugin `version` field from each entry inside `plugins[]`. Plugin versions live only in each `plugin.json`. This follows the new Versioning Policy.

### Fixed

- `README.md`, section "Installing a single plugin": Corrected the name of the configuration file from `.claude/settings.json` to `.claude/settings.local.json`. The file name now matches the file that the marketplace-add snippet above this section targets. This stops users from defining `extraKnownMarketplaces` in two different configuration files.

## [1.0.1] - 2026-05-04

### Changed

- Renamed the marketplace from `vasar-claude-marketplace` to `vasar-plugins-marketplace`. The new name matches the data model of Claude Code. The file `marketplace.json` lists plugins, so "plugins" is the more accurate name for the category.
- Updated all repository URL references in `README.md` and `CHANGELOG.md` to the new GitHub URL. The GitHub repository was renamed in the Web UI. Git redirects the old URL automatically.

### Fixed

- `README.md` schema example for `plugin.json`: Removed the directory-string fields `skills`, `agents`, and `commands` (for example `"./skills/"`). The example now mirrors the metadata-only manifests that this repository ships. It also explains that Claude Code discovers components automatically from the default locations.

## [1.0.0] - 2026-05-04

### Added

- Added the initial marketplace layout with three plugins:
  - `dev-essentials` has four composer agents (PR, Task, Test, Docs), ten workflow commands, and seven cross-stack skills. The skills cover markdown, XML docs, git worktrees, PR review comments, feature pipeline, general conventions, and `create-documentation`.
  - `dotnet-backend-dev` has fifteen .NET, Clean Architecture, DDD, EF Core, OpenAPI, and Mapperly skills. It also has a backend conventions hub with nine topic references. The topics are controllers, services, configuration, domain models, EF patterns, logging, mappers, security, and testing.
  - `gop-pipeline` is the Git Operations Pipeline workflow. The stages run in this order: `plan`, `implement`, `build`, `test`, `validate`, `commit`. It has five parallel validator subagents for correctness, reuse, security, compliance, and performance. It also has build, test, and commit agents.
- Added the repository artifacts:
  - A README with install instructions and an authoring reference
  - An MIT LICENSE
  - A root `CLAUDE.md` with documentation-first guardrails and repository conventions
  - This CHANGELOG
  - `.gitignore`
- Added the manifest layout. The file `.claude-plugin/marketplace.json` lists the three plugins. Each `plugin.json` declares only metadata (name, version, description, author). It relies on Claude Code to discover components automatically at the documented default locations: `skills/`, `commands/`, and `agents/`.

[Unreleased]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.5.0...HEAD
[7.5.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.4.0...v7.5.0
[7.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.3.0...v7.4.0
[7.3.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.2.2...v7.3.0
[7.2.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.2.1...v7.2.2
[7.2.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.2.0...v7.2.1
[7.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.1.0...v7.2.0
[7.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v7.0.0...v7.1.0
[7.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.2.3...v7.0.0
[6.2.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.2.2...v6.2.3
[6.2.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.2.1...v6.2.2
[6.2.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.2.0...v6.2.1
[6.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.1.3...v6.2.0
[6.1.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.1.2...v6.1.3
[6.1.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.1.1...v6.1.2
[6.1.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.1.0...v6.1.1
[6.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v6.0.0...v6.1.0
[6.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.9...v6.0.0
[5.4.9]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.8...v5.4.9
[5.4.8]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.7...v5.4.8
[5.4.7]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.6...v5.4.7
[5.4.6]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.5...v5.4.6
[5.4.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.4...v5.4.5
[5.4.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.3...v5.4.4
[5.4.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.2...v5.4.3
[5.4.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.1...v5.4.2
[5.4.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.4.0...v5.4.1
[5.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.3.1...v5.4.0
[5.3.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.3.0...v5.3.1
[5.3.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.2.1...v5.3.0
[5.2.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.2.0...v5.2.1
[5.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.1.0...v5.2.0
[5.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.0.2...v5.1.0
[5.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.0.1...v5.0.2
[5.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v5.0.0...v5.0.1
[5.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.28.0...v5.0.0
[4.28.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.27.0...v4.28.0
[4.27.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.26.0...v4.27.0
[4.26.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.25.3...v4.26.0
[4.25.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.25.2...v4.25.3
[4.25.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.25.1...v4.25.2
[4.25.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.25.0...v4.25.1
[4.25.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.24.0...v4.25.0
[4.24.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.23.1...v4.24.0
[4.23.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.23.0...v4.23.1
[4.23.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.22.1...v4.23.0
[4.22.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.22.0...v4.22.1
[4.22.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.21.0...v4.22.0
[4.21.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.20.0...v4.21.0
[4.20.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.19.0...v4.20.0
[4.19.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.18.0...v4.19.0
[4.18.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.17.2...v4.18.0
[4.17.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.17.1...v4.17.2
[4.17.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.17.0...v4.17.1
[4.17.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.16.1...v4.17.0
[4.16.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.16.0...v4.16.1
[4.16.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.15.0...v4.16.0
[4.15.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.14.5...v4.15.0
[4.14.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.14.4...v4.14.5
[4.14.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.14.2...v4.14.4
[4.14.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.14.1...v4.14.2
[4.14.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.14.0...v4.14.1
[4.14.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.13.0...v4.14.0
[4.13.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.12.2...v4.13.0
[4.12.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.12.1...v4.12.2
[4.12.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.12.0...v4.12.1
[4.12.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.7...v4.12.0
[4.11.7]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.6...v4.11.7
[4.11.6]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.5...v4.11.6
[4.11.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.4...v4.11.5
[4.11.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.3...v4.11.4
[4.11.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.2...v4.11.3
[4.11.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.1...v4.11.2
[4.11.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.11.0...v4.11.1
[4.11.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.10.0...v4.11.0
[4.10.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.9.0...v4.10.0
[4.9.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.8.6...v4.9.0
[4.8.6]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.8.5...v4.8.6
[4.8.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.8.4...v4.8.5
[4.8.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.8.3...v4.8.4
[4.8.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.8.2...v4.8.3
[4.8.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.8.1...v4.8.2
[4.8.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.8.0...v4.8.1
[4.8.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.8...v4.8.0
[4.7.8]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.7...v4.7.8
[4.7.7]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.6...v4.7.7
[4.7.6]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.5...v4.7.6
[4.7.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.4...v4.7.5
[4.7.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.3...v4.7.4
[4.7.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.2...v4.7.3
[4.7.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.1...v4.7.2
[4.7.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.7.0...v4.7.1
[4.7.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.6.0...v4.7.0
[4.6.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.5.5...v4.6.0
[4.5.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.5.4...v4.5.5
[4.5.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.5.3...v4.5.4
[4.5.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.5.2...v4.5.3
[4.5.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.5.1...v4.5.2
[4.5.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.5.0...v4.5.1
[4.5.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.4.0...v4.5.0
[4.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.2.5...v4.4.0
[4.2.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.2.4...v4.2.5
[4.2.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.2.3...v4.2.4
[4.2.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.2.2...v4.2.3
[4.2.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.2.1...v4.2.2
[4.2.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.2.0...v4.2.1
[4.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.1.1...v4.2.0
[4.1.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.1.0...v4.1.1
[4.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.0.0...v4.1.0
[4.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.10.0...v4.0.0
[3.10.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.9.0...v3.10.0
[3.9.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.8.0...v3.9.0
[3.8.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.7.0...v3.8.0
[3.7.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.5...v3.7.0
[3.6.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.4...v3.6.5
[3.6.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.3...v3.6.4
[3.6.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.2...v3.6.3
[3.6.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.1...v3.6.2
[3.6.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.0...v3.6.1
[3.6.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.5.0...v3.6.0
[3.5.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.4.0...v3.5.0
[3.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.3.1...v3.4.0
[3.3.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.3.0...v3.3.1
[3.3.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.3...v3.3.0
[3.2.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.2...v3.2.3
[3.2.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.1...v3.2.2
[3.2.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.0...v3.2.1
[3.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.1.1...v3.2.0
[3.1.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.1.0...v3.1.1
[3.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.0.2...v3.1.0
[3.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.0.1...v3.0.2
[3.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.0.0...v3.0.1
[3.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.5.0...v3.0.0
[2.5.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.2...v2.5.0
[2.4.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.1...v2.4.2
[2.4.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.0...v2.4.1
[2.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/releases/tag/v1.0.0
