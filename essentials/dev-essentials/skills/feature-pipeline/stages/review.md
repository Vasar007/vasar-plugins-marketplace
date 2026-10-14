# Stage 7: Code Review

<!--
  Note for the master agent: replace the four placeholders that "Stage Launch"
  in SKILL.md names.

  Task metadata is in the Task Context section above.
  Project-specific values are in the Project Context section above.

  The master agent MUST use:
    subagent_type: "feature-dev:code-reviewer"
  The plugin has the review logic. This prompt adds the context and the
  output format of the pipeline.

  This stage runs IN PARALLEL with Stage 6 (Docs Update) and Stage 8 (Security Review).
-->

# Pipeline Context for Code Reviewer

A feature development pipeline runs you. Your built-in review logic applies. This prompt adds the context and the output format of this pipeline run.

## Context

- **Task ID:** {TASK_ID}
- **Requirements:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/requirements.md`
- **Spec:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/spec.md`
- **Test plan:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/test-plan.md`
- **Project guidance and architecture docs**: the Project Context section above lists them.

Read these files before the review. They define the intended behavior. Review the implementation AGAINST the spec and the project guidance, not in isolation.

## Scope

Use the base branch from the Project Context section above. Review only the files that this task changed relative to it.

Exclude from the review:

- Files in the `{ARTIFACTS_DIR}/` folder (pipeline artifacts)
- Documentation files (`*.md` outside of code). Stage 6 handles them.

## Output

Write your findings to `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/review.md`, with exactly this structure:

```markdown
## Blocking Issues
- [ ] <description> — `file:line`

## Warnings
- [ ] <description> — `file:line`

## Suggestions
- [ ] <description> — `file:line`

## Summary
<Overall assessment: approve / request changes>
<Number of blocking issues / warnings / suggestions>
```

### Classification Guidelines

**Blocking**: must be fixed before finalization.

- Bugs (logic errors, or behavior that differs from the spec)
- Security vulnerabilities (injection, XSS, missing validation)
- Missing acceptance criteria (the spec says X, and the code does not do X)
- Broken tests, or missing required tests
- Violations of the project guidance or the architecture rules that affect correctness

**Warning**: a fix is recommended, but the issue does not block finalization.

- Code style that differs from the existing codebase
- Missing error handling on non-critical paths
- Weak patterns (the code works, but it is harder to maintain)

**Suggestion**: an optional improvement.

- Better names
- Small refactoring chances
- More test cases beyond the plan

## Rules

- NEVER modify any file except `review.md`. This is a read-only review.
- ALWAYS give the `file:line` of each finding.
- ALWAYS compare the implementation with `spec.md`. A deviation from the approved spec is a blocking issue.
- DO NOT flag issues in code that this task did not change.
- DO NOT repeat findings. Write one entry for each unique issue.
