# Changelog

This file records all notable changes to this marketplace.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for each plugin separately.
For the current version of a plugin, see the `plugin.json` file of that plugin.
In each release heading, the linked number is the release tag of the marketplace, for example `v2.1.0`.
The other numbers in a heading are plugin versions.

## [Unreleased]

No changes yet.

## dev-essentials 2.4.1, dotnet-backend-dev 1.2.1, and gop-pipeline 1.1.1 in release [2.4.1] - 2026-10-14

### Changed in dev-essentials

- All text in the changed skills, commands, and agents now follows plain-English rules. This means short sentences, active voice, one word for one meaning, and no filler. The workflow rules are the same. The notes below name what moved and where.
- `subagent-orchestration`: Moved the three worked examples to the new file `references/worked-examples.md`. Rule 3 now lists the current parameters of the `Agent` tool.
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
- `create-tests`: Removed the repeated example files from `SKILL.md`. The seven enforced gates now apply to every test class, and the text says so.
- `create-domain-model`, `create-exception`, `create-primitive-wrapper`, `create-string-resource`, and `add-session-logging`: The text now follows plain-English rules, and the examples use neutral business nouns and full method bodies.

### Fixed in dotnet-backend-dev

- `update-swagger-spec`: The controller sketch now says that the class name, the base class, and the try-catch rule come from `create-controller`.
- `create-ef-entity`: An application service is created for each case in the list, also for validation across entities. Before, one line named only orchestration.
- `add-configuration-option`: Helm is now an example. The checklist works for any deployment system.

### Changed in gop-pipeline

- `gop-work`: Moved the routing for `--interactive` to the new file `references/interactive-routing.md`. The text now follows plain-English rules.
- The eight `gop-` agents: The text now follows plain-English rules. The validators now say how they read staged, unstaged, and new files.

### Fixed in gop-pipeline

- `gop-work`: After the second re-run cycle, the run starts no third cycle. If only warnings remain, it goes to Phase 5 and lists the warnings in the final report.
- `gop-work`: The text now uses the tool name `Agent`, not the old name `Task`.

## dev-essentials 2.4.0 and gop-pipeline 1.1.0 in release [2.4.0] - 2026-10-13

### Added in dev-essentials

- `save-context`: Added Step 5, a light cleanup of the context and handoff files of the session. It runs by default, and `--no-cleanup` turns it off. It deletes finished context files that git does not track. It trims files that open work still needs, updates facts that are no longer true, and fixes links to deleted files. It asks before it deletes a file from an older session or a branch. If another command runs the steps of `save-context`, the cleanup does not run.

### Changed in dev-essentials

- Workflows with decision gates now run without a stop at those gates by default. Deletion of data, posts to outside systems, push, and pull request creation still wait for the user. The new flag `--interactive` brings back every gate. The new flag `--autonomous` removes every stop, also before deletion, posts, push, and pull request creation. It does not add steps: a push that needs `--push` still needs it. It merges only where a workflow has a merge step and the branch policy allows a merge without a review. If the work cannot continue without an answer, the workflow asks in every mode. Each workflow carries the same "Autonomy" section.
- Without `--autonomous`, the workflows ask about a critical decision that has no ground in the plan. With `--autonomous`, they choose the option that follows the plan and the existing code, and list the decision in the final report for review. They do not destroy git work that has no other copy, for example a branch with unmerged commits or uncommitted changes. One exception: a squash merge makes `git branch -d` refuse a branch whose content is in the base branch. They delete such a branch with `git branch -D` only if its pull request is merged (read through the GitHub MCP tools) and the local tip equals the head SHA of that pull request. Else they keep the branch and list it in the final report. This rule does not cover a context file that a cleanup step classifies for deletion.
- The change covers 13 workflows. Commands: `research-implement-review-report`, `implement-task`, `implement-batch`, `implement`, `opsx-implement`, and `save-context`. Skills: `review-loop`, `feature-pipeline`, `process-pr-comments`, `audit-personal-conventions`, `bug-hunt`, `trim-artifacts`, and `git-worktree-management`.
- `review-loop`: Without `--interactive`, the run does not wait at the Phase 4 triage. With `--autonomous`, it also decides a finding that is not clear-cut, and lists the decision in the new Phase 9 section "Decisions for your review".
- `process-pr-comments`: By default, it implements larger fixes and non-trivial suggestions whose approach or direction the comment or the code settles. The new parameter `interactive` brings back draft-and-wait. `autonomous` covers question and discussion replies, design-level fixes, and push. It now also creates `[OutOfScope]` issues through Task Composer without a question. If both `interactive` and `autonomous` are set, the skill asks once which mode to use.
- `feature-pipeline`: Human Approve #1 stops only with `--interactive`. In the default mode, Task Comment #1 waits for Human Approve #2, which stops. With `--interactive` or `--autonomous`, the run posts Task Comment #1 before implementation. With `--autonomous`, Human Approve #2 stops in one case: blocking issues remain after the automatic fix round. Without `--interactive`, one automatic fix round runs before Human Approve #2 shows open blocking issues.
- `audit-personal-conventions`: Phase 5 approves the recommended C, D, and E items by default and defers the rest. Phase 9a asks once before it writes stubs. With `--autonomous`, no Phase 9 gate stops. This includes the per-repo push gate. The precondition tests before each gate still run.
- `engineering-discipline` Rule 2: If an auto-approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Else the decision stays a question for the user. With `--autonomous`, the agent chooses the option that follows the plan and the existing code, and lists the decision for the user to review.
- `github-mcp-conventions` Rule 1: Without `--interactive`, a workflow that documents it (`bug-hunt`) may take `owner/repo` from the `origin` remote. It must report the value as taken from the remote.
- `subagent-orchestration`: A workflow that runs with its default autonomy uses Opus instead of a question about Fable. The run-format agreement can come from no objection.
- `subagent-orchestration`: Rule 5 now allows `SendMessage` to your own subagent by its agent ID. Use it to resume the subagent after a stop, or to correct it on the same task. The rule still forbids `name`, `team_name`, shared task lists, and messages between subagents. Rule 3 and the anti-patterns now say the same.
- `subagent-orchestration`: Replaced the section "Trust but verify" with three tiers. The orchestrator checks cheap facts, an agent checks the content, and the orchestrator spot-checks only before a high-risk action. The "Check scope" part of "Run format agreement" now points to these tiers.
- `process-pr-comments` and `audit-personal-conventions`: Replaced the claim that a subagent cannot get a follow-up message. The Claude Code docs show that `SendMessage` can resume a subagent.
- `save-context`: "Confirm to user" is now Step 6, and the next-session continuation prompt is now Step 7.
- `research-implement-review-report` and `implement-task`: The final report no longer ends with the next-session continuation prompt of `save-context`. The commands print the report only.
- `task-composer`: If the user ran a calling skill with `autonomous`, that skill can confirm `mode: create` for the user.

### Removed in dev-essentials

- `save-context`: Removed the tip to use `--context <path>` with `/implement` or `/opsx-implement`.
- `review-loop`: Removed the flag `--auto-proceed`. The run waits at the Phase 4 triage only with `--interactive`.
- `process-pr-comments`: Removed the parameter `auto-push`. To push without a question, ask for the push in the request. The parameter `autonomous` removes all gates of the skill.

### Changed in gop-pipeline

- `gop-work`: Without `--interactive`, Explore and Plan agents write the plan, and the run approves it. The run accepts validation proposals with a confidence of 90% or more, and every CRITICAL proposal when the result is `BLOCKED`. The push now waits for the approval of the user. With `--interactive`, Plan Mode and the old routing come back, and the plan approval covers the push. With `--autonomous`, no gate stops, and `gop-commit` pushes without a question.
- `gop-commit`: New input `push` (`yes` or `no`, default `no`).

## dev-essentials 2.3.0 in release [2.3.0] - 2026-10-13

### Added

- Added the skill `bug-hunt`. It runs a read-only bug hunt over a whole repository and saves one verified bug report. It exports the analyzed commit and the base branch with `git archive`, splits the code into areas, and skips known bugs from notes files and GitHub issues. It never creates GitHub issues. Its step-0 meta-plan states the run format: the orchestrator checks only the structure of the report, and chat gets at most one status line for each step and one final report. A run context file keeps the stable facts of the run for the agents and for later rounds. The final chat report is saved as `bug-hunt-final-summary.md`. The user can turn off the base comparison, clone a newer base from the remote, turn off experiments, and set pause points with a scheduled resume.
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
  - `gop-pipeline` is the Git Operations Pipeline workflow. The stages run in this order: plan, implement, build, test, validate, commit. It has five parallel validator subagents for correctness, reuse, security, compliance, and performance. It also has build, test, and commit agents.
- Added the repository artifacts:
  - A README with install instructions and an authoring reference
  - An MIT LICENSE
  - A root `CLAUDE.md` with documentation-first guardrails and repository conventions
  - This CHANGELOG
  - `.gitignore`
- Added the manifest layout. The file `.claude-plugin/marketplace.json` lists the three plugins. Each `plugin.json` declares only metadata (name, version, description, author). It relies on Claude Code to discover components automatically at the documented default locations: `skills/`, `commands/`, and `agents/`.

[Unreleased]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.1...HEAD
[2.4.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.0...v2.4.1
[2.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/releases/tag/v1.0.0
