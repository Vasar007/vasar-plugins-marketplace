# Constructor Null-Argument Tests

For any service or hosted service with multiple constructor dependencies, null-argument coverage
uses exactly **two** tests: one positive, one negative. The negative test iterates over a
`List<Action>` — one entry per dependency — rather than using boolean-stripe `[TestCase]` parameters.

## Pattern overview

- **Test 1 (positive):** `Constructor_OnAllArgumentsProvided_CreatesInstance` — calls the SUT
  factory helper with an all-valid `Create{Mock}()` positional argument per dependency; asserts
  `act.Should().NotThrow()`.
- **Test 2 (negative):** `Constructor_ThrowsArgumentNullException_WhenNullValueProvided` — builds a
  `List<Action>` where each lambda calls the SUT factory helper with all-valid positional
  `Create{Mock}()` arguments EXCEPT exactly one dependency passed as `null!`; iterates with
  `foreach` and asserts `act.Should().Throw<ArgumentNullException>()` per entry.
- A private helper `CreateServiceWithAllArguments` (or `Create{Sut}WithAllArguments`) lives
  at the file end inside `#region Helper Methods`. Use `private static` when all nested `Create*`
  helpers are static; drop `static` (instance method) when any nested helper needs `Fixture` from
  `BaseMockTest` — `CreateServiceWithAllArguments` must match its callees' static-ness. Every ctor
  parameter is **required and positional — no `= null` default, no `??` fallback of any kind**.
  This is the ONE helper in the test class that stays required-positional; every other
  `Create{Mock}` helper takes optional params applied via `.ApplyIf(...)` (see
  [SKILL.md](../SKILL.md) rule 4).
- The **boolean-stripes `[TestCase(true,false,...)]` pattern is banned** — see Anti-pattern section.

## Why the helper must be required-positional, not `dep ?? Create{Mock}()`

An earlier, now-removed version of this pattern declared the helper's parameters as nullable
optionals with an internal fallback:

```csharp
// ❌ BUGGY — DO NOT COPY. Every negative test built on this shape is a silent no-op.
private static OrderProcessingService CreateServiceWithAllArguments(
    ILogger<OrderProcessingService>? logger = null,
    IOrderRepository? repository = null) =>
    new(
        logger ?? CreateLogger(),
        repository ?? CreateRepository());
```

`??` returns its right-hand side whenever the left-hand side is `null`. Calling
`CreateServiceWithAllArguments(logger: null!)` under this shape does **not** pass `null` to the
constructor — `logger ?? CreateLogger()` evaluates to `CreateLogger()`, a fully valid mock, and
the constructor never sees `null`. Every `Constructor_ThrowsArgumentNullException_...` test built
this way passes, but for the wrong reason: the `ArgumentNullException` guard is never exercised at
all. This was discovered empirically (build-and-run passed; the negative assertions were no-ops)
and confirmed independently in a second repository with the identical bug and fix.

**The fix:** make every parameter required and positional. There is no default to fall back to,
so the only way to satisfy the compiler is to pass either a real, valid mock or `null!` — and
`null!` now actually reaches the constructor.

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
        // Arrange.
        // Act.
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

        // Act + Assert.
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

    // static: TestLoggerBuilder.CreateWithoutSetup<T> accepts a fixture parameter that it ignores
    // for no-setup loggers, so this helper needs no Fixture access.
    private static ILogger<OrderProcessingService> CreateLogger()
    {
        return TestLoggerBuilder.CreateWithoutSetup<OrderProcessingService>(null!);
    }

    // non-static: these helpers need Fixture (from BaseMockTest) to construct their builders.
    // CreateServiceWithAllArguments is therefore also non-static (it calls these instance helpers).
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

- Every entry in the `actions` list calls the SAME required-positional `Create{Mock}()` helpers,
  swapping `null!` into exactly one positional slot — adding a new dependency is one line.
- Because the list is built from lambdas, each `Create{Mock}()` call is deferred until that
  specific action runs; there is no shared "all valid" instance that a null substitution could
  hide behind.
- The `#region Constructor Tests` block sits at the top of the class, before feature-specific
  regions.
- `CreateServiceWithAllArguments` is the ONE helper in the file that is required-positional. Every
  other `Create{Mock}` helper here (`CreateRepository`, `CreateOrderService`, …) follows the
  normal "one helper, optional params, `.ApplyIf(...)`" convention when a test case needs to vary
  its configuration — see [SKILL.md](../SKILL.md) rule 4.

## Anti-pattern: boolean stripes

The following shape is **explicitly bad code** in this pattern — avoid it:

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

- Every dependency requires its own boolean column in the parameter list.
- Reordering, renaming, or adding a ctor parameter forces editing the entire `[TestCase]` matrix.
- The method signature carries N booleans that obscure intent — the reader must mentally map each
  boolean position back to the parameter it controls.
- NUnit names the test cases by position unless explicit `TestName` is provided — one typo and the
  test name lies.

**Replace with the `foreach`-over-`List<Action>` pattern shown in the Canonical example above.**
Adding a new dependency is a single line in the `actions` list; removing one is a single deletion.

## Related gate: the same pattern applies to methods, not just constructors

Public methods with required reference-type parameters get the same treatment — one combined
`<Method>_ShouldThrowArgumentNullException_ForEachRequiredArgument` test per method. See
[enforced-gates.md](enforced-gates.md) gate 1.
