# Scenario Tests

Scenario tests live in `{ProjectName}.WebApi.Tests/Scenarios/` and exercise **real end-to-end
orchestration** across all application layers. They are fundamentally different from unit tests
that use mock builders — do not apply mock-builder patterns here.

## What scenario tests are for

A scenario test starts at the HTTP layer (or at a top-level application service) and exercises the
full call chain down through application services, domain logic, and infrastructure — with only
the true external boundary stubbed. The goal is to catch integration bugs that mocks would hide:
null returns, missing mappings, incorrect orchestration order, and cross-layer contract drift.

Scenario tests are the last line of defence before production. They are not fast unit tests with
selective mocking — they are slow, stateful, integration-style tests that exercise the real system.

## Forbidden in scenario tests

The following are **strictly forbidden** in `WebApi.Tests/Scenarios/` (and any equivalent
integration-test project that exercises real orchestration):

| Forbidden                            | Why                                                                             |
|--------------------------------------|---------------------------------------------------------------------------------|
| `IFixture` / `AutoFixture`           | Fixture-driven construction hides missing registrations and object-graph errors |
| `Substitute.For<T>()`               | Replaces real services with stubs that return defaults, hiding failures         |
| `Fixture.Create<IInterface>()`       | Same problem as `Substitute.For<T>()` — produces a silent NSubstitute mock     |
| `Fixture.Freeze<IInterface>()`       | Same problem                                                                    |
| Test Mock Builders (`Test*Builder`)  | Builders are for unit tests; they do not compose a real dependency graph        |
| Mocks inside stubs internally        | A stub that internally delegates to a mock defeats the stub's purpose           |

## Allowed pattern — stubs and raw data only

**Stub only the leaf dependency** that requires an external connection (network call, Key Vault,
external HTTP client, secret store). Let every real service implementation run.

Naming convention: `Stub{DependencyName}` — e.g., `StubExternalSecretService`.

A stub is a concrete class that implements the interface with in-memory state seeded by the test.
It contains no NSubstitute machinery internally.

```csharp
// ✅ CORRECT — leaf stub, no mocks inside
public sealed class StubExternalSecretService : IExternalSecretService
{
    private readonly Dictionary<ResourceId, Credential> _credentials = new();

    public void AddCredential(ResourceId id, Credential credential) =>
        _credentials[id] = credential;

    public Task<Credential?> GetCredentialAsync(ResourceId id, CancellationToken ct) =>
        Task.FromResult(_credentials.GetValueOrDefault(id));
}
```

Raw data (domain objects, configuration records, primitive values) is created directly via
constructors or generator classes — NOT via `IFixture`.

## Worked example

The following scenario tests that placing a new order end-to-end stores it and
emits an integration event, without mocking any intermediate service.

### Test fixture

```csharp
// Copyright (c) Vasily Vasilyev

using FluentAssertions;
using NUnit.Framework;
using MyApp.WebApi.Tests.Scenarios.Helpers;

namespace MyApp.WebApi.Tests.Scenarios.Orders;

/// <summary>
/// End-to-end scenario: order placement flow.
/// Only the external secret service is stubbed (leaf dependency).
/// All other services — including authentication, orchestration, and persistence — run for real.
/// </summary>
[TestFixture]
[NonParallelizable] // Scenario tests share a real database — no parallel runs
public sealed class OrderProcessingScenarioTests : ScenarioBaseTest
{
    private StubExternalSecretService _secretService = null!;

    [SetUp]
    public void SetUp()
    {
        _secretService = new StubExternalSecretService();
        RegisterStub<IExternalSecretService>(_secretService);
    }

    [Test]
    public async Task PlaceOrder_WithValidRequest_StoresOrderAndEmitsEvent()
    {
        // Arrange.
        var resourceId = new ResourceId(Guid.NewGuid());
        var credential = new Credential(username: "admin", password: "secret");
        _secretService.AddCredential(resourceId, credential);

        var request = new PlaceOrderRequest(
            resourceId: resourceId,
            userId: new UserId(Guid.NewGuid()),
            name: new OrderName("my-order"));

        // Act.
        var response = await Client.PostAsJsonAsync("/api/v1/orders", request);

        // Assert.
        response.StatusCode.Should().Be(HttpStatusCode.Accepted);

        var created = await GetOrderFromDatabaseAsync(request.Name);
        created.Should().NotBeNull();
        created!.Status.Should().Be(OrderStatus.Processing);

        var emittedEvent = GetEmittedEvent<OrderPlacedEvent>();
        emittedEvent.Should().NotBeNull();
        emittedEvent!.Name.Should().Be(request.Name);
    }
}
```

### Stub class

```csharp
// Copyright (c) Vasily Vasilyev

namespace MyApp.WebApi.Tests.Scenarios.Helpers.Stubs;

/// <summary>
/// In-memory stub for <see cref="IExternalSecretService"/>.
/// Replaces the external secret store leaf dependency so scenario tests run without a real connection.
/// No mocks inside — seeded directly with raw credential objects.
/// </summary>
public sealed class StubExternalSecretService : IExternalSecretService
{
    private readonly Dictionary<ResourceId, Credential> _credentials = new();

    /// <summary>
    /// Seeds a credential to be returned when <see cref="GetCredentialAsync"/> is called
    /// with the given <paramref name="id"/>.
    /// </summary>
    public void AddCredential(ResourceId id, Credential credential)
    {
        _credentials[id] = credential;
    }

    /// <inheritdoc />
    public Task<Credential?> GetCredentialAsync(ResourceId id, CancellationToken cancellationToken)
    {
        return Task.FromResult(_credentials.GetValueOrDefault(id));
    }
}
```

### What the stub does NOT contain

```csharp
// ❌ FORBIDDEN — mock inside a stub
public sealed class BadStubExternalSecretService : IExternalSecretService
{
    private readonly IExternalSecretService _inner =
        Substitute.For<IExternalSecretService>(); // ← forbidden

    public Task<Credential?> GetCredentialAsync(ResourceId id, CancellationToken ct)
    {
        _inner.GetCredentialAsync(id, ct)
            .Returns(Task.FromResult<Credential?>(null)); // ← forbidden
        return _inner.GetCredentialAsync(id, ct);
    }
}
```

## Summary

| What to do                                      | How                                                           |
|-------------------------------------------------|---------------------------------------------------------------|
| Stub a leaf external dependency                 | Write a `Stub{Name}` class with in-memory state               |
| Provide test data                               | Use real constructors or generator classes — no `IFixture`    |
| Run intermediate services (auth, orchestration) | Leave them as real implementations — do NOT mock them         |
| Configure the stub                              | Call seeding methods (`AddCredential(...)`) in `[SetUp]`      |
