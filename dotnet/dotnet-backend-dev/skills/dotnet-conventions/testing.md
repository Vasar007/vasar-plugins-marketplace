# Testing Conventions

## Framework & Libraries

- **NUnit 3** test framework.
- **FluentAssertions** (`Should()`) — prefer over NUnit `Assert.*`.
- **NSubstitute** for mocking — but NEVER use `Substitute.For<T>()` directly (see below).
- **AutoFixture** for test data — but NEVER use `Fixture.Freeze<IInterface>()` or `Fixture.Create<IInterface>()` directly.

## Base Classes

| Base Class                         | Use For                                            |
|------------------------------------|----------------------------------------------------|
| `BaseTest`                         | Basic tests without mocking                        |
| `BaseMockTest`                     | Tests needing mocks via AutoFixture                |
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

## MANDATORY: Use the create-tests Skill for Examples

Before writing ANY test, invoke the `create-tests` skill — it provides a matching example per test type (domain model, exception, wrapper, repository, options validation, binding, DI, controller, migration, mocked service). Do not guess the shape of tests from memory.

## Test Class Structure

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class XxxTests : {BaseClass}
{
    private readonly XxxGenerator _generator;

    public XxxTests()
    {
        _generator = XxxGenerator.Instance;
    }
}
```

## AAA Comments (MANDATORY)

Every test MUST have `// Arrange.` `// Act.` `// Assert.` with dot and blank line after each:

```csharp
[Test]
public void Method_Condition_ExpectedResult()
{
    // Arrange.
    var input = GenerateInput();

    // Act.
    var result = _sut.DoSomething(input);

    // Assert.
    result.Should().NotBeNull();
}
```

## STRICT: No Direct Mock Creation

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

This applies to EVERY interface mock. If `Test{Interface}Builder` doesn't exist, create it first in the repo's `*.Tests.Common/Helpers/Mocks/{Feature}/` folder.

## STRICT: Private Helper Methods (Mandatory Indirection)

Test cases MUST NOT call builders or generators directly:

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

Rules:

1. **One `Create{Mock}` per mock dependency** — no overloads.
2. **One `Generate{Model}` per test data type** — no overloads.
3. **No post-setup on returned mocks** — once returned from builder, mock is fully configured. Never add `.Returns()` after.
4. Use optional parameters with sensible defaults.
5. Use bulk `Add*Range` methods over loops.

## Common Builders

Typically already available in `*.Tests.Common/Helpers/Mocks/`:

- `TestOptionsMonitorBuilder<T>` — `IOptionsMonitor<T>` / `IOptions<T>`
- `TestLoggerBuilder` — `ILogger<T>` (static `CreateWithoutSetup<T>(Fixture)`)
- Various repository and service builders.

## Test Data Generators

Singletons in `*.Tests.Common/Helpers/Generators/`:

- `{Model}Generator.Instance`
- Provide `Create{Model}()` (explicit params) and `Generate{Model}()` (random) methods.

## Database Integration Tests

```csharp
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]    // manual DbContext
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))] // DI DbContext
```

Use `{Service}InMemoryDbOptions` for in-memory EF tests instead of mocking `DbContext`.

## Code Style in Tests

- Use **System type names**: `String`, `Int32`, `Boolean` (not `string`, `int`, `bool`).
- Use `var` for delegate variables: `var act = () => _sut.DoSomething();`
- Reuse expected variables — compare `actual.Should().Be(expected)`, not repeated literals.
- Use `[TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]` for null/empty/whitespace validation.
- Use `[NonParallelizable]` only when test requires exclusive DB or external resource access.
