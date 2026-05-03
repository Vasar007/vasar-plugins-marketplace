---
name: create-ef-entity
description: Create EF Core entity with mapper and repository for database persistence. Use when persisting domain models in any EF Core project. Triggers on requests like "create entity", "persist to database", "add repository", "EF mapping".
---

# Create EF Entity

Create EF Core entities, mappers, and repositories in your infrastructure project for database persistence.

## Architecture Overview

```mermaid
Domain Model (sealed record)
    ↓ Mapper
Entity (mutable record for EF)
    ↓ Repository
Cosmos DB
```

## Files to Create

For a new entity `{EntityName}`, create:

1. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/Entities/{EntityName}Entity.cs` - EF entity class
2. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/Entities/{EntityName}EntityConfiguration.cs` - EF configuration
3. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/Entities/{EntityName}Mapper.cs` - Domain↔Entity mapper
4. `src/{ProjectName}.Infrastructure/Persistence/{Feature}/{EntityName}Repository.cs` - Repository implementation
5. `src/{ProjectName}.Application/Persistence/I{EntityName}Repository.cs` - Repository interface

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

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace {ProjectNamespace}.Infrastructure.Persistence.{Feature}.Entities;

/// <summary>
/// EF Core configuration for <see cref="{EntityName}Entity"/>.
/// </summary>
internal sealed class {EntityName}EntityConfiguration : IEntityTypeConfiguration<{EntityName}Entity>
{
    public void Configure(EntityTypeBuilder<{EntityName}Entity> builder)
    {
        builder.ToContainer("{ContainerName}");
        builder.ToTable("{LogicalTableName}"); // Logical table name for the entity
        builder.HasPartitionKey(e => e.PartitionKey);
        builder.HasKey(e => e.Id);

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
- Full examples (SessionMapper, ApplianceMapper)

## Step 4: Repository Interface (Application layer)

**IMPORTANT**: Repository interfaces should extend `IRepository<TEntity, TKey>` (or `IRepository<TEntity, TKey1, TKey2>` for composite keys) from `MyApp.Framework.Application.Abstractions.Repositories` NuGet package.

**Why?** `IRepository<>` provides common CRUD methods and XML documentation to avoid duplication:

- `FindByPrimaryKeyAsync` - Gets entity by ID (returns null if not found)
- `GetAllAsync` - Gets all entities
- `AddAsync` - Adds new entity
- `UpdateAsync` - Updates existing entity
- `DeleteByPrimaryKeyAsync` - Deletes entity by ID

**Examples:**

```csharp
// Single-key repository
public interface IApplianceRepository : IRepository<Appliance, ApplianceId>
{
    // Add custom query methods beyond base CRUD
    Task<Appliance?> FindByComputeInstanceIdAsync(ComputeInstanceId instanceId, CancellationToken cancellationToken = default);
    Task<AppliancesPage> GetAllByQueryAsync(ApplianceQuery query, CancellationToken cancellationToken = default);
}

// Composite-key repository
public interface IRdsInstanceDeploymentResultRepository : IRepository<RdsAuroraServerlessV2ClusterDeploymentResult, DeploymentId, RdsDbClusterId>
{
    // Add custom query methods
    Task<ModelsPage<RdsAuroraServerlessV2ClusterDeploymentResult>> GetAllByQueryAsync(RdsInstanceDeploymentResultQuery query, CancellationToken cancellationToken = default);
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

## Step 5: Register Repository in DI

Register the repository standalone in `PersistenceDependencyInjection.cs`:

```csharp
serviceCollection.AddScoped<I{EntityName}Repository, {EntityName}Repository>();
```

The mapper is created internally by the repository (`new {EntityName}Mapper()`) — no separate DI registration needed.

## Step 6: Application Service (Optional)

Application services are only needed when orchestrating across multiple repositories or external clients. For simple CRUD, the repository is sufficient — inject it directly into callers.

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

Note: Repositories call `SaveChangesAsync` internally — callers (including services) must NOT call it.

## Key Rules

1. **Entities are mutable records** - use `{ get; set; }` for updateable properties
2. **Use `required` modifier** on properties that must be set
3. **Collections use `ICollection<T>` with `new List<T>()`** - NOT collection expressions
4. **Mappers use Riok.Mapperly** with `[Mapper]` attribute
5. **Repository interfaces in Application**, implementations in Infrastructure
6. **Mappers instantiated internally** by repositories via `new TMapper()`
7. **Repositories registered standalone** in `PersistenceDependencyInjection.cs` as `AddScoped<IRepo, Repo>()`
8. **Repositories call SaveChangesAsync internally** — callers must NOT call it

## Tests

Create tests for EF entities, mappers, repositories, and services:

**Repository (Integration Tests)**: Test CRUD operations against in-memory/SQLite/Cosmos emulator databases.

**Mapper (Unit Tests)**: Test domain↔entity conversions when custom logic exists.

**Service (Unit Tests)**: Test business logic, validation, and orchestration with mocked repositories.

**See the [create-tests](../create-tests/SKILL.md) skill for complete unit and integration testing guidance.**

## Checklist

- [ ] Entity class with `required` properties
- [ ] EntityConfiguration with container/partition key
- [ ] Mapper with ToEntity, ToDomain, UpdateEntity methods (see [model-mapping](../model-mapping/SKILL.md))
- [ ] Repository interface extends `IRepository<>` in Application layer
- [ ] Repository implementation in Infrastructure layer (creates mapper internally via `new TMapper()`)
- [ ] Repository registered standalone in `PersistenceDependencyInjection.cs` as `AddScoped<IRepo, Repo>()`
- [ ] Application service interface and implementation (if needed for orchestration)
- [ ] Service registered in DI (if applicable)
- [ ] DbSet added to {ServiceName}DbContext
