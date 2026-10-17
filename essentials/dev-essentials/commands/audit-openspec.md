---
description: Audit the artifacts of an OpenSpec change before implementation
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

   For each artifact, answer these questions:

   **Completeness:**
   - Are all referenced types, interfaces, methods defined or clearly pointed to?
   - Are all acceptance criteria testable and specific?
   - Are edge cases covered?
   - Are error handling strategies defined?

   **Consistency:**
   - Do artifacts agree with each other? (design matches proposal scope, tasks match design)
   - Do naming conventions match the existing codebase?

   **Clarity:**
   - Can an AI agent implement each task without asking questions?
   - Are there ambiguous phrases like "as appropriate", "if needed", "similar to X"?
   - Are inputs/outputs for each operation clearly defined?

   **Codebase alignment:**
   - Do artifacts reference correct existing patterns, base classes, interfaces?
   - Are dependency injection patterns correct?

3. **Cross-reference with codebase**

   For every file, class, interface, method, configuration option, repository, or service mentioned in the artifacts:
   - Find out whether it exists in the codebase.
   - Find out whether its signature or contract matches what the artifacts assume.
   - Look for recent changes that can make an assumption wrong.

   Record each mismatch as a finding.

4. **Reverify findings**

   Go through the full list of findings again. Find out whether each finding is a **real issue** or a false positive. Remove each finding that turns out to be fine.

5. **Report**

   Present findings organized by severity:

   **Blockers**: the work cannot start until they are resolved.
   - Missing information, contradictions, impossible requirements

   **Warnings**: they can cause problems during implementation.
   - Ambiguities, assumptions that need a test, missing edge cases

   **Suggestions**: they improve the quality.
   - Better naming, more test cases, documentation gaps

   For each finding, include: which artifact/section, what the issue is, and a concrete suggestion for resolution.

## Guardrails

- **Read-only**: do not change any artifact, document, or code. Only report findings.
- **Be specific**: name the file, the section, and the exact gap. Example: "The design names `IFooService`, but the code has no such interface."
- **Ask the user**: if a finding can go either way, ask the user.
- **Verify before confident fixes**: a suggested fix for a technical claim (configuration, schema, library API, method signature, codebase reference, or DI lifetime) must rest on a primary source: official docs, a known-working real example, or a throwaway test. If you did not test it, label it as a theory, not as a fix. See `dev-essentials:engineering-discipline` Rule 5.
