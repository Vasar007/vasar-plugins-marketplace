---
description: Audit a design plan file or folder before implementation.
---

Audit a design plan (file or folder) for issues, ambiguities, and missing context before implementation.

**Arguments**: $ARGUMENTS

- Format: `<path-to-plan>`
- Path to a plan file (`.md`) or folder containing design documents.
- If no arguments, use the **AskUserQuestion tool** to ask for the path.

## Steps

1. **Read all documents**

   Read every `.md` file at the given path. If the path is a folder, also read the `.md` files in its subfolders.

2. **Deep analysis**

   For each document, answer these questions:

   **Completeness:**
   - Are all referenced types, interfaces, methods defined or clearly pointed to?
   - Are all acceptance criteria testable and specific?
   - Are edge cases covered?
   - Are error handling strategies defined?
   - Are all phases/tasks self-contained enough to implement independently?

   **Consistency:**
   - Do documents agree with each other?
   - Do naming conventions match the existing codebase?
   - Are task dependencies correctly ordered?

   **Clarity:**
   - Can an AI agent implement each task without asking questions?
   - Are there ambiguous phrases like "as appropriate", "if needed", "similar to X"?
   - Are inputs/outputs for each operation clearly defined?
   - Are modification instructions specific? ("add method X to class Y" not "update the service")

   **Codebase alignment:**
   - Do documents reference correct existing patterns, base classes, interfaces?
   - Are dependency injection patterns correct?

3. **Cross-reference with codebase**

   For every file, class, interface, method, configuration option, repository, or service mentioned in the plan:
   - Find out whether it exists in the codebase.
   - Find out whether its signature or contract matches what the plan assumes.
   - Look for recent changes that can make an assumption wrong.

   Record each mismatch as a finding.

4. **Read back the code references**

   Make sure that each finding that names code cites a `path:line` that this run opened, and that the line says what the finding claims. Correct or remove each finding that fails this test. If a finding says that code does not exist, it needs no `path:line`. Name the search that found nothing, for example the `Grep` pattern and the folder.

5. **Report**

   Present findings organized by severity:

   **Blockers**: the work cannot start until they are resolved.
   - Missing information, contradictions, impossible requirements

   **Warnings**: they can cause problems during implementation.
   - Ambiguities, assumptions that need a test, missing edge cases

   **Suggestions**: they improve the quality.
   - Better naming, more test cases, documentation gaps

   For each finding, include: which document/section, what the issue is, and a concrete suggestion for resolution.

## Guardrails

- **Read-only**: do not change any artifact, document, or code. Only report findings.
- **Be specific**: name the file, the section, and the exact gap. Example: "The design names `IFooService`, but the code has no such interface."
- **Ask the user**: if a finding can go either way, ask the user.
- **Verify before confident fixes**: a suggested fix for a technical claim (configuration, schema, library API, method signature, codebase reference, or DI lifetime) must rest on a primary source: official docs, a known-working real example, or a throwaway test. If you did not test it, label it as a theory, not as a fix. See `dev-essentials:engineering-discipline` Rule 5.
