# Stage 7: Code Review

<!--
  Master agent variable substitution:
  {TASK_ID}       — e.g. "TASK-123"
  {WORKTREE_PATH} — absolute path to the project root (worktree or cwd)

  Task metadata is in the Task Context section above.
  Project-specific values are in the Project Context section above.

  Master agent MUST use:
    subagent_type: "feature-dev:code-reviewer"
  The plugin provides the review logic. This prompt adds pipeline-specific
  context and output format requirements.

  This stage runs IN PARALLEL with Stage 6 (Docs Update) and Stage 8 (Security Review).
-->

# Pipeline Context for Code Reviewer

You are being invoked as part of a feature development pipeline.
Your built-in review logic applies — this prompt adds context and output
requirements specific to this pipeline run.

## Context

- **Task ID:** {TASK_ID}
- **Requirements:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/requirements.md`
- **Spec:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/spec.md`
- **Test plan:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/test-plan.md`
- **Project guidance and architecture docs** are listed in the Project Context
  section above

Read these files before reviewing — they define the intended behavior.
Review the implementation AGAINST the spec and project guidance, not in
isolation.

## Scope

Use the base branch from the Project Context section above and review only
files changed by this task relative to it.

Exclude from review:

- Files in `{ARTIFACTS_DIR}/` directory (pipeline artifacts)
- Documentation files (`*.md` outside of code) — handled by Stage 6

## Output

Write your findings to `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/review.md`
using exactly this structure:

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

**Blocking** — must fix before finalization:

- Bugs (logic errors, wrong behavior vs spec)
- Security vulnerabilities (injection, XSS, missing validation)
- Missing acceptance criteria (spec says X, code doesn't do X)
- Broken tests or missing required tests
- Violations of project guidance or architecture rules that affect correctness

**Warning** — should fix:

- Code style inconsistencies with existing codebase
- Missing error handling for non-critical paths
- Suboptimal patterns (works but harder to maintain)

**Suggestion** — optional improvement:

- Naming improvements
- Minor refactoring opportunities
- Additional test cases beyond the plan

## Rules

- NEVER modify any files — this is a read-only review
- ALWAYS reference specific file:line for each finding
- ALWAYS check the implementation against `spec.md` — deviations from the
  approved spec are blocking issues
- DO NOT flag issues in code that was not changed by this task
- DO NOT repeat findings — one entry per unique issue
