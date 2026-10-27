---
description: Write, refactor, or extend .NET tests for one or more targets. A target is a class, a module (a folder or a namespace), or a whole project. The command dispatches one `test-engineer` agent for each target, runs independent targets in parallel, and shows one merged report.
when_to_use: Use it for "write tests for X", "add tests for this folder", "test this project", or "refactor these tests". For one new test in an existing test class, use the create-tests skill.
argument-hint: "<class | file.cs | folder | namespace | project.csproj> [...] [-- extra instructions]"
---

Write, refactor, or extend tests for one or more targets. The `dotnet-backend-dev:test-engineer` agent does the work, one agent for each target. The main session only parses the arguments, dispatches the agents, and merges their reports. It does not load the `create-tests` skill, and it does not read source or test files.

**Arguments**: $ARGUMENTS

- Accepts one or more targets, separated by spaces or commas.
- Text after `--` is extra instructions. Each agent gets this text word for word.
- The form of each argument sets the kind and the size of its target:

  | Argument | Target kind | Scope |
  | --- | --- | --- |
  | A class name, for example `OrderPricingService` | Class | The class and its test class |
  | The path of a `.cs` file | Class | Each class in the file |
  | The path of a folder that has no `.csproj` file in it | Module | Each class in the folder and its subfolders |
  | A namespace, for example `MyProject.Application.Orders` | Module | Each class in the namespace |
  | The path of a `.csproj` file, a folder that has a `.csproj` file in it, or a project name | Assembly | Each class in the project |

- A target in a test project, for example `ShoppingCartTests`, gets a refactor. Its agent refactors the test class to the conventions and adds the missing tests. Any other target gets new or extended tests.
- Examples:
  - `OrderPricingService`: one agent writes tests for this class.
  - `InvoiceNumberGenerator, CustomerLookupService`: two agents run in parallel, one for each class.
  - `ShoppingCartTests`: one agent refactors this test class.
  - `<repo-source-folder>/MyProject/Path/To/MyClass.cs`: one agent writes tests for the class in this file.
  - `<repo-source-folder>/MyProject.Application/Orders`: one agent writes tests for each class in this folder.
  - `<repo-source-folder>/MyProject.Domain/MyProject.Domain.csproj`: one agent writes tests for each class in this project.
  - `OrderPricingService -- only add the missing null-argument tests`: one agent, with the extra instructions.
  - No arguments: ask which targets to test.

## Steps

1. **Parse arguments**

   Split the arguments into targets and extra instructions. If no target is given, use the **AskUserQuestion tool** to ask which classes, folders, namespaces, or projects need tests.

2. **Find each target**

   Find the kind and the absolute path of each target with Glob and Grep only. Do not read source or test files. The agent reads them in its own context.

   - Class name: search the `*.cs` files of the repository for the type declaration, for example `class OrderPricingService`.
   - Namespace: search the `*.cs` files for `namespace <name>`. If no file declares it, search for a `<name>.csproj` file. If one exists, the target is an assembly.
   - Path: make sure that the path exists. A folder that has a `.csproj` file in it is an assembly. A folder without one is a module.

   If an argument matches nothing, or it matches more than one type or project, use the **AskUserQuestion tool** to ask which one the user means. If an argument is not a target, ask whether it is an extra instruction.

3. **Group the targets**

   Two agents must not write to the same file. So merge the targets that overlap, before you dispatch:

   - The same scope named twice is one target.
   - A class and its test class, for example `OrderPricingService` and `OrderPricingServiceTests`, are one target.
   - A target inside another target is part of the larger target. Examples are a class inside a module and a module inside an assembly.
   - Two classes whose tests go into the same test file are one target with a list of classes.

   All targets that are left after the merge are independent. One agent can still need a test builder or a generator that another agent creates. Step 6 finds this case and fixes it.

4. **Dispatch the agents**

   Make one `Agent` call for each target, with `subagent_type: "dotnet-backend-dev:test-engineer"`. Put all calls in one message, so that the agents run in parallel. Dispatch at most four agents at the same time, because each agent builds the code and runs the tests. If more targets are left, dispatch them in a new message when the first agents complete.

   Put these items into each brief:

   - The absolute path of the repository root (`git rev-parse --show-toplevel`).
   - The target kind: class, module, or assembly.
   - The target as the user typed it, and its scope: the absolute path of the `.cs` file, the folder, or the `.csproj` file. For a namespace, also the namespace. For a merged class target, the list of classes.
   - The mode: new or extended tests, or a refactor of a test class.
   - The scope of each other agent of this run, or "no other agents". The agent then does not change a file in the scope of another agent.
   - The extra instructions, word for word. If there are none, say that the user gave no extra instructions.
   - This line: "Do this work yourself. Do not dispatch other agents."

5. **Answer questions and split large targets**

   The agent does not ask the user. It puts each question in its report. If a report has a question, ask the user with the **AskUserQuestion tool**. Then send the answer to that agent with `SendMessage` and its agent ID. If `SendMessage` fails, dispatch the agent again with the answer in the brief.

   A module or an assembly with more than 20 classes is too large for one agent. Its agent writes no tests. It lists the classes of the scope, grouped by folder, in the `Too large` line of its report. Split this list into class targets:

   - Put the classes into groups of at most 20 classes. If the classes of one folder fit into one group, keep them together.
   - Each group is a merged class target with its list of classes. No class is in two groups. Each group keeps the mode of the large target.
   - Dispatch the groups with step 4. Do not go back to step 3, because step 3 merges the groups into the large target again.
   - If an agent of a group reports `Too large` again, or a `Too large` line has no classes, do not split again. Ask the user with the **AskUserQuestion tool** how to split the target.

6. **Check the combined result**

   If two or more agents ran, do these checks:

   - If two reports name the same new builder or generator file, dispatch one more `dotnet-backend-dev:test-engineer` agent. Its brief names the file and the test classes of both reports. The agent makes sure that the file has one consistent version and that the tests of both reports pass.
   - Run `dotnet test --filter "FullyQualifiedName~<TestClass1>|FullyQualifiedName~<TestClass2>"` once, with each test class from the reports. If the repo requires it, add the path of the solution. Show only the summary lines. If a test fails, dispatch the agent of that target again with the failure in the brief.

7. **Report results**

   Merge the reports of the agents into one report:

   - A table with one row for each target: the target, the files created or modified, the test count (new tests, changed tests, fixed tests), and the result of the test run.
   - The builders and generators that the agents created.
   - The classes that an agent skipped, with the reason.
   - If step 6 ran, the result of the combined test run.

## Guardrails

- **Do not write or change tests in the main session.** The `test-engineer` agent loads the `create-tests` skill and its examples. It follows all conventions of the skill.
- **Do not read source or test files in the main session** to enrich a brief. The agent finds and reads them in its own context.
- **Do not dispatch two agents that write to the same file at the same time.** Merge their targets in step 3.
