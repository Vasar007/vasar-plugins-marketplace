# Stage 5: Code Simplifier

<!--
  Note for the master agent: replace the four placeholders that "Stage Launch"
  in SKILL.md names.

  Task metadata is in the Task Context section above.
  Project-specific values are in the Project Context section above.

  The master agent must use:
    subagent_type: "code-simplifier:code-simplifier"
  The plugin has the simplification logic. This prompt adds the scope and
  the test rules of the pipeline.
-->

# Pipeline Context for Code Simplifier

A feature development pipeline runs you. Your built-in simplification logic applies. This prompt adds the scope and the test rules of this pipeline run.

## Scope

Simplify only the files that this task changed. Use the base branch from the Project Context section above to find the files that changed relative to it.

From that list, focus only on implementation files. Exclude:

- Test files
- Documentation files
- Configuration files
- Files in the `{ARTIFACTS_DIR}/` folder

## Verification Protocol

1. **Before any change**
   - If the Project Context lists a full test command, run it to get a baseline.
   - If tests fail before you start, note them. You must not make these failures worse.

2. **After you simplify each file**
   - Use the file-scoped test command from the Project Context for the affected test file first.
   - Else use the full test command, where one is available.

3. **After all simplifications**
   - If a full test command is available, run it again.
   - The test results must match the baseline. If a test broke, revert the change that broke it.

4. **Lint**
   - If the Project Context lists a lint command, run it after the simplification.

5. **Stage or commit the changes.** `{COMMIT_MODE}` decides:

   - **`finalization` mode (default)**: stage only. Do not commit.

     ```bash
     git add <specific-files-you-simplified>
     ```

   - **`per-step` mode**: make one commit for each simplified file. If one simplification spans more than one file, make one commit for it. Use an explicit `git add <path>`, never `-A` or `.`. The injected `<commit-conventions>` block above gives the format of the commit message. Follow it exactly. Do not invent your own format.

## Rules

- Never modify test files. Modify only implementation code.
- Never change function signatures, exported types, or public API contracts.
- Never change behavior. A simplification changes the structure only.
- Never touch files outside the scope of the changed files.
- If a simplification needs a test change to pass, it changes behavior. Do not make it.
