---
description: Multi-agent team review of artifacts/designs from different perspectives
---

Launch a team of agents to review artifacts/designs from multiple professional perspectives simultaneously.

**Arguments**: $ARGUMENTS

- Format: `<path> [agent-count] [model]`
- `path`: the file or folder to review (required). If it is not provided, use **AskUserQuestion** to ask.
- `agent-count`: the number of agents (optional, default: 5). Maps to roles below.
- `model`: the model of the agents (optional, default: current model).

If arguments are ambiguous or missing the path, use **AskUserQuestion** to clarify.

## Agent Roles

Assign roles in this order based on agent count:

| #   | Code Name                | Perspective                                                            |
|-----|--------------------------|------------------------------------------------------------------------|
| 1   | business analyst         | Requirements coverage, user stories, acceptance criteria, edge cases   |
| 2   | technical architecture   | System design, patterns, scalability, integration points, dependencies |
| 3   | QA engineer              | Testability, test coverage gaps, failure modes, data validation        |
| 4   | senior developer         | Implementation feasibility, code quality, naming, existing patterns    |
| 5   | devil's advocate         | Challenge assumptions, find contradictions, worst-case scenarios       |

If agent count < 5, use the first N roles. If agent count > 5, add roles like "security engineer", "performance engineer", "DX/usability reviewer" as needed.

## Steps

1. **Read the target**

   Read all `.md` files at the given path. If the path is a folder, also read the `.md` files in its subfolders. Summarize the content so you can include it in each agent's prompt.

2. **Launch the agent team**

   For each role, launch an Agent (subagent_type: `general-purpose`) with the following prompt structure. Do not use `Explore` or `dev-essentials:code-locator` for a role. They only find code, and they do not load the CLAUDE.md files of the repository.

   ```md
   Find what blocks a correct implementation of the following artifacts or design, from the point of view of a **{role name}**.
   This is a read-only review. Do not change any file.

   ## Target
   Path: {path}

   ## Content
   {summarized content or file listing — keep concise but sufficient}

   ## Your Task
   1. Read all files at the target path carefully.
   2. Review from your **{role name}** perspective. Report every issue that you find, also one that you are not sure of. The consolidation step filters the findings, so a filter here drops real issues.
   3. Categorize findings by severity:
      - **Blockers** — must be resolved before implementation
      - **Warnings** — could cause problems, should be addressed
      - **Suggestions** — would improve quality
   4. For each finding: state which file/section, what the issue is, a concrete suggestion, and your confidence (high, medium, or low).
   5. Test each claim about the codebase against the real code. If you did not test a suggested fix against a primary source (official docs or a working example in the code), label it as a theory, not as a fix. For a broad search, you can dispatch the agent type `dev-essentials:code-locator`. It returns locations only, and you judge them.
   6. **Reverify**: Go through your findings again. Remove anything that is not a real issue on closer inspection. Be strict — only keep genuine problems.
   7. Present your final findings with your role clearly stated at the top.
   ```

   **Launch:** launch all agents in a single message so they run concurrently, then wait for all results (see `dev-essentials:subagent-orchestration` Rule 3).

3. **Consolidate results**

   After all agents finish:
   - Collect all findings from all agents.
   - Deduplicate. If several agents found the same issue, merge them into one entry, and name the roles that flagged it.
   - Filter once, here. If a finding does not affect correctness or a stated requirement, move it to Suggestions. The other findings stay under Blockers or Warnings.
   - Present a unified report:

   ```md
   ### Team Review Report: {path}

   **Reviewers:** {list of roles}

   **Blockers** (must fix):
   - [flagged by: {roles}] issue description

   **Warnings** (should address):
   - [flagged by: {roles}] issue description

   **Suggestions** (nice to have):
   - [flagged by: {roles}] issue description

   **Agreement matrix:** Note which findings had consensus (multiple roles) vs. single-role findings.
   ```

## Guardrails

- **Read-only**: do not change any file. Only report findings.
- **One filter, at consolidation**: the agents report every finding with a confidence. Step 3 is the only step that filters.
- **Be specific**: every finding names a concrete file/section and includes a resolution suggestion.
- **Verify before confident fixes**: apply this rule to the findings of the agents and to your consolidation. A suggested fix for a technical claim (configuration, schema, library API, method signature, codebase reference, or DI lifetime) must rest on a primary source: official docs, a known-working real example, or a throwaway test. If neither an agent nor you tested it, label it as a theory, not as a fix. See `dev-essentials:engineering-discipline` Rule 5.
