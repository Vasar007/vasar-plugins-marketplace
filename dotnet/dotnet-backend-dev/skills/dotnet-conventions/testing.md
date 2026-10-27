# Testing Conventions

## Framework & Libraries

The tests use these libraries of the project. The rules name each library by its role.

- **The test framework** (for example, NUnit 3) runs the tests and gives the test and fixture attributes.
- **The assertion library** (for example, FluentAssertions with `Should()`). Prefer it over the assertions of the test framework (for example, NUnit `Assert.*`).
- **The mocking library** (for example, NSubstitute). Never create a mock with it directly, for example with `Substitute.For<T>()` (see below).
- **The test data library** (for example, AutoFixture). Never get an interface mock from it directly, for example with `Fixture.Freeze<IInterface>()` or `Fixture.Create<IInterface>()`.

The code examples in this file use NUnit, FluentAssertions, NSubstitute, and AutoFixture. With another test framework, assertion library, mocking library, or test data library, use its equivalent attributes and calls.

## Base Classes

| Base Class                         | Use For                                            |
|------------------------------------|----------------------------------------------------|
| `BaseTest`                         | Basic tests without mocking                        |
| `BaseMockTest`                     | Tests needing mocks via the test data library      |
| `BaseEqualityMemberTests<T>`       | Domain models with IEquatable + IEqualityOperators |
| `BaseExceptionTests<T>`            | Custom exception classes                           |
| `BaseValidatableObjectTests`       | Configuration options validation                   |
| `BaseConfigurationBindingTests<T>` | Configuration binding from JSON/env vars           |
| `BaseDependencyInjectionTests`     | DI registration verification                       |
| `BaseStringWrapperTests<T>`        | String-based primitive wrappers                    |
| `BaseGuidWrapperTests<T>`          | GUID-based primitive wrappers                      |
| `BaseRepositoryWithOneKeyTest`     | Single-key repository CRUD (integration)           |
| `BaseRepositoryWithTwoKeysTest`    | Composite-key repository CRUD (integration)        |
| `WebApiBaseTest`                   | Controller/API endpoints (integration)             |

These base classes live in the repo's `*.Tests.Common` project (exact name varies per service).

## Use the create-tests Skill for Examples

Before you write any test, invoke the `create-tests` skill. It has a matching example for each test type: domain model, exception, wrapper, repository, options validation, binding, DI, controller, migration, and mocked service. Do not guess the shape of tests from memory.

## Test Class Structure

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class XxxTests : {BaseClass}
{
    private readonly XxxGenerator _generator;

    public XxxTests()
    {
        _generator = new XxxGenerator();
    }
}
```

## AAA Comments

Every test must have `// Arrange.` `// Act.` `// Assert.` with dot and blank line after each:

```csharp
[Test]
public void Method_Condition_ExpectedResult()
{
    // Arrange.
    var input = GenerateInput();
    var service = CreateService();

    // Act.
    var result = service.DoSomething(input);

    // Assert.
    result.Should().NotBeNull();
}
```

For combined sections, join the names with `&`: `// Act & Assert.`, `// Arrange, Act & Assert.`, or `// Arrange & Act.`. Never use `+`.

## No Direct Mock Creation

```csharp
// ❌ FORBIDDEN
var mock = Substitute.For<IService>();
var repo = Fixture.Freeze<IMyRepository>();
var svc = Fixture.Create<IMyService>();

// ✅ REQUIRED — use Test Mock Builders
var repo = new TestMyRepositoryBuilder(Fixture)
    .AddItem(item1)
    .Build();

// ✅ Empty mock via static factory
var repo = TestMyRepositoryBuilder.CreateWithoutSetup(Fixture);
```

This applies to every interface mock. If `Test{Interface}Builder` does not exist, create it first in the `*.Tests.Common/Helpers/Mocks/{Feature}/` folder of the repo.

## Private Helper Methods

Test cases must not call builders or generators directly:

```csharp
// ❌ WRONG — generator called directly in test
var item = _itemGenerator.GenerateItem(name: "A");

// ✅ CORRECT — wrapped in private helper
var item = GenerateItem(name: "A");

private Item GenerateItem(String? name = null)
{
    return _itemGenerator.GenerateItem(name: name ?? "default");
}
```

Each mock dependency has exactly one `Create{Mock}` helper, and each test data type has exactly one `Generate{Model}` helper, with no overloads. Do not add setup such as `.Returns()` to a mock that a helper returns. The full rules, with the optional parameters, `.ApplyIf`, and the bulk `Add*Range` methods, are in [Private Helper Methods](../create-tests/SKILL.md#private-helper-methods) of the `create-tests` skill.

## Common Builders

Typically already available in `*.Tests.Common/Helpers/Mocks/`:

- `TestOptionsMonitorBuilder<T>`: `IOptionsMonitor<T>` and `IOptions<T>`
- `TestLoggerBuilder`: `ILogger<T>` (static `CreateWithoutSetup<T>(Fixture)`)
- Various repository and service builders.

## Test Data Generators

Generators are in `*.Tests.Common/Helpers/Generators/`:

- Each test class creates its generators with `new {Model}Generator()`. A generator has no static `Instance` property (see [Test Model Generators](../create-tests/SKILL.md#test-model-generators) in `create-tests`).
- Provide `Create{Model}()` (explicit params) and `Generate{Model}()` (random) methods.

## Database Integration Tests

```csharp
[TestFixture]
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]    // manual DbContext
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))] // DI DbContext
```

A generic test class that has `[TestFixtureSource]` also has `[TestFixture]`.

Use `{Service}InMemoryDbOptions` for in-memory EF tests instead of mocking `DbContext`.

## Code Style in Tests

- Use **System type names**: `String`, `Int32`, `Boolean` (not `string`, `int`, `bool`).
- Use `var` for delegate variables: `var act = () => service.DoSomething();`
- Reuse expected variables. Compare with the assertion library (for example, `actual.Should().Be(expected)`), not with repeated literals.
- Use the `StringNullOrWhiteSpace_TestCases` test-case source for null/empty/whitespace validation (for example, `[TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]` in NUnit).
- Turn off parallel runs (for example, with `[NonParallelizable]` in NUnit) only for a test that needs exclusive access to a database or an external resource.
