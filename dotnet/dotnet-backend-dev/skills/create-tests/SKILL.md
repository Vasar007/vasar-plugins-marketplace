---
name: create-tests
description: Write or change .NET unit and integration tests with the test framework, the assertion library, and the mock builders and generators of the project.
when_to_use: Use it for "create tests", "unit tests", "test this class", or "write tests for".
---

# Create Tests

Create .NET unit and integration tests in `tests/` or `src/Tests/`. The tests use the base classes below and these libraries of the project:

- The test framework (for example, NUnit) runs the tests and gives the test and fixture attributes.
- The assertion library (for example, FluentAssertions) gives the assertions.
- The mocking library (for example, NSubstitute) makes the mocks.
- The test data library (for example, AutoFixture) makes the test data and gives the mocks to the Test Mock Builders through a fixture.

The rules name each library by its role. The code examples here and in [examples/](examples/) use NUnit, FluentAssertions, and NSubstitute through AutoFixture. With another library, use its equivalent attributes and calls.

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

| Base class | Use for | Type |
| --- | --- | --- |
| `BaseTest` | Basic tests without mocks | Unit |
| `BaseMockTest` | Tests that need mocks through the test data library | Unit |
| `BaseEqualityMemberTests<T>` | Domain models with `IEquatable<T>` and `IEqualityOperators` | Unit |
| `BaseExceptionTests<T>` | Custom exception classes | Unit |
| `BaseValidatableObjectTests` | Validation of configuration options | Unit |
| `BaseConfigurationBindingTests<T>` | Configuration binding from JSON and environment variables | Unit |
| `BaseDependencyInjectionTests` | DI registration | Unit |
| `BaseStringWrapperTests<T>` | String-based primitive wrappers | Unit |
| `BaseGuidWrapperTests<T>` | GUID-based primitive wrappers | Unit |
| `BaseInt32WrapperTests<T>` | Integer-based primitive wrappers | Unit |
| `BaseRepositoryWithOneKeyTest` | CRUD of a repository with one key | Integration |
| `BaseRepositoryWithTwoKeysTest` | CRUD of a repository with a composite key | Integration |
| `WebApiBaseTest` | Controller and API endpoints | Integration |
| `BaseMockTest` | Database and product migrations (see [migration-tests.md](examples/migration-tests.md)) | Integration |

**MANDATORY:** Before you write ANY test class, you **MUST read the matching example file** in [examples/](examples/). Read the example first, then write the test.

| What you test | Read this example first |
| --- | --- |
| Domain model with `IEquatable<T>` | [domain-model-tests.md](examples/domain-model-tests.md) |
| Custom exception | [exception-tests.md](examples/exception-tests.md) |
| Primitive wrapper (string, GUID, or integer ID) | [wrapper-tests.md](examples/wrapper-tests.md) |
| Repository CRUD | [repository-tests.md](examples/repository-tests.md) |
| Validation of configuration options | [config-options-tests.md](examples/config-options-tests.md) |
| Configuration binding from JSON or environment variables | [config-binding-tests.md](examples/config-binding-tests.md) |
| DI registration | [di-registration-tests.md](examples/di-registration-tests.md) |
| Service with mocked dependencies | [mock-builders.md](examples/mock-builders.md) and [generators.md](examples/generators.md) |
| Controller or API endpoint | [controller-tests.md](examples/controller-tests.md) |
| Database or product migration | [migration-tests.md](examples/migration-tests.md) |
| Constructor null-argument tests | [constructor-null-arg-tests.md](examples/constructor-null-arg-tests.md) |
| Method null-argument tests, async lambdas, SUT names, helper order, argument matchers (for example, NSubstitute `Arg.Any<T>()`) or `default`, `ThrowIfNull()`, block bodies | [enforced-gates.md](examples/enforced-gates.md) |
| Scenario or end-to-end integration test | [scenario-tests.md](examples/scenario-tests.md) |

The seven gates of [enforced-gates.md](examples/enforced-gates.md) apply to every test class, together with the matching example. Two exceptions apply. If the mocking library is not NSubstitute, Gate 5 does not apply. Gate 1 applies only to a test class that calls the methods of the SUT directly. It never applies to controller tests through the HTTP client or to scenario tests. See "Enforced gates" in the checklist below.

If no example matches your case, look for a similar test class in the test projects of the repository. They are usually under `tests/`, `src/Tests/`, `Sources/Tests/`, or `Tests/`. Follow the pattern of that class. Never guess the API of a base class. Read it first.

## Test Scope and Props Files

### Conditional compilation — targeted runs only

Some test paths compile only under a define constant, for example the constant for an integration emulator. If the coverage of your work depends on such a path, do these steps:

1. Add the define constant to the Debug `<DefineConstants>` in `Directory.Build.props` for the time of the work.
2. Run **only** targeted tests: `dotnet test --filter "FullyQualifiedName~<name>"`. Never run the full suite while the constant is set.
3. **Before the full-suite run**, remove the constant from the Debug constants. The props file then has its committed content again.
4. Run the full suite before you report the work as complete. No failure counts as pre-existing: you must fix each red signal in the session (see `dev-essentials:engineering-discipline` Rule 1).

### Props / config files — never stage automatically

Never stage `Directory.Build.props`, `Directory.Packages.props`, or `global.json` in a commit, unless the user **explicitly named them**. If they show as changed in `git status`, leave them alone. Do not reset, stash, or restore them.

## Required Conventions

### General Rules

- **Use the assertion library** (for example, FluentAssertions `Should()`) instead of the assertions of the test framework (for example, NUnit `Assert.*`). Use the assertions of the test framework only for an assertion that the assertion library does not have.
- **Use System type names** instead of C# aliases: `String` not `string`, `Int32` not `int`, `Boolean` not `bool`, and so on.
- **Use `var` for delegates** in tests that assert that a call throws or does not throw (for example, FluentAssertions `Throw` or `NotThrow`). Example: `var act = () => service.DoSomething();`.
- **Reuse values.** Compare against the expected variable, not a repeated literal:

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

- If the test class already has private `Create{Mock}` or `Generate{Model}` methods, **use them**. Do not create new ones, and do not call builders or generators directly.

### Test Structure

ALL tests MUST use the comments `// Arrange.`, `// Act.`, and `// Assert.`. Each comment has a **dot at the end**, and a **blank line follows each section**:

```csharp
[Test]
public void MethodName_Condition_ExpectedResult()
{
    // Arrange.
    var input = CreateTestInput();
    var service = CreateService();

    // Act.
    var result = service.DoSomething(input);

    // Assert.
    result.Should().NotBeNull();
}
```

If one statement does the work of two or three sections, use one combined comment. Join the section names with `&`, and keep the dot at the end: `// Act & Assert.` or `// Arrange, Act & Assert.`. `// Arrange & Act.` is also allowed, for a statement that builds the SUT and is the action under test. Never use `+` or another separator.

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

**ALWAYS use test model generators** to create test data:

- Generators are singletons: `{Model}Generator.Instance`.
- They are in `Tests.Common/Helpers/Generators/` or `{ProjectName}.Tests.Common/Helpers/Generators/`.
- They have `Create{Model}()` methods (explicit parameters) and `Generate{Model}()` methods (random values).
- **NEVER call generators directly in test cases.** Wrap each call in a private `Generate{Model}(...)` helper method (see [Private Helper Methods](#private-helper-methods-mandatory-indirection)).
- See [examples/generators.md](examples/generators.md) for patterns.

### Parallelization

**Run most test fixtures in parallel** (for example, with `[Parallelizable(ParallelScope.Fixtures)]` in NUnit).

**Turn off parallel runs** (for example, with `[NonParallelizable]` in NUnit) in these cases:

- The test changes shared database state that conflicts with parallel tests.
- The test needs exclusive access to an external resource, for example a local database emulator.

```csharp
[Test]
[NonParallelizable]
public async Task AddAsync_OnSeveralEntitiesWithSameCompositeAlternateKeys_ShouldThrow()
{
    // Test that requires exclusive DB access
}
```

### Private Helper Methods (Mandatory Indirection)

**Test cases MUST NOT call Test Mock Builders or Test Data Generators directly.** Wrap all builder and generator calls in **private helper methods**. Each helper is the single configuration point for one mock or one data object.

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
    var repository = CreateMyRepository(new[] { item1, item2 });
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
    var repository = CreateMyRepository(new[] { item1, item2 });
    // repository is fully configured — no additional .Returns/.ReturnsForAnyArgs here
    // ...
}

private Item GenerateItem(String name)
{
    return _itemGenerator.GenerateItem(name: name);
}

private IMyRepository CreateMyRepository(Item[] items)
{
    return new TestMyRepositoryBuilder(Fixture)
        .AddItemRange(items) // use bulk Add*Range methods — no foreach/if-else in helpers
        .Build(); // ALL method setups live inside TestMyRepositoryBuilder
}
```

**Rules for private helper methods:**

1. **Exactly one `Create{Mock}` method for each mock dependency**, with no overloads. The one method wraps the builder and takes parameters for the items and the configuration that the mock needs. All test cases in the class share it.
2. **Exactly one `Generate{Model}` method for each test data type in the test class**, with no overloads. The one method wraps the generator call.
3. **No post-setup on returned mocks.** After `Create{Mock}` returns, the mock is **fully configured**. Never add a setup of the mocking library on the result in the test case. Examples are `.Returns()`, `.ReturnsForAnyArgs()`, and any other NSubstitute setup. If you need a new behavior, **extend the Test Mock Builder** with a new method or option. Then expose it through the parameters of the `Create{Mock}` helper. One exception: `ExternalServicesMock` of `WebApiBaseTest` in Web API tests. The base test injects this mock into the ASP.NET pipeline, where it intercepts the calls of the running app to external services. So a test case can set up its behavior after the setup, as `examples/controller-tests.md` shows.
4. **The single `Create{Mock}` helper takes optional parameters and applies them with `.ApplyIf`**. Rule 1 ("exactly one helper for each dependency, no overloads") does NOT mean that the helper has no optional parameters. The single helper takes an **optional nullable parameter** (`Foo? p = null`) for each setting that a test case needs. It applies each one with an `.ApplyIf(condition, b => b.WithFoo(p!))` call in the fluent chain of the builder. **Never** use an `if` block with a separate `builder` variable. **Never** use a bare `??` fallback inside a `.With(...)` call. Two test cases that need different `Create{Mock}` inputs call the **same single** method with different named-argument values. A test class never has a second `CreateMyRepository` for the same dependency. `Generate{Model}` helpers follow the looser `Generate*` column in the table below: plain optional parameters with defaults are allowed, and `.ApplyIf` is not required.

   | Location | `Create*` | `Generate*` |
   | --- | --- | --- |
   | Test class | `Create{Mock}` (a helper that wraps a Test Mock Builder): optional nullable parameters, applied with `.ApplyIf(...)` (except `CreateServiceWithAllArguments`) | Optional parameters with defaults are allowed |
   | Generator class | Required parameters only | Optional parameters are allowed (nullable fallback) |

   ```csharp
   // ✅ CORRECT - one helper, optional params, .ApplyIf chain
   private IMyRepository CreateMyRepository(Item[]? items = null, Exception? failureException = null)
   {
       return new TestMyRepositoryBuilder(Fixture)
           .ApplyIf(items is not null, b => b.AddItemRange(items!))
           .ApplyIf(failureException is not null, b => b.WithFailure(failureException!))
           .Build();
   }

   // ❌ WRONG - if-block with a separately-declared builder variable
   private IMyRepository CreateMyRepository(Item[]? items = null)
   {
       var builder = new TestMyRepositoryBuilder(Fixture);
       if (items is not null)
           builder.AddItemRange(items);
       return builder.Build();
   }

   // ❌ WRONG - ?? fallback inside .With(...)/.AddItemRange(...)
   private IMyRepository CreateMyRepository(Item[]? items = null)
   {
       return new TestMyRepositoryBuilder(Fixture)
           .AddItemRange(items ?? Array.Empty<Item>())
           .Build();
   }
   ```

   **Exception: `CreateServiceWithAllArguments` (or `Create{Sut}WithAllArguments`).** This SUT-factory helper is only for the constructor null-argument tests. It is the ONE helper in a test class that stays **required and positional: no optional parameters and no `??` fallback of any kind**. Each negative-test lambda must pass `null!` for the argument under test. An optional parameter with a `??` fallback replaces that `null!` with a valid mock, and the test then proves nothing (see [Constructor Null-Argument Tests](#constructor-null-argument-tests)). This exception applies to **exactly one helper in each test class**. Every other `Create{Mock}` and `Generate*` helper in the class follows rule 4. A test-class helper that wraps a generator `Create{Model}` method can take required parameters, like the generator method.

   In generator classes (`xxxGenerator.cs` under `Tests.Common/Helpers/Generators/...`), `Create*` takes required parameters only. `Generate*` can take nullable optional parameters with `null` defaults, which mean "fill with random values".

   **Escape hatch.** Get explicit approval from the user before you add a second `Create{Mock}` or `Generate{Model}` variant for the same dependency under a different name. A justification after the fact is not allowed.

5. **Follow the existing test class and assembly first. IMPORTANT:**
   Before you write any `Create{Mock}` or `Generate{Model}` helper, **read the existing test class**. Also read the nearby test classes of the same fixture and the shared helpers of the same test assembly. Copy the shapes that they use. Do NOT add a new `Create*` or `Generate*` pattern that conflicts with neighboring tests in the same fixture or assembly. Example: `CreateMyRepository` already exists and takes `Item[]`. Then your new test uses that signature with different `Item[]` values and does not add a second helper. If the existing shape is wrong (for example, it already has two `Create*` overloads), tell the user. Do not add a third overload.

6. **Use bulk `Add*Range` methods for collection items.** Use `AddItemRange(items)`, not a `foreach` loop of single `.AddItem()` calls. This rule is separate from rule 4. `Add*Range` adds a collection of items in one call. `.ApplyIf(...)` (rule 4) applies *one optional setting*. If a helper has both, use both. Do not use the `params` keyword in a helper.

7. **Reusable assertion helpers** for repeated assert blocks:

```csharp
private void AssertModelEquals(MyModel expected, MyModel actual)
{
    actual.Id.Should().Be(expected.Id);
    actual.Name.Should().Be(expected.Name);
}
```

## Mocking Rules

### STRICT PROHIBITION: No Direct Mock Creation

**NEVER** create mocks of interfaces directly in test fixtures or test cases. The code below shows the direct calls of NSubstitute and AutoFixture. **ALL** of these are **FORBIDDEN**, and so are the equivalent calls of another mocking library or test data library:

```csharp
// ❌ FORBIDDEN - Substitute.For
var mock = Substitute.For<IService>();

// ❌ FORBIDDEN - Fixture.Freeze on interfaces
var repository = Fixture.Freeze<IMyRepository>();

// ❌ FORBIDDEN - Fixture.Create on interfaces
var mock = Fixture.Create<IMyService>();
```

**ALWAYS use a Test Mock Builder** (a `Test{Interface}Builder` class) instead:

```csharp
// ✅ CORRECT - use Test Mock Builder for ALL interface mocks
var repository = new TestMyRepositoryBuilder(Fixture)
    .AddItem(item1)
    .AddItem(item2)
    .Build();

// ✅ CORRECT - empty mock via static factory
var repository = TestMyRepositoryBuilder.CreateWithoutSetup(Fixture);
```

This rule applies to **every** interface dependency, also to a mock with one method, a one-time setup, or no configuration at all. If a `Test{Interface}Builder` does not exist yet, **create it first** in `Tests.Common/Helpers/Mocks/{Feature}/`.

**Inside a `Test{Interface}Builder`:** this rule is for NSubstitute through AutoFixture. Get the substitute with `_fixture.Create<IInterface>()`, NOT with `Substitute.For<IInterface>()`. The NSubstitute customization of AutoFixture makes an equivalent mock, works with the rest of the fixture configuration, and matches the other builders of the repository. With another mocking library or test data library, get the mock the way that the other builders of the repository do. Use `Substitute.For<T>` only in the rare case where AutoFixture cannot make the substitute. Examples are a sealed concrete type or a generic constraint that AutoFixture refuses. Then add a one-line comment that says why. Do NOT silently change `_fixture.Create<…>()` to `Substitute.For<T>` as a "fix".

**No post-setup:** a mock that a builder or a `Create{Mock}` helper returns is **fully configured** (rule 3 above).

Builders that already exist:

- `TestOptionsMonitorBuilder<T>` for `IOptionsMonitor<T>` and `IOptions<T>`
- `TestLoggerBuilder` for `ILogger<T>` (static `CreateWithoutSetup<T>(Fixture)`)
- Repository and service builders: see `Tests.Common/Helpers/Mocks/` for the full list

**Repository builders** give the mock a state: it keeps the items that the test adds, updates, and deletes. See [examples/mock-builders.md](examples/mock-builders.md) for complete patterns.

## Constructor Null-Argument Tests

Each service or hosted service with one or more constructor dependencies MUST have exactly **two** constructor tests. With one dependency, the `actions` list has one entry:

1. **Positive:** `Constructor_OnAllArgumentsProvided_CreatesInstance` calls `CreateServiceWithAllArguments(...)` with a valid value for each dependency. It asserts that the call does not throw (for example, `act.Should().NotThrow()`).
2. **Negative:** `Constructor_ThrowsArgumentNullException_WhenNullValueProvided` is a single test method with a **`foreach` over a `List<Action>`**. Each entry calls `CreateServiceWithAllArguments(...)` with valid positional arguments, except exactly one dependency that gets `null!`. In each iteration, the test asserts that the call throws `ArgumentNullException` (for example, `act.Should().Throw<ArgumentNullException>()`).

`CreateServiceWithAllArguments` goes at the end of the file, inside `#region Helper Methods`. Each constructor parameter is **required and positional: no `= null` default and no `??` fallback**. The boolean-stripes pattern (parameterized test cases with one boolean for each dependency, for example `[TestCase(true, false, ...)]` in NUnit) is FORBIDDEN.

Read [examples/constructor-null-arg-tests.md](examples/constructor-null-arg-tests.md) before you write these tests. It has the canonical example, the reason for required positional parameters, the rule for `static` and instance helpers, and the forbidden boolean-stripes pattern.

## Database Integration Tests

| Factory | Use it in |
| --- | --- |
| `TestDbContextFactory_AllCases` | Repository tests that create the `DbContext` themselves (most common) |
| `TestDbContextFactory_DiSafeCases` | Tests that get the `DbContext` from the DI container, for example migration tests |

See [examples/repository-tests.md](examples/repository-tests.md) for the fixture attributes and the class shapes.

## String Validation Pattern

Use the `StringNullOrWhiteSpace_TestCases` test-case source for null, empty, and whitespace validation of a `String` parameter (for example, `[TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]` in NUnit). The test takes a `String? invalidValue` parameter and asserts that the call throws `ArgumentException` (for example, `Throw<ArgumentException>()`).

## Scenario Tests (WebApi.Tests/Scenarios/)

Scenario tests run **real end-to-end orchestration**. They MUST NOT contain any mocking infrastructure.

**Forbidden in scenario tests:**

- The test data library (for example, `IFixture`, `AutoFixture`, or any `Fixture.*` call)
- Any mock of the mocking library (for example, `Substitute.For<T>()`)
- An interface mock from the test data library (for example, `Fixture.Create<IInterface>()` or `Fixture.Freeze<IInterface>()`)
- Test Mock Builders (`Test{Interface}Builder`)
- Mocks inside stubs

**Allowed: stubs and raw data only.** Stub only the **leaf dependency** that needs an external connection. All real service implementations run. Name a stub `Stub{DependencyName}`.

See [examples/scenario-tests.md](examples/scenario-tests.md) for a complete example of a stub and a scenario test.

## Checklist

### All test types

- [ ] **Read the matching example file in examples/ BEFORE you write any code**
- [ ] The test class inherits the correct base class
- [ ] The fixture attributes of the test framework (for example, `[TestFixture]` and `[Parallelizable(ParallelScope.Fixtures)]` in NUnit), unless the fixture is non-parallelizable
- [ ] All tests use the `// Arrange.` `// Act.` `// Assert.` comments, or a combined form with `&`, such as `// Act & Assert.` or `// Arrange, Act & Assert.` (see "Test Structure")
- [ ] Props files (`Directory.Build.props`, `Directory.Packages.props`, `global.json`) are NOT staged, unless the user named them explicitly

### Enforced gates (details in [enforced-gates.md](examples/enforced-gates.md))

- [ ] Gate 1 (only for a test class that calls the methods of the SUT directly, never for controller tests through the HTTP client or for scenario tests): each public method with a required reference parameter has ONE `foreach` null-argument test. A required `String` parameter gets its own `StringNullOrWhiteSpace_TestCases` test instead.
- [ ] Gate 2: no `async () => await x` around a single expression
- [ ] Gate 3: the SUT variable and its helper use the role noun of the class (`processor`, `CreateProcessor`), never `sut`
- [ ] Gate 4: helper methods come last, in one `#region Helper Methods`
- [ ] Gate 5 (if the mocking library is NSubstitute): `Arg.Any<T>()` for arguments, and `default` only for a record struct that throws `AmbiguousArgumentsException`
- [ ] Gate 6: `obj.ThrowIfNull()`, not `ArgumentNullException.ThrowIfNull(obj)`
- [ ] Gate 7: block bodies for methods, no expression-bodied methods

### Unit / integration tests (non-scenario)

- [ ] Test data comes from test model generators, not inline object creation
- [ ] Every interface mock comes from a Test Mock Builder. No direct mock of the mocking library or the test data library in test cases (for example, `Substitute.For<T>()`, `Fixture.Freeze<IInterface>()`, or `Fixture.Create<IInterface>()`). With NSubstitute through AutoFixture, a builder gets its substitute with `_fixture.Create<IInterface>()`.
- [ ] Test cases call builders and generators only through private `Create{Mock}` and `Generate{Model}` helpers, and add no setup to a returned mock
- [ ] The helpers follow rules 1 to 7 of [Private Helper Methods](#private-helper-methods-mandatory-indirection), with `CreateServiceWithAllArguments` as the one required-positional exception
- [ ] Constructor tests use the `foreach` over `List<Action>` pattern, with NO boolean-stripes test cases (for example, `[TestCase(true,false,...)]` in NUnit)
- [ ] Constructor tests for validation
- [ ] `ToString` test for domain models
- [ ] `StringNullOrWhiteSpace_TestCases` for string validation
- [ ] The test class extends the base class of its kind from [Base Classes Overview](#base-classes-overview). Domain models with `IEquatable<T>` and `IEqualityOperators` **MUST** extend `BaseEqualityMemberTests<T>` (override `CreateUniqueValue`, and optionally `GetValueMutatorsForInequality` or `GetValueMutatorsForEquality`).
- [ ] Migration tests run for each test database provider through the `TestDbContextFactory_DiSafeCases` fixture source (for example, `[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]` in NUnit)
- [ ] Migration tests cover an empty database, the happy path, idempotency, and invalid data

### Scenario tests (`WebApi.Tests/Scenarios/`)

- [ ] The test follows every rule of [Scenario Tests](#scenario-tests-webapitestsscenarios): no test data library (`Fixture.*`), no mocking library (`Substitute.For<T>()`), no Test Mock Builders, and no mocks inside stubs
- [ ] Data comes from raw constructors **or** generator classes, never from the test data library (for example, `IFixture` or AutoFixture)
