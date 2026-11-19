# Domain Model Tests - BaseEqualityMemberTests\<T\>

Use `BaseEqualityMemberTests<T>` for **all** domain models implementing `IEquatable<T>` and `IEqualityOperators<T, T, Boolean>`.

## Contents

- Base Class
- Required Override
- Optional Overrides (Mutators)
- Complete Example (Simple record: all fields affect equality)
- Complete Example (Complex model: some fields are excluded from equality)
- Key Points

The test class of a model that implements these interfaces must inherit from `BaseEqualityMemberTests<T>`. Do not inherit from `BaseTest` or `BaseMockTest` for such models.

The code examples in this file use NUnit and FluentAssertions. With another test framework or assertion library, use its equivalent attributes and calls.

## Base Class

Location: `MyApp.Testing.Basic.Equality.BaseEqualityMemberTests<T>`

Type constraint: `where TValue : IEquatable<TValue>, IEqualityOperators<TValue, TValue, Boolean>`

Provides automatic tests for:

- Equality operators (`==`, `!=`)
- `Equals()` method (same object, identical objects, different objects, null/default, different type)
- `GetHashCode()` consistency (same, identical, different, mutator-based)
- `ToString()` consistency (same vs different objects)
- Field-level inequality via `GetValueMutatorsForInequality()`
- Field-level equality via `GetValueMutatorsForEquality()`

## Required Override

There is only **one** abstract method to implement:

```csharp
/// <summary>
/// Creates a unique, fully populated instance. Each call MUST return a different instance
/// (different equality-significant fields) so the base class can test inequality.
/// </summary>
protected abstract TValue CreateUniqueValue();
```

**NOTE:** The base class already provides `CreateConstantValue()`. It caches the result of the first `CreateUniqueValue()` call. Do not override it.

## Optional Overrides (Mutators)

Override these to test field-level equality semantics:

```csharp
/// <summary>
/// Yields mutators that change fields that AFFECT equality (important fields).
/// Base class asserts: mutated value != original, hash codes differ.
/// </summary>
protected virtual IEnumerable<Func<TValue, TValue>> GetValueMutatorsForInequality()
{
    yield break; // default: no mutators
}

/// <summary>
/// Yields mutators that change fields that DO NOT affect equality (unimportant fields).
/// Base class asserts: mutated value == original, hash codes are same.
/// </summary>
protected virtual IEnumerable<Func<TValue, TValue>> GetValueMutatorsForEquality()
{
    yield break; // default: no mutators
}
```

## Complete Example (Simple record — all fields affect equality)

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.Domain.Stores.Shipments;
using MyApp.Tests.Common.Helpers.Generators.Stores;
using MyApp.Tests.Common.Helpers.Generators.Shipping.Shipments;
using MyApp.Testing.Basic.Equality;

namespace MyApp.Domain.Tests.Stores.Shipments;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class StoreShipmentsTests : BaseEqualityMemberTests<StoreShipments>
{
    private readonly StoreGenerator _storeGenerator;
    private readonly ShipmentGenerator _shipmentGenerator;

    public StoreShipmentsTests()
    {
        _storeGenerator = new StoreGenerator();
        _shipmentGenerator = new ShipmentGenerator();
    }

    [Test]
    public void ToString_ShouldReturnStringContainingAllProperties()
    {
        // Arrange.
        var shipments = CreateUniqueValue();

        // Act.
        var stringRepresentation = shipments.ToString();

        // Assert.
        stringRepresentation.Should().NotBeNullOrEmpty();
        stringRepresentation.Should().Contain(nameof(StoreShipments));
        stringRepresentation.Should().Contain(nameof(StoreShipments.OutboundShipmentId));
        stringRepresentation.Should().Contain(shipments.OutboundShipmentId.ToString());
        stringRepresentation.Should().Contain(nameof(StoreShipments.ReturnShipmentId));
        stringRepresentation.Should().Contain(shipments.ReturnShipmentId.ToString());
    }

    // --- BaseEqualityMemberTests overrides ---

    protected override StoreShipments CreateUniqueValue()
    {
        return _storeGenerator.GenerateStoreShipments();
    }

    protected override IEnumerable<Func<StoreShipments, StoreShipments>> GetValueMutatorsForInequality()
    {
        yield return x => x with { OutboundShipmentId = GenerateShipmentId() };
        yield return x => x with { ReturnShipmentId = GenerateShipmentId() };
        yield return x => x with { ReplacementShipmentId = GenerateShipmentId() };
        yield return x => x with { ExchangeShipmentId = GenerateShipmentId() };
        yield return x => x with { StoreId = GenerateStoreId() };
    }

    // NOTE: Do NOT override GetValueMutatorsForEquality — only needed when some fields are excluded from equality

    private ShipmentId GenerateShipmentId()
    {
        return _shipmentGenerator.GenerateShipmentId();
    }

    private StoreId GenerateStoreId()
    {
        return _storeGenerator.GenerateStoreId();
    }
}
```

## Complete Example (Complex model — some fields are excluded from equality)

Override `GetValueMutatorsForEquality()` **only** for a model with fields that do not affect equality, for example mutable properties such as `Name` or `Status`:

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.Domain.Sales.Customers;
using MyApp.Tests.Common.Helpers.Generators.Sales.Customers;
using MyApp.Testing.Basic.Equality;

namespace MyApp.Domain.Tests.Sales.Customers;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class CustomerTests : BaseEqualityMemberTests<Customer>
{
    private readonly CustomerGenerator _customerGenerator;
    private readonly StoreGenerator _storeGenerator;
    private readonly OrganizationGenerator _organizationGenerator;
    private readonly SalesRegionGenerator _salesRegionGenerator;

    public CustomerTests()
    {
        _customerGenerator = new CustomerGenerator();
        _storeGenerator = new StoreGenerator();
        _organizationGenerator = new OrganizationGenerator();
        _salesRegionGenerator = new SalesRegionGenerator();
    }

    // --- BaseEqualityMemberTests overrides ---

    protected override Customer CreateUniqueValue()
    {
        return _customerGenerator.GenerateCustomer();
    }

    protected override IEnumerable<Func<Customer, Customer>> GetValueMutatorsForInequality()
    {
        // Fields that AFFECT equality — changing them makes instances unequal
        yield return x => x with { CustomerId = GenerateCustomerId() };
        yield return x => x with { SalesRegionId = _salesRegionGenerator.GenerateSalesRegionId() };
        yield return x => x with { CreatedTime = x.CreatedTime.AddDays(1) };
    }

    protected override IEnumerable<Func<Customer, Customer>> GetValueMutatorsForEquality()
    {
        // Fields that DO NOT affect equality — changing them keeps instances equal
        yield return x => CreateCustomer(x.CustomerId, GenerateCustomerName(), x.SalesRegionId, x.Status, x.CustomerStore, x.Organizations, x.CreatedTime, x.LoyaltyProgram);
        yield return x => CreateCustomer(x.CustomerId, x.CustomerName, x.SalesRegionId, x.Status.SelectOtherUniqueEnumValue(), x.CustomerStore, x.Organizations, x.CreatedTime, x.LoyaltyProgram);
        yield return x => CreateCustomer(x.CustomerId, x.CustomerName, x.SalesRegionId, x.Status, GenerateStore(), x.Organizations, x.CreatedTime, x.LoyaltyProgram);
    }

    // --- Additional tests beyond automatic equality tests ---

    [Test]
    public void ToString_ShouldReturnStringContainingAllProperties()
    {
        // Arrange.
        var customer = CreateUniqueValue();

        // Act.
        var stringRepresentation = customer.ToString();

        // Assert.
        stringRepresentation.Should().NotBeNullOrEmpty();
        stringRepresentation.Should().Contain(nameof(Customer));
        stringRepresentation.Should().Contain(nameof(Customer.CustomerId));
        stringRepresentation.Should().Contain(customer.CustomerId.ToString());
        // ... check all properties
    }

    private CustomerId GenerateCustomerId()
    {
        return _customerGenerator.GenerateCustomerId();
    }

    private CustomerName GenerateCustomerName()
    {
        return _customerGenerator.GenerateCustomerName();
    }

    private Store GenerateStore()
    {
        return _storeGenerator.GenerateStore();
    }

    private Customer CreateCustomer(
        CustomerId customerId,
        CustomerName customerName,
        SalesRegionId salesRegionId,
        CustomerStatus status,
        Store store,
        IReadOnlyList<Organization> organizations,
        DateTimeUtc createdTime,
        CustomerLoyaltyProgram loyaltyProgram)
    {
        return _customerGenerator.CreateCustomer(
            customerId: customerId,
            customerName: customerName,
            salesRegionId: salesRegionId,
            status: status,
            store: store,
            organizations: organizations,
            createdTime: createdTime,
            loyaltyProgram: loyaltyProgram
        );
    }
}
```

## Key Points

1. **Inheritance**: a test for a model that implements `IEquatable<T>` and `IEqualityOperators` must use `BaseEqualityMemberTests<T>`

2. **Only one abstract method**: `CreateUniqueValue()`. Each call must return a distinct instance (different equality-significant fields). The base class calls it several times to test inequality

3. **`CreateConstantValue()`**: the base class provides it, and it returns the same cached instance. The base class uses it to test that identical instances are equal. Do not override it

4. **Mutators for inequality**: override `GetValueMutatorsForInequality()` to yield `with` expressions that change one equality-significant field at a time. The base class asserts that these give unequal instances

5. **Mutators for equality**: override `GetValueMutatorsForEquality()` **only** for a model with fields that equality excludes, for example a mutable `Name` or `Status`. If all fields take part in equality, do not override it

6. **Additional tests**: add `ToString` and method behavior tests as test methods next to the automatic equality tests. Add a constructor test only for a constructor with logic, for example a check of its arguments (see [Useful Tests](../SKILL.md#useful-tests))

7. **Private helpers**: make all generator and factory calls through private methods, with the same rules as in [SKILL.md](../SKILL.md)

8. **Unsure about the pattern**: read the example table in [SKILL.md](../SKILL.md) first. If no example matches, look for a similar test class in the Domain.Tests project of the repository and follow its pattern. The project is usually `Sources/Tests/<Project>.Domain.Tests/` or `Tests/<Project>.Domain.Tests/`
