---
description: Multi-agent team review of artifacts/designs from different perspectives
---

Review artifacts or designs from several professional points of view.

**Arguments**: $ARGUMENTS

- Format: `<path> [agent-count] [model]`
- `path`: the file or folder to review (required). If it is not provided, use **AskUserQuestion** to ask.
- `agent-count`: a whole number of 1 or more (optional). With a count, the run takes the team route. With no count, it takes the two-view route. See "Routes".
- `model`: the model of the agents (optional, default: current model). If the second argument is not a whole number and names a model, it is the model, and the run takes the two-view route. For any other second argument, or for a third argument after a model, use **AskUserQuestion**. Example: `/audit-team docs/design.md opus`.

If arguments are ambiguous or missing the path, use **AskUserQuestion** to clarify.

## Agent Roles

| #   | Code Name                | Perspective                                                            |
|-----|--------------------------|------------------------------------------------------------------------|
| 1   | business analyst         | Requirements coverage, user stories, acceptance criteria, edge cases   |
| 2   | technical architecture   | System design, patterns, scalability, integration points, dependencies |
| 3   | QA engineer              | Testability, test coverage gaps, failure modes, data validation        |
| 4   | senior developer         | Implementation feasibility, code quality, naming, existing patterns    |
| 5   | devil's advocate         | Challenge assumptions, find contradictions, worst-case scenarios       |

## Routes

- **Two-view route** (no count): the main session reviews the target with all roles of the table as lenses. Then one fresh agent takes the devil's advocate role. The agent does not see the review of the main session, so it is the independent view. The main session already holds the target from Step 1, so its pass reads the target no second time. The `model` argument applies to the agent only.
- **Team route** (a count): one agent for each of the first N roles, in the order of the table. If the count is more than 5, add roles like "security engineer", "performance engineer", "DX/usability reviewer" as needed.

## Steps

1. **Read the target**

   Read all `.md` files at the given path. If the path is a folder, also read the `.md` files in its subfolders. Summarize the content so you can include it in each agent's prompt.

2. **Review**

   Each role agent is an Agent with subagent_type: `general-purpose` and the prompt below. Do not use `Explore` or `dev-essentials:code-locator` for a role. They only find code, and they do not load the CLAUDE.md files of the repository.

   ```md
   Review the following artifacts or design from the point of view of a **{role name}**.
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
   6. Present your final findings with your role clearly stated at the top.
   ```

   On the two-view route:

   1. Review the target with each role of the table as a lens, one role at a time. Follow items 2 to 5 of the prompt for each lens, and note the role of each finding. Finish this list before you launch the agent, so that the result of the agent does not change your review.
   2. Launch one role agent for the devil's advocate role. Fill its prompt with the summary of Step 1 only, and put none of your findings in it. If the `model` argument is set, pass it to the agent.

   On the team route, launch one role agent for each role, all in a single message so that they run concurrently. Then wait for all results (see `dev-essentials:subagent-orchestration` Rule 3).

3. **Consolidate results**

   After the review of Step 2 is done:
   - Collect all findings: on the two-view route, the findings of the main session and of the agent. On the team route, the findings of all agents.
   - Deduplicate. If several roles found the same issue, merge them into one entry, and name the roles that flagged it. On the two-view route, name a lens of the main session as `main: {role name}`, and the agent as `agent: devil's advocate`.
   - Filter once, here. If a finding does not affect correctness or a stated requirement, move it to Suggestions. The other findings stay under Blockers or Warnings.
   - Present a unified report in the form below. Keep its heading and each bold label word for word, also `**Agreement matrix:**`. `review-loop` reads the parts Blockers, Warnings, and Suggestions and the agreement matrix by these labels.

   ```md
   ### Team Review Report: {path}

   **Reviewers:** {list of roles}

   **Blockers** (must fix):
   - [flagged by: {roles}] issue description (confidence: high, medium, or low)

   **Warnings** (should address):
   - [flagged by: {roles}] issue description (confidence: high, medium, or low)

   **Suggestions** (nice to have):
   - [flagged by: {roles}] issue description (confidence: high, medium, or low)

   **Agreement matrix:** Note which findings had consensus (multiple roles) vs. single-role findings.
   ```

   On the two-view route, the **Reviewers** line names the main session with its lenses and the devil's advocate agent. If the main session and the agent both flag a finding, the finding has consensus. The lenses of the main session are one view, so an agreement of two lenses is not consensus.

## Guardrails

- **Read-only**: do not change any file. Only report findings.
- **One filter, at consolidation**: the role agents and the lens pass of the main session report every finding with a confidence. Step 3 is the only step that filters.
- **Be specific**: every finding names a concrete file/section and includes a resolution suggestion.
- **Verify before confident fixes**: apply this rule to the findings of the agents and to your consolidation. A suggested fix for a technical claim (configuration, schema, library API, method signature, codebase reference, or DI lifetime) must rest on a primary source: official docs, a known-working real example, or a throwaway test. If neither an agent nor you tested it, label it as a theory, not as a fix. See `dev-essentials:engineering-discipline` Rule 5.
