# Repository Tests - BaseRepositoryWithOneKeyTest / BaseRepositoryWithTwoKeysTest

Use repository base classes for integration tests that verify CRUD operations against a real database (a document-database emulator or in-memory).

## Contents

- Base Classes
- Test Fixture Source
- Required Overrides
- Complete Example: Single Key Repository
- Complete Example: Two Keys Repository
- Parallelization
- Provided Base Tests
- Key Points

The code examples in this file use NUnit and FluentAssertions. With another test framework or assertion library, use its equivalent attributes and calls.

## Base Classes

| Class                                                                       | Use For                 | Location             |
|-----------------------------------------------------------------------------|-------------------------|----------------------|
| `BaseRepositoryWithOneKeyTest<TFactory, TRepo, TEntity, TModel, TKey>`      | Single primary key      | Infrastructure.Tests |
| `BaseRepositoryWithTwoKeysTest<TFactory, TRepo, TEntity, TModel, TPK, TAK>` | Primary + alternate key | Infrastructure.Tests |

## Test Fixture Source

```csharp
// Use TestDbContextFactory_AllCases for repository tests (manual DbContext)
[TestFixture]
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]

// Use TestDbContextFactory_DiSafeCases when DbContext comes from DI
[TestFixture]
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]
```

The class shapes for the two factories:

```csharp
// Manual DbContext creation (most common)
[TestFixture]
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]
public sealed class MyRepositoryTests<TTestDbContextFactory>
    : BaseRepositoryWithOneKeyTest<TTestDbContextFactory, ...>
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    public MyRepositoryTests()
    {
    }
}

// DI-managed DbContext
[TestFixture]
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]
public sealed class MyServiceIntegrationTests<TTestDbContextFactory> : BaseMockTest
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    private readonly TTestDbContextFactory _testDbContextFactory;

    public MyServiceIntegrationTests()
    {
        _testDbContextFactory = new TTestDbContextFactory();
    }
}
```

## Required Overrides

```csharp
// Get the DbSet for the entity type
protected abstract DbSet<TEntity> GetDbSet(ServiceDbContext dbContext);

// Create repository instance with the DbContext
protected abstract TRepository CreateRepository(ServiceDbContext dbContext);

// Create a valid model instance (async to support complex setup)
protected abstract Task<TModel> CreateModelAsync();

// Create a new primary key value (for not-found tests)
protected abstract TPrimaryKey CreatePrimaryKey();

// Extract primary key from entity (for lookup after save)
protected abstract TPrimaryKey GetPrimaryKeyFromEntity(TEntity entity);

// For TwoKeysTest only:
protected abstract TAlternateKey CreateAlternateKey();
protected abstract TAlternateKey GetAlternateKeyFromEntity(TEntity entity);
```

## Complete Example - Single Key Repository

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.EntityFrameworkCore;
using MyApp.Domain.Sales.Customers;
using MyApp.Infrastructure.Persistence;
using MyApp.Infrastructure.Persistence.Sales.Customers;
using MyApp.Infrastructure.Tests.ForTests;
using MyApp.Infrastructure.Tests.ForTests.Factories;
using MyApp.Tests.Common.Helpers.Generators.Sales.Customers;

namespace MyApp.Infrastructure.Tests.Persistence.Sales.Customers;

[TestFixture]
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class CustomerRepositoryTests<TTestDbContextFactory>
    : BaseRepositoryWithOneKeyTest<TTestDbContextFactory, ICustomerRepository, CustomerEntity, Customer, CustomerId>
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    private readonly CustomerGenerator _generator;

    public CustomerRepositoryTests()
    {
        _generator = new CustomerGenerator();
    }

    protected override DbSet<CustomerEntity> GetDbSet(ServiceDbContext dbContext)
    {
        return dbContext.Customers;
    }

    protected override ICustomerRepository CreateRepository(ServiceDbContext dbContext)
    {
        return new CustomerRepository(dbContext);
    }

    protected override Task<Customer> CreateModelAsync()
    {
        var model = GenerateCustomer();
        return Task.FromResult(model);
    }

    protected override CustomerId CreatePrimaryKey()
    {
        return _generator.GenerateCustomerId();
    }

    protected override CustomerId GetPrimaryKeyFromEntity(CustomerEntity entity)
    {
        return CustomerId.FromValue(entity.CustomerId);
    }

    // ============ Additional repository-specific tests ============

    [Test]
    [NonParallelizable] // Requires exclusive DB access
    public async Task AddAsync_OnDuplicateKey_ShouldThrow()
    {
        // Arrange.
        var repository = CreateRepository(DbContext);
        var model = await CreateModelAsync();

        await repository.AddAsync(model);

        // Create duplicate with same ID
        var duplicate = GenerateCustomer() with { CustomerId = model.CustomerId };

        // Act.
        var act = () => repository.AddAsync(duplicate);

        // Assert.
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Test]
    public async Task UpdateAsync_ShouldModifyExistingEntity()
    {
        // Arrange.
        var repository = CreateRepository(DbContext);
        var model = await CreateAndSaveModelAsync(repository);

        var updatedName = GenerateCustomerName();
        var updatedModel = model with { CustomerName = updatedName };

        // Act.
        await repository.UpdateAsync(updatedModel);

        // Assert.
        var result = await repository.FindByPrimaryKeyAsync(model.CustomerId);
        result.Should().NotBeNull();
        result!.CustomerName.Should().Be(updatedName);
    }

    private async Task<Customer> CreateAndSaveModelAsync(ICustomerRepository repository)
    {
        var model = await CreateModelAsync();
        await repository.AddAsync(model);
        return model;
    }

    private Customer GenerateCustomer()
    {
        return _generator.GenerateCustomer();
    }

    private CustomerName GenerateCustomerName()
    {
        return _generator.GenerateCustomerName();
    }
}
```

## Complete Example - Two Keys Repository

```csharp
[TestFixture]
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class MarketShipmentRepositoryTests<TTestDbContextFactory>
    : BaseRepositoryWithTwoKeysTest<
        TTestDbContextFactory,
        IMarketShipmentRepository,
        MarketShipmentEntity,
        MarketShipment,
        ShipmentId,    // Primary key
        MarketId>        // Alternate key
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    private readonly ShipmentGenerator _generator;

    public MarketShipmentRepositoryTests()
    {
        _generator = new ShipmentGenerator();
    }

    // ... implement all 6 required overrides

    protected override MarketId CreateAlternateKey()
    {
        return _generator.GenerateMarketId();
    }

    protected override MarketId GetAlternateKeyFromEntity(MarketShipmentEntity entity)
    {
        return MarketId.FromValue(entity.MarketId);
    }
}
```

## Parallelization

Most repository tests can run in parallel (for example, with `[Parallelizable(ParallelScope.Fixtures)]` in NUnit).

**Turn off parallel runs** (for example, with `[NonParallelizable]` in NUnit) for tests that:

- Test unique constraint violations (concurrent inserts can interfere)
- Modify shared state that other tests read
- Test database-level locks or transactions

## Provided Base Tests

The base classes automatically test:

- `FindByPrimaryKeyAsync`: returns an existing entity
- `FindByPrimaryKeyAsync`: returns null for a missing entity
- `GetByPrimaryKeyAsync`: returns an existing entity
- `GetByPrimaryKeyAsync`: throws `NotFoundException` for a missing entity
- `GetAllAsync`: returns all entities
- `DeleteByPrimaryKeyAsync`: removes the entity
- `DeleteByPrimaryKeyAsync`: does not throw for a missing entity

**Not provided**: tests for `AddAsync` and `UpdateAsync`. If you need them, add them yourself.

For `TwoKeysTest`, also tests:

- `FindByAlternateKeyAsync`: returns the entity, or null
- `GetByAlternateKeyAsync`: returns the entity, or throws `NotFoundException`
- `DeleteByAlternateKeyAsync`: removes the entity, or does not throw

## Key Points

1. **Use generators**: Create test models with a generator that the test class creates with `new {Model}Generator()`

2. **Async CreateModelAsync**: allows a complex setup, for example related entities that the test creates first

3. **Test fixture source**: Runs tests against multiple database providers

4. **Private helpers**: Extract `CreateAndSaveModelAsync()` pattern for reuse

5. **No parallel runs for conflicts**: turn off parallel runs for tests that can interfere with other tests
