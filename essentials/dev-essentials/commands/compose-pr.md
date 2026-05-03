---
description: Create a concise architectural PR description from git diffs
---

Create a pull request description by analyzing the full git diff of the current branch against the target branch (e.g., `main`/`master`).

**Arguments**: $ARGUMENTS

- If arguments are provided, use them as additional context or instructions for the PR description.

## Steps

1. **Determine the base branch**

   Run `git symbolic-ref refs/remotes/origin/HEAD` to detect the repo's default branch (e.g. `main`, `master`, or `release/1.0/master`). If that fails, ask the user.

2. **Analyze all commits and diffs**

   Use `git log` and `git diff` against the base branch to understand the full scope of changes.

   **IMPORTANT**: Ignore ephemeral artifacts — OpenSpec drafts (`openspec/` directory), notes folders (`Notes/`), and any other scratch areas the repo uses. Focus on actual code and configuration changes (source folders, test folders, pipelines, Dockerfiles, helm charts).

3. **Compose the PR description**

   Write the description in the following format and save it to a file at `Notes/PRs/PR-<branch-short-name>.md`:

   ```markdown
   # <Top-level header: a clear, descriptive title for the change — do NOT just copy the commit message>

   ## Summary
   <1-3 bullet points describing what this PR does at a high level>

   ## Key Changes

   ### <Category 1> (e.g., Domain, Application, Infrastructure, API, Configuration, Tests)
   - <change description>
   - <change description>

   ### <Category 2>
   - <change description>

   ## Impact
   - <What areas of the system are affected>
   - <Any breaking changes or migration notes>

   ## Test Plan
   - [ ] <testing checklist item>
   - [ ] <testing checklist item>
   ```

   Keep it under 2000 characters. Be concise and architectural — describe *what* and *why*, not line-by-line *how*.

4. **Output the result**

   Show the composed PR description to the user. Mention the file path where it was saved.

## Guardrails

- Do NOT include OpenSpec artifacts or Notes in the analysis
- Do NOT just repeat commit messages — synthesize them into a coherent narrative
- Choose a good top-level header that captures the essence of the change
- Keep the description concise — this is for reviewers, not documentation
- Group changes by architectural layer, not by commit
