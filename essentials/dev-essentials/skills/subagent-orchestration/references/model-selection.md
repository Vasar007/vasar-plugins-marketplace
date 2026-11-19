# Model Selection Details

The section "Model selection" of `SKILL.md` holds the model matrix and its rules. This file holds the rest of that section and the effort rules of Rule 5.

## How a model gets applied

- A session does not switch its own model in the middle of a conversation. It keeps the model that it runs.
- To reach any other model, **dispatch a subagent with the `model` parameter of the `Agent` tool**. Never use `/model`. Use a name that this parameter accepts. The current names are `sonnet`, `opus`, `haiku`, and `fable`. The tool can add newer names.
- So **work for any model other than the model of the session must be delegated**. If a skill or the user names a model that the session does not run, that work becomes a subagent dispatch. The same holds for a stronger model in the matrix, but not for a cheaper one (Rule 1). On a Sonnet session, a code change that Rule 1 keeps in the main loop stays there, also a bug fix with no fix plan. A plan, a review, and a decision that no plan settles still go to an Opus subagent.
- **`subagent_type: "fork"` ignores `model`**. A fork inherits the model of the parent. If a task needs a specific model, use an agent type that is not a fork.
- **A plugin agent type can set its own model.** Its agent file sets `model`. A dispatch of that type can then leave out the `model` parameter. A `model` parameter in the call wins over the agent file. Leave out `model` for `dev-essentials:code-locator`, `dev-essentials:fact-gatherer`, and `dev-essentials:test-runner`.
- **Only an agent file sets the auto-compact window.** The field is `autoCompactWindow`. The subagent compacts its context at that size. The `Agent` tool has no parameter for it. About 100,000 tokens is a good size for search, fact, and build-check work. A larger context often costs more and adds noise. A `general-purpose` dispatch does not compact at this size. The three agent types above handle a code search, a fact question, and a long build and test run. Their files set `autoCompactWindow: 100000`. If a test of Rule 1 sends one of these kinds of work to a subagent, dispatch the matching type.

## The model of the orchestrating session

- Run the orchestrating session on Opus or Sonnet, never on Haiku, because it makes the decisions of the workflow. If the session runs on Haiku, say so to the user before the first dispatch. Suggest a new session on Sonnet or Opus, for example with `claude --model sonnet`.
- On a Sonnet session, give each critical decision that the workflow makes without the user to a short Opus subagent. An example is a run in the full mode. `dev-essentials:engineering-discipline` Rule 2 defines a critical decision. The brief holds the options, the plan, and the facts from the code. The subagent returns its choice and the reason.

## Plan → execute split

1. **Plan on Opus.** Dispatch an Opus subagent to build the plan. If the session already runs on Opus, this dispatch is not necessary. The plan names, for each task, the exact paths, the anchors (`path:line` and method names), and the key signatures. Then each executor reads only those places, and does not search again.
2. **Execute by the tests of Rule 1.** A task that passes a test goes to a Sonnet subagent with the plan of that task.

## Haiku scope (mechanical execution only)

Haiku is not only for one-step lookups. Prefer Haiku over Sonnet for a short sequence of actions with **no synthesis of its own**. Every decision is already made, and the subagent only runs the steps.

- **Haiku-eligible**: a new PR from a pushed branch, with a PR description that is already written. The push itself stays with the main agent (Rule 4). A post of a comment that is already drafted. A new run of a known command, with a report of its output. An explicit 1-2-3 edit list. Also the work of the agent types above, because they return facts and no synthesis.
- **Guardrail: the content must already be decided**. If the dispatch must first *produce* the content, the work is not mechanical. Examples: a summary comment that comes from reading and combining several days of work across several PRs, or a decision about which values are correct. Keep such work on Sonnet. If it is closer to planning or judgment, use Opus. Eligibility comes from content that is already decided, never from the tool that the dispatch calls. No blanket Haiku rule exists for PR creation or issue updates. A question that needs judgment goes whole to an Opus subagent, not to a fact gatherer. Examples: an ambiguous behavior, a permission, a public contract, or a choice between designs.
- **Worked contrast**: "create the PR for the pushed `<branch>` from the description already composed above" goes to **Haiku**. "Summarize this task's work across 3 PRs and 4 days, then post it as the closeout comment" goes to **Sonnet**.
- **Code search**: do not count on the built-in `Explore` agent for a cheap search, because its model can change between releases. When a test of Rule 1 sends a code search to a subagent, the skills of this plugin dispatch `dev-essentials:code-locator`. Its agent file sets `model: haiku`, so its cost does not change with a release. Like `Explore`, the three agent types do not load the `CLAUDE.md` files of the project. So each brief restates the project rules that the agent needs.
- **One dispatch, one model**. If one dispatch both drafts and delivers, it stays on Sonnet. If the draft is already a separate, finished artifact, you can split the work into a Sonnet draft and a Haiku post. Never add a dispatch only to reach Haiku.

## Effort

Pass `effort` on each dispatch of a general agent type such as `general-purpose`. Use the level that the user or a skill names. If no one names a level, pass `medium`, the start of the ladder in `SKILL.md`. A review starts at `high`, because no self-test shows that it fell short. Mechanical work can use `low`. A model that does not support a level runs at the highest level below it. For any other agent type, pass `effort` in two cases: the user or a skill names a level, or the session runs at a lower effort than the task needs. Two kinds of dispatch differ:

- An agent type whose file sets `effort`, for example `dev-essentials:test-runner`, needs no `effort` parameter. A parameter in the call wins over the file.
- A fork takes no `effort` parameter.

If the `Agent` tool has no `effort` parameter, or the model has no effort levels, leave it out. Then the ladder makes no move that only raises the effort.

Do not set the effort of the session with the environment variable `CLAUDE_CODE_EFFORT_LEVEL`. It overrides the `effort` parameter and the agent file of every subagent. To set the effort of the session, use `/effort` or the `--effort` flag.
