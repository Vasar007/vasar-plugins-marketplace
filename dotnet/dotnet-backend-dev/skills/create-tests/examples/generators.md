# Test Model Generators

Use test model generators to create consistent, valid test data. **Never create test data inline.** Always use generators.

## Generator Pattern

Location: `Tests.Common/Helpers/Generators/{Feature}/`

```text
Generators/
├── Accounts/
│   └── AccountGenerator.cs
├── Catalog/
│   ├── CategoryGenerator.cs
│   └── ProductGenerator.cs
├── Orders/
│   ├── OrderGenerator.cs
│   └── OrderLineGenerator.cs
├── Organizations/
│   └── OrganizationGenerator.cs
├── Payments/
│   └── PaymentGenerator.cs
├── Sales/
│   ├── Customers/
│   │   └── CustomerGenerator.cs
│   └── Markets/
│       └── MarketGenerator.cs
├── Sessions/
│   └── SessionGenerator.cs
├── Stores/
│   └── StoreGenerator.cs
└── Versioning/
    ├── ProductVersionGenerator.cs
    └── VersionInfoGenerator.cs
```

## Generator Structure

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.OnlyForTests.Data.Generators;
using MyApp.OnlyForTests.Enumerations;

namespace MyApp.Tests.Common.Helpers.Generators.Sales.Markets;

public sealed class MarketGenerator
{
    /// <summary>
    /// Singleton instance for convenient access.
    /// </summary>
    public static MarketGenerator Instance { get; } = new();

    public MarketGenerator()
    {
    }

    // ============ Create methods - explicit parameters ============

    /// <summary>
    /// Creates model with explicit parameter values.
    /// Use when you need specific values for assertions.
    /// </summary>
    public Market CreateMarket(MarketId marketId)
    {
        return Market.FromId(marketId: marketId);
    }

    public MarketListing CreateMarketListing(MarketId marketId)
    {
        return new MarketListing(marketId: marketId);
    }

    // ============ Generate methods - random/unique values ============

    /// <summary>
    /// Generates model with random unique values.
    /// Use when you just need a valid instance, values don't matter.
    /// </summary>
    public Market GenerateMarket()
    {
        return CreateMarket(marketId: GenerateMarketId());
    }

    public MarketListing GenerateMarketListing()
    {
        return CreateMarketListing(marketId: GenerateMarketId());
    }

    // ============ Generate primitive values ============

    public MarketId GenerateMarketId()
    {
        // Select random from well-known, append GUID for uniqueness
        return WellKnownMarkets.WellKnown.GetRandomItem(
            selectedMarket => MarketId.FromValue($"{selectedMarket.Id.Value}.{Guid.NewGuid()}")
        );
    }

    public MarketName GenerateMarketName()
    {
        return GenerateMarketId().ResolveMarketDisplayName();
    }
}
```

## Naming Conventions

| Method prefix | Purpose | Example |
| --- | --- | --- |
| `Create{Model}` | Explicit parameters, for specific assertions | `CreateMarket(marketId)` |
| `Generate{Model}` | Random values, for tests where the values do not matter | `GenerateMarket()` |
| `Generate{Primitive}` | Random primitive wrapper values | `GenerateMarketId()` |

## Usage in Tests

This example shows only the choice between `Create` and `Generate`. A real test class also follows [SKILL.md](../SKILL.md). It wraps each generator call in a private `Generate{Model}` helper. It also names the SUT variable after the role of its class (gate 3 of [enforced-gates.md](enforced-gates.md)), not `sut`.

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class MarketServiceTests : BaseMockTest
{
    private readonly MarketGenerator _generator;

    public MarketServiceTests()
    {
        // Use singleton instance
        _generator = MarketGenerator.Instance;
    }

    [Test]
    public async Task GetMarket_WithValidId_ReturnsMarket()
    {
        // Arrange.
        // ✅ Use Create when you need specific values for assertions
        var expectedMarketId = _generator.GenerateMarketId();
        var expectedMarket = _generator.CreateMarket(expectedMarketId);

        SetupRepositoryToReturn(expectedMarket);
        var sut = Fixture.Create<MarketService>();

        // Act.
        var result = await sut.GetMarketAsync(expectedMarketId);

        // Assert.
        result.Should().Be(expectedMarket);
    }

    [Test]
    public async Task GetAllMarkets_ReturnsAllMarkets()
    {
        // Arrange.
        // ✅ Use Generate when you just need valid instances
        var market1 = _generator.GenerateMarket();
        var market2 = _generator.GenerateMarket();
        var market3 = _generator.GenerateMarket();

        SetupRepositoryToReturn(market1, market2, market3);
        var sut = Fixture.Create<MarketService>();

        // Act.
        var results = await sut.GetAllMarketsAsync();

        // Assert.
        results.Should().HaveCount(3);
        results.Should().Contain(market1);
    }
}
```

## Generator Composition

Generators can use other generators for complex models:

```csharp
public sealed class CustomerGenerator
{
    private readonly StoreGenerator _storeGenerator;
    private readonly OrganizationGenerator _orgGenerator;

    public CustomerGenerator()
    {
        _storeGenerator = StoreGenerator.Instance;
        _orgGenerator = new OrganizationGenerator();
    }

    public Customer GenerateCustomer()
    {
        return new Customer(
            customerId: GenerateCustomerId(),
            customerName: GenerateCustomerName(),
            status: CustomerStatus.Creating,
            store: _storeGenerator.GenerateStore(), // Compose
            organizations: GenerateSeveralOrganizations(),
            createdTime: DateTimeUtc.UtcNow
        );
    }

    private IReadOnlyCollection<Organization> GenerateSeveralOrganizations()
    {
        return new[]
        {
            _orgGenerator.GenerateOrganization(),
            _orgGenerator.GenerateOrganization(),
        };
    }
}
```

## Parameterized Generation

For models with optional/configurable parts:

```csharp
public CustomerAccount GenerateCustomerAccount(
    Int32? usageCount = null,
    AccountStatus? status = null)
{
    return new CustomerAccount(
        accountNumber: GenerateAccountNumber(),
        accountId: GenerateAccountId(),
        usageCount: usageCount ?? Random.Shared.Next(0, 100),
        status: status ?? AccountStatus.Active
    );
}
```

## Key Points

1. **Singleton access**: Use `{Generator}.Instance` for convenience

2. **Create vs Generate**: `Create` for explicit values, `Generate` for random

3. **Composition**: Complex generators use other generators

4. **Uniqueness**: `Generate` methods append GUIDs or use random selection

5. **Keep tests independent**: Generated values are unique per call

6. **Parameterized generation**: let a test override specific properties
