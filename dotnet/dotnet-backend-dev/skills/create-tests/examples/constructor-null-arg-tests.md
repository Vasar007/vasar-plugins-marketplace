# Constructor Null-Argument Tests

For any service or hosted service with multiple constructor dependencies, null-argument coverage
uses exactly **two** tests: one positive, one negative. The negative test iterates over a
`List<Action>` — one entry per dependency — rather than using boolean-stripe `[TestCase]` parameters.

## Pattern overview

- **Test 1 (positive):** `Constructor_OnAllArgumentsProvided_CreatesInstance` — calls the SUT
  factory helper with all valid defaults; asserts `act.Should().NotThrow()`.
- **Test 2 (negative):** `Constructor_ThrowsArgumentNullException_WhenNullValueProvided` — builds a
  `List<Action>` where each lambda passes exactly one dependency as `null!`; iterates with
  `foreach` and asserts `act.Should().Throw<ArgumentNullException>()` per entry.
- A private helper `CreateServiceWithAllArguments` (or `Create{Sut}WithAllArguments`) lives
  at the file end inside `#region Helper Methods`. Use `private static` when all nested `Create*`
  helpers are static; drop `static` (instance method) when any nested helper needs `Fixture` from
  `BaseMockTest` — `CreateServiceWithAllArguments` must match its callees' static-ness. Each ctor
  parameter is nullable with a `?? Create{Mock}()` fallback so the negative test can null out one
  dep at a time using named arguments.
- The **boolean-stripes `[TestCase(true,false,...)]` pattern is banned** — see Anti-pattern section.

## Canonical example

The following example tests `ProvisioningService` which has five constructor dependencies.

```csharp
// Copyright (c) Vasily Vasilyev

using FluentAssertions;
using NUnit.Framework;
using MyApp.Application.Tenants.Services;

namespace MyApp.Application.Tests.Tenants.Services;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class ProvisioningServiceTests : BaseMockTest
{
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
            () => CreateServiceWithAllArguments(applianceService: null!),
            () => CreateServiceWithAllArguments(eventPublisher: null!),
            () => CreateServiceWithAllArguments(optionsMonitor: null!),
        };

        // Act + Assert.
        foreach (var act in actions)
            act.Should().Throw<ArgumentNullException>();
    }

    #endregion

    // ... other test regions ...

    #region Helper Methods

    private ProvisioningService CreateServiceWithAllArguments(
        ILogger<ProvisioningService>? logger = null,
        IItemRepository? repository = null,
        IApplianceService? applianceService = null,
        IEventPublisher? eventPublisher = null,
        IOptionsMonitor<ProvisioningOptions>? optionsMonitor = null) =>
        new(
            logger ?? CreateLogger(),
            repository ?? CreateRepository(),
            applianceService ?? CreateApplianceService(),
            eventPublisher ?? CreateEventPublisher(),
            optionsMonitor ?? CreateOptionsMonitor());

    // static: TestLoggerBuilder.CreateWithoutSetup<T> accepts a fixture parameter that it ignores
    // for no-setup loggers, so null! is intentional and this helper needs no Fixture access.
    private static ILogger<ProvisioningService> CreateLogger() =>
        TestLoggerBuilder.CreateWithoutSetup<ProvisioningService>(null!);

    // non-static: these helpers need Fixture (from BaseMockTest) to construct their builders.
    // CreateServiceWithAllArguments is therefore also non-static (it calls these instance helpers).
    private IItemRepository CreateRepository() =>
        TestItemRepositoryBuilder.CreateWithoutSetup(Fixture);

    private IApplianceService CreateApplianceService() =>
        new TestApplianceServiceBuilder(Fixture).Build();

    private IEventPublisher CreateEventPublisher() =>
        new TestEventPublisherBuilder(Fixture).Build();

    private IOptionsMonitor<ProvisioningOptions> CreateOptionsMonitor() =>
        new TestOptionsMonitorBuilder<ProvisioningOptions>(Fixture)
            .WithValue(new ProvisioningOptions())
            .Build();

    #endregion
}
```

### Key details

- One entry in the `actions` list per constructor parameter — adding a new dependency is one line.
- Named arguments (`repository: null!`) make the diff grep-friendly: reviewers immediately see
  which dep is being nulled.
- The helper uses `?? Create{Mock}()` fallbacks so every call except the one under test gets a valid
  mock automatically.
- The `#region Constructor Tests` block sits at the top of the class, before feature-specific
  regions.

## Anti-pattern: boolean stripes

The following shape is **explicitly bad code** in this pattern — avoid it:

```csharp
// ❌ BAD CODE — boolean-stripes pattern
[Test]
[TestCase(true,  false, false, false, false, TestName = "Constructor_WhenLoggerIsNull_Throws")]
[TestCase(false, true,  false, false, false, TestName = "Constructor_WhenRepositoryIsNull_Throws")]
[TestCase(false, false, true,  false, false, TestName = "Constructor_WhenApplianceServiceIsNull_Throws")]
[TestCase(false, false, false, true,  false, TestName = "Constructor_WhenEventPublisherIsNull_Throws")]
[TestCase(false, false, false, false, true,  TestName = "Constructor_WhenOptionsMonitorIsNull_Throws")]
public void Constructor_ThrowsArgumentNullException_WhenDependencyIsNull(
    Boolean nullLogger,
    Boolean nullRepository,
    Boolean nullApplianceService,
    Boolean nullEventPublisher,
    Boolean nullOptionsMonitor)
{
    var act = () => new ProvisioningService(
        nullLogger ? null! : CreateLogger(),
        nullRepository ? null! : CreateRepository(),
        nullApplianceService ? null! : CreateApplianceService(),
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
