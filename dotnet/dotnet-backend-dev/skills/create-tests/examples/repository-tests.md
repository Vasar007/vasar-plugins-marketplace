# Repository Tests - BaseRepositoryWithOneKeyTest / BaseRepositoryWithTwoKeysTest

Use repository base classes for integration tests that verify CRUD operations against a real database (a document-database emulator or in-memory).

## Base Classes

| Class                                                                       | Use For                 | Location             |
|-----------------------------------------------------------------------------|-------------------------|----------------------|
| `BaseRepositoryWithOneKeyTest<TFactory, TRepo, TEntity, TModel, TKey>`      | Single primary key      | Infrastructure.Tests |
| `BaseRepositoryWithTwoKeysTest<TFactory, TRepo, TEntity, TModel, TPK, TAK>` | Primary + alternate key | Infrastructure.Tests |

## Test Fixture Source

```csharp
// Use TestDbContextFactory_AllCases for repository tests (manual DbContext)
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]

// Use TestDbContextFactory_DiSafeCases when DbContext comes from DI
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]
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
using MyApp.Domain.Workload.Tenants;
using MyApp.Infrastructure.Persistence;
using MyApp.Infrastructure.Persistence.Workload.Tenants;
using MyApp.Infrastructure.Tests.ForTests;
using MyApp.Infrastructure.Tests.ForTests.Factories;
using MyApp.Tests.Common.Helpers.Generators.Workload.Tenants;

namespace MyApp.Infrastructure.Tests.Persistence.Workload.Tenants;

[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class TenantRepositoryTests<TTestDbContextFactory>
    : BaseRepositoryWithOneKeyTest<TTestDbContextFactory, ITenantRepository, TenantEntity, Tenant, TenantId>
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    private readonly TenantGenerator _generator;

    public TenantRepositoryTests()
    {
        _generator = new TenantGenerator();
    }

    protected override DbSet<TenantEntity> GetDbSet(ServiceDbContext dbContext)
    {
        return dbContext.Tenants;
    }

    protected override ITenantRepository CreateRepository(ServiceDbContext dbContext)
    {
        return new TenantRepository(dbContext);
    }

    protected override Task<Tenant> CreateModelAsync()
    {
        var model = _generator.GenerateTenant();
        return Task.FromResult(model);
    }

    protected override TenantId CreatePrimaryKey()
    {
        return _generator.GenerateTenantId();
    }

    protected override TenantId GetPrimaryKeyFromEntity(TenantEntity entity)
    {
        return TenantId.FromValue(entity.TenantId);
    }

    // ============ Additional repository-specific tests ============

    [Test]
    [NonParallelizable] // Requires exclusive DB access
    public async Task AddAsync_OnDuplicateKey_ShouldThrow()
    {
        // Arrange.
        var repository = CreateRepository();
        var model = await CreateModelAsync();

        await repository.AddAsync(model);
        await DbContext.SaveChangesAsync();

        // Create duplicate with same ID
        var duplicate = _generator.GenerateTenant() with { TenantId = model.TenantId };

        // Act.
        var act = async () =>
        {
            await repository.AddAsync(duplicate);
            await DbContext.SaveChangesAsync();
        };

        // Assert.
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Test]
    public async Task UpdateAsync_ShouldModifyExistingEntity()
    {
        // Arrange.
        var repository = CreateRepository();
        var model = await CreateAndSaveModelAsync(repository);

        var updatedName = _generator.GenerateTenantName();
        var updatedModel = model with { TenantName = updatedName };

        // Act.
        await repository.UpdateAsync(updatedModel);
        await DbContext.SaveChangesAsync();

        // Assert.
        var result = await repository.FindByPrimaryKeyAsync(model.TenantId);
        result.Should().NotBeNull();
        result!.TenantName.Should().Be(updatedName);
    }

    // ============ Private helpers ============

    private async Task<Tenant> CreateAndSaveModelAsync(ITenantRepository repository)
    {
        var model = await CreateModelAsync();
        await repository.AddAsync(model);
        await DbContext.SaveChangesAsync();
        return model;
    }
}
```

## Complete Example - Two Keys Repository

```csharp
[TestFixtureSource(typeof(TestDbContextFactory_AllCases))]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class RegionalDeploymentResultRepositoryTests<TTestDbContextFactory>
    : BaseRepositoryWithTwoKeysTest<
        TTestDbContextFactory,
        IRegionalDeploymentResultRepository,
        RegionalDeploymentResultEntity,
        RegionalDeploymentResult,
        DeploymentId,    // Primary key
        RegionId>        // Alternate key
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    private readonly DeploymentGenerator _generator;

    public RegionalDeploymentResultRepositoryTests()
    {
        _generator = DeploymentGenerator.Instance;
    }

    // ... implement all 6 required overrides

    protected override RegionId CreateAlternateKey()
    {
        return _generator.GenerateRegionId();
    }

    protected override RegionId GetAlternateKeyFromEntity(RegionalDeploymentResultEntity entity)
    {
        return RegionId.FromValue(entity.RegionId);
    }
}
```

## Parallelization

Most repository tests can run in parallel (`[Parallelizable(ParallelScope.Fixtures)]`).

**Use `[NonParallelizable]`** for tests that:

- Test unique constraint violations (concurrent inserts may interfere)
- Modify shared state that other tests read
- Test database-level locks or transactions

## Provided Base Tests

The base classes automatically test:

- `FindByPrimaryKeyAsync` - returns entity when exists
- `FindByPrimaryKeyAsync` - returns null when not exists
- `GetByPrimaryKeyAsync` - returns entity when exists
- `GetByPrimaryKeyAsync` - throws `NotFoundException` when not exists
- `GetAllAsync` - returns all entities
- `DeleteByPrimaryKeyAsync` - removes entity
- `DeleteByPrimaryKeyAsync` - does not throw when entity does not exist

**NOT provided** (add these yourself if needed): `AddAsync`, `UpdateAsync` tests.

For `TwoKeysTest`, also tests:

- `FindByAlternateKeyAsync` - returns entity / returns null
- `GetByAlternateKeyAsync` - returns entity / throws `NotFoundException`
- `DeleteByAlternateKeyAsync` - removes entity / does not throw

## Key Points

1. **Use generators** - Create test models via `{Model}Generator.Instance`

2. **Async CreateModelAsync** - Allows complex setup (e.g., creating related entities first)

3. **Test fixture source** - Runs tests against multiple database providers

4. **Private helpers** - Extract `CreateAndSaveModelAsync()` pattern for reuse

5. **NonParallelizable for conflicts** - Mark tests that could interfere with parallel execution
