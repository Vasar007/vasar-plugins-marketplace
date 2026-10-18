---
name: audit-personal-conventions
description: "Audit personal Claude Code conventions (memory files, global and project CLAUDE.md files, and personal commands, agents, and skills). Decide which rules to promote into a marketplace plugin. It classifies each rule, shows a triage for approval, authors the approved entities, runs a review loop, and bumps the plugin version."
when_to_use: "Use it for 'audit my memory', 'promote my memory to skills', or 'which of my rules belong in the marketplace'. Do not use it to turn one named rule into a skill."
---

# Audit Personal Conventions

Personal conventions grow without review. They mix project-local trivia, personal taste, rules that many sources repeat, and bug reports against shipped skills. This skill sorts them in one audit-and-triage workflow. It follows the workflow of an earlier ad-hoc promotion of personal memory into a marketplace.

**Hard requirement: no hardcoded marketplace or host name**. Each mention of "the marketplace" resolves from `--marketplace=` and from the `name` field of that `marketplace.json`. This holds for the skill text, its phase prompts, its output templates, and its examples. The target can be a different marketplace than the one that ships this skill. Do not name this marketplace, another specific marketplace, or a specific host in prose, templates, or examples. One exception: you can name the source marketplace of an external, optional tool that this skill mentions.

## When NOT to use

Do not use this skill to promote one rule that the user names directly, for example "turn this into a skill" about one paragraph. Write that entity by hand. If `skill-creator` is installed, you can use it instead. `skill-creator` is an official Anthropic plugin from the `claude-plugins-official` marketplace, and it does not ship with this plugin. This skill is for the audit and triage of many sources at once.

## Path resolution rule

Resolve the Claude config root from the `CLAUDE_CONFIG_DIR` environment variable. If that variable is not set, use the home directory of the user plus `/.claude`. Never hardcode a username, a drive letter, or an absolute path in the text, prompts, or examples of this skill. Write each path relative to the config root or to the repo root.

## Arguments

| Flag | Default | Meaning |
| --- | --- | --- |
| `--scope=<tokens>` | `all` | Tokens, combined with commas: `memory`, `global-claude-md`, `project-claude-md`, `claude-md` (alias for both CLAUDE.md tokens), `personal-entities` (personal global `commands/`, `agents/`, `skills/`), and `all`. If `all` comes with another token, warn and use `all`. If a token is unknown, STOP and list the valid tokens. |
| `--projects=auto\|none\|<list>` | `auto` | `auto` takes every directory under the projects folder of the config root (see Phase 0). It decodes each encoded name by probing candidate paths, collapses worktree siblings into their one real parent repo, and reports the collapse count. `none` means global sources only. A list accepts project names, decoded paths, or encoded directory names. If an entry does not resolve, STOP. |
| `--exclude-projects=<list>` | empty | Remove these projects from the `auto` set. |
| `--marketplace=<path>` | auto-detect | The root of the target marketplace repo, which receives the promoted entities. It can be a different marketplace than the one that ships this skill. If the current working tree contains `.claude-plugin/marketplace.json`, auto-detect uses it. Else, STOP and ask. With `--resume=<path>`, Phase 0 uses its resume order instead. |
| `--target-plugin=<name>` | none (ambiguous: ask) | The default destination plugin in the target marketplace. The triage can choose another plugin for each item. |
| `--min-evidence=<N>` | `1` | Present only the promotion candidates that at least N independent sources corroborate. |
| `--dispositions=<tokens>` | all | Filter for the triage that the run presents: `promote`, `promote-scoped`, `fix-shipped`, `prune`, `keep`. The tokens map to the six dispositions: `promote`=C, `promote-scoped`=D, `fix-shipped`=E, `prune`=F, `keep`=A+B. `keep` covers both leave-alone dispositions, because the run never acts on them. The filter can hide `keep` items from the detail table, but the summary always counts them. |
| `--include-vendored` | off (bare) | Include the vendored or third-party CLAUDE.md files in personal repos, with a clear label. By default, the run excludes them. |
| `--rounds=<N>` | `2` | The number of review cycles for the review-loop skill of the target marketplace (see Phase 7). |
| `--cleanup-mode=stub\|annotate\|none` | `stub` | Applies to fully promoted memory files only. `none` touches nothing for that item, also not its bullet in the `MEMORY.md` index. Details in Phase 9a. |
| `--update-global-claude-md` | off (bare) | **Opt-in.** Without it, Phase 9b only reports which rules of the global CLAUDE.md can become a pointer, and how to re-run to apply them. It edits nothing. With it, Phase 9b asks for each file before it writes (see Phase 9b for the exact question). |
| `--cross-repo=off\|all\|<repo>[,<repo>...]` | `off` | **Opt-in.** Turns on Phase 9c, which edits the tracked CLAUDE.md files of OTHER repos. Bare `--cross-repo` means `--cross-repo=all`. If this run promoted nothing and no `--resume` TODO file is given, the run ignores the flag with a warning. See the 9c-only re-entry mode in Phase 9c and `references/cleanup-and-provenance.md`. |
| `--branch-prefix=<prefix>` | derive from context, else ask | The prefix of the branch name for Phase 9c branches (`<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>`). Default: if a CLAUDE.md file of the project or the global CLAUDE.md states a branch-name convention, take the prefix from it. Else, ask the user once for each run, before the first cross-repo branch. |
| `--delete-personal-entities` | off (bare) | **Opt-in.** Lets Phase 9d delete personal global command, agent, and skill files that an entity supersedes. That entity is either promoted in this run, or already shipped (then Phase 3 classifies the file F-stale). The checks and questions of Phase 9d still gate each deletion. Without the flag, Phase 9d only reports the superseded files with a suggested manual action. |
| `--resume=<path>` | none | Resumes a deferred Phase 9c cleanup from its TODO file, without a new audit. This is the 9c-only re-entry mode (Phase 9c.1). Phase 0 resolves the marketplace root in its resume order. |
| `--dry-run` | off (bare) | Run Phases 0 to 4 only, and stop after the triage. No approval gate, no authoring, no cleanup. |
| `--report=chat\|<path>` | `chat` | Where the final report goes. |
| `--interactive` | off (bare) | Wait at the Phase 5 approval gate. Without it, Phase 5 approves the recommended items itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |

**Only `--autonomous` skips the Phase 9 gates. This includes the per-repo push gate.** The opt-in flags `--update-global-claude-md`, `--cross-repo`, and `--delete-personal-entities` turn on a capability. They do not skip its gates. The Phase 5 approval gate follows "Autonomy". By default, the run approves the recommended items itself. With `--interactive`, it waits.

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
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Guardrails

- Classify per rule, not per file. One source file often mixes dispositions.
- The `type:` frontmatter field is never a category signal by itself. Read the content.
- The corroboration count is the strongest promote signal. Always count it before you propose a new entity.
- An **E** disposition is never a new entity. It is always a fix to an existing shipped entity, and then the run prunes the source.
- Never auto-edit a project-repo CLAUDE.md without `--cross-repo`.
- Never push without an explicit per-repo yes, even with `--cross-repo` set. `--autonomous` counts as that yes.
- Never push the commits of the target marketplace either, unless the user explicitly says so elsewhere in the session.
- Never delete a personal entity file without all of these: `--delete-personal-entities`, its automated check of publication and local load, the once-per-run marketplace-publish gate, and its own per-file question. `--autonomous` counts as the publish gate and the per-file yes. The automated check still runs.
- Never touch a file outside the provenance list of an approved item.
- Never assign a disposition to a wrapper personal entity before a full-text diff against its wrapped entity.

## References and examples

| File | When to read |
| --- | --- |
| `references/source-inventory.md` | Phase 0 and Phase 1: the discovery paths, decode-and-probe, the worktree-sibling collapse, the wrapper diff, and the twelve structural landmines. |
| `references/classification-framework.md` | Phase 3: the full decision tree, the tie-breakers, and the calibration cases. |
| `references/report-templates.md` | Phase 4 (the triage template) and Phase 10 (the run report template). |
| `references/entity-authoring-conventions.md` | Phase 6: the entity kind, the frontmatter, the body structure, and the commit discipline. |
| `references/cleanup-and-provenance.md` | Phase 9: the templates, the full 9c and 9d mechanics, the exact questions, and the dirty-repo matrix. |
| `examples/full-audit-walkthrough.md` | A full run: invocation, triage, partial approval, authoring, review, version bump, all four Phase 9 sub-phases, and a 9c-only resume in a later invocation. |
| `examples/fix-shipped-entity.md` | The E-disposition path, with three worked cases from end to end. |

## Phases (the workflow)

### Phase 0 — Resolve scope

Parse the flags. Resolve the Claude config root with the path resolution rule above. Then resolve the root of the target marketplace.

**Non-resume runs** (no `--resume=<path>`): if the user gave `--marketplace=`, use it. Else, auto-detect the current working tree by its `.claude-plugin/marketplace.json`. If neither resolves, STOP and ask.

**`--resume=<path>` runs**: load the TODO file first. If the TODO has no `Marketplace remote` field, STOP and ask, on every path below. Precondition A (9c.2, step 8) compares the remote with that field, and the compare always fails for an empty field. Then resolve the marketplace root with the first of these steps that applies:

0. If the TODO has no `Marketplace root` field (an old TODO file), resolve as in a non-resume run: `--marketplace=`, else auto-detect in the current working tree. If neither resolves, STOP and ask.
1. If `--marketplace=` is given, and `git -C <supplied> config --get remote.origin.url` matches the persisted `Marketplace remote`, use the given path. It is the same repo in another clone location. Show the match.
2. If `--marketplace=` is given and its remote clearly differs from a persisted `Marketplace remote`, STOP and ask. Never pick one of the two silently. Precondition A in 9c.2 also treats a mismatch as a hard failure.
3. If the persisted `Marketplace root` exists on disk, use it. Precondition A in 9c.2 still checks its remote again.
4. If the given clone has no `origin` remote, STOP and ask for a clone that has one. Precondition A needs `origin` to fetch the default branch.
5. If no step above applies (the persisted root is not on disk, and no usable `--marketplace=` exists), STOP. Show the persisted root and remote, and ask the user for the current clone path of that marketplace. Check the answer as in step 1. If the remotes clearly differ, ask again, and never accept the answer. If the answer has no `origin` remote, ask again. On a resume run, never fall back to auto-detect in the current working directory.

Before you build the project set, read `references/source-inventory.md`. Build the project set from `--projects` with its decode-and-probe procedure and its worktree-sibling collapse. Before you read any source file, show the resolved scope to the user:

- The scope tokens.
- The project count, the worktree-collapse count, and the encoded names that did not resolve.
- The marketplace path and name.
- The source of the marketplace root: persisted-unchanged, explicit-override-remote-matched, or user-supplied-after-ask.
- The target plugin, or "none".

### Phase 1 — Inventory (read-only)

Phase 1 is read-only. No flag combination lets it change a file.

Follow `references/source-inventory.md`, which you read in Phase 0:

- The discovery paths for each source type. Dedupe the files by resolved absolute path, so that each file counts once.
- The decode-and-probe procedure for encoded project directory names.
- The worktree-sibling collapse. A collapsed repo counts as one independent source for each rule in Phase 3.
- The mandatory diff of each wrapper personal entity against the entity that it wraps.
- The twelve structural landmines. Know them before you extract rules.

### Phase 2 — Extract atomic rules

Write one record for each RULE, not for each file. One CLAUDE.md or memory file often mixes categories, so a classification per file gets the mixed cases wrong. Each record has these fields:

- A normalized one-line statement of the rule.
- A `source: <path>:<line>` citation. The Phase 10 report uses the same format for the numbered review findings (`F1`/`F2`/`F3`, see `references/entity-authoring-conventions.md`). With it, an authoring commit can trace a generalized rule back to its origin.
- The source class: memory, global CLAUDE.md, project CLAUDE.md, or personal entity.
- Each inheritance or scope qualifier from Phase 1, for example a nested CLAUDE.md that narrows or negates a parent rule.

### Phase 3 — Classify, cluster, corroborate

Read `references/classification-framework.md` now, and apply its Steps 1 to 7 and its calibration cases. In short:

1. **Corroborate first.** Count the independent sources of each cluster of equivalent rules. Repetition across sources is the strongest promote signal.
2. **Check the already-promoted status against the on-disk plugin manifests of the target marketplace.** Never trust the "migrated" claim of a memory index. Never trust the runtime skills listing either. It mixes the personal global skills of the user with the shipped skills of the marketplace, and only the file location tells them apart.
3. **Assign exactly one disposition** from the six-value enum:
   - **A-local**: leave. Truly project-local, with no promotion value.
   - **B-taste**: leave, unless named evidence shows an established team code style.
   - **C-universal**: promote as a new entity, unscoped.
   - **D-scoped**: promote as a new entity, with the scope stated in the description of the entity.
   - **E-fix-shipped**: fix the existing shipped entity, then prune the source. Never a new entity. A phrase like "stopgap until X is updated" is a near-certain marker.
   - **F-stale**: prune or annotate. The run produces no new content.

Before you propose a new entity, also apply the B-vs-C tie-breaker (Step 3), the over-generalization screen (Step 6), and the gap-vs-overlap check (Step 7). Never use the `type:` frontmatter field as a category signal (Step 5).

### Phase 4 — Present the triage

Copy the Phase 4 triage template from `references/report-templates.md`. Fill every table, and replace the bracketed placeholders. Do not change the section structure.

### Phase 5 — Approval gate (hard gate)

Without `--interactive`, the run answers this gate itself. It approves every C and D item that the triage recommends to promote, and every E item that it recommends to fix. It defers every F item and every item under "Needs your call". It writes these answers into the report in the "Approval" format, then starts Phase 6. With `--interactive`, wait for the reply of the user, as below.

Number the items with one global `#N` numbering across every table of Phase 4. The reply has three verbs, `approve`, `defer`, and `reject`, and two shorthands, `approve all promotes` and `approve none`. **Anything not named is deferred, always.** No approval is implicit.

`reject` vs `defer`: the run records a rejected item as rejected, with the reason. A later run does not propose it again in the same form. A deferred item comes back on a later run, because nobody decided it this time.

If an approval covers only part of a cluster, and the other members are deferred or rejected, re-scope the destination entity to the approved part. With `--interactive`, show the smaller shape and get a new yes before authoring. Without `--interactive`, state the smaller shape in the report. A skill of 4 rules minus 3 deferred rules can stop being worth its own entity.

**Approving an E item is its own risk class.** An E item edits a shipped entity that other sessions rely on. With `--interactive`, get a separate yes for each E item. `approve all promotes` never covers an E item, because it covers only new-entity promotions.

### Phase 6 — Author approved entities

Before you dispatch an authoring subagent, record the HEAD SHA of the target marketplace repo: `git -C <marketplace-root> rev-parse HEAD`. Call it `<pre-authoring-sha>`. Phase 7 uses it to limit the review loop to the authoring commits of this run.

Read `references/entity-authoring-conventions.md`, and follow it. It covers the entity kind, the frontmatter, the description, the body structure, the references split, the `Load-bearing terms`, and the commits.

**No version bump happens in this phase.** Phase 8 does the version bumps after the shape is final.

### Phase 7 — Review loop

Invoke the review-loop skill of the TARGET marketplace with `<marketplace-root>` as its working directory. `target=diff` resolves the range in the working directory of the loop. If the target marketplace is not the one that this skill runs from, any other working directory gives the wrong repo. If the target marketplace is this one, the call is `dev-essentials:review-loop target=diff <pre-authoring-sha>..HEAD --rounds=<N>`. If this run has `--interactive` or `--autonomous`, add that flag.

Use the two-dot commit range from the SHA of Phase 6, not a three-dot branch-base diff (`<base>...HEAD`). A three-dot diff also takes the commits that the branch carried before Phase 6. The loop then raises findings and applies edits on content that this run did not approve. Use the current flag syntax of that skill: `--flag=value` for flags with a value, and a required `target=` selector. If a different target marketplace ships an equivalent review-loop skill, use that skill with its own interface. If neither exists, do a single-pass self-review, and say so in the report. This skill does not need `review-loop` in every target marketplace.

Before you invoke the loop, make sure that the range still describes this run. If `git -C <marketplace-root> merge-base --is-ancestor <pre-authoring-sha> HEAD` fails, STOP. In that case, Phase 6 rebased, reset, or otherwise rewrote history, and the range no longer holds only the commits of this run. A diff of that range shows unrelated older content as deletions.

If this session has its own review-loop defaults, apply them (for example, a cycle count, a reviewer model, or a fixer model). They are defaults of the session, not a requirement of this skill.

### Phase 8 — Finalize (version bump)

Bump the version once for each affected plugin, in the `plugin.json` of that plugin only. Do it after Phase 7 settles the final shape. Do not bump for each commit, and do not bump before the shape is final. One run can touch more than one plugin, because `--target-plugin` allows a choice for each item. Each affected plugin still gets exactly one bump for the run. Use the highest severity that the changes of that plugin reached in this run:

- **PATCH**: backward-compatible fixes only, for example typos, clarifications, wording changes, and fixed examples. A run with only E dispositions (a fix to an existing shipped entity, no new entity) usually needs this bump.
- **MINOR**: pure additions, for example new entities or additive changes to an existing entity.
- **MAJOR**: the run removed or renamed an existing invocation path.

Do not add a second bump in the middle of the run. An earlier ad-hoc promotion in the history of this marketplace did that and had to revert it.

**Restart notice for new entities**. A C-universal or D-scoped promotion authors a new skill, command, or agent. If this run did that, the Phase 10 report must tell the user to restart Claude Code fully. An E-fix-shipped edit does not need the notice. The Phase 10 template in `references/report-templates.md` has the text of the notice.

After the version bump, record the new HEAD SHA of the target marketplace repo, as in Phase 6: `git -C <marketplace-root> rev-parse HEAD`. Call it `<this-run-marketplace-head-sha>`. It is the tip after the bump, so the ancestor check of Precondition A (9c.2) covers every commit of this run: the "Add X" commits, the review-round commits, and the version-bump commit.

### Phase 9 — Source-side cleanup

Read `references/cleanup-and-provenance.md` before any part of Phase 9. It holds the templates, the full 9c and 9d mechanics, the exact questions, and the dirty-repo matrix.

Phase 9 has four sub-phases, and each one has its own gate, because the risk grows from 9a to 9c. **9a (personal memory files) is on by default.** It touches only private files of the user, outside any repo. `--cleanup-mode` controls it (`stub` by default). **9b, 9c, and 9d each need an explicit opt-in flag**. 9b edits the global CLAUDE.md, 9c edits project CLAUDE.md files in other repos, and 9d deletes personal entities. They also ask again before they write or delete. **Nothing in any OTHER repository changes without `--cross-repo`.**

With `--autonomous`, no gate of Phase 9 stops. This covers the 9a stub question, the 9b per-file question, and the 9c.3 sequencing gate. It also covers the 9c.8 push gate (push and open the PR) and the 9d questions. At the 9c.6 question about unrelated dirt, take its default: skip. At the 9c.7 path question, take the proposed path. The tests before each gate still run: Preconditions A, B, and C, and the hard stops of 9c.6. A failed test still skips or defers its repo or file. The final report lists each gate that passed and each push, PR, and deletion.

#### 9a — Personal memory files (default-on)

`--cleanup-mode` controls 9a:

- A **fully promoted** file: `stub` replaces the body with a one-line pointer. `annotate` puts a pointer above the body and keeps the body. `none` touches nothing for that item: no stub, no annotation, and no `MEMORY.md` index bullet for it. List it as a manual TODO. The other items of the run that use `stub` or `annotate` still get their index bullets.
- A **partially promoted** file: never stub it. Annotate only the promoted section, and keep the rest of the file as it is.
- An approved **F** item in a memory file or a `MEMORY.md` index: remove only the stale line or reference (with `--cleanup-mode=annotate`, annotate it). It falls under the same once-per-run question as `stub`. An E source in the global CLAUDE.md goes through 9b, one in a project CLAUDE.md through 9c, and a personal entity through 9d. An F item in a CLAUDE.md has no promotion, so 9b and 9c cannot process it. Keep it report-only: list it in the "Manual TODOs" of the report.

Without `--interactive`, no user reply at Phase 5 approved the cleanup, and `stub` deletes the body of personal memory files. So list the files that `stub` changes, and ask once before you write. With `--autonomous`, list them in the report, and write without the question. This question stays, although 9a is on by default, because no user reply approved the deletion. `annotate` and `none` need no question.

Extend the existing `MEMORY.md` index of the project. Never write a new index from scratch. If the index has no `## Cross-project rules — migrated to marketplace skills` heading, add it. Under that heading, add one bullet for each promoted item: `rule summary -> <plugin>:<entity> -> date -> plugin version`. If the rule maps to one part of a multi-rule entity, add `Rule N` or `§ section` in parentheses after the entity. `references/cleanup-and-provenance.md` has the templates and the heading format.

#### 9b — Global CLAUDE.md (opt-in via `--update-global-claude-md`)

Without the flag, the run writes nothing, and the Phase 9 output includes this line:

```text
Global CLAUDE.md — N rule(s) could be replaced with a pointer; re-run with `--update-global-claude-md` to apply
```

With the flag, show the exact diff (the removed text and the pointer) for each promoted rule from the global CLAUDE.md. Then ask for each file: "Replace this section of your global CLAUDE.md with a pointer to `<plugin>:<entity>`? (yes/no)". Never apply the changes in a batch without the question for each file, because this file loads into every session. With `--autonomous`, apply each replacement without the question, and list each one in the report.

#### 9c — Cross-repo project CLAUDE.md files (opt-in via `--cross-repo=`)

Read sections 9c.0 to 9c.9 of `references/cleanup-and-provenance.md` before any part of 9c. They hold the exact commands, questions, and templates. The steps:

- **9c.0, classify the source file with git.** A tracked file goes through this cross-repo flow. An untracked or ignored file goes through the private-file path of 9b: a direct edit and a question for each file, with no branch and no PR.
- **9c.1, flag.** `--cross-repo` turns on a capability. It does not approve anything in advance. Each repo still needs its own push-gate yes (or `--autonomous`) at 9c.8. In the 9c-only re-entry mode, `--resume=<path>` makes 9c work on the promotion set of the TODO file, and 9c starts at 9c.2.
- **9c.2, three preconditions for each promotion, all required, before the run creates anything.** A: the promotion is published on the fetched default branch of the target marketplace. B: repo B can load the plugin. C: the published entity still holds each term of `Load-bearing terms`, matched as a fixed string. If a precondition fails for a repo, skip that repo, record it in the deferred TODO (9c.7), and continue with the other repos.
- **9c.3, sequencing gate, once for each run, before the run creates any worktree.** Show the results of Precondition A, and require an explicit `yes`. On any other answer, stop: write the deferred TODO, and touch no other repo. If Precondition A already failed, skip the question and defer.
- **9c.4, mechanism for each repo.** Process the repos one at a time, in ascending order of absolute path. For each repo: preflight, the branch `<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>`, a worktree, a surgical edit, and one commit with an explicit `git add <path>`. Then the push gate, and the PR through the tools of the detected host.
- **9c.5, pointer template.** Extend the `## Cross-project rules — migrated to marketplace skills` heading with one bullet for each promoted rule. Each bullet keeps a one-line gist.
- **9c.6, dirty repos.** Each of these states is a hard STOP with no override:
  - The target file is modified, staged, or in conflict.
  - A rebase, merge, or cherry-pick is in progress.
  - HEAD is detached or unborn.
  - The worktree creation fails.

  An untracked target file goes to the private-file path of 9c.0 instead. For unrelated dirt elsewhere in the repo, report it and ask once, with skip as the default. Never force-push, amend, rebase, stash, or discard anything in repo B beyond the target file.
- **9c.7, deferred TODO.** Write it in the CALLING repo, and propose its path first. Each time that a repo is skipped or deferred, write it. This includes a promotion that waits only because `--cross-repo` was `off`. A later run reads it with `--resume=<path>`, and that run does not repeat the Phase 5 approval gate.
- **9c.8, push gate for each repo.** Show the facts of the change, then ask "Push this branch and open a PR? (yes / no / push-only)". This gate is the one decision point for each repo.
- **9c.9, guardrails.** Follow the list in the reference.

#### 9d — Personal entities: commands/agents/skills (default: report-only)

Read the 9d section of `references/cleanup-and-provenance.md` before 9d. 9d applies to personal global commands, agents, and skills under `<claude-root>/{commands,agents,skills}` in two cases:

- An entity that this run promoted or E-fixed (Phase 6) fully supersedes the file.
- Phase 3 classified the file **F-stale**, because an already-shipped entity supersedes it. F-stale for another reason does not count. The F item must be approved at Phase 5. A deferred or rejected F item stays report-only.

By default, 9d deletes and edits nothing. It lists each superseded file in the "Manual TODOs" list of the Phase 10 report, with a suggested action and the way to resume.

A wrapper that still needs its personal layer but also carries an F-stale section is never eligible for deletion, even with `--delete-personal-entities`. The reference describes the report-only handling of this partially superseded wrapper.

With `--delete-personal-entities`, three gates run in this order before the run removes a file:

1. An automated check of publication and local load: Preconditions A and C of 9c.2, and a check that the `settings.json` of the caller registers or enables the plugin. The reference has the variant for each of the two cases.
2. A marketplace-publish question, once for each run.
3. A per-file `yes` right before each deletion, with the matching Precondition C lines as coverage quotes.

If step 1 fails, or the step 2 answer is not `yes`, all personal entity files of this run fall back to report-only. After a step 1 failure, the run shows no question at all. A `no` at step 3 falls back to report-only for that file only.

### Phase 10 — Report

By default, the report goes to chat. Do not assume that the calling repo has a `Notes/Plans` or `Notes/Results` convention. Write a file in two cases only: `--report=<path>` names one, or the calling repo clearly has its own convention for report files. In that case, propose the path, and ask before you write it. Copy the Phase 10 run report template from `references/report-templates.md`. If a row of "Shipped this run" is a new entity, add the restart notice of Phase 8.

## Cross-references

| Skill | Relationship |
| --- | --- |
| `dev-essentials:review-loop` | If the target marketplace is this one, Phase 7 uses it. It is not a hard dependency. If the target marketplace has no equivalent, Phase 7 does a single-pass self-review and says so. |
| `dev-essentials:subagent-orchestration` | The dispatch rules for each multi-step task that this skill delegates. Without it in the target marketplace, decide each dispatch case by case. |
| `dev-essentials:git-worktree-management` | If the target marketplace ships it, Phase 9c uses it to create worktrees. Else, Phase 9c runs `git worktree add` and notes the degraded path. |
| `dev-essentials:github-mcp-conventions` | If a cross-repo target is on GitHub, Phase 9c.4 step 7 creates the PR with the GitHub MCP tools. Without them, or after a connection or an authentication error, it uses `gh pr create`, a named exception to Rule 5 of that skill. Without both, it reports the PR text for a manual PR creation. The skill governs the owner and repo values and the pagination of the PR call. |
| `dev-essentials:write-markdown` | Each Markdown file that this skill writes or edits: new entities in Phase 6 and pointer edits in Phase 9. |
