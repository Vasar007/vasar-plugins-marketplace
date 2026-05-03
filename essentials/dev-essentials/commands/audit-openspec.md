---
description: Deep verification of OpenSpec change artifacts before implementation
---

Audit all artifacts in an OpenSpec change folder for issues, ambiguities, and missing context before implementation.

**Arguments**: $ARGUMENTS

- Format: `<change-folder-name>`
- The folder under `openspec/changes/`.
- If no arguments, use the **AskUserQuestion tool** to ask for the change folder name.

## Steps

1. **Read all artifacts**

   Read every file in `openspec/changes/{FOLDER}/`:
   - `proposal.md`, `design.md`, `tasks.md`, `delta-spec*.md`, and any other `.md` files.

2. **Deep analysis**

   For each artifact, verify:

   **Completeness:**
   - Are all referenced types, interfaces, methods defined or clearly pointed to?
   - Are all acceptance criteria testable and specific?
   - Are edge cases covered?
   - Are error handling strategies defined?

   **Consistency:**
   - Do artifacts agree with each other? (design matches proposal scope, tasks match design)
   - Do naming conventions match the existing codebase?
   - Are referenced files/classes/methods real? (verify against actual code)

   **Clarity:**
   - Could an AI agent implement each task without asking questions?
   - Are there ambiguous phrases like "as appropriate", "if needed", "similar to X"?
   - Are inputs/outputs for each operation clearly defined?

   **Codebase alignment:**
   - Do artifacts reference correct existing patterns, base classes, interfaces?
   - Are dependency injection patterns correct?
   - Do referenced configuration options, repositories, services actually exist?
   - Do method signatures match what the codebase actually has?

3. **Cross-reference with codebase**

   For every file, class, interface, or method mentioned in the artifacts:
   - Verify it exists in the codebase.
   - Verify signatures/contracts match what the artifacts assume.
   - Check for recent changes that might invalidate assumptions.

4. **Reverify findings**

   Go through the full list of findings again. Confirm each is a **real issue**, not a false positive. Remove anything that turns out to be fine on closer inspection.

5. **Report**

   Present findings organized by severity:

   **Blockers** — Cannot implement without resolving:
   - Missing information, contradictions, impossible requirements

   **Warnings** — Could cause problems during implementation:
   - Ambiguities, assumptions that should be validated, missing edge cases

   **Suggestions** — Would improve quality:
   - Better naming, additional test cases, documentation gaps

   For each finding, include: which artifact/section, what the issue is, and a concrete suggestion for resolution.

## Guardrails

- **Read-only** — do not modify any artifacts or code. Only report findings.
- **Be thorough** — check every corner, every reference, every assumption.
- **Be specific** — "the design mentions IFooService but it doesn't exist" not "some interfaces might be missing".
- **Verify against real code** — do not trust artifact claims about the codebase without checking.
- **Ask the user** if you find something that could go either way.
- **Report only real issues** — reverify each finding before including it.
