# Constructor Null-Argument Tests

For a service or hosted service with one or more constructor dependencies, null-argument coverage uses exactly **two** tests: one positive and one negative. With one dependency, the `List<Action>` has one entry. The negative test iterates over a `List<Action>` with one entry for each dependency. It does not use boolean-stripe test cases (for example, `[TestCase]` parameters in NUnit).

The code examples in this file use NUnit, FluentAssertions, and AutoFixture. With another test framework, assertion library, or test data library, use its equivalent attributes and calls.

## Pattern overview

- **Test 1 (positive):** `Constructor_OnAllArgumentsProvided_CreatesInstance` calls the SUT factory helper with a valid `Create{Mock}()` positional argument for each dependency. It asserts `act.Should().NotThrow()`.
- **Test 2 (negative):** `Constructor_ThrowsArgumentNullException_WhenNullValueProvided` builds a `List<Action>`. Each lambda calls the SUT factory helper with valid positional `Create{Mock}()` arguments, EXCEPT exactly one dependency that gets `null!`. The test iterates with `foreach` and asserts `act.Should().Throw<ArgumentNullException>()` for each entry.
- A private helper `CreateServiceWithAllArguments` (or `Create{Sut}WithAllArguments`) goes at the end of the file, inside `#region Helper Methods`. If all nested `Create*` helpers are static, make it `private static`. If any nested helper needs `Fixture` from `BaseMockTest`, make it an instance method. `CreateServiceWithAllArguments` must match the `static` choice of its callees. Each constructor parameter is **required and positional: no `= null` default and no `??` fallback of any kind**. This is the ONE helper in the test class that stays required and positional. Every other `Create{Mock}` helper takes optional parameters and applies them with `.ApplyIf(...)` (see [SKILL.md](../SKILL.md) rule 4).
- The **boolean-stripes pattern is banned**: parameterized test cases with one boolean for each dependency (for example, `[TestCase(true,false,...)]` in NUnit). See the anti-pattern section below.

## Why the helper must be required-positional, not `dep ?? Create{Mock}()`

A tempting but wrong shape declares the parameters of the helper as nullable optionals with an internal fallback:

```csharp
// ❌ BUGGY — DO NOT COPY. Every negative test built on this shape is a silent no-op.
private static OrderProcessingService CreateServiceWithAllArguments(
    ILogger<OrderProcessingService>? logger = null,
    IOrderRepository? repository = null) =>
    new(
        logger ?? CreateLogger(),
        repository ?? CreateRepository());
```

`??` returns its right-hand side whenever the left-hand side is `null`. So `CreateServiceWithAllArguments(logger: null!)` with this shape does **not** pass `null` to the constructor. `logger ?? CreateLogger()` gives `CreateLogger()`, a fully valid mock, and the constructor never gets `null`. Each `Constructor_ThrowsArgumentNullException_...` test with this shape passes for the wrong reason: the `ArgumentNullException` guard never runs.

**The fix:** make every parameter required and positional. There is no default to fall back to. The only way to satisfy the compiler is to pass a real, valid mock or `null!`, and `null!` then reaches the constructor.

## Canonical example

The following example tests `OrderProcessingService` which has five constructor dependencies.

```csharp
// Copyright (c) Vasily Vasilyev

using FluentAssertions;
using NUnit.Framework;
using MyApp.Application.Orders.Services;

namespace MyApp.Application.Tests.Orders.Services;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class OrderProcessingServiceTests : BaseMockTest
{
    #region Constructor Tests

    [Test]
    public void Constructor_OnAllArgumentsProvided_CreatesInstance()
    {
        // Arrange & Act.
        var act = () => CreateServiceWithAllArguments(
            CreateLogger(), CreateRepository(), CreateOrderService(),
            CreateEventPublisher(), CreateOptionsMonitor());

        // Assert.
        act.Should().NotThrow();
    }

    [Test]
    public void Constructor_ThrowsArgumentNullException_WhenNullValueProvided()
    {
        // Arrange.
        var actions = new List<Action>
        {
            () => CreateServiceWithAllArguments(
                null!, CreateRepository(), CreateOrderService(),
                CreateEventPublisher(), CreateOptionsMonitor()),
            () => CreateServiceWithAllArguments(
                CreateLogger(), null!, CreateOrderService(),
                CreateEventPublisher(), CreateOptionsMonitor()),
            () => CreateServiceWithAllArguments(
                CreateLogger(), CreateRepository(), null!,
                CreateEventPublisher(), CreateOptionsMonitor()),
            () => CreateServiceWithAllArguments(
                CreateLogger(), CreateRepository(), CreateOrderService(),
                null!, CreateOptionsMonitor()),
            () => CreateServiceWithAllArguments(
                CreateLogger(), CreateRepository(), CreateOrderService(),
                CreateEventPublisher(), null!),
        };

        // Act & Assert.
        foreach (var act in actions)
            act.Should().Throw<ArgumentNullException>();
    }

    #endregion

    // ... other test regions ...

    #region Helper Methods

    private OrderProcessingService CreateServiceWithAllArguments(
        ILogger<OrderProcessingService> logger,
        IOrderRepository repository,
        IOrderService orderService,
        IEventPublisher eventPublisher,
        IOptionsMonitor<OrderProcessingOptions> optionsMonitor)
    {
        return new(logger, repository, orderService, eventPublisher, optionsMonitor);
    }

    // non-static: these helpers need Fixture (from BaseMockTest) to construct their builders.
    // CreateServiceWithAllArguments is therefore also non-static (it calls these instance helpers).
    private ILogger<OrderProcessingService> CreateLogger()
    {
        return TestLoggerBuilder.CreateWithoutSetup<OrderProcessingService>(Fixture);
    }

    private IOrderRepository CreateRepository()
    {
        return TestOrderRepositoryBuilder.CreateWithoutSetup(Fixture);
    }

    private IOrderService CreateOrderService()
    {
        return new TestOrderServiceBuilder(Fixture).Build();
    }

    private IEventPublisher CreateEventPublisher()
    {
        return new TestEventPublisherBuilder(Fixture).Build();
    }

    private IOptionsMonitor<OrderProcessingOptions> CreateOptionsMonitor()
    {
        return new TestOptionsMonitorBuilder<OrderProcessingOptions>(Fixture)
            .WithValue(new OrderProcessingOptions())
            .Build();
    }

    #endregion
}
```

### Key details

- Each entry in the `actions` list calls `CreateServiceWithAllArguments` with the SAME `Create{Mock}()` helpers and puts `null!` into exactly one positional slot. A new dependency adds one line.
- The list holds lambdas, so each `Create{Mock}()` call is deferred to the run of its action. No shared valid instance exists that can hide a null substitution.
- The `#region Constructor Tests` block is at the top of the class, before the regions for features.
- `CreateServiceWithAllArguments` is the ONE required-positional helper in the file. The other `Create{Mock}` helpers here (`CreateRepository`, `CreateOrderService`, and the others) follow the normal convention. If a test case needs another configuration of a mock, the helper takes optional parameters and applies them with `.ApplyIf(...)`. See [SKILL.md](../SKILL.md) rule 4.

## Anti-pattern: boolean stripes

This shape is **explicitly bad code** for this pattern. Do not use it:

```csharp
// ❌ BAD CODE — boolean-stripes pattern
[Test]
[TestCase(true,  false, false, false, false, TestName = "Constructor_WhenLoggerIsNull_Throws")]
[TestCase(false, true,  false, false, false, TestName = "Constructor_WhenRepositoryIsNull_Throws")]
[TestCase(false, false, true,  false, false, TestName = "Constructor_WhenOrderServiceIsNull_Throws")]
[TestCase(false, false, false, true,  false, TestName = "Constructor_WhenEventPublisherIsNull_Throws")]
[TestCase(false, false, false, false, true,  TestName = "Constructor_WhenOptionsMonitorIsNull_Throws")]
public void Constructor_ThrowsArgumentNullException_WhenDependencyIsNull(
    Boolean nullLogger,
    Boolean nullRepository,
    Boolean nullOrderService,
    Boolean nullEventPublisher,
    Boolean nullOptionsMonitor)
{
    var act = () => new OrderProcessingService(
        nullLogger ? null! : CreateLogger(),
        nullRepository ? null! : CreateRepository(),
        nullOrderService ? null! : CreateOrderService(),
        nullEventPublisher ? null! : CreateEventPublisher(),
        nullOptionsMonitor ? null! : CreateOptionsMonitor());
    act.Should().Throw<ArgumentNullException>();
}
```

**Why it is bad:**

- Each dependency needs its own boolean column in the parameter list.
- A reorder, a rename, or a new constructor parameter forces an edit of the whole matrix of test cases. In NUnit, this matrix is the list of `[TestCase]` attributes.
- The method signature carries N booleans that hide the intent. The reader must map each boolean position back to the parameter that it controls.
- The test framework can name the test cases by position. For example, NUnit does so unless a case has an explicit `TestName`. One typo, and the test name is wrong.

**Replace it with the `foreach` over `List<Action>` pattern of the canonical example above**. A new dependency is one line in the `actions` list, and a removed one is one deleted line.

## Related gate: the same pattern applies to methods, not just constructors

Public methods with required reference-type parameters get the same treatment: one combined `<Method>_ShouldThrowArgumentNullException_ForEachRequiredArgument` test for each method. See [enforced-gates.md](enforced-gates.md) gate 1 for the rule and its scope.
