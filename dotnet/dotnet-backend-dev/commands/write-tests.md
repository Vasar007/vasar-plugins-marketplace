---
description: Write, refactor, or extend .NET tests for one or more targets. A target is a class, a module (a folder or a namespace), or a whole project. For one class, the main session writes the tests. Else the command dispatches one `test-engineer` agent for each target, runs independent targets in parallel, and shows one merged report.
when_to_use: Use it for "write tests for X", "add tests for this folder", "test this project", or "refactor these tests". For one new test in an existing test class, use the create-tests skill.
argument-hint: "<class | file.cs | folder | namespace | project.csproj> [...] [-- extra instructions]"
---

Write, refactor, or extend tests for one or more targets. If the run has one target of the kind Class, the main session writes its tests with the `create-tests` skill. Else the `dotnet-backend-dev:test-engineer` agent does the work, one agent for each target. On this route, the main session only parses the arguments, dispatches the agents, and merges their reports. It does not load the `create-tests` skill, and it does not read source or test files.

**Arguments**: $ARGUMENTS

- Accepts one or more targets, separated by spaces or commas.
- Text after `--` is extra instructions. The main session follows them, or each agent gets this text word for word.
- The form of each argument sets the kind and the size of its target:

  | Argument | Target kind | Scope |
  | --- | --- | --- |
  | A class name, for example `OrderPricingService` | Class | The class and its test class |
  | The path of a `.cs` file | Class | Each class in the file |
  | The path of a folder that has no `.csproj` file in it | Module | Each class in the folder and its subfolders |
  | A namespace, for example `MyProject.Application.Orders` | Module | Each class in the namespace |
  | The path of a `.csproj` file, a folder that has a `.csproj` file in it, or a project name | Assembly | Each class in the project |

- A target in a test project, for example `ShoppingCartTests`, gets a refactor. The test class gets the conventions and the missing tests. Any other target gets new or extended tests.
- Examples:
  - `OrderPricingService`: the main session writes tests for this class.
  - `InvoiceNumberGenerator, CustomerLookupService`: two agents run in parallel, one for each class.
  - `ShoppingCartTests`: the main session refactors this test class.
  - `<repo-source-folder>/MyProject/Path/To/MyClass.cs`: the main session writes tests for the class in this file.
  - `<repo-source-folder>/MyProject.Application/Orders`: one agent writes tests for each class in this folder.
  - `<repo-source-folder>/MyProject.Domain/MyProject.Domain.csproj`: one agent writes tests for each class in this project.
  - `OrderPricingService -- only add the missing null-argument tests`: the main session, with the extra instructions.
  - No arguments: ask which targets to test.

## Steps

1. **Parse arguments**

   Split the arguments into targets and extra instructions. If no target is given, use the **AskUserQuestion tool** to ask which classes, folders, namespaces, or projects need tests.

2. **Find each target**

   Find the kind and the absolute path of each target with Glob and Grep only. Do not read source or test files in this step.

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

4. **Choose the route, and dispatch the agents**

   If step 3 leaves one target and its kind is Class, write its tests in the main session. Do the steps of the section "One class in the main session" below, and then go to step 7. Each other run dispatches agents: two or more targets, a module, or an assembly.

   The delegation tests of Rule 1 of `dev-essentials:subagent-orchestration` give the reason. Two or more targets are independent work that runs in parallel. A module or an assembly puts many file reads and long test output into a context, and the main session needs only the short report. One class passes neither test. A subagent for it adds a cold start, a brief, and a report, and it cannot ask the user.

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
   - Dispatch the groups as agents with step 4. Do not go back to step 3, because step 3 merges the groups into the large target again.
   - If an agent of a group reports `Too large` again, or a `Too large` line has no classes, do not split again. Ask the user with the **AskUserQuestion tool** how to split the target.

6. **Check the combined result**

   If two or more agents ran, do these checks:

   - If two reports name the same new builder or generator file, dispatch one more `dotnet-backend-dev:test-engineer` agent. Its brief names the file and the test classes of both reports. The agent makes sure that the file has one consistent version and that the tests of both reports pass.
   - Run `dotnet test --filter "FullyQualifiedName~<TestClass1>|FullyQualifiedName~<TestClass2>"` once, with each test class from the reports. If the repo requires it, add the path of the solution. Show only the summary lines. If a test fails, dispatch the agent of that target again with the failure in the brief.

7. **Report results**

   Merge the reports of the agents into one report. For one class in the main session, give the same report for its one target:

   - A table with one row for each target: the target, the files created or modified, the test count (new tests, changed tests, fixed tests), and the result of the test run.
   - The builders and generators that the agents created.
   - The classes that an agent skipped, with the reason.
   - If step 6 ran, the result of the combined test run.

## One class in the main session

The main session does the work of a `test-engineer` agent for the one target. Follow the extra instructions together with the conventions of the skill. A `.cs` file or a merged class target can hold more than one class. Then do steps 2 to 7 for each class, one class after another.

1. Load the `dotnet-backend-dev:create-tests` skill with the Skill tool. The agent gets this skill preloaded, so the main session loads it first. If the Skill call fails, stop and report the error.
2. Read the source class. Find its test type in the example table of the skill. Search the test projects for an existing test file of the class. If the target is in a test project, the mode is a refactor.
3. Skip a type that has no behavior to test, for example an interface, an enum, or generated code (`*.g.cs`, `*.Designer.cs`). Name each skipped type in the report, with the reason.
4. Before you write code, read each example file that the table names for the test type. The files are in the `examples/` folder of the skill. First, read each file from `${CLAUDE_PLUGIN_ROOT}/skills/create-tests/examples/`. Claude Code puts the absolute folder of this plugin at the start of that path. If that path starts with `$`, or the folder does not exist, read each file from `<folder>/examples/`. The Skill tool output names this base folder (`Base directory for this skill: <folder>`). If it names no folder, find the files with Glob and the pattern `plugins/cache/*/dotnet-backend-dev/*/skills/create-tests/examples/*.md`. Search below the Claude home folder. If the variable `CLAUDE_CONFIG_DIR` is set, that folder is its value. Else it is `<home>/.claude`. If the pattern finds more than one version folder, use the highest version.
5. Search the `*.Tests.Common/Helpers/Mocks/` folder for test builders and the `*.Tests.Common/Helpers/Generators/` folder for generators, and reuse them. If a builder or a generator is missing, create it first with the patterns of the examples.
6. Write the tests with all conventions of the skill. For a refactor, fix each violation of the conventions and keep the test logic.
7. Run `dotnet test --filter "FullyQualifiedName~<TestClassName>"`. If the repo uses a filter for each test project, add the path of the test project. Fix each compile error and each failed test, and run the tests again until all tests pass. Show only the summary lines.
8. If you need an answer of the user, for example for the escape hatch of the skill, ask with the **AskUserQuestion tool**.

## Guardrails

- **Write or change tests in the main session only for one target of the kind Class** (step 4). For each other run, the `test-engineer` agents write the tests. Each agent loads the `create-tests` skill and its examples, and it follows all conventions of the skill.
- **On the agent route, do not read source or test files in the main session**, for example to enrich a brief. The agent finds and reads them in its own context. For one target of the kind Class, the main session reads them in the section "One class in the main session".
- **Do not dispatch two agents that write to the same file at the same time.** Merge their targets in step 3.
- **Do not commit, stash, or check out.** The user decides about the commit.
