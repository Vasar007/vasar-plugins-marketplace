# Test Model Generators

Use test model generators to create consistent, valid test data. **Never create test data inline.** Always use generators. A test can need fixed values for its assertion, for example for a sort order. Pass these values to a generator `Create{Model}` method through a private helper of the test class.

The code examples in this file use NUnit, FluentAssertions, and AutoFixture. With another test framework, assertion library, or test data library, use its equivalent attributes and calls.

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

The test cases call private helpers, as [SKILL.md](../SKILL.md) requires. The `GenerateMarket` helper makes the choice between the two generator methods. If the test needs a specific value, the helper calls `Create`. If any valid value works, it calls `Generate`. `TestMarketRepositoryBuilder` is the Test Mock Builder of the repository (see [mock-builders.md](mock-builders.md)).

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class MarketServiceTests : BaseMockTest
{
    private readonly MarketGenerator _generator;

    public MarketServiceTests()
    {
        _generator = new MarketGenerator();
    }

    [Test]
    public async Task GetMarket_WithValidId_ReturnsMarket()
    {
        // Arrange.
        var expectedMarketId = GenerateMarketId();
        var expectedMarket = GenerateMarket(marketId: expectedMarketId);

        var repository = CreateMarketRepository(markets: new[] { expectedMarket });
        Fixture.Inject(repository);

        var service = Fixture.Create<MarketService>();

        // Act.
        var result = await service.GetMarketAsync(expectedMarketId);

        // Assert.
        result.Should().Be(expectedMarket);
    }

    [Test]
    public async Task GetAllMarkets_ReturnsAllMarkets()
    {
        // Arrange.
        var market1 = GenerateMarket();
        var market2 = GenerateMarket();
        var market3 = GenerateMarket();

        var repository = CreateMarketRepository(markets: new[] { market1, market2, market3 });
        Fixture.Inject(repository);

        var service = Fixture.Create<MarketService>();

        // Act.
        var results = await service.GetAllMarketsAsync();

        // Assert.
        results.Should().HaveCount(3);
        results.Should().Contain(market1);
    }

    private Market GenerateMarket(MarketId? marketId = null)
    {
        // ✅ Create for a specific value, Generate when any valid value works
        return marketId is { } id
            ? _generator.CreateMarket(marketId: id)
            : _generator.GenerateMarket();
    }

    private MarketId GenerateMarketId()
    {
        return _generator.GenerateMarketId();
    }

    private IMarketRepository CreateMarketRepository(Market[]? markets = null)
    {
        return new TestMarketRepositoryBuilder(Fixture)
            .ApplyIf(markets is not null, b => b.AddMarketRange(markets!))
            .Build();
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
        _storeGenerator = new StoreGenerator();
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

1. **New instance**: Create each generator with `new {Model}Generator()`. Do not add a static `Instance` property. This is a rule of the project: a shared static generator caused test failures that were hard to trace in real projects.

2. **Create vs Generate**: `Create` for explicit values, `Generate` for random

3. **Composition**: Complex generators use other generators

4. **Uniqueness**: `Generate` methods append GUIDs or use random selection

5. **Keep tests independent**: Generated values are unique per call

6. **Parameterized generation**: let a test override specific properties
