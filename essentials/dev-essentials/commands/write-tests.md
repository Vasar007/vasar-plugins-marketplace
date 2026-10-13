---
description: Write, refactor, or extend tests for specified classes
---

Write, refactor, or extend tests for one or more classes.

**Arguments**: $ARGUMENTS

- Accepts one or more class names or file paths, separated by spaces or commas.
- A business logic class gets new or updated tests in its test file. An existing test class gets a refactor or new tests.
- Examples:
  - `OrderPricingService`: write tests for this service.
  - `InvoiceNumberGenerator, CustomerLookupService`: write tests for both classes.
  - `ShoppingCartTests`: refactor this existing test class.
  - `<repo-source-folder>/MyProject/Path/To/MyClass.cs`: write tests for the class in this file.
  - No arguments: ask which classes to test.

## Steps

1. **Parse arguments**

   Extract class names or file paths from the arguments. If no arguments are provided, use the **AskUserQuestion tool** to ask which classes need tests.

2. **For each target class**

   a. **Find the source file**: search the source folder of the repo for the class definition. Typical folders are `Sources/`, `src/`, or a top-level project folder.

   b. **Read the source class**: understand its dependencies, methods, behavior, and the interfaces that it implements.

   c. **Load the `create-tests` skill** with the Skill tool. Determine the test type, and read the example files that the example table of the skill names for that type. Also read `examples/enforced-gates.md` of the skill, because its gates apply to every test class.

   d. **Look for existing tests**: search the test projects of the repo for an existing test class. Typical folders are `Sources/Tests/`, `Tests/`, or `tests/`.

   e. **Look for existing builders and generators**: search `*.Tests.Common/Helpers/Mocks/` and `*.Tests.Common/Helpers/Generators/` in the test-common project of the repo.

   f. **Write or refactor tests**:
      - If the test file exists, refactor it to match the conventions, and add the missing tests.
      - If the test file does not exist, create a new test file that follows the example pattern.
      - Create the missing Test Mock Builders and Generators first.

   g. **Run tests**: `dotnet test --filter "FullyQualifiedName~{TestClassName}"`. If the repo requires it, add the path of the test project. If a test fails, fix it before you report.

3. **Report results**

   For each class:
   - What was created/modified
   - Test count (new tests written, existing tests fixed)
   - Test run results (pass/fail)
   - Any builders or generators that were created

## Guardrails

- **MUST load `create-tests` and read the matching example** before writing any test code.
- **Follow ALL conventions** of the `create-tests` skill. Take no shortcuts.
- **Do NOT improvise** test patterns. If you are unsure, read the examples or search the existing tests.
