---
description: Create a concise architectural PR description from git diffs.
---

Create a pull request description from the full git diff of the current branch against the target branch, for example `main` or `master`.

**Arguments**: $ARGUMENTS

- Optional: extra context or instructions for the PR description.

## Steps

1. **Determine the base branch**

   Run `git symbolic-ref refs/remotes/origin/HEAD` to detect the default branch of the repo, for example `main`, `master`, or `release/1.0/master`. If that fails, ask the user.

2. **Analyze all commits and diffs**

   Use `git log` and `git diff` against the base branch to understand the full scope of changes.

   **IMPORTANT**: Ignore ephemeral artifacts: OpenSpec drafts (`openspec/` directory), notes folders (`Notes/`), and any other scratch areas the repo uses. Focus on actual code and configuration changes (source folders, test folders, pipelines, Dockerfiles, helm charts).

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

   Keep it under 2000 characters. Be concise and architectural: describe *what* and *why*, not line-by-line *how*. The readers are reviewers, not users of documentation.

4. **Output the result**

   Show the composed PR description to the user. Mention the file path where it was saved.

## Guardrails

- Do NOT just repeat commit messages. Combine them into one coherent narrative.
- Group changes by architectural layer, not by commit.
