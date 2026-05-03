---
description: Write, refactor, or enhance tests for specified classes
---

Write, refactor, or enhance tests for one or more classes.

**Arguments**: $ARGUMENTS

- Accepts one or more class names or file paths, separated by spaces or commas
- Can be business logic classes (will create/update their test files) or existing test classes (will refactor/enhance them)
- Examples:
  - `ProvisioningPlanService` — write tests for this service
  - `SecurePasswordGenerator, AccountAvailabilityService` — write tests for both classes
  - `ProvisioningPlanTests` — refactor this existing test class
  - `<repo-source-folder>/MyProject/Path/To/MyClass.cs` — write tests for file at path
  - (no arguments) — prompt for which classes to test

## Steps

1. **Parse arguments**

   Extract class names or file paths from the arguments. If no arguments provided, use the **AskUserQuestion tool** to ask which classes need tests.

2. **For each target class**

   a. **Find the source file** — search the repo's source folder (typically `Sources/`, `src/`, or a top-level project folder) for the class definition

   b. **Read the source class** — understand dependencies, methods, behavior, interfaces implemented

   c. **Determine test type** and invoke the `create-tests` skill to read the matching example. Mapping:
      - Domain model with `IEquatable` → `domain-model-tests.md`
      - Custom exception → `exception-tests.md`
      - Primitive wrapper → `wrapper-tests.md`
      - Repository → `repository-tests.md`
      - Configuration options → `config-options-tests.md`
      - Configuration binding → `config-binding-tests.md`
      - DI registration → `di-registration-tests.md`
      - Service/business logic → `mock-builders.md` + `generators.md`
      - Controller → `controller-tests.md`
      - Migration → `migration-tests.md`

   d. **Also read the main `create-tests` SKILL.md** — via the Skill tool so Claude loads it properly

   e. **Check for existing tests** — search the repo's test projects (typically under `Sources/Tests/`, `Tests/`, or `tests/`) for an existing test class

   f. **Check for existing builders/generators** — search `*.Tests.Common/Helpers/Mocks/` and `*.Tests.Common/Helpers/Generators/` within the repo's test-common project

   g. **Write or refactor tests**:
      - If test file exists → refactor to match conventions, add missing tests
      - If test file doesn't exist → create new test file following the example pattern
      - Create any missing Test Mock Builders or Generators first

   h. **Run tests** — `dotnet test --filter "FullyQualifiedName~{TestClassName}"` to verify (add the specific test project path if the repo requires it)

3. **Report results**

   For each class:
   - What was created/modified
   - Test count (new tests written, existing tests fixed)
   - Test run results (pass/fail)
   - Any builders or generators that were created

## Guardrails

- **MUST invoke `create-tests` and read the matching example** before writing any test code
- **Follow ALL conventions** from the `create-tests` skill — no shortcuts
- **Do NOT improvise** test patterns — if unsure, read examples or search existing tests
- **Create missing infrastructure first** — builders, generators before test classes
- **Run tests after writing** — fix any failures before reporting done
- Use the `create-tests` skill for guidance on all test patterns
