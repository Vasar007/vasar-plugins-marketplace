---
description: Create a concise architectural PR description from git diffs.
---

Create a pull request description for the current branch. The `dev-essentials:pr-composer` agent writes it. The format of that agent is the one PR description format of this plugin.

**Arguments**: $ARGUMENTS

- Optional: extra context or instructions for the PR description.

## Steps

1. **Dispatch the agent**

   Call the `Agent` tool with `subagent_type: "dev-essentials:pr-composer"`. Put these items into the brief:

   - The absolute path of the repository root (`git rev-parse --show-toplevel`).
   - If the user named a base branch, that base branch.
   - The text of `$ARGUMENTS`, word for word, as extra context. If it is empty, say that the user gave no extra context.

2. **Show the result**

   When the agent completes, show the user the PR description and the path of the file that the agent saved. If the agent asks a question, for example about the base branch, ask the user. Then dispatch the agent again with the answer in the brief.

## Guardrails

- Do not write the description yourself. The format, the length limits, and the writing rules are in the agent file.
