---
description: Deep verification of a design plan before implementation
---

Audit a design plan (file or folder) for issues, ambiguities, and missing context before implementation.

**Arguments**: $ARGUMENTS

- Format: `<path-to-plan>`
- Path to a plan file (`.md`) or folder containing design documents.
- If no arguments, use the **AskUserQuestion tool** to ask for the path.

## Steps

1. **Read all documents**

   Read every `.md` file at the given path. If a folder, read all Markdown files recursively.

2. **Deep analysis**

   For each document, verify:

   **Completeness:**
   - Are all referenced types, interfaces, methods defined or clearly pointed to?
   - Are all acceptance criteria testable and specific?
   - Are edge cases covered?
   - Are error handling strategies defined?
   - Are all phases/tasks self-contained enough to implement independently?

   **Consistency:**
   - Do documents agree with each other?
   - Do naming conventions match the existing codebase?
   - Are referenced files/classes/methods real? (verify against actual code)
   - Are task dependencies correctly ordered?

   **Clarity:**
   - Could an AI agent implement each task without asking questions?
   - Are there ambiguous phrases like "as appropriate", "if needed", "similar to X"?
   - Are inputs/outputs for each operation clearly defined?
   - Are modification instructions specific? ("add method X to class Y" not "update the service")

   **Codebase alignment:**
   - Do documents reference correct existing patterns, base classes, interfaces?
   - Are dependency injection patterns correct?
   - Do referenced configuration options, repositories, services actually exist?
   - Do method signatures match what the codebase actually has?

3. **Cross-reference with codebase**

   For every file, class, interface, or method mentioned in the plan:
   - Verify it exists in the codebase.
   - Verify signatures/contracts match what the plan assumes.
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

   For each finding, include: which document/section, what the issue is, and a concrete suggestion for resolution.

## Guardrails

- **Read-only** — do not modify any documents or code. Only report findings.
- **Be thorough** — check every corner, every reference, every assumption.
- **Be specific** — "the plan mentions IFooService but it doesn't exist" not "some interfaces might be missing".
- **Verify against real code** — do not trust plan claims about the codebase without checking.
- **Ask the user** if you find something that could go either way.
- **Report only real issues** — reverify each finding before including it.
- **Verify before confident fixes.** When suggesting a resolution for any technical claim found in the plan — config, schema, library API, method signature, codebase reference, or DI lifetime — verify against a primary source first: official docs, a known-working real example, or a throwaway test. Pattern-matching a plausible-sounding cause and presenting it as the answer wastes review cycles and erodes trust. Frame unverified suggestions as theories ("this might be …"), not authoritative fixes. See `dev-essentials:engineering-discipline`.
