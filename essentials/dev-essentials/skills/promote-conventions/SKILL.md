---
name: promote-conventions
description: "Promote the approved items of an audit-personal-conventions triage into a marketplace plugin. It authors the entities, runs a review loop, bumps the plugin version, and cleans up the sources."
disable-model-invocation: true
argument-hint: "[approve <numbers> | approve all promotes | approve none | defer <numbers> | reject <numbers>] [--rounds=N] [--cleanup-mode=stub|annotate|none] [--update-global-claude-md] [--cross-repo=off|all|<repo>,...] [--branch-prefix=<prefix>] [--delete-personal-entities] [--resume=<path>] [--marketplace=<path>] [--scope=<tokens>] [--projects=<list>] [--exclude-projects=<list>] [--target-plugin=<name>] [--min-evidence=<N>] [--dispositions=<tokens>] [--include-vendored] [--report=chat|<path>] [--mode interactive|partial|full]"
---

# Promote Conventions

This skill promotes the approved items of a triage into a marketplace plugin. The triage comes from `dev-essentials:audit-personal-conventions`. Only the user starts this skill, because it changes files, versions, and other repos. It follows the workflow of an earlier ad-hoc promotion of personal memory into a marketplace.

**Hard requirement: no hardcoded marketplace or host name**. Each mention of "the marketplace" resolves from `--marketplace=` and from the `name` field of that `marketplace.json`. This holds for the skill text, its phase prompts, its output templates, and its examples. The target can be a different marketplace than the one that ships this skill. Do not name this marketplace, another specific marketplace, or a specific host in prose, templates, or examples. One exception: you can name the source marketplace of an external, optional tool that this skill mentions.

## Path resolution rule

Resolve the Claude config root from the `CLAUDE_CONFIG_DIR` environment variable. If that variable is not set, use the home directory of the user plus `/.claude`. Never hardcode a username, a drive letter, or an absolute path in the text, prompts, or examples of this skill. Write each path relative to the config root or to the repo root.

The configured branch prefix is `${user_config.branch_prefix}`. Set it with `/plugin configure` (see `plugin.json`). If the value still shows as a `${...}` placeholder, no value is saved. Then the configured branch prefix is empty.

## Start rule

This skill continues a Phase 4 triage of `dev-essentials:audit-personal-conventions` in this conversation. The arguments are the Phase 5 reply. If the conversation has no triage, invoke `dev-essentials:audit-personal-conventions` first. Pass it the scope flags of this invocation: `--scope`, `--projects`, `--exclude-projects`, `--marketplace`, `--target-plugin`, `--min-evidence`, `--dispositions`, and `--include-vendored`. That skill stops after its triage. Ignore its closing line about this skill, and continue at Phase 5.

`--resume=<path>` runs the 9c-only re-entry mode of Phase 9c, and it needs no triage. It starts at "Phase 0 for a resume run".

The full mode does not skip the triage, because a mode removes stops and adds no steps.

## Phase 0 for a resume run

This section applies only with `--resume=<path>`. Every other run uses the marketplace root that `dev-essentials:audit-personal-conventions` resolved in its Phase 0.

Load the TODO file first. If the TODO has no `Marketplace remote` field, stop, on every path below. Ask the user for the remote URL of the marketplace that the TODO was written for. Use the answer as the persisted `Marketplace remote` for this run, and write it into the TODO. If the user cannot name the URL, the TODO needs a new full run. Precondition A (9c.2, step 8) compares the remote with that field, and the compare always fails for an empty field. Then resolve the marketplace root with the first of these steps that applies:

0. If the TODO has no `Marketplace root` field (an old TODO file), resolve as in a non-resume run: `--marketplace=`, else auto-detect in the current working tree. If neither resolves, stop and ask. An old TODO has no `Marketplace remote` either, so the user gave it above. Then make sure that the remote of the resolved root matches that remote, as in step 1. If the remotes clearly differ, stop and ask.
1. If `--marketplace=` is given, and `git -C <supplied> config --get remote.origin.url` matches the persisted `Marketplace remote`, use the given path. It is the same repo in another clone location. Show the match.
2. If `--marketplace=` is given and its remote clearly differs from a persisted `Marketplace remote`, stop and ask. Never pick one of the two silently. Precondition A in 9c.2 also treats a mismatch as a hard failure.
3. If the persisted `Marketplace root` exists on disk, use it. Precondition A in 9c.2 still checks its remote again.
4. If the given clone has no `origin` remote, stop and ask for a clone that has one. Precondition A needs `origin` to fetch the default branch.
5. If no step above applies (the persisted root is not on disk, and no usable `--marketplace=` exists), stop. Show the persisted root and remote, and ask the user for the current clone path of that marketplace. Check the answer as in step 1. If the remotes clearly differ, ask again, and never accept the answer. If the answer has no `origin` remote, ask again. On a resume run, never fall back to auto-detect in the current working directory.

## Arguments

| Flag | Default | Meaning |
| --- | --- | --- |
| `--rounds=<N>` | `2` | The number of review cycles for the review-loop skill of the target marketplace (see Phase 7). |
| `--marketplace=<path>` | none | With `--resume=<path>`: the clone of the marketplace repo that the TODO file names (see "Phase 0 for a resume run"). Without `--resume`: the Start rule passes it to the audit, where it is the root of the target marketplace. |
| `--cleanup-mode=stub\|annotate\|none` | `stub` | Applies to fully promoted memory files only. `none` touches nothing for that item, also not its bullet in the `MEMORY.md` index. Details in Phase 9a. |
| `--update-global-claude-md` | off (bare) | **Opt-in.** Without it, Phase 9b only reports which rules of the global CLAUDE.md can become a pointer, and how to re-run to apply them. It edits nothing. With it, Phase 9b asks for each file before it writes (see Phase 9b for the exact question). |
| `--cross-repo=off\|all\|<repo>[,<repo>...]` | `off` | **Opt-in.** Turns on Phase 9c, which edits the tracked CLAUDE.md files of OTHER repos. Bare `--cross-repo` means `--cross-repo=all`. If this run promoted nothing and no `--resume` TODO file is given, the run ignores the flag with a warning. See the 9c-only re-entry mode in Phase 9c and `references/cleanup-and-provenance.md`. |
| `--branch-prefix=<prefix>` | derive from context, else ask | The prefix of the branch name for Phase 9c branches (`<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>`). Default: use the first of these that gives a prefix: a branch-naming rule in the CLAUDE.md file of the project, the configured branch prefix, a branch-naming rule in the global CLAUDE.md. If none gives a prefix, ask the user once for each run, before the first cross-repo branch. |
| `--delete-personal-entities` | off (bare) | **Opt-in.** Lets Phase 9d delete personal global command, agent, and skill files that an entity supersedes. That entity is either promoted in this run, or already shipped (then Phase 3 classifies the file F-stale). The checks and questions of Phase 9d still gate each deletion. Without the flag, Phase 9d only reports the superseded files with a suggested manual action. |
| `--resume=<path>` | none | Resumes a deferred Phase 9c cleanup from its TODO file, without a new audit. This is the 9c-only re-entry mode (Phase 9c.1). See "Phase 0 for a resume run". |
| `--report=chat\|<path>` | `chat` | Where the final report goes. |
| `--mode interactive\|partial\|full` | `partial` | The work mode. `dev-essentials:work-modes` defines the modes, and the gate table in "Autonomy" says what each mode does here. |

When the conversation has no triage, the Start rule passes these scope flags to the audit: `--scope`, `--projects`, `--exclude-projects`, `--target-plugin`, `--min-evidence`, `--dispositions`, and `--include-vendored`. `dev-essentials:audit-personal-conventions` defines them.

**Only the full mode skips the Phase 9 gates. This includes the per-repo push gate.** The opt-in flags `--update-global-claude-md`, `--cross-repo`, and `--delete-personal-entities` turn on a capability. They do not skip its gates. The Phase 5 approval gate follows "Autonomy". By default, the run approves the recommended items itself. In the interactive mode, it waits.

## Autonomy

Before the first step, load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the modes, the rules for every mode, and the hard stops. This table lists each gate of this workflow and what each mode does there.

| Gate | Partial (the default) | Interactive | Full |
| --- | --- | --- | --- |
| Phase 5: approval of the triage | Approve the recommended C, D, and E items. Defer F items and "Needs your call" | Wait for the reply | Same as partial |
| Phase 5: an E item, or a part of a cluster | State the smaller shape in the report | A separate yes | Same as partial |
| Phase 9a: the `stub` writes | Ask once | No question, because the Phase 5 reply approved them | List them, and write |
| Phase 9b, 9c.3, 9c.8, and 9d questions | Ask | Ask | No stop |
| Phase 9c.6: unrelated dirt | Ask once. Skip is the default | Same | Skip |
| Phase 9c.7: the TODO path | Propose it, and ask | Same | Take the proposed path |
| Phase 10: a report file | Propose the path, and ask | Same | Take the proposed path |
| Push of the target marketplace | Never, unless the user says so | Same | Same |

Each Phase 9 gate runs only with its opt-in flag. The tests before each gate still run in the full mode.

## Guardrails

- An **E** disposition is never a new entity. It is always a fix to an existing shipped entity, and then the run prunes the source.
- Never auto-edit a project-repo CLAUDE.md without `--cross-repo`.
- Never push without an explicit per-repo yes, even with `--cross-repo` set. The full mode counts as that yes.
- Never push the commits of the target marketplace either, unless the user explicitly says so elsewhere in the session.
- Never delete a personal entity file without all of these: `--delete-personal-entities`, its automated check of publication and local load, the once-per-run marketplace-publish gate, and its own per-file question. The full mode counts as the publish gate and the per-file yes. The automated check still runs.
- Never touch a file outside the provenance list of an approved item.

## References and examples

| File | When to read |
| --- | --- |
| `references/entity-authoring-conventions.md` | Phase 6: the entity kind, the frontmatter, the body structure, and the commit discipline. |
| `references/cleanup-and-provenance.md` | Phase 9: the templates, the full 9c and 9d mechanics, the exact questions, and the dirty-repo matrix. |
| `references/report-templates.md` | Phase 10: the run report template. |
| `examples/full-audit-walkthrough.md` | A full run: invocation, triage, partial approval, authoring, review, version bump, all Phase 9 sub-phases, and a 9c-only resume in a later invocation. |

## Phases (the workflow)

Phases 0 to 4 run in `dev-essentials:audit-personal-conventions`. The phase numbers stay the same in both skills, because the reference files cite them.

### Phase 5 — Approval gate (hard gate)

Phase 5 starts from the Phase 4 triage (see "Start rule"). If the arguments hold a reply with the Phase 5 verbs, that reply answers this gate in every mode. Else, outside the interactive mode, the run answers this gate itself. It approves every C and D item that the triage recommends to promote, and every E item that it recommends to fix. It defers every F item and every item under "Needs your call". It writes these answers into the report in the "Approval" format, then starts Phase 6. In the interactive mode, wait for the reply of the user, as below.

Number the items with one global `#N` numbering across every table of Phase 4. The reply has the verbs `approve`, `defer`, and `reject`, and the shorthands `approve all promotes` and `approve none`. **Anything not named is deferred, always.** No approval is implicit.

`reject` vs `defer`: the run records a rejected item as rejected, with the reason. A later run does not propose it again in the same form. A deferred item comes back on a later run, because nobody decided it this time.

If an approval covers only part of a cluster, and the other members are deferred or rejected, re-scope the destination entity to the approved part. In the interactive mode, show the smaller shape and get a new yes before authoring. Outside the interactive mode, state the smaller shape in the report. A skill of 4 rules minus 3 deferred rules can stop being worth its own entity.

**Approving an E item is its own risk class.** An E item edits a shipped entity that other sessions rely on. In the interactive mode, get a separate yes for each E item. `approve all promotes` never covers an E item, because it covers only new-entity promotions.

### Phase 6 — Author approved entities

Before you dispatch an authoring subagent, record the HEAD SHA of the target marketplace repo: `git -C <marketplace-root> rev-parse HEAD`. Call it `<pre-authoring-sha>`. Phase 7 uses it to limit the review loop to the authoring commits of this run.

Read `references/entity-authoring-conventions.md`, and follow it. It covers the entity kind, the frontmatter, the description, the body structure, the references split, the `Load-bearing terms`, and the commits.

**No version bump happens in this phase.** Phase 8 does the version bumps after the shape is final.

### Phase 7 — Review loop

Invoke the review-loop skill of the TARGET marketplace with `<marketplace-root>` as its working directory. `target=diff` resolves the range in the working directory of the loop. If the target marketplace is not the one that this skill runs from, any other working directory gives the wrong repo. If the target marketplace is this one, the call is `dev-essentials:review-loop target=diff <pre-authoring-sha>..HEAD --rounds=<N>`. Add the `--mode` of this run.

Use the two-dot commit range from the SHA of Phase 6, not a three-dot branch-base diff (`<base>...HEAD`). A three-dot diff also takes the commits that the branch carried before Phase 6. The loop then raises findings and applies edits on content that this run did not approve. Use the current flag syntax of that skill: `--flag=value` for flags with a value, and a required `target=` selector. If a different target marketplace ships an equivalent review-loop skill, use that skill with its own interface. If neither exists, do a single-pass self-review, and say so in the report. This skill does not need `review-loop` in every target marketplace.

Before you invoke the loop, make sure that the range still describes this run. If `git -C <marketplace-root> merge-base --is-ancestor <pre-authoring-sha> HEAD` fails, stop. In that case, Phase 6 rebased, reset, or otherwise rewrote history, and the range no longer holds only the commits of this run. A diff of that range shows unrelated older content as deletions.

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

Each sub-phase of Phase 9 has its own gate, because the risk grows from 9a to 9c. **9a (personal memory files) is on by default.** It touches only private files of the user, outside any repo. `--cleanup-mode` controls it (`stub` by default). **9b, 9c, and 9d each need an explicit opt-in flag**. 9b edits the global CLAUDE.md, 9c edits project CLAUDE.md files in other repos, and 9d deletes personal entities. They also ask again before they write or delete. **Nothing in any OTHER repository changes without `--cross-repo`.**

In the full mode, no gate of Phase 9 stops. This covers the 9a stub question, the 9b per-file question, and the 9c.3 sequencing gate. It also covers the 9c.8 push gate (push and open the PR) and the 9d questions. At the 9c.6 question about unrelated dirt, take its default: skip. At the 9c.7 path question, take the proposed path. The tests before each gate still run: Preconditions A, B, and C, and the hard stops of 9c.6. A failed test still skips or defers its repo or file. The final report lists each gate that passed and each push, PR, and deletion.

#### 9a — Personal memory files (default-on)

`--cleanup-mode` controls 9a:

- A **fully promoted** file: `stub` replaces the body with a one-line pointer. `annotate` puts a pointer above the body and keeps the body. `none` touches nothing for that item: no stub, no annotation, and no `MEMORY.md` index bullet for it. List it as a manual TODO. The other items of the run that use `stub` or `annotate` still get their index bullets.
- A **partially promoted** file: never stub it. Annotate only the promoted section, and keep the rest of the file as it is.
- An approved **F** item in a memory file or a `MEMORY.md` index: remove only the stale line or reference (with `--cleanup-mode=annotate`, annotate it). It falls under the same once-per-run question as `stub`. An E source in the global CLAUDE.md goes through 9b, one in a project CLAUDE.md through 9c, and a personal entity through 9d. An F item in a CLAUDE.md has no promotion, so 9b and 9c cannot process it. Keep it report-only: list it in the "Manual TODOs" of the report.
- A source in a KB clone stays report-only. List it in the Manual TODOs of the report, because the rules of the KB own its notes.

Outside the interactive mode, no user reply at Phase 5 approved the cleanup, and `stub` deletes the body of personal memory files. So list the files that `stub` changes, and ask once before you write. In the full mode, list them in the report, and write without the question. This question stays, although 9a is on by default, because no user reply approved the deletion. `annotate` and `none` need no question.

Extend the existing `MEMORY.md` index of the project. Never write a new index from scratch. If the index has no `## Cross-project rules — migrated to marketplace skills` heading, add it. Under that heading, add one bullet for each promoted item: `rule summary -> <plugin>:<entity> -> date -> plugin version`. If the rule maps to one part of a multi-rule entity, add `Rule N` or `§ section` in parentheses after the entity. `references/cleanup-and-provenance.md` has the templates and the heading format.

#### 9b — Global CLAUDE.md (opt-in via `--update-global-claude-md`)

Without the flag, the run writes nothing, and the Phase 9 output includes this line:

```text
Global CLAUDE.md — N rule(s) could be replaced with a pointer; re-run with `--update-global-claude-md` to apply
```

With the flag, show the exact diff (the removed text and the pointer) for each promoted rule from the global CLAUDE.md. Then ask for each file: "Replace this section of your global CLAUDE.md with a pointer to `<plugin>:<entity>`? (yes/no)". Never apply the changes in a batch without the question for each file, because this file loads into every session. In the full mode, apply each replacement without the question, and list each one in the report.

#### 9c — Cross-repo project CLAUDE.md files (opt-in via `--cross-repo=`)

Read sections 9c.0 to 9c.9 of `references/cleanup-and-provenance.md` before any part of 9c. They hold the exact commands, questions, and templates. The steps:

- **9c.0, classify the source file with git.** A tracked file goes through this cross-repo flow. An untracked or ignored file goes through the private-file path of 9b: a direct edit and a question for each file, with no branch and no PR.
- **9c.1, flag.** `--cross-repo` turns on a capability. It does not approve anything in advance. Each repo still needs its own push-gate yes (or the full mode) at 9c.8. In the 9c-only re-entry mode, `--resume=<path>` makes 9c work on the promotion set of the TODO file, and 9c starts at 9c.2.
- **9c.2, the preconditions for each promotion, all required, before the run creates anything.** A: the promotion is published on the fetched default branch of the target marketplace. B: repo B can load the plugin. C: the published entity still holds each term of `Load-bearing terms`, matched as a fixed string. If a precondition fails for a repo, skip that repo, record it in the deferred TODO (9c.7), and continue with the other repos.
- **9c.3, sequencing gate, once for each run, before the run creates any worktree.** Show the results of Precondition A, and require an explicit `yes`. On any other answer, stop: write the deferred TODO, and touch no other repo. If Precondition A already failed, skip the question and defer.
- **9c.4, mechanism for each repo.** Process the repos one at a time, in ascending order of absolute path. For each repo: preflight, the branch `<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>`, a worktree, a surgical edit, and one commit with an explicit `git add <path>`. Then the push gate, and the PR through the tools of the detected host.
- **9c.5, pointer template.** Extend the `## Cross-project rules — migrated to marketplace skills` heading with one bullet for each promoted rule. Each bullet keeps a one-line gist.
- **9c.6, dirty repos.** Each of these states is a hard stop with no override:
  - The target file is modified, staged, or in conflict.
  - A rebase, merge, or cherry-pick is in progress.
  - HEAD is detached or unborn.
  - The worktree creation fails.

  An untracked target file goes to the private-file path of 9c.0 instead. For unrelated dirt elsewhere in the repo, report it and ask once, with skip as the default. Never force-push, amend, rebase, stash, or discard anything in repo B beyond the target file.
- **9c.7, deferred TODO.** Write it in the CALLING repo, and propose its path first. Each time that a repo is skipped or deferred, write it. This includes a promotion that waits only because `--cross-repo` was `off`. A later run reads it with `--resume=<path>`, and that run does not repeat the Phase 5 approval gate.
- **9c.8, push gate for each repo.** Show the facts of the change, then ask "Push this branch and open a PR? (yes / no / push-only)". This gate is the one decision point for each repo.
- **9c.9, guardrails.** Follow the list in the reference.

#### 9d — Personal entities: commands/agents/skills (default: report-only)

Read the 9d section of `references/cleanup-and-provenance.md` before 9d. 9d applies to personal global commands, agents, and skills under `<claude-root>/{commands,agents,skills}` in these cases:

- An entity that this run promoted or E-fixed (Phase 6) fully supersedes the file.
- Phase 3 classified the file **F-stale**, because an already-shipped entity supersedes it. F-stale for another reason does not count. The F item must be approved at Phase 5. A deferred or rejected F item stays report-only.

By default, 9d deletes and edits nothing. It lists each superseded file in the "Manual TODOs" list of the Phase 10 report, with a suggested action and the way to resume.

A wrapper that still needs its personal layer but also carries an F-stale section is never eligible for deletion, even with `--delete-personal-entities`. The reference describes the report-only handling of this partially superseded wrapper.

With `--delete-personal-entities`, these gates run in this order before the run removes a file:

1. An automated check of publication and local load: Preconditions A and C of 9c.2, and a check that the `settings.json` of the caller registers or enables the plugin. The reference has the variant for each case.
2. A marketplace-publish question, once for each run.
3. A per-file `yes` right before each deletion, with the matching Precondition C lines as coverage quotes.

If step 1 fails, or the step 2 answer is not `yes`, all personal entity files of this run fall back to report-only. After a step 1 failure, the run shows no question at all. A `no` at step 3 falls back to report-only for that file only.

### Phase 10 — Report

By default, the report goes to chat. Do not assume that the calling repo has a convention for report files. Write a file only in these cases: `--report=<path>` names one, or the calling repo clearly has its own convention for report files. In that case, propose the path, and ask before you write it. Copy the Phase 10 run report template from `references/report-templates.md`. If a row of "Shipped this run" is a new entity, add the restart notice of Phase 8.

## Cross-references

| Skill | Relationship |
| --- | --- |
| `dev-essentials:audit-personal-conventions` | Phases 0 to 4. It produces the triage that this skill continues. |
| `dev-essentials:review-loop` | If the target marketplace is this one, Phase 7 uses it. It is not a hard dependency. If the target marketplace has no equivalent, Phase 7 does a single-pass self-review and says so. |
| `dev-essentials:subagent-orchestration` | The dispatch rules for each multi-step task that this skill delegates. Without it in the target marketplace, decide each dispatch case by case. |
| `dev-essentials:git-worktree-management` | If the target marketplace ships it, Phase 9c uses it to create worktrees. Else, Phase 9c runs `git worktree add` and notes the degraded path. |
| `dev-essentials:github-mcp-conventions` | If a cross-repo target is on GitHub, Phase 9c.4 step 7 creates the PR with the GitHub MCP tools. Without them, or after a connection or an authentication error, it uses `gh pr create`, a named exception to Rule 5 of that skill. Without both, it reports the PR text for a manual PR creation. The skill governs the owner and repo values and the pagination of the PR call. |
| `dev-essentials:write-markdown` | Each Markdown file that this skill writes or edits: new entities in Phase 6 and pointer edits in Phase 9. |
