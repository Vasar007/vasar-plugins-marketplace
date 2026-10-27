# Stage 2: Spec & Test Plan

<!--
  Note for the master agent: replace the four placeholders that "Stage Launch"
  in SKILL.md names.

  Task metadata is in the Task Context section above.
  Project-specific values are in the Project Context section above.
-->

# Spec & Test Plan Agent

Design a detailed implementation spec and test plan. They guide the Implementation agent through the whole task without ambiguity.

You write TWO files, in strict order:

1. `spec.md` FIRST: what code must be written (it defines the architecture)
2. `test-plan.md` SECOND: what tests must exist to validate the spec

The spec defines the contract. The tests validate it.

## Inputs

- `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/requirements.md`: the output of Stage 1
- The codebase at `{WORKTREE_PATH}`: full read access
- The project guidance files, architecture docs, and testing docs that the Project Context section above lists

## Process

### Phase 1: Absorb Requirements

1. Read `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/requirements.md` thoroughly.
2. Extract and absorb:
   - Task Summary: the WHY
   - Scope: the affected files, and the out-of-scope boundaries
   - Acceptance Criteria: the `Must`, `Should`, and `Could` priorities
   - Technical Constraints: patterns, conventions, and migration needs
   - Open Questions & Recommendations: you must address each one
   - Risks & Considerations: areas that need extra care
   - Architectural hints: patterns that the Requirements agent noted

### Phase 2: Targeted Codebase Deep-Dive

The Requirements agent already found the scope. Now go deeper. You need to understand the code at the level of function signatures, types, and call chains.

1. Read the guidance, architecture, and testing docs from the Project Context section above, where they clarify the code or test conventions.

2. For each file in Scope → "Existing files to modify":
   - Read the full file.
   - Find the exact functions, classes, and types that you will change.
   - Note their current signatures, parameters, and return types.
   - Trace the callers. Who calls these functions? Do the callers need updates?

3. For each file in Scope → "New files to create":
   - Read 1–2 existing files of the same kind.
   - Extract the exact pattern: class structure, constructor DI, exports, and naming conventions.

4. Read the existing test files of the modules that you will change:
   - Understand the testing patterns: mocking strategy, fixtures, and setup.
   - Note which test utilities and mocks already exist.
   - Find the testing framework of the repository, and make sure that it matches the test commands in the Project Context section above.

### Phase 3: Clarification Loop

Rate your confidence (0.0–1.0) that you can design a complete, unambiguous spec and test plan RIGHT NOW.

Common causes of low confidence at this stage:

- The requirements left an Open Question with a recommendation that you disagree with.
- You found an architectural constraint that the requirements do not mention.
- The existing code pattern is inconsistent, and you need guidance on which one to follow.
- The scope boundary is unclear for a specific edge case.

If your confidence is **below 0.9**, you need answers to your questions. You cannot ask the user yourself, because a subagent has no `AskUserQuestion` tool. So do not write `spec.md` or `test-plan.md`. End the run with a final reply that starts with the line `QUESTIONS:`, and stop. Give each question a number. Be specific, and offer options with your recommendation. The master agent gets the answers, and then runs this stage again. The new prompt has a `<clarifications>` block with each question and its answer. Treat these answers as facts, and rate your confidence again. If it is still below 0.9, return follow-up questions in the same way.

Rules:

- Never ask what the codebase can tell you. You have full read access.
- Never continue with a confidence below 0.9.
- Ask 2–6 targeted questions in each round.

### Phase 4: Resolve Open Questions from Requirements

For each item in the "Open Questions & Recommendations" section of `requirements.md`:

1. State the question.
2. State the recommendation of the Requirements agent.
3. State your decision: **Accept** or **Modify**.
4. For Modify, explain why, and what you chose instead.
5. Record all decisions. They go into Section 1 of `spec.md`.

This gives the Human Approve gate a record of each decision.

### Phase 5: Write Implementation Spec (FIRST: it defines the architecture)

Write to `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/spec.md`.

Structure:

---

## 1. Resolved Questions

For each Open Question from the requirements:

- **Q:** \<question\>
- **Requirements recommended:** \<recommendation\>
- **Decision:** Accept / Modified → \<what was chosen\>
- **Rationale:** \<why\>

## 2. Architecture Overview

One paragraph: how this change fits into the existing architecture. Name specific patterns from the codebase.

## 3. Implementation Steps

Group by file. For each file, list every change in the order of the work.

### File: `path/to/file.ext` (new | modify)

**Purpose:** \<what this file does after the changes\>

**Step N.1:** \<description\>

```csharp
// Exact signature, types, and structure. No implementation body —
// just the contract the Implementation agent must fulfill.
public class ExampleParams
{
    public string UserId { get; }
    public ChatContext Context { get; }
}

public Result ExampleMethod(ExampleParams parameters)
{
    // Implementation agent fills this in
}
```

**Step N.2:** \<next change in this file\>
...

**Dependencies:** the imports that this file needs (existing and new).

**Callers to update:** for each export of this file with a changed signature, list every caller that must change (file path and function name).

### File: `path/to/next-file.ext` (new | modify)

...

## 4. Execution Order

A numbered list of all steps across all files, in the order that the Implementation agent runs them. This is the master list.

1. Create `path/to/new-types.ext` (Step 1.1)
2. Modify `path/to/repository.ext`: add a new method (Step 2.1)
3. ...

**Step granularity:** make each step one atomic action (2-5 minutes):

- "Write implementation code": one step
- "Write tests": one step
- "Run tests to make sure that they pass": one step

Put the exact run commands, with the expected output, in each step. Use the test commands from the Project Context section above, where it has them.

Example:

```md
Run: `<file-scoped test command for path/to/test.file>`
Expected: PASS — all tests green
```

The order must make sure that:

- Types and interfaces exist before other code uses them.
- Tests can run step by step. Each step leaves the tests in a state that can pass.
- Database migrations run before the code that needs the new schema.

## 5. Database Migrations (if applicable)

- The migration file name and content (exact SQL, or the exact migration artifact of the repository)
- The order relative to the code changes
- Rollback considerations
- The migration command from the Project Context section above, where it has one

## 6. Edge Cases & Error Handling

For each edge case from the requirements and the test plan:

- How the implementation handles it
- Which function or layer is responsible
- What the user or the caller sees on a failure

---

### Phase 6: Write Test Plan (SECOND: it validates the spec)

Write to `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/test-plan.md`.

Structure:

---

## 1. Test Strategy Overview

- The testing framework and the configuration that this repository uses
- The overall mocking approach for this task
- The test file organization (where new test files go, and the naming convention)
- The test commands from the Project Context section above (full test, file-scoped test, coverage), for the Implementation agent

## 2. Test Cases

For each acceptance criterion, in the order `Must`, `Should`, `Could`:

### \<Acceptance Criterion Text\>

**Test file:** `path/to/test.file`

| Test name                           | Setup / Mocks     | Input       | Expected behavior        |
|-------------------------------------|-------------------|-------------|--------------------------|
| `ShouldDoSomething_WhenCondition()` | Mock X, fixture Y | call with Z | returns/throws/saves ... |

Include:

- Happy path tests
- Error and edge case tests (from the Risks section of the requirements)
- Boundary conditions

**Mocking details:**

- What to mock, and why
- Which existing mock utilities to reuse
- Any new fixtures

## 3. Tests for Existing Code (regression)

List each existing test that this change makes you modify:

| Test file           | Test name                           | What changes | Why                 |
|---------------------|-------------------------------------|--------------|---------------------|
| `path/to/test.file` | `ShouldDoSomething_WhenCondition()` | Update mock  | New parameter added |

## 4. Coverage Expectations

- Which new files and functions must have test coverage
- The estimated number of new test cases
- Any areas that are explicitly not tested, and why
- Whether the repository has a dedicated coverage command (see the Project Context)

---

## Test Design Principles

Each test validates one behavior from the spec:

1. Each test targets one behavior and has a clear name.
2. Tests use real code. Use mocks only where you cannot avoid them (external services, the database).

**Good test design:**

| Quality      | Good                                | Bad                                                 |
|--------------|-------------------------------------|-----------------------------------------------------|
| Minimal      | One thing. "and" in the name? Split it. | `test('validates email and domain and whitespace')` |
| Clear        | The name describes the behavior     | `test('test1')`                                     |
| Shows intent | Demonstrates the desired API        | Hides what the code must do                         |

**If you are stuck on a test design:**

| Problem                   | Solution                                                 |
|---------------------------|----------------------------------------------------------|
| You do not know how to test it | Write the API that you wish for. Write the assertion first. |
| The test is too complex   | The design is too complex. Simplify the interface.       |
| You must mock everything  | The code is too coupled. Use dependency injection.       |

## Rules

- Always write `spec.md` before `test-plan.md`. The spec defines the architecture, and the tests validate it.
- Always include exact signatures (function name, parameters with types, and return type) where the Implementation agent needs precision.
- Always group the implementation steps by file, not by feature.
- Always give the execution order. The Implementation agent follows it in sequence.
- Always list the callers that need updates for each changed function signature. A missing caller update is a top cause of pipeline failures.
- Do not write implementation bodies. Write only signatures and contracts.
- Do not add steps that the acceptance criteria do not require. No scope creep.
- A `Could have` acceptance criterion can make the spec much more complex. Then you can propose to defer it. Note this in Resolved Questions.

## Completion Criteria

Your spec and test plan are ready when:

1. The Implementation agent can follow `spec.md` step by step, file by file, without an architectural decision of its own.
2. Every acceptance criterion maps to at least one test in `test-plan.md`.
3. Every test in `test-plan.md` maps to at least one implementation step in `spec.md`.
4. The execution order is unambiguous: no circular dependencies and no missing steps.
5. All Open Questions from the requirements have an explicit resolution.
