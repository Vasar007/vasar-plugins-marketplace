---
name: create-ef-entity
description: Create an EF Core entity with its configuration, model mapper, and repository.
when_to_use: Use it for "create entity", "persist to database", "add repository", or "EF mapping".
---

# Create EF Entity

Create EF Core entities, mappers, and repositories in your infrastructure project for database persistence.

The templates use the private shared framework of the `MyApp.Framework` namespaces. If the repo does not use it, follow the closest existing code of the repo.

## Architecture Overview

```text
Domain Model (sealed record)
    ↓ Mapper
Entity (mutable record for EF)
    ↓ Repository
Database (for example, Cosmos DB)
```

## Files to Create

For a new entity `{EntityName}`, create:

1. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/Entities/{EntityName}Entity.cs` - EF entity class
2. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/Entities/{EntityName}EntityConfiguration.cs` - EF configuration
3. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/Entities/{EntityName}Mapper.cs` - Domain↔Entity mapper
4. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/{EntityName}Repository.cs` - Repository implementation
5. `src/{ProjectName}.Application/{Feature}/Repositories/I{EntityName}Repository.cs` - Repository interface

## Step 1: Entity Class

```csharp
// Copyright (c) Vasily Vasilyev

using System.Diagnostics.CodeAnalysis;
using {ProjectNamespace}.Domain.{Feature};
using {ProjectNamespace}.Common.DateAndTime;

namespace {ProjectNamespace}.Infrastructure.Persistence.{Feature}.Entities;

/// <inheritdoc cref="{DomainModel}"/>
[SuppressMessage("Style", "IDE0028:Simplify collection initialization")]
public sealed record {EntityName}Entity
{
    /// <inheritdoc cref="{DomainModel}.Id"/>
    public required Guid Id { get; init; }

    /// <inheritdoc cref="{DomainModel}.Name"/>
    public required String Name { get; set; }

    // IMPORTANT: Use ICollection<T> with new List<T>() for collections, NOT collection expressions
    /// <summary>
    /// Collection of related items.
    /// </summary>
    /// <remarks>
    /// Do not replace with a collection expression. Use only standard List here to avoid EF errors.
    /// </remarks>
    public ICollection<RelatedEntity> Items { get; } = new List<RelatedEntity>();

    /// <inheritdoc cref="{DomainModel}.CreatedTime"/>
    public required DateTimeUtc CreatedTime { get; init; }
}
```

## Step 2: Entity Configuration

The example uses the Cosmos DB provider of EF Core (`ToContainer`). For another database provider, use the storage configuration that the provider needs.

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using {ProjectNamespace}.Infrastructure.Persistence.Configuration; // DbStorages
using {FrameworkNamespace}; // HasUniversalKey (framework extension)

namespace {ProjectNamespace}.Infrastructure.Persistence.{Feature}.Entities;

/// <summary>
/// EF Core configuration for <see cref="{EntityName}Entity"/>.
/// </summary>
internal sealed class {EntityName}EntityConfiguration : IEntityTypeConfiguration<{EntityName}Entity>
{
    public void Configure(EntityTypeBuilder<{EntityName}Entity> builder)
    {
        builder.ToContainer(DbStorages.{ServiceContainerConstant}); // document database provider only
        builder.ToTable("{LogicalTableName}"); // Logical table name for the entity
        builder.HasUniversalKey(e => e.Id); // primary key (framework extension)

        // Configure owned types for embedded objects
        builder.OwnsMany(e => e.Items);
    }
}
```

## Step 3: Mapper

Create a mapper to convert between domain models and EF entities.

**See the [model-mapping](../model-mapping/SKILL.md) skill for complete details:**

- EF/Persistence mapper structure (non-static sealed partial class)
- Required attributes and configuration
- `ToEntity`, `ToDomain`, `UpdateEntity` methods
- `[UseMapper]` pattern for injecting other mappers
- Full examples

## Step 4: Repository Interface (Application layer)

Repository interfaces must extend `IRepository<TEntity, TKey>` (or `IRepository<TEntity, TKey1, TKey2>` for composite keys) from `MyApp.Framework.Application.Abstractions.Repositories` NuGet package.

**Why?** `IRepository<>` provides common CRUD methods and XML documentation to avoid duplication:

- `FindByPrimaryKeyAsync` - Gets entity by ID (returns null for an unknown ID)
- `GetAllAsync` - Gets all entities
- `AddAsync` - Adds new entity
- `UpdateAsync` - Updates existing entity
- `DeleteByPrimaryKeyAsync` - Deletes entity by ID

**Examples:**

```csharp
// Single-key repository
public interface IOrderRepository : IRepository<Order, OrderId>
{
    // Add custom query methods beyond base CRUD
    Task<Order?> FindByInvoiceIdAsync(InvoiceId invoiceId, CancellationToken cancellationToken = default);
    Task<OrdersPage> GetAllByQueryAsync(OrderQuery query, CancellationToken cancellationToken = default);
}

// Composite-key repository
public interface IShipmentItemRepository : IRepository<ShipmentItem, ShipmentId, ProductId>
{
    // Add custom query methods
    Task<ModelsPage<ShipmentItem>> GetAllByQueryAsync(ShipmentItemQuery query, CancellationToken cancellationToken = default);
}
```

**Pattern:**

```csharp
// Copyright (c) Vasily Vasilyev

using {ProjectNamespace}.Domain.{Feature};
using {ProjectNamespace}.Framework.Application.Abstractions.Repositories;

namespace {ProjectNamespace}.Application.{Feature}.Repositories;

/// <summary>
/// Provides methods for managing <see cref="{DomainModel}"/> entities in the repository.
/// </summary>
public interface I{EntityName}Repository : IRepository<{DomainModel}, {IdType}>
{
    // Add custom query methods beyond base CRUD operations
}
```

## Step 4b: Repository Implementation (Infrastructure layer)

Implement `I{EntityName}Repository` in `{EntityName}Repository`. Follow the "Repository Pattern" section of [ef-patterns.md](../dotnet-conventions/ef-patterns.md). Create the mapper in the constructor with `new {EntityName}Mapper()`. Use Find + Update instead of `UpsertAsync`. Call `SaveChangesAsync` inside each mutation.

## Step 5: Register Repository in DI

Register the repository standalone in `PersistenceDependencyInjection.cs`:

```csharp
serviceCollection.AddScoped<I{EntityName}Repository, {EntityName}Repository>();
```

The repository creates the mapper internally (`new {EntityName}Mapper()`). The mapper needs no separate DI registration.

## Step 5b: Add the DbSet

Add this property to `{ServiceName}DbContext`:

```csharp
public DbSet<{EntityName}Entity> {EntityName}s => Set<{EntityName}Entity>();
```

## Step 6: Application Service (Optional)

Create an application service only for one of the cases below. For simple CRUD, inject the repository directly into callers.

**When to create a service:**

- Orchestrate multiple repositories or external clients
- Add cross-entity business validation
- Coordinate background tasks with sessions

**Pattern** (if needed):

```csharp
public sealed class {Entity}Service : I{Entity}Service
{
    private readonly ILogger<{Entity}Service> _logger;
    private readonly I{Entity}Repository _{entity}Repository;

    public {Entity}Service(
        ILogger<{Entity}Service> logger,
        I{Entity}Repository {entity}Repository)
    {
        _logger = logger.ThrowIfNull();
        _{entity}Repository = {entity}Repository.ThrowIfNull();
    }
}
```

Note: Repositories call `SaveChangesAsync` internally. Callers, including services, must not call it.

## Step 7: Build, Then Add a Migration

1. Build the changed projects with `dotnet build` (see `dev-essentials:dotnet-build-test`). If the build fails, fix the errors and build again.
2. Find the database provider that the app uses in production. A repo can pick the provider by configuration, for example Cosmos DB in production and SQLite or InMemory in tests. Only the production provider counts. If the production provider is not clear, ask the user.
3. If the production provider is relational (for example, SQL Server or PostgreSQL), add a migration with the [add-migration](../add-migration/SKILL.md) skill. Its table chooses the migration system. A new `DbSet` has no table until a migration creates it, so the first query fails without the migration. A document database (for example, Cosmos DB) has no schema, so a new entity needs no migration there.

## Key Rules

1. **Entities are mutable records**: use `{ get; set; }` for updateable properties
2. **Use `required` modifier** on properties that must be set
3. **Collections use `ICollection<T>` with `new List<T>()`**, not collection expressions
4. **Mappers use the mapping library** (for example, Riok.Mapperly with the `[Mapper]` attribute)
5. **Repository interfaces in Application**, implementations in Infrastructure
6. **Mappers instantiated internally** by repositories via `new TMapper()`
7. **Repositories registered standalone** in `PersistenceDependencyInjection.cs` as `AddScoped<IRepo, Repo>()`
8. **Repositories call SaveChangesAsync internally**. Callers must not call it.

## Tests

Create tests for EF entities, mappers, repositories, and services:

**Repository (Integration Tests)**: Test CRUD operations against the test database providers of the project (for example, the EF Core in-memory provider, SQLite, or the Cosmos DB emulator).

**Mapper (Unit Tests)**: Test the domain↔entity conversions of a mapper that has custom logic.

**Service (Unit Tests)**: Test business logic, validation, and orchestration with mocked repositories.

**See the [create-tests](../create-tests/SKILL.md) skill for complete unit and integration testing guidance.**

## Checklist

- [ ] Entity class with `required` properties
- [ ] EntityConfiguration with the service container (document database only) and the key
- [ ] Mapper with ToEntity, ToDomain, UpdateEntity methods (see [model-mapping](../model-mapping/SKILL.md))
- [ ] Repository interface extends `IRepository<>` in Application layer
- [ ] Repository implementation in Infrastructure layer (creates mapper internally via `new TMapper()`)
- [ ] Repository registered standalone in `PersistenceDependencyInjection.cs` as `AddScoped<IRepo, Repo>()`
- [ ] Application service interface and implementation (only for a case in the Step 6 list)
- [ ] Service registered in DI (if applicable)
- [ ] DbSet added to {ServiceName}DbContext
- [ ] The changed projects build with no errors
- [ ] On a relational provider, a migration for the new `DbSet` (see [add-migration](../add-migration/SKILL.md))
