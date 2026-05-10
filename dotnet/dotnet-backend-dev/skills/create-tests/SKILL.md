---
name: create-tests
description: Create unit and integration tests following standard conventions with NUnit, FluentAssertions, and proper base class inheritance. Use when creating any tests. Triggers on requests like "create tests", "unit tests", "test this class", "write tests for", "integration tests".
---

# Create Tests

Create unit and integration tests in `tests/` or `src/Tests/` following standard conventions using NUnit, FluentAssertions, and proper base classes.

## Test Project Structure

```text
tests/ (or src/Tests/)
├── {ProjectName}.Domain.Tests/         # Domain model unit tests
├── {ProjectName}.Application.Tests/    # Service unit tests
├── {ProjectName}.Infrastructure.Tests/ # Repository integration tests, client tests
├── {ProjectName}.Configuration.Tests/  # Config options validation tests
├── {ProjectName}.WebApi.Tests/         # Controller integration tests
└── {ProjectName}.Tests.Common/         # Shared test infrastructure
```

## Base Classes Overview

| Base Class                         | Use For                                            | Type        |
|------------------------------------|----------------------------------------------------|-------------|
| `BaseTest`                         | Basic tests without mocking                        | Unit        |
| `BaseMockTest`                     | Tests needing mocks via AutoFixture                | Unit        |
| `BaseEqualityMemberTests<T>`       | Domain models with IEquatable + IEqualityOperators | Unit        |
| `BaseExceptionTests<T>`            | Custom exception classes                           | Unit        |
| `BaseValidatableObjectTests`       | Configuration options validation                   | Unit        |
| `BaseConfigurationBindingTests<T>` | Configuration binding from JSON/env vars           | Unit        |
| `BaseDependencyInjectionTests`     | DI registration verification                       | Unit        |
| `BaseStringWrapperTests<T>`        | String-based primitive wrappers                    | Unit        |
| `BaseGuidWrapperTests<T>`          | GUID-based primitive wrappers                      | Unit        |
| `BaseInt32WrapperTests<T>`         | Integer-based primitive wrappers                   | Unit        |
| `BaseRepositoryWithOneKeyTest`     | Single-key repository CRUD                         | Integration |
| `BaseRepositoryWithTwoKeysTest`    | Composite-key repository CRUD                      | Integration |
| `WebApiBaseTest`                   | Controller/API endpoints                           | Integration |
| `BaseMockTest`                     | Database/product migrations (see [migration-tests.md](examples/migration-tests.md)) | Integration |

**CRITICAL — MANDATORY STEP:** Before writing ANY test class, you **MUST read the matching example file** from [examples/](examples/). This is NOT optional — skipping this step leads to incorrect test structure, wrong base class usage, and missing conventions. Read the example FIRST, then write the test.

| What you're testing                    | Read this example first                                                                 |
|----------------------------------------|-----------------------------------------------------------------------------------------|
| Domain model with IEquatable           | [domain-model-tests.md](examples/domain-model-tests.md)                                 |
| Custom exception                       | [exception-tests.md](examples/exception-tests.md)                                       |
| Primitive wrapper (string/GUID/int ID) | [wrapper-tests.md](examples/wrapper-tests.md)                                           |
| Repository CRUD                        | [repository-tests.md](examples/repository-tests.md)                                     |
| Configuration options validation       | [config-options-tests.md](examples/config-options-tests.md)                             |
| Configuration binding from JSON/env    | [config-binding-tests.md](examples/config-binding-tests.md)                             |
| DI registration                        | [di-registration-tests.md](examples/di-registration-tests.md)                           |
| Service with mocked dependencies       | [mock-builders.md](examples/mock-builders.md) + [generators.md](examples/generators.md) |
| Controller/API endpoint                | [controller-tests.md](examples/controller-tests.md)                                     |
| Database/product migration             | [migration-tests.md](examples/migration-tests.md)                                       |
| Constructor null-arg tests             | [constructor-null-arg-tests.md](examples/constructor-null-arg-tests.md)                 |
| Scenario / end-to-end integration      | [scenario-tests.md](examples/scenario-tests.md)                                         |

If no example matches your scenario, **search existing tests** in the repo's test projects (typically under `Sources/Tests/` or `Tests/`) for a similar test class and follow its pattern. Never guess the base class API — always verify first.

## Required Conventions

### General Rules

- **Use FluentAssertions** (`Should()`) — prefer over NUnit `Assert.*`. Fall back to `Assert` only when FluentAssertions does not provide an equivalent assertion method.
- **Use System type names** instead of C# aliases: `String` not `string`, `Int32` not `int`, `Boolean` not `bool`, etc.
- **Use `var` for delegates** in test cases where you check for `Throw` or `NotThrow` (e.g., `var act = () => _sut.DoSomething();`).
- **Reuse values** — avoid duplication. Compare against the expected variable, not a repeated literal:

```csharp
// ❌ BAD - duplicated literal
var expected = 42;
var actual = DoSomething();
actual.Should().Be(42);

// ✅ GOOD - reuses expected variable
var expected = 42;
var actual = DoSomething();
actual.Should().Be(expected);
```

- **Prioritize private helper methods** — if there are existing private `Create{Mock}` / `Generate{Model}` methods in the test class, use them instead of creating new ones or calling builders/generators directly.
- **Search for examples** — if you don't find matching examples or instructions in the skill docs, search for similar use-cases and classes in the repo's test projects (typically under `Sources/Tests/` or `Tests/`) and follow their patterns.

### Test Structure

ALL tests MUST use `// Arrange.` `// Act.` `// Assert.` comments with a **dot at the end** and a **blank line after each section**:

```csharp
[Test]
public void MethodName_Condition_ExpectedResult()
{
    // Arrange.
    var input = CreateTestInput();

    // Act.
    var result = _sut.DoSomething(input);

    // Assert.
    result.Should().NotBeNull();
}
```

### Test Class Structure

```csharp
// Copyright (c) Vasily Vasilyev

using FluentAssertions;
using NUnit.Framework;

namespace {ProjectNamespace}.{Layer}.Tests.{Feature};

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class {ClassName}Tests : {BaseClass}
{
    // Use test model generators for consistent data
    private readonly SomeGenerator _generator;

    public {ClassName}Tests()
    {
        _generator = SomeGenerator.Instance;
    }

    // Tests organized by method/feature
}
```

### Test Model Generators

**ALWAYS use test model generators** for creating test data consistently:

- Generators are singletons: `{Model}Generator.Instance`
- Located in `Tests.Common/Helpers/Generators/` or `{ProjectName}.Tests.Common/Helpers/Generators/`
- Provide `Create{Model}()` (explicit params) and `Generate{Model}()` (random) methods
- **NEVER call generators directly in test cases** — wrap each call in a private `Generate{Model}(...)` helper method (see [Private Helper Methods](#private-helper-methods-mandatory-indirection))
- See [examples/generators.md](examples/generators.md) for patterns

### Parallelization

**`[Parallelizable(ParallelScope.Fixtures)]`** applies to most test fixtures.

**Exceptions - use `[NonParallelizable]`** when:

- Test modifies shared database state that conflicts with parallel tests
- Test requires exclusive access to external resource (Cosmos emulator, etc.)

```csharp
[Test]
[NonParallelizable]
public async Task AddAsync_OnSeveralEntitiesWithSameCompositeAlternateKeys_ShouldThrow()
{
    // Test that requires exclusive DB access
}
```

### Private Helper Methods (Mandatory Indirection)

**Test cases MUST NOT call Test Mock Builders or Test Data Generators directly.** All builder and generator usage must be wrapped in **private helper methods** that serve as the single configuration point for each mock or data object.

```csharp
// ❌ WRONG - builder called directly in test case
[Test]
public void TestCase()
{
    var item1 = _itemGenerator.GenerateItem(name: "A");
    var item2 = _itemGenerator.GenerateItem(name: "B");
    var repository = new TestMyRepositoryBuilder(Fixture)
        .AddItem(item1)
        .AddItem(item2)
        .Build();
    // ...
}

// ❌ WRONG - additional mock setup after calling Create helper
[Test]
public void TestCase()
{
    var repository = CreateMyRepository(item1, item2);
    repository.FindByPrimaryKeyAsync(Arg.Any<MyId>(), Arg.Any<CancellationToken>())
        .Returns(ci => ...); // FORBIDDEN - setup must be inside the builder
    // ...
}

// ✅ CORRECT - all builder/generator calls in private methods, no post-setup
[Test]
public void TestCase()
{
    var item1 = GenerateItem(name: "A");
    var item2 = GenerateItem(name: "B");
    var repository = CreateMyRepository(item1, item2);
    // repository is fully configured — no additional .Returns/.ReturnsForAnyArgs here
    // ...
}

private Item GenerateItem(String? name = null)
{
    return _itemGenerator.GenerateItem(name: name ?? "default");
}

private IMyRepository CreateMyRepository(params Item[] items)
{
    return new TestMyRepositoryBuilder(Fixture)
        .AddItemRange(items) // use bulk Add*Range methods — no foreach/if-else in helpers
        .Build(); // ALL method setups live inside TestMyRepositoryBuilder
}
```

**Rules for private helper methods:**

1. **Exactly one `Create{Mock}` method per mock dependency** — no overloads. A single method wraps the builder, accepts parameters for the items/config the mock needs. All test cases in the class share this one method
2. **Exactly one `Generate{Model}` method per test data type in the test class** — no overloads. A single method wraps the generator call
3. **No post-setup on returned mocks** — after `Create{Mock}` returns, the mock is **fully configured**. Never add `.Returns()`, `.ReturnsForAnyArgs()`, or any NSubstitute setup on the result in the test case. If you need a new behavior, **extend the Test Mock Builder** with a new method/option, then expose it through the `Create{Mock}` helper's parameters
4. **No optional / nullable parameters** — the rule depends on where the helper lives:

   | Location        | `Create*`                                            | `Generate*`                     |
   |-----------------|------------------------------------------------------|---------------------------------|
   | Test class      | NO optionals (except `CreateServiceWithAllArguments`)| NO optionals                    |
   | Generator class | NO optionals                                         | optionals OK (nullable fallback)|

   In test classes (`xxxTests.cs`), BOTH `Create*` and `Generate*` helpers MUST be optional-free — no overloads, no nullable optionals, no `params` arrays. When two test cases need different inputs, they pass different required argument values through the **same single** `Create{Mock}` or `Generate{Model}` method — there is never a second `CreateMyRepository` or a second `GenerateItem` in the same test class.

   **Exception — `CreateServiceWithAllArguments` (or `Create{Sut}WithAllArguments`):** the single SUT-factory helper used exclusively in constructor null-argument tests MUST use nullable optional parameters (`? dep = null` with `?? Create{Mock}()` fallbacks). This carve-out applies to **exactly one helper per test class**. Every other `Create*` helper in the test class remains required-only.

   In generator classes (`xxxGenerator.cs` under `Tests.Common/Helpers/Generators/...`), `Create*` stays required-only; `Generate*` MAY use nullable optional parameters with `null` defaults to mean "fill with random."

   **Universal escape hatch:** explicit human approval is required before adding any NEW optional parameter outside the two established patterns. No retroactive justification allowed.

5. **Follow the existing test class / assembly first — IMPORTANT:**
   Before writing any `Create{Mock}` or `Generate{Model}` helper, **read the existing test class, nearby test classes in the same fixture, and any shared helpers in the same test assembly**. Mirror the shapes already established there. Do NOT introduce a new `Create*` or `Generate*` pattern that conflicts with neighboring tests in the same fixture or assembly — if `CreateMyRepository` already exists and takes `Item[]`, your new test must use that same signature and pass different `Item[]` values, not create a second helper. When the existing shape is wrong (e.g., it already has two `Create*` overloads), flag it explicitly to the user rather than adding a third one.

6. **Use bulk `Add*Range` methods** — prefer `AddItemRange(items)` over `foreach` loops or `ApplyIf` chains:

```csharp
// ✅ CORRECT - single method, uses AddItemRange, no params keyword
private IMyRepository CreateMyRepository(Item[] items)
{
    return new TestMyRepositoryBuilder(Fixture)
        .AddItemRange(items)
        .Build();
}

// ❌ WRONG - two Create methods for the same mock in the same class
private IMyRepository CreateMyRepository(Item[] items) { ... }
private IMyRepository CreateMyRepository(Item? specialItem = null) { ... }
```

7. **Reusable assertion helpers** for repetitive assert blocks:

```csharp
private void AssertModelEquals(MyModel expected, MyModel actual)
{
    actual.Id.Should().Be(expected.Id);
    actual.Name.Should().Be(expected.Name);
}
```

## Mocking Rules

### STRICT PROHIBITION: No Direct Mock Creation

**NEVER** create mocks for interfaces directly in test fixtures or test cases. The following are **ALL FORBIDDEN**:

```csharp
// ❌ FORBIDDEN - Substitute.For
var mock = Substitute.For<IService>();

// ❌ FORBIDDEN - Fixture.Freeze on interfaces
var repository = Fixture.Freeze<IMyRepository>();

// ❌ FORBIDDEN - Fixture.Create on interfaces
var mock = Fixture.Create<IMyService>();
```

**ALWAYS use a Test Mock Builder** (`Test{Interface}Builder`) class instead:

```csharp
// ✅ CORRECT - use Test Mock Builder for ALL interface mocks
var repository = new TestMyRepositoryBuilder(Fixture)
    .AddItem(item1)
    .AddItem(item2)
    .Build();

// ✅ CORRECT - empty mock via static factory
var repository = TestMyRepositoryBuilder.CreateWithoutSetup(Fixture);
```

This rule applies to **every** interface dependency, regardless of complexity — even single-method mocks, one-off setups, or mocks with no configuration at all. If a `Test{Interface}Builder` does not exist yet, **create one first** in `Tests.Common/Helpers/Mocks/{Feature}/`.

**Inside a `Test{Interface}Builder`:** prefer `_fixture.Create<IInterface>()` to obtain the substitute, NOT `Substitute.For<IInterface>()`. AutoFixture's NSubstitute customisation produces an equivalent mock, integrates with the rest of the fixture-driven configuration, and matches the convention used by every other builder in this repo. `Substitute.For<T>` is an escape hatch for the rare case where AutoFixture genuinely cannot produce the substitute (e.g., a sealed concrete or a generic constraint AutoFixture refuses) — when you use it, add a one-line comment explaining why. Do NOT silently swap `_fixture.Create<…>()` to `Substitute.For<T>` as a "fix."

**No post-setup allowed:** Once a mock is returned from a builder (or `Create{Mock}` helper), it is **fully configured**. Never add `.Returns()`, `.ReturnsForAnyArgs()`, or any NSubstitute setup on it in the test case. If a new behavior is needed, extend the builder.

Common builders already available:

- `TestOptionsMonitorBuilder<T>` — for `IOptionsMonitor<T>` / `IOptions<T>`
- `TestLoggerBuilder` — for `ILogger<T>` (static `CreateWithoutSetup<T>(Fixture)`)
- Repository/service builders — see `Tests.Common/Helpers/Mocks/` for full list

**Repository builders** provide stateful mock behavior for testing:

```csharp
var repository = new TestAccountDeploymentResultRepositoryBuilder(Fixture)
    .AddAccountDeploymentResult(result1)
    .Build();
```

See [examples/mock-builders.md](examples/mock-builders.md) for complete patterns.

## Constructor Null-Argument Tests

Every service or hosted service with multiple constructor dependencies MUST have exactly **two** constructor tests:

1. **Positive** — `Constructor_OnAllArgumentsProvided_CreatesInstance`: calls `CreateServiceWithAllArguments()` (all valid deps); asserts `act.Should().NotThrow()`.
2. **Negative** — `Constructor_ThrowsArgumentNullException_WhenNullValueProvided`: single `[Test]`, **`foreach` over `List<Action>`** where each entry passes exactly one dep as `null!`; asserts `act.Should().Throw<ArgumentNullException>()` per iteration.

See [examples/constructor-null-arg-tests.md](examples/constructor-null-arg-tests.md) for a complete worked example.

### Canonical shape

```csharp
#region Constructor Tests

[Test]
public void Constructor_OnAllArgumentsProvided_CreatesInstance()
{
    // Arrange.
    // Act.
    var act = () => CreateServiceWithAllArguments();

    // Assert.
    act.Should().NotThrow();
}

[Test]
public void Constructor_ThrowsArgumentNullException_WhenNullValueProvided()
{
    // Arrange.
    var actions = new List<Action>
    {
        () => CreateServiceWithAllArguments(logger: null!),
        () => CreateServiceWithAllArguments(repository: null!),
        () => CreateServiceWithAllArguments(scopeFactory: null!),
        () => CreateServiceWithAllArguments(optionsMonitor: null!),
    };

    // Act + Assert.
    foreach (var act in actions)
        act.Should().Throw<ArgumentNullException>();
}

#endregion
```

The helper `CreateServiceWithAllArguments` goes at the file end inside `#region Helper Methods`. It accepts each ctor parameter as **nullable with a `?? Create{Mock}()` fallback**:

```csharp
private static MyService CreateServiceWithAllArguments(
    ILogger<MyService>? logger = null,
    IMyRepository? repository = null,
    IServiceScopeFactory? scopeFactory = null,
    IOptionsMonitor<MyOptions>? optionsMonitor = null) =>
    new(
        logger ?? CreateLogger(),
        repository ?? CreateMyRepository(),
        scopeFactory ?? CreateScopeFactory(),
        optionsMonitor ?? CreateOptionsMonitor());
```

**`static` vs instance:** the helper is `private static` when every inner `Create{Mock}` helper is also static. When any inner helper requires `Fixture`, that helper — and therefore `CreateServiceWithAllArguments` — must be `private` (non-static). See the worked example in [examples/constructor-null-arg-tests.md](examples/constructor-null-arg-tests.md) for a mixed case.

### Anti-pattern: boolean stripes (FORBIDDEN)

```csharp
// ❌ BAD CODE — boolean-stripes pattern
[TestCase(true,  false, false, false, TestName = "Constructor_WhenLoggerIsNull_Throws")]
[TestCase(false, true,  false, false, TestName = "Constructor_WhenRepositoryIsNull_Throws")]
[TestCase(false, false, true,  false, TestName = "Constructor_WhenScopeFactoryIsNull_Throws")]
[TestCase(false, false, false, true,  TestName = "Constructor_WhenOptionsMonitorIsNull_Throws")]
public void Constructor_ThrowsArgumentNullException_WhenDependencyIsNull(
    Boolean nullLogger, Boolean nullRepository, Boolean nullScopeFactory, Boolean nullOptionsMonitor)
{
    var act = () => new MyService(
        nullLogger ? null! : CreateLogger(),
        nullRepository ? null! : CreateMyRepository(),
        nullScopeFactory ? null! : CreateScopeFactory(),
        nullOptionsMonitor ? null! : CreateOptionsMonitor());
    act.Should().Throw<ArgumentNullException>();
}
```

**Why it is bad:** every parameter requires its own boolean column; reordering or renaming a ctor parameter forces editing the entire matrix; the method signature carries N booleans that obscure intent. Use the `foreach`-over-`List<Action>` pattern instead — adding or removing a dependency is one line.

## Database Integration Tests

### TestDbContextFactory Options

| Factory                            | Use When                                        |
|------------------------------------|-------------------------------------------------|
| `TestDbContextFactory_AllCases`    | Repository tests that manually create DbContext |
| `TestDbContextFactory_DiSafeCases` | Tests where DbContext comes from DI container   |

```csharp
// Manual DbContext creation (most common)
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]
public sealed class MyRepositoryTests : BaseRepositoryWithOneKeyTest<...>
{
    public MyRepositoryTests(ITestDbContextFactory factory) : base(factory) { }
}

// DI-managed DbContext
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]
public sealed class MyServiceIntegrationTests : BaseDbTest<...>
{
    public MyServiceIntegrationTests(ITestDbContextFactory factory) : base(factory) { }
}
```

## String Validation Pattern

Use `[TestCaseSource]` for null/empty/whitespace validation:

```csharp
[TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]
public void Method_ShouldThrow_WhenStringIsInvalid(String? invalidValue)
{
    // Arrange.
    // ...

    // Act.
    var act = () => _sut.Method(invalidValue!);

    // Assert.
    act.Should().Throw<ArgumentException>();
}
```

## Scenario Tests (WebApi.Tests/Scenarios/)

Scenario tests exercise **real end-to-end orchestration**. They MUST NOT contain any mocking infrastructure:

**Forbidden in scenario tests:**

- `IFixture`, `AutoFixture`, or any `Fixture.*` calls
- `Substitute.For<T>()`
- `Fixture.Create<IInterface>()` or `Fixture.Freeze<IInterface>()`
- Test Mock Builders (`Test{Interface}Builder`)
- Mocks inside stubs internally

**Allowed pattern — stubs and raw data only:**

Stub only the **leaf dependency** that actually requires an external connection. Let all real service implementations run. Name stubs `Stub{DependencyName}`.

```csharp
// ✅ CORRECT — stub only the leaf external dependency
public sealed class StubExternalSecretService : IExternalSecretService
{
    private readonly Dictionary<ResourceId, Credential> _credentials = new();

    public void AddCredential(ResourceId id, Credential credential) =>
        _credentials[id] = credential;

    public Task<Credential?> GetCredentialAsync(ResourceId id, CancellationToken ct) =>
        Task.FromResult(_credentials.GetValueOrDefault(id));
}
```

```csharp
// ❌ FORBIDDEN — mocking internal service in scenario test
var authService = Substitute.For<IAuthenticationService>();
authService.AuthenticateAsync(Arg.Any<ResourceId>(), Arg.Any<CancellationToken>())
    .Returns(new AuthResult(...));
```

**Why:** Mocking internal services hides integration bugs — the mock returns null/default values that mask real failures. The scenario test's value comes from exercising cross-layer orchestration with only the true external boundary stubbed.

See [examples/scenario-tests.md](examples/scenario-tests.md) for a complete worked example.

## Test Scope and Props Files

### Conditional compilation — targeted runs only

When working on anything whose coverage depends on a conditionally-compiled test path (e.g., an integration emulator define constant):

1. Temporarily add the define constant to the Debug `<DefineConstants>` in `Directory.Build.props`.
2. Run **only** targeted tests: `dotnet test --filter "FullyQualifiedName~<name>"` — never run the full suite while the constant is set.
3. **Before the full-suite pass**, remove the constant from Debug constants so the props file is back to its committed form.
4. Run the full suite before declaring work complete. There are no pre-existing failures — every red signal in the session is yours to fix (see `dev-essentials:engineering-discipline` Rule 1).

### Props / config files — never stage automatically

Never stage `Directory.Build.props`, `Directory.Packages.props`, or `global.json` in any commit unless the user has **explicitly named them**. If they appear dirty in `git status`, leave them alone — do not reset, stash, or restore.

## Reference Files

- **examples/** - Complete examples for each test pattern:
  - `domain-model-tests.md` - BaseEqualityMemberTests\<T\> usage
  - `exception-tests.md` - BaseExceptionTests\<T\> usage
  - `wrapper-tests.md` - BaseStringWrapperTests\<T\>, BaseGuidWrapperTests\<T\> usage
  - `repository-tests.md` - Repository integration tests
  - `config-options-tests.md` - BaseValidatableObjectTests usage
  - `config-binding-tests.md` - BaseConfigurationBindingTests\<T\> usage
  - `di-registration-tests.md` - BaseDependencyInjectionTests usage
  - `mock-builders.md` - Test mock builder patterns
  - `generators.md` - Test model generator patterns
  - `controller-tests.md` - WebApiBaseTest usage
  - `migration-tests.md` - Database/product migration testing with production data
  - `constructor-null-arg-tests.md` - foreach-over-List\<Action\> ctor null-arg pattern
  - `scenario-tests.md` - Scenario/integration tests with stubs-only (no mocks)

## Checklist

### All test types

- [ ] **Read the matching example file from examples/ BEFORE writing any code**
- [ ] Test class inherits correct base class
- [ ] `[TestFixture]` and `[Parallelizable(ParallelScope.Fixtures)]` attributes (unless non-parallelizable)
- [ ] All tests use `// Arrange.` `// Act.` `// Assert.` comments
- [ ] Props files (`Directory.Build.props`, `Directory.Packages.props`, `global.json`) NOT staged unless user named them explicitly

### Unit / integration tests (non-scenario)

- [ ] Use test model generators (not inline object creation)
- [ ] **NO** `Substitute.For<T>()`, `Fixture.Freeze<IInterface>()`, or `Fixture.Create<IInterface>()` in test cases — use Test Mock Builders exclusively
- [ ] Inside `Test{Interface}Builder`, use `_fixture.Create<IInterface>()` (NOT `Substitute.For<T>()`) to obtain the substitute
- [ ] Test Mock Builders used for **every** interface mock (create builder if missing)
- [ ] **NO** direct builder/generator calls in test cases — all wrapped in private `Create{Mock}` / `Generate{Model}` helper methods
- [ ] **NO** additional `.Returns()` / NSubstitute setup on mocks after builder returns — extend the builder instead
- [ ] In test classes: NO optional parameters or `params` arrays on `Create*` or `Generate*` helpers — except `CreateServiceWithAllArguments` (the ctor null-arg factory), which MUST use nullable optionals
- [ ] In generator classes: `Create*` required-only; `Generate*` may use nullable optional fallbacks
- [ ] **IMPORTANT:** Before writing any `Create{Mock}` / `Generate{Model}` helper, read the existing test class and assembly — mirror established shapes; do NOT introduce a conflicting second helper
- [ ] Constructor tests use `foreach`-over-`List<Action>` pattern — NO boolean-stripes `[TestCase(true,false,...)]`
- [ ] Constructor tests for validation
- [ ] ToString test for domain models
- [ ] Use `StringNullOrWhiteSpace_TestCases` for string validation
- [ ] Domain models with `IEquatable<T>` + `IEqualityOperators` **MUST** extend `BaseEqualityMemberTests<T>` (override `CreateUniqueValue`, optionally `GetValueMutatorsForInequality`/`GetValueMutatorsForEquality`)
- [ ] Custom exceptions extend `BaseExceptionTests<T>`
- [ ] Primitive wrappers extend `BaseStringWrapperTests<T>`, `BaseGuidWrapperTests<T>`, etc.
- [ ] Config options extend `BaseValidatableObjectTests`
- [ ] Config binding tests extend `BaseConfigurationBindingTests<T>`
- [ ] DI registration tests extend `BaseDependencyInjectionTests`
- [ ] Migrations use `[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]`
- [ ] Migration tests verify empty database, happy path, idempotency, invalid data handling

### Scenario tests (`WebApi.Tests/Scenarios/`)

- [ ] **NO** `IFixture`, `AutoFixture`, or any `Fixture.*` calls
- [ ] **NO** `Substitute.For<T>()` — stubs only (named `Stub{DependencyName}`)
- [ ] **NO** Test Mock Builders (`Test{Interface}Builder`)
- [ ] Data is created via raw constructors **or** generator classes — never via `IFixture`/AutoFixture
- [ ] Stub only the **leaf external dependency**; all real service layers run unmodified
- [ ] Mocks are NOT used inside stubs internally
