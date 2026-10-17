---
name: add-migration
description: Add an EF Core database migration or a product upgrade migration, with the storage configuration that the database provider needs.
when_to_use: Use it for "add migration", "schema change", "data transformation", or "product upgrade".
---

# Add Migration

Create EF Core migrations for database schema changes or product-level upgrade operations using the Framework migration system.

## Migration Types

The Framework provides two migration interfaces:

### IDatabaseMigration

For **database schema changes and data transformations**.

```csharp
public interface IDatabaseMigration : IMigration
{
    /// <summary>
    /// Gets the database provider this migration targets.
    /// </summary>
    /// <remarks>
    /// When <see langword="null"/>, the migration runs on all database providers.
    /// When set to a specific provider (e.g., <see cref="DatabaseProviderType.AzureCosmos"/>),
    /// the migration only executes when the service is using that provider.
    /// </remarks>
    DatabaseProviderType? TargetProvider { get; }
}
```

**Use for**:

- Adding new fields to entities
- Transforming existing data (for example, splitting or combining fields)
- Reading all documents, modifying them, and saving back (Cosmos DB pattern)
- Schema-specific changes (for example, SQLite-only or Cosmos-only migrations)

**Execution order**: Database migrations run **before** product migrations.

### IProductMigration

For **product-level upgrade operations**.

```csharp
public interface IProductMigration : IMigration
{
    // Marker interface - no additional members.
    // Product migrations run on all database providers.
}
```

**Use for**:

- Upgrading deployed infrastructure (resource stacks, compute instances)
- Reconfiguring cloud-provider resources (for example, access roles or firewall rules)
- One-time data cleanup or transformation tasks
- Running operations that depend on external services

**Execution order**: Product migrations run **after** all database migrations complete.

## Migration Base Interface

Both types implement `IMigration`:

```csharp
public interface IMigration
{
    /// <summary>
    /// Gets the unique identifier for this migration.
    /// </summary>
    /// <remarks>
    /// Migration identifiers typically follow the format "YYYYMMDD_Description"
    /// (e.g., "20250101_AddOrderFields") to ensure proper ordering.
    /// </remarks>
    MigrationId Id { get; }

    /// <summary>
    /// Gets the version that this migration brings the system to.
    /// </summary>
    /// <remarks>
    /// Migrations are ordered and filtered by this version. Only migrations with
    /// versions higher than the current stored version will be executed.
    /// </remarks>
    VersionInfo Version { get; }

    /// <summary>
    /// Gets a human-readable description of what this migration does.
    /// </summary>
    String Description { get; }

    /// <summary>
    /// Executes the migration logic.
    /// </summary>
    Task ExecuteAsync(IMigrationContext context, CancellationToken cancellationToken);
}
```

## Step-by-Step Workflow

### 1. Determine Migration Type

**Database Migration** if:

- Adding/removing entity properties
- Transforming existing data formats
- Schema-specific changes

**Product Migration** if:

- Upgrading external infrastructure
- One-time product upgrade tasks
- Operations involving external service calls

### 2. Create Migration Class

**File location**: `src/{ProjectName}.Infrastructure/Persistence/Migration/{Feature}/`

**Naming convention**: `{Description}Migration.cs`

Example: `EmbedLineItemsInOrderSummaryMigration.cs`

#### Database Migration Example

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using {ProjectNamespace}.Infrastructure.Persistence;
using MyApp.Framework.Assertions;
using MyApp.Framework.Configuration.Options.Persistence;
using MyApp.Framework.Domain.Migrations;
using MyApp.Framework.Domain.Versioning;
using MyApp.Framework.Infrastructure.Migrations.Abstractions;
using MyApp.Framework.Infrastructure.Migrations.Contexts;

namespace {ProjectNamespace}.Infrastructure.Persistence.Migration.Orders.Summaries;

/// <summary>
/// Migration to transform order summary storage from legacy separate records to unified embedded entities.
/// </summary>
/// <remarks>
/// <para>
/// This migration transforms the order summary storage model:
/// </para>
/// <list type="bullet">
///   <item>Reads legacy records from <c>OrderEventsLegacy</c> DbSet</item>
///   <item>Groups records by SessionId (one Placed + optional Paid per session)</item>
///   <item>Combines data into a single unified entity with embedded structured data</item>
///   <item>Writes new unified records to <c>OrderSummaries</c> DbSet</item>
///   <item>Removes legacy records after successful migration</item>
/// </list>
/// <para>
/// The migration is idempotent - if no legacy records exist, it will complete without changes.
/// </para>
/// </remarks>
public sealed class EmbedLineItemsInOrderSummaryMigration : IDatabaseMigration
{
    private readonly ILogger<EmbedLineItemsInOrderSummaryMigration> _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="EmbedLineItemsInOrderSummaryMigration"/> class.
    /// </summary>
    /// <param name="logger">The logger instance.</param>
    /// <exception cref="ArgumentNullException">
    /// <paramref name="logger" /> is <see langword="null" />.
    /// </exception>
    public EmbedLineItemsInOrderSummaryMigration(
        ILogger<EmbedLineItemsInOrderSummaryMigration> logger)
    {
        _logger = logger.ThrowIfNull();
    }

    /// <inheritdoc />
    public MigrationId Id => MigrationId.FromValue("20260113_EmbedLineItemsInOrderSummary");

    /// <inheritdoc />
    public VersionInfo Version => VersionInfo.ParseVersion("1.1.0.0");

    /// <inheritdoc />
    public String Description => "Combines Placed and Paid order event records into unified entities with embedded data.";

    /// <inheritdoc />
    public DatabaseProviderType? TargetProvider => null; // All providers.

    /// <inheritdoc />
    public async Task ExecuteAsync(IMigrationContext context, CancellationToken cancellationToken)
    {
        var dbContext = context.GetRequiredService<{ServiceName}DbContext>();

        _logger.LogInformation("Starting EmbedLineItemsInOrderSummaryMigration...");

        var legacyEvents = await dbContext.OrderEventsLegacy
            .ToListAsync(cancellationToken);

        _logger.LogInformation(
            "Found {Count} legacy order event records to process.",
            legacyEvents.Count
        );

        if (legacyEvents.Count == 0)
        {
            _logger.LogInformation("No legacy records to migrate. Migration complete.");
            return;
        }

        // Process records...
        // (Transform data, create new entities, remove legacy records)

        await dbContext.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("EmbedLineItemsInOrderSummaryMigration completed.");
    }
}
```

#### Product Migration Example

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.Extensions.Logging;
using {ProjectNamespace}.Application.Services.Sales.Storefronts;
using MyApp.Framework.Assertions;
using MyApp.Framework.Domain.Migrations;
using MyApp.Framework.Domain.Versioning;
using MyApp.Framework.Infrastructure.Migrations.Abstractions;
using MyApp.Framework.Infrastructure.Migrations.Contexts;

namespace {ProjectNamespace}.Infrastructure.Persistence.Migration.Storefronts;

/// <summary>
/// Product migration to upgrade all storefronts to the latest version.
/// </summary>
/// <remarks>
/// This migration:
/// <list type="bullet">
///   <item>Enumerates all published storefronts across all sales channels</item>
///   <item>Initiates upgrade operations for storefronts below target version</item>
///   <item>Tracks upgrade progress via sessions</item>
/// </list>
/// </remarks>
public sealed class UpgradeStorefrontsMigration : IProductMigration
{
    private readonly ILogger<UpgradeStorefrontsMigration> _logger;

    public UpgradeStorefrontsMigration(
        ILogger<UpgradeStorefrontsMigration> logger)
    {
        _logger = logger.ThrowIfNull();
    }

    /// <inheritdoc />
    public MigrationId Id => MigrationId.FromValue("20260115_UpgradeStorefronts");

    /// <inheritdoc />
    public VersionInfo Version => VersionInfo.ParseVersion("1.2.0.0");

    /// <inheritdoc />
    public String Description => "Upgrades all storefronts to the latest product version.";

    /// <inheritdoc />
    public async Task ExecuteAsync(IMigrationContext context, CancellationToken cancellationToken)
    {
        var storefrontService = context.GetRequiredService<IStorefrontService>();

        _logger.LogInformation("Starting UpgradeStorefrontsMigration...");

        // Product upgrade logic...
        // (Call external services, upgrade storefronts, etc.)

        _logger.LogInformation("UpgradeStorefrontsMigration completed.");
    }
}
```

### 3. Migration ID Format

**Format**: `"YYYYMMDD_Description"`

```csharp
public MigrationId Id => MigrationId.FromValue("20260128_AddOrderDiscountFields");
```

**Rules**:

- **YYYYMMDD**: Creation date of the migration (use the actual date)
- **Description**: PascalCase, concise, describes what the migration does
- Must be **unique** across all migrations

**Examples**:

- `20260113_EmbedLineItemsInOrderSummary`
- `20260115_UpgradeStorefronts`
- `20260128_AddCustomerRetentionPolicy`
- `20260201_MigrateSessionLogsToNewFormat`

### 4. Version Format

**Format**: `VersionInfo.ParseVersion("Major.Minor.Build.Revision")`

```csharp
public VersionInfo Version => VersionInfo.ParseVersion("1.1.0.0");
```

**Rules**:

- **Major.Minor.Build.Revision** matches product version
- Only migrations with a version **higher** than the stored version are executed
- All migrations for a version are executed in `MigrationId` (date) order

**Examples**:

- `1.0.0.0` - Initial release migrations
- `1.1.0.0` - Feature update migrations
- `1.2.0.0` - Next feature update
- `2.0.0.0` - Major version upgrade migrations

### 5. Implement ExecuteAsync

**Key requirements**:

1. **Idempotent**: Safe to run multiple times
2. **Logging**: Log start, progress, and completion
3. **Error handling**: Let exceptions propagate (framework handles retries)
4. **CancellationToken**: Respect cancellation requests

```csharp
public async Task ExecuteAsync(IMigrationContext context, CancellationToken cancellationToken)
{
    // 1. Get required services from context
    var dbContext = context.GetRequiredService<{ServiceName}DbContext>();
    var someService = context.GetRequiredService<ISomeService>();

    // 2. Log start
    _logger.LogInformation("Starting {MigrationName}...", nameof(MyMigration));

    // 3. Check if migration is needed (idempotency)
    var recordsToMigrate = await dbContext.SomeEntities
        .Where(e => e.NeedsMigration)
        .ToListAsync(cancellationToken);

    if (recordsToMigrate.Count == 0)
    {
        _logger.LogInformation("No records to migrate. Migration complete.");
        return;
    }

    _logger.LogInformation("Found {Count} records to migrate.", recordsToMigrate.Count);

    // 4. Process records
    foreach (var record in recordsToMigrate)
    {
        // Transform data...
        record.NewField = ComputeNewValue(record);
    }

    // 5. Save changes
    await dbContext.SaveChangesAsync(cancellationToken);

    // 6. Log completion
    _logger.LogInformation(
        "{MigrationName} completed: migrated {Count} records.",
        nameof(MyMigration),
        recordsToMigrate.Count
    );
}
```

#### Cosmos DB Pattern (Read-Transform-Write)

For Cosmos DB, migrations typically follow this pattern:

```csharp
// Read all documents of a type
var entities = await dbContext.Orders.ToListAsync(cancellationToken);

// Transform in memory
foreach (var entity in entities)
{
    // Add new field
    entity.NewField = ComputeValue(entity);
    
    // Mark as modified (EF Core change tracking)
    dbContext.Entry(entity).State = EntityState.Modified;
}

// Write back to Cosmos DB
await dbContext.SaveChangesAsync(cancellationToken);
```

**Why this pattern?** Cosmos DB does not enforce a schema, so you must:

1. Read existing documents
2. Transform them in memory (add/remove/modify properties)
3. Save back to persist schema changes

For grouping records, JSON parsing, progress logs, removal of legacy data, and batch processing, read [references/common-patterns.md](references/common-patterns.md).

### 6. Add Container Configuration (Cosmos DB)

If migration adds new entity types, configure container in `{ServiceName}DbContext`:

**File**: `src/{ProjectName}.Infrastructure/Persistence/{ServiceName}DbContext.cs`

```csharp
protected override void OnModelCreating(ModelBuilder modelBuilder)
{
    base.OnModelCreating(modelBuilder);

    // Existing containers...

    // New container for migration
    modelBuilder.Entity<NewEntity>()
        .ToContainer("NewEntities")
        .HasPartitionKey(e => e.PartitionKey);

    modelBuilder.Entity<NewEntity>()
        .HasKey(e => e.Id);
}
```

**DbSet property**:

```csharp
public DbSet<NewEntity> NewEntities => Set<NewEntity>();
```

### 7. Create Tests

Create tests for the migration that cover data transformation, idempotency, and error handling.

**File location**: `tests/{ProjectName}.Infrastructure.Tests/Persistence/Migration/{Feature}/`

**Naming**: `{MigrationName}Tests.cs`

**See [create-tests](../create-tests/SKILL.md) skill, specifically [examples/migration-tests.md](../create-tests/examples/migration-tests.md) for:**

- Test fixture structure with `[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]`
- Essential test scenarios (empty database, happy path, idempotency, invalid data, multiple records)
- Production data testing patterns
- Helper methods (SetupServiceProvider, CreateMigrationContext, CreateMigration)
- Complete examples from real migrations

**Essential tests to include**:

1. Empty database scenario
2. Happy path (successful data transformation)
3. Idempotency (running twice produces same result)
4. Invalid/malformed data handling
5. Multiple records/sessions

### 8. Register Migration (Optional)

**Most cases**: Framework auto-discovers migrations via reflection. No explicit registration needed.

**Manual registration** (if needed):

```csharp
services.AddSingleton<IDatabaseMigration, EmbedLineItemsInOrderSummaryMigration>();
```

## Cosmos DB Specific Considerations

### Partition Key Cannot Change

Once a container is created with a partition key, **you cannot change it**.

If you need a different partition key:

1. Create a new container with the new partition key
2. Migrate data from old container to new container
3. Update DbContext to use new container
4. Delete old container (after verification)

### No Schema Enforcement

Cosmos DB does not enforce a schema, so:

- Old documents can coexist with new schema
- Migrations must handle documents that can lack the new fields
- Each time you read a property that can be missing, test it for `null`

### Container Configuration

When adding new containers, configure in `OnModelCreating`:

```csharp
modelBuilder.Entity<MyNewEntity>()
    .ToContainer("MyNewEntities")
    .HasPartitionKey(e => e.CustomerId); // Choose appropriate partition key

modelBuilder.Entity<MyNewEntity>()
    .HasKey(e => e.Id);

// If using composite keys
modelBuilder.Entity<MyNewEntity>()
    .HasKey(e => new { e.Id, e.SecondaryKey });
```

## Execution Flow

1. **Service starts** → Migration engine initializes
2. **Reads current version** from `__MigrationHistory` container
3. **Discovers all migrations** via reflection
4. **Filters migrations** with version > current version
5. **Orders by version, then MigrationId** (date order within version)
6. **Executes database migrations** first
7. **Executes product migrations** second
8. **Updates version** in `__MigrationHistory` after all migrations succeed
9. **Service continues** normal operation

**Failure behavior**: If any migration fails, the service stops, and the migration must be fixed and redeployed.

## Troubleshooting

### Migration Not Executing

1. Find out whether the `MigrationId` is unique
2. Find out whether the `Version` is higher than the current stored version
3. Read the logs for discovery errors
4. Make sure that the migration class is `public` and has a parameterless constructor or a DI-compatible constructor

### Migration Fails in Production

1. Check logs for exception details
2. Find out whether the migration is idempotent (safe to run again)
3. If data is corrupted, manually fix via Cosmos DB Data Explorer
4. Deploy fixed migration
5. If the migration wrote only part of the data and is not idempotent, add logic that skips the items that it already migrated

### Performance Issues (Large Datasets)

1. Add batch processing (see "Batch Processing" in [references/common-patterns.md](references/common-patterns.md))
2. Log progress every N records
3. Consider breaking into multiple smaller migrations
4. For Cosmos DB, monitor RU consumption

## Checklist

- [ ] Determined migration type (IDatabaseMigration or IProductMigration)
- [ ] Created migration class in `Infrastructure/Persistence/Migration/{Feature}/`
- [ ] Used correct MigrationId format: `"YYYYMMDD_Description"`
- [ ] Set Version to match product version (for example, "1.1.0.0")
- [ ] Implemented idempotent ExecuteAsync logic
- [ ] Added logging for start, progress, and completion
- [ ] Handled CancellationToken properly
- [ ] For new entity types, added container configuration to DbContext
- [ ] Created test class with [TestFixtureSource] for all database providers
- [ ] Tested empty database scenario
- [ ] Tested happy path (successful migration)
- [ ] Tested idempotency (running twice)
- [ ] Tested invalid/malformed data handling
- [ ] Tested with production data (where available)
- [ ] Tested the removal of legacy data (if applicable)
- [ ] Added XML documentation to migration class
- [ ] Reviewed for performance (batch processing for large datasets)

## Related Skills

- [create-tests](../create-tests/SKILL.md): Testing patterns for migrations (BaseMockTest, TestFixtureSource)
- [create-ef-entity](../create-ef-entity/SKILL.md): Creating entities and repositories
- `dev-essentials:generate-xml-docs`: XML documentation standards
- `dev-essentials:create-documentation`: Documenting migrations in Docs/Migrations/
