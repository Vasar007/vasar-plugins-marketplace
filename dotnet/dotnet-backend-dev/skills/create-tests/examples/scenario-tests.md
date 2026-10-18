# Scenario Tests

Scenario tests live in `{ProjectName}.WebApi.Tests/Scenarios/`. They run **real end-to-end orchestration** across all application layers. They are very different from unit tests that use mock builders. Do not use mock-builder patterns here.

The code examples in this file use NUnit, FluentAssertions, NSubstitute, and AutoFixture. With another test framework, assertion library, mocking library, or test data library, use its equivalent attributes and calls.

## What scenario tests are for

A scenario test starts at the HTTP layer, or at a top-level application service. It runs the full call chain through application services, domain logic, and infrastructure. Only the true external boundary is a stub. The goal is to catch the integration bugs that mocks hide: null returns, missing mappings, a wrong orchestration order, and drift between the contracts of the layers.

Scenario tests are the last line of defense before production. They are not fast unit tests with some mocks. They are slow, stateful, integration-style tests that run the real system.

## Forbidden in scenario tests

These are **strictly forbidden** in `WebApi.Tests/Scenarios/` and in any similar integration-test project that runs real orchestration:

| Forbidden | Why |
| --- | --- |
| The test data library (for example, `IFixture` / `AutoFixture`) | Construction through the fixture hides missing registrations and errors in the object graph |
| Any mock of the mocking library (for example, `Substitute.For<T>()`) | It replaces real services with stubs that return defaults, and so it hides failures |
| An interface from the test data library (for example, `Fixture.Create<IInterface>()`) | Same problem as a mock of the mocking library: it makes a silent mock (for example, an NSubstitute mock) |
| A frozen interface from the test data library (for example, `Fixture.Freeze<IInterface>()`) | Same problem |
| Test Mock Builders (`Test*Builder`) | Builders are for unit tests. They do not build a real dependency graph |
| Mocks inside stubs | A stub that sends its calls to a mock has no purpose |

## Allowed pattern — stubs and raw data only

**Stub only the leaf dependency** that needs an external connection (a network call, an external HTTP client, or a payment gateway). Let every real service implementation run.

Naming convention: `Stub{DependencyName}`, for example `StubExternalPaymentGateway`.

A stub is a concrete class that implements the interface with in-memory state that the test seeds. It contains no code of the mocking library (for example, NSubstitute).

```csharp
// ✅ CORRECT — leaf stub, no mocks inside
public sealed class StubExternalPaymentGateway : IExternalPaymentGateway
{
    private readonly Dictionary<PaymentId, Payment> _payments = new();

    public void AddPayment(PaymentId id, Payment payment)
    {
        _payments[id] = payment;
    }

    public Task<Payment?> GetPaymentAsync(PaymentId id, CancellationToken ct)
    {
        return Task.FromResult(_payments.GetValueOrDefault(id));
    }
}
```

Raw data (domain objects, configuration records, primitive values) comes directly from constructors or generator classes, NOT from the test data library (for example, `IFixture`).

## Worked example

This scenario places a new order end to end. It tests that the order is stored and that an integration event goes out, with no mock of an intermediate service.

### Test fixture

```csharp
// Copyright (c) Vasily Vasilyev

using FluentAssertions;
using NUnit.Framework;
using MyApp.WebApi.Tests.Scenarios.Helpers;

namespace MyApp.WebApi.Tests.Scenarios.Orders;

/// <summary>
/// End-to-end scenario: order placement flow.
/// Only the external payment gateway is stubbed (leaf dependency).
/// All other services — including authentication, orchestration, and persistence — run for real.
/// </summary>
[TestFixture]
[NonParallelizable] // Scenario tests share a real database — no parallel runs
public sealed class OrderProcessingScenarioTests : ScenarioBaseTest // project-specific base — analogous to WebApiBaseTest in the Base Classes Overview table; check Tests.Common for the exact class name in your repo
{
    private StubExternalPaymentGateway _paymentGateway = null!;

    [SetUp]
    public void SetUp()
    {
        _paymentGateway = new StubExternalPaymentGateway();
        RegisterStub<IExternalPaymentGateway>(_paymentGateway);
    }

    [Test]
    public async Task PlaceOrder_WithValidRequest_StoresOrderAndEmitsEvent()
    {
        // Arrange.
        var paymentId = PaymentId.CreateNew();
        var payment = new Payment(amount: 100m, currency: "USD");
        _paymentGateway.AddPayment(paymentId, payment);

        var request = new PlaceOrderRequest(
            paymentId: paymentId,
            userId: UserId.CreateNew(),
            name: OrderName.FromValue("my-order"));

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
/// In-memory stub for <see cref="IExternalPaymentGateway"/>.
/// Replaces the external payment gateway leaf dependency so scenario tests run without a real connection.
/// No mocks inside — seeded directly with raw payment objects.
/// </summary>
public sealed class StubExternalPaymentGateway : IExternalPaymentGateway
{
    private readonly Dictionary<PaymentId, Payment> _payments = new();

    /// <summary>
    /// Seeds a payment to be returned when <see cref="GetPaymentAsync"/> is called
    /// with the given <paramref name="id"/>.
    /// </summary>
    public void AddPayment(PaymentId id, Payment payment)
    {
        _payments[id] = payment;
    }

    /// <inheritdoc />
    public Task<Payment?> GetPaymentAsync(PaymentId id, CancellationToken cancellationToken)
    {
        return Task.FromResult(_payments.GetValueOrDefault(id));
    }
}
```

### What the stub does NOT contain

```csharp
// ❌ FORBIDDEN — mock inside a stub
public sealed class BadStubExternalPaymentGateway : IExternalPaymentGateway
{
    private readonly IExternalPaymentGateway _inner =
        Substitute.For<IExternalPaymentGateway>(); // ← forbidden

    public Task<Payment?> GetPaymentAsync(PaymentId id, CancellationToken ct)
    {
        _inner.GetPaymentAsync(id, ct)
            .Returns(Task.FromResult<Payment?>(null)); // ← forbidden
        return _inner.GetPaymentAsync(id, ct);
    }
}
```

## Summary

| What to do | How |
| --- | --- |
| Stub a leaf external dependency | Write a `Stub{Name}` class with in-memory state |
| Provide test data | Use real constructors or generator classes, no test data library (for example, `IFixture`) |
| Run intermediate services (auth, orchestration) | Leave them as real implementations. Do NOT mock them. |
| Configure the stub | Call seeding methods (`AddPayment(...)`) in the per-test setup method (for example, `[SetUp]` in NUnit) |
