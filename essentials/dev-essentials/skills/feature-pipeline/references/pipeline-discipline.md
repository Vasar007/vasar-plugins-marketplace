# Pipeline discipline

The master agent reads this file at Step 0 of `SKILL.md`. These three safeguards apply to the master agent and to every stage. A stage subagent never sees this file. So step 4 of "Launch steps" in `references/stage-launch.md` copies the three safeguards into the prompt of each stage, and the subagents must follow them too.

## Safeguard 1: claims about Claude Code

Before you state how a Claude Code feature works, read the current system prompt. Do not match patterns from training data. Examples: Skill tool dispatch, Agent tool subagent types, and the merge order of settings. More examples: MCP tool prefixes, plugin loading, slash-command routing, and the memory system. The system prompt is the source of truth for the session, and it changes between Claude Code versions. If you are not sure, say so and look it up. Do not state a categorical rule. See `dev-essentials:engineering-discipline` for the wider rule.

## Safeguard 2: schema, manifest, and configuration errors

At any stage, you can find a schema error, a failed manifest validation, or a mismatch with a library API. Before you propose a fix, find the cause in a primary source: the official docs or a known-working example, for example the plugin `feature-dev`. Until then, call your diagnosis a theory ("this can be ..."), not a fix. See `dev-essentials:subagent-orchestration` for the quality of briefs.

## Safeguard 3: an MCP failure

If the MCP server of the task provider fails, answer two questions before you look at the install state or advise a restart:

1. Does the server fail only in this session, or also in other Claude sessions that run at the same time?
2. Which terminal hosts Claude Code? Warp and other sandboxed terminals isolate MCP child processes.

If the host can isolate subprocesses, advise a plain OS terminal (cmd, pwsh, or Windows Terminal), not a restart in place.
