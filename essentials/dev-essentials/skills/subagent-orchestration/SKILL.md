---
name: subagent-orchestration
description: "How the main agent dispatches work in long, multi-step tasks, and which model each dispatch uses."
when_to_use: "Use it for 'orchestrate this', 'dispatch a subagent', or 'handle this multi-stage task'. Use it also in feature-pipeline, review-loop, or PR-comment processing, and to choose between a subagent and inline work. It applies to every multi-stage workflow."
---

# Subagent Orchestration

Multi-stage tasks (feature-pipeline, review-loop, audit-team, PR-comment processing, multi-commit fix stacks) depend on these choices of the main agent: what to delegate, what to do inline, and how to write each brief. This skill has rules for these choices. It also owns the model matrix for the dispatches, so the skill works without a personal `CLAUDE.md` file. The section "Run format agreement" defines the run format that a long orchestrated run states at the start.

## Model selection

Every dispatch carries a `model`, or uses an agent type whose file sets the model (see "How a model gets applied" in `references/model-selection.md`). The choice of the model is part of the orchestration decision. The phrase "per the model matrix" in the rules below means this matrix.

| Model | When to use | Typical tasks |
| --- | --- | --- |
| **Opus** | Default, at `medium` effort: the start of the ladder below. A review starts at `high`. Work that needs a decision that no plan or brief settles yet. A wrong decision costs more than the larger model. | The implementation approach before coding. The plan for the fix of a review finding. The review of a change. A bug fix with no fix plan. |
| **Sonnet** | Well-scoped work: an approved plan, a written fix plan, or the brief settles each decision. Also a capable orchestrator. | Execution of an approved plan in subagent sessions. A fix with a written fix plan. A draft from given facts. The orchestration itself. |
| **Haiku** | Routine work with no thinking: read, extract, and apply mechanically. | Extraction of information from logs, tickets, or tasks. An explicit 1-2-3 edit list. Lookups. See "Haiku scope" in `references/model-selection.md`. |
| **Fable** | The top of the ladder: a step that still falls short on Opus at `xhigh`, within the three moves of the ladder. | A hard plan, fix, or design. |

**The ladder: effort before model.** A higher effort costs less than a larger model, so the run tries it first. The ladder moves each step that runs in a subagent, also a dispatch that a workflow skill names. A model and an effort that a skill names are the start of the ladder for that step. A step falls short in these cases. First, its self-test fails, the orchestrator resumes the subagent one time with the error lines, and the self-test fails again. Second, the reviewer of the step reports a finding on its result that blocks the merge: a severity of `High` or above, or a blocking issue. The self-test is the check that the brief names, for example the build or the tests. At each new effort or model, the step gets one resume again. A failure whose fix is out of the scope of the step is not a fall short. Examples are a missing tool, a network error, or a fix in unrelated code. Stop, and tell the user, as `dev-essentials:engineering-discipline` Rule 1 says. If a step falls short, run it again one effort level higher, up to `xhigh`. If it still falls short at `xhigh`, move it one model up at `high`: from Haiku to Sonnet, from Sonnet to Opus, or from Opus to Fable. The step already fell short, so the larger model starts above the default. The ladder ends after three moves of one step, or at Fable at `xhigh`. A move from `low` to `medium` is not one of the three. At the end of the ladder, stop, and report the step. The level `max` needs the word of the user or of a skill. A limit of tries that a skill names wins over the ladder. Say each move in one line: the step, the new model and effort, and what fell short.

**The user's explicit choice outranks this matrix and its ladder**. Use the model that the user names for a task, also against the matrix and against the model defaults of any skill. Leave a model that the user set for the session as it is. Never "correct" it back to a default.

**A move up to Fable is never silent.** Ask the user before each one. Exception: a workflow outside the interactive mode of `dev-essentials:work-modes` does not ask. It makes the move, and names the step and what fell short in its final report. A Fable default that the workflow itself documents is not a move up.

The rest of this section is in `references/model-selection.md`. It covers how a model gets applied, the model of the orchestrating session, the plan → execute split, and the Haiku scope. Read it before the first dispatch that sets a `model`.

## Rule 1 — Use a subagent only when a delegation test holds

Before you give work to a subagent, find the test that sends it there:

1. Context. The work puts many file reads or long tool output into the main context, but the later steps need only a short result.
2. Parallel work. The parts are independent and can run at the same time (Rule 3).
3. Independent view. The work is a review of work that the main agent wrote. The review is the product, or the run is unattended. A fresh context gives the reviewer its own view.
4. Tool isolation. The work needs a different tool set, for example read-only tools.
5. Else, do the work in the main loop.

The tests name a kind of work, not a size, so they hold on any model. More reasons send work to a subagent. One is a step that needs a stronger model than the session runs (see "The model of the orchestrating session" in `references/model-selection.md`). Another is a high-volume read of an outside system (Rule 4). Never dispatch work only to reach a cheaper model.

So the main loop does small lookups and the small tasks of a plan itself. Examples are a `Grep` and two `Read` calls that find a file or a value. Other examples are a one-line edit on a known path and a plan task that edits a few files that the session already read. A dispatch costs a brief, a cold start, and a report that can lose detail. If no test holds, a dispatch does not pay off.

A workflow skill can name its own dispatches, for example the stages of `dev-essentials:feature-pipeline` or the reviewer of `dev-essentials:review-loop`. Keep those dispatches. The tests decide where the skill leaves the choice open.

In the final reply, add one line that starts with `Route:`. Name each dispatch and its test, for example `Route: code search (context), two fixes (parallel work)`. If no test decided a dispatch, name its reason instead: `workflow` (a workflow skill names the dispatch), `stronger model`, or `outside system` (Rule 4). An example is `Route: reviewer (workflow), PR threads (outside system)`. If no work went to a subagent, write `Route: main loop`.

PR-comment work (anything that maps to `dev-essentials:process-pr-comments`) has its own dispatches. Do not dispatch a subagent that runs the skill. The skill asks the user questions and waits for the go-ahead for each push, and a subagent cannot reach the user.

- **User asks raw** ("process PR comments", "give me a fix plan", "handle review feedback"): invoke the skill in the main session. If the user asked only for a plan, pass `dry-run`.
- **User explicitly invokes `/dev-essentials:process-pr-comments`**: the skill orchestrates from the main agent. The main agent never runs the high-volume MCP reads on the outside system inline.

**A phase that itself orchestrates is its own dispatch**. A step whose own execution model is "dispatch N further subagents and coordinate their output" is a separate phase. The orchestrating session dispatches it after the report of the previous phase arrives. Never fold it into the brief of the previous phase to save a round trip. The canonical case is `dev-essentials:review-loop`. It is not "more implementation work", because it dispatches its own reviewer, and it can dispatch its own fixer subagent. A brief that says "implement this, then review-loop it" gives that second layer of fan-out to the implementer (`main → implementer → its own reviewer/fixer`). This removes the one checkpoint that matters: the orchestrator reads the implementation report and checks the commit before the review starts. Each dispatch stays one phase wide.

The pattern to copy already ships in this plugin. `dev-essentials:research-implement-review-report` keeps Phase 2 (Implement) and Phase 3 (Review loop) as two separate phases, and the orchestrating session drives both, for this reason. Follow that shape. Do not invent a bundled variant of it.

Self-test before you send any multi-step brief: does any step in this brief require the agent to dispatch its own subagents? If yes, cut the brief at that step, and make that step your own next dispatch.

**Describe the dispatch you actually made**. What the orchestrating session tells the user about a dispatch must match the brief that it sent. Never describe a narrower scope than the prompt holds. Example of this error: "dispatched steps 1-5, I will handle step 6 myself later", but steps 6 and 7 are word for word in that prompt. A summary of a dispatch is a claim about the prompt, not a memory of the intent. So read the brief again before you describe it. If the brief is broader than you intended, dispatch a narrower one. Never describe it as narrower than it is.

This rule covers the handoff decision of the orchestrator only. Rule 7 covers what a receiver does with a concrete, bounded task. In the phase-bundling case above, a bundled brief and a pass-through delegator make the same shape (`main → agent → agent's own dispatches`) with no checkpoint for the orchestrator. Here the defect is in the brief. Make the brief shorter, and do not rely on the receiver to refuse it under Rule 7.

For a worked example of a bundled review loop, see [references/worked-examples.md](references/worked-examples.md).

## Rule 2 — Pass user-supplied context verbatim; do not pre-research to enrich it

The user can give context before the main agent dispatches subagents. Examples are finding counts ("25 issues"), file lists ("3 clients, ignore SMS"), path patterns, scope guards, and exact line references. Quote this context word for word in the prompt of the subagent. Do not run your own grep, glob, or read calls to test the numbers of the user or to list the files. Do not pre-read source to write a "richer" brief.

Reason: research before a dispatch fills the context of the main agent with facts that the subagent can find fast in its own context. The main agent then has fewer tokens for the orchestration decisions that only it can make. Pre-research lowers the quality of the work.

Before each tool call that comes before a dispatch, ask yourself: did the user already tell me this, or can the subagent learn it as fast? If yes, skip the call.

Acceptable exceptions:

- A light sanity check against a catastrophic dispatch. Example: one `git status` to find out whether the worktree is clean, before you ask a subagent to commit.
- Real ambiguity in the wording of the user. Ask a question to clear it up. Do not research around it.

Anti-pattern: "let me preload the PR metadata so the subagent's prompt is richer". Do not do this. Pass the IDs and let the subagent fetch.

## Rule 3 — Dispatch independent work as several `Agent` calls in one message

Subagents run in the background by default. When a subagent completes, a task notification arrives. Do not poll, sleep, or call a "check progress" tool while you wait. The notification is the signal.

**Parallel dispatch.** To run independent work at the same time, make several `Agent` calls in ONE assistant message. All subagents start together, and each one sends its own notification.

**Sequential dependency** (stage B needs the output of stage A): dispatch A, wait for the notification of A, and then dispatch B in a later message.

**Forks.** `subagent_type: "fork"` starts a subagent that inherits the whole conversation, the tools, and the model of the main session. It ignores the `model` parameter (see "How a model gets applied" in `references/model-selection.md`). Use a fork for a side task that needs the full context. For work that needs a specific model or a clean context, use another agent type with a complete brief.

Other cases:

- **Bash/PowerShell**: never set `run_in_background: true` on Bash or PowerShell for convenience. Long-running Bash and PowerShell commands stay in the foreground. Rule 3 of `dev-essentials:dotnet-build-test` names the exceptions: an explicit request of the user, and a long test run in a subagent. A command that runs absurdly long is a sign of a real problem, not a reason to send it to the background.
- **`SendMessage` is not a dispatch.** Use it only to resume or correct a subagent that you dispatched for the same task (see Rule 5). For new work, make a fresh, unnamed `Agent` call.

## Rule 4 — Delegate high-volume external-system MCP work to subagents by default

By default, dispatch high-volume MCP work on an outside system to a subagent, so that the context of the main agent stays clean. This covers the tools `mcp__plugin_github_github__*` and the tools of similar MCP servers for outside systems. It covers reads and writes with large payloads or with iteration.

The main agent calls these MCP tools itself only in these cases:

1. The user explicitly asked it to ("post the replies yourself", "create the issue directly", "do the push yourself"). Only such explicit words count. A "proceed" or a "continue" is not an explicit ask.
2. The next subagent needs one surgical, low-volume call before it can start, for example the metadata of one PR that its prompt must hold. Even then, prefer to ask the subagent to fetch it.

The rule covers reads, such as list threads, get a PR by ID, get a repo, or search issues. It also covers writes, such as post a reply, resolve a thread, or create an issue.

Reason: PR-thread payloads are large. Even with minimal options, the threads of a PR with 20 or more comments fill the main context. They hold comment HTML, identity data, and `_links` arrays. The main agent does not need most of it for its orchestration decisions. Subagents read the threads, classify them, and report the small structured summary that the main agent uses. If the main agent needs a few values from the payload, for example the timestamps for reply anchors, the subagent returns them in its report.

If an MCP server for an outside system is missing in the current session, ask the user to fix it (`/mcp`). Do not fall back to REST APIs or CLI tools. For GitHub, Rule 5 of `dev-essentials:github-mcp-conventions` allows the `gh` CLI in two cases: no MCP tool has the call or a field that it needs, or the call fails again after a retry. A missing server is not one of these cases. A subagent names each `gh` call and its reason in its report. A skill that names its own `gh` step follows that step. The main agent repairs a missing server, because the user sees the MCP errors there.

What this rule does not change:

- Push commands stay with the main agent. A push is one-shot and has a small payload, and the user can inspect its repair surface (force-push prevention, branch checks) in the main session.
- Rule 2 still holds. Pass IDs word for word, and do not fetch first.
- A single call with no thread iteration, for example the status of one PR, is acceptable in the main agent. The payload is small and the call is one-shot.

For a worked example of a thread fetch in the main agent, see [references/worked-examples.md](references/worked-examples.md).

## Rule 5 — No named teammates or team coordination, and `SendMessage` only for the same task

Do not pass the `Agent` tool's `name` parameter. If agent teams are on in an interactive session, a named subagent starts as a teammate, not as a plain subagent. Claude Code does not ask first. A teammate is a separate, long-lived session in a team, with its own mailbox and idle notices. That is the wrong shape for "do this, report back, done." You do not need a name to reach the subagent later: a dispatch returns an agent ID (see the limits below for the exceptions), and `SendMessage` accepts that ID.

Never use `team_name`. Never use `TaskCreate`, `TaskUpdate`, `TaskList`, or `TodoWrite` as a shared task list between subagents with `owner` or `blockedBy` ownership. Never make subagents send messages to each other. That is team coordination, not delegation, and it is out of scope here. You can use the task tools alone in the orchestrating session to track your own progress for the user.

The correct dispatch shape has these fields. Leave out `model` for an agent type whose file sets it (see "How a model gets applied" in `references/model-selection.md`).

```text
Agent(
    subagent_type: "...",       # or a specific agent type
    model:         "...",       # per the model matrix
    effort:        "...",       # see the rules below
    description:   "Short 3-5 word label",
    prompt:        "<complete, self-contained brief>"
)
# no name, no team_name
```

Pass `effort` as `references/model-selection.md` § Effort says.

Everything the subagent needs goes in `prompt`. The subagent starts in its own context window and does not see your conversation. So the brief must be fully self-contained (see "Brief quality matters more than brief count" below).

Use `SendMessage` to your own subagent only for the same task, in these cases:

- Resume: the subagent stopped before it delivered, for example on a usage limit, a crash, its `maxTurns` limit, or a `TaskStop`. Send a short resume note to its agent ID. It continues with its full history.
- Correct: the subagent still runs, or its report is incomplete for the same task. An example is a report with open items that need an answer from the user. Send the correction or the answer to its agent ID.

Limits:

- Record the agent ID of each dispatch that you can need to resume. The built-in `Explore` and `Plan` agents return no agent ID, so you cannot resume them.
- If the user stopped the agent in `/tasks`, Claude Code refuses the message. If `SendMessage` fails or finds no agent, dispatch a fresh subagent with the same brief and a note on what is already done.
- For new or unrelated work, make a fresh, unnamed `Agent` call. Do not give it to an old subagent.

## Rule 6 — Worktree-path discipline for write-capable dispatches

Every write-capable subagent dispatch (one that edits files or runs git commands) must carry the ABSOLUTE worktree path. Put it in the first few lines of the brief, and again at every concrete instruction that touches files. Do not assume that a dispatched subagent starts in the worktree of the orchestrating session. Its shell CWD can be the MAIN repo root. Most relative paths exist in both places, so an ambiguous brief lets the subagent silently edit the wrong copy.

Tell the subagent this rule: if its brief gives no absolute worktree path, it must stop and ask. It never assumes the current working directory, and it never infers the worktree from a relative path somewhere else in the brief.

If two or more worktrees are in play, put an explicit CORRECT/WRONG example block near the top of the brief. Example:

```text
## Worktree (REQUIRED — read first)

CORRECT: <absolute-path-to-repo>\.claude\worktrees\<full-branch-ref>\
WRONG  : <absolute-path-to-repo>\

Most files exist in BOTH. NEVER edit anything outside the CORRECT path. Every Read/Edit/Write uses an ABSOLUTE path starting with CORRECT. Every git call uses `git -C "<CORRECT>"`.
```

Every git call in the work of the subagent uses `git -C "<absolute-worktree-path>"`. Never use a bare `git` that relies on the inherited CWD.

These verification gates belong in every such brief:

- **Pre-flight** (the first action of the subagent): `git -C "<worktree>" rev-parse --abbrev-ref HEAD` prints the expected branch name. If it does not, stop. Also save the output of `git -C "<main-repo-root>" status --porcelain` for the Post-edit gate.
- **Post-edit** (after each batch of edits): run `git -C "<main-repo-root>" status --porcelain -- <paths>`. `<paths>` are the files that the subagent edited, relative to the worktree root. The output must hold no entry that the Pre-flight output did not hold. This shows that no edit leaked into the main repo. Look only at these paths, because other agents can change other files of the main repo at the same time. If the worktree is the main repo root, skip this gate. If the gate fails, stop, and report the paths. Do not revert them, because another agent can own them.

No `.bak` files. The Edit tool already fails loudly on a content mismatch. So manual backups are not necessary, and they pollute the tree.

This rule is about the briefs of dispatched subagents. The mechanics of worktree creation and lifecycle (create, list, remove) belong to `dev-essentials:git-worktree-management`, not to this rule.

## Rule 7 — Do the work you were dispatched to do; no pass-through delegators

An agent with a concrete, bounded task DOES that task. A re-dispatch of the task to a fresh subagent, with only a relay of its report, is a hop that does nothing. It buys no parallelism and protects nothing, because the context of the parent was already sized for the job. It costs a full brief rewrite and another notification round trip. This binds every level: the main session, and any subagent that got a concrete task.

As the receiver of a bounded task, never dispatch your whole task again. Do the concrete work yourself. Dispatch a part of it only for one of the reasons of Rule 1:

- A test of Rule 1 sends that part to a subagent.
- The part needs a stronger model than you run.
- The part is a high-volume read of an outside system (Rule 4).

Never dispatch a part only to reach a cheaper model. If your brief forbids further dispatches, follow the brief.

**Brief accordingly**. If the task really needs fan-out, say so in the brief. For concrete work, write this line in the brief: "do this work yourself. Do not dispatch further subagents for it." A brief that says neither produced the worktree-cleanup failure in [references/worked-examples.md](references/worked-examples.md).

## Brief quality matters more than brief count

A vague brief produces shallow work. Each delegation must include:

- **What is done** so far in this session. Paste the relevant context. Do not paraphrase it.
- **What to do**: the deliverable in concrete terms (file paths, expected outputs).
- **What not to do**: scope guards ("do not implement", "do not edit X").
- **Skills the subagent must invoke**, for example `dotnet-backend-dev:create-tests` before it writes tests.
- **The verification commands** that prove the work is done (build commands, test filters).
- **Reporting format**: what the final message of the subagent must contain.
- **Stop-and-report condition** for ambiguous cases.
- **Whether further fan-out is allowed**. For a concrete, bounded task, write "do this yourself. Do not dispatch further subagents" (see Rule 7).

A 10-line brief that prevents one wrong dispatch is worth more than three 3-line briefs that each need a redo.

## Trust but verify

Check a subagent report in these tiers:

1. Cheap facts, always, by the orchestrator: the files exist, the counts match the report, the build, test, or validator output shows a pass, and each commit holds only the intended files. If one fails, fix it or dispatch a repair. Read the verbatim result lines that the subagent reports. Do not add a run after each report. Before a commit or a push, run the build and the tests one time in the main loop. That run is the check of all reports since the last run. Use one command whose output holds only the result lines and the errors, and keep its exit code (for .NET, the filters of `dev-essentials:dotnet-build-test`). If each command exits with code 0 and the result line shows zero failed tests, the run is green. Any other result is not green. Run the tests that the subagent ran. If it ran none, run the tests that cover the changed files. A green run of the main loop after the last edit counts. If the run is red, fix the cause or send the error lines back, and run again. Compare only the status, the error count, and the Failed, Passed, and Total counts with the report. Ignore the duration and the warning count, because they differ between runs. If a run can take longer than 10 minutes, dispatch `dev-essentials:test-runner`. Its brief gives the absolute worktree path, the commands, and the test filter or the words that the whole test suite runs. It also says that the run can take longer than 10 minutes. If its status is STOPPED, answer its question and dispatch it again, or ask the user. Also dispatch it for runs in several worktrees at the same time (test 2).
2. Content, by an agent: a verifier or reviewer agent checks whether a finding, a cited line, or a claimed behavior is true. If the workflow has no such agent and the next step depends on the content, dispatch one. Do not redo its work. Every re-read stays in the main context for the rest of the run.
3. Spot-check, by the orchestrator, only before a high-risk action: a push, a deletion, a post to an outside system, or a recommendation that the user acts on. Re-read only the lines that the action depends on. If a subagent claimed a green build or green tests after a rebase, run them again (for .NET, see `dev-essentials:dotnet-build-test`).

In a fan-out, match each report to the unit that you dispatched. A failed agent, a stopped agent, and a reply that Claude Code marks as cut off or partial give no report. Give each unit with no report one resume (Rule 5) or one new dispatch. If it fails again, name it in the final report as not covered, and report no clean result for it. A limit of tries that a skill names wins, and a run format does not replace this check.

Do not accept "the failure was there before" as a reason to ignore a red build or test (see `dev-essentials:engineering-discipline` Rule 1).

## Run format agreement

A long orchestrated run can state its run format at the start. The run format has these parts: the check scope and the reporting rules. A skill that uses this section names its concrete checks and how the user agrees: at a gate in the interactive mode, or by not objecting. `dev-essentials:bug-hunt` and `dev-essentials:review-loop` use it.

Check scope: the skill names its concrete checks for tiers 1 and 2 of `Trust but verify`. Tier 3 still applies.

Reporting:

- Do not write detailed interim results in chat. They scroll out of view. Long results go to files.
- Write at most one short status line for each phase, for example "Step 3: area 2 of 5 done."
- When a question blocks the run, ask it in chat at once.
- End with one final report. If the instructions of the user define an end-of-run report format, use it. Else use the default of the skill.

Agreement:

- State the run format once, at the start of the run. Do not add a new stop only for this.
- In the interactive mode, the user agrees at the first gate that the skill already has, such as a plan sign-off or a triage acknowledgment. Else the user agrees by not objecting. If the user already asked for full autonomy, or the request already gives the same rules, the agreement is implicit. State the format and continue.
- The user can change the format at any time. Follow the change.
- When the format is agreed, the check scope replaces these things for this run only. The first is tiers 1 and 2 of the `Trust but verify` section above. Tier 3 still applies. The second is any rule in the instructions of the user that asks the orchestrator to re-check every subagent claim. Checks that the skill itself requires still run.

## Anti-patterns

The rules above hold the other anti-patterns. The list below adds more:

- "Subagents cannot use MCP tools, so the main agent has to post." This is wrong. If the schemas are loaded, subagents can call MCP tools.
- One independent task split across several redundant `Agent` dispatches, where a single dispatch does the job.
