# EF Core & Infrastructure Patterns

## Document Database Container

If the production database is not a document database, skip this section. In a document database (for example, Cosmos DB), all entities of a .NET backend service typically use one container. The container has the name of the service. Its name constant lives in a `DbStorages` static class in the `Infrastructure/Persistence/Configuration` folder.

Example (one .NET backend service):

```csharp
public static class DbStorages
{
    public const String ServiceContainer = "MyService";
}
```

Replace the class/constant with the repo's own names.

## Entity Configuration

```csharp
internal sealed class XxxEntityConfiguration : IEntityTypeConfiguration<XxxEntity>
{
    public void Configure(EntityTypeBuilder<XxxEntity> builder)
    {
        builder.ToContainer(DbStorages.{ServiceContainerConstant}); // document database provider only (for example, Cosmos DB)
        builder.ToTable("TableName");
        builder.HasUniversalKey(e => e.Id);          // primary key (framework extension)
        builder.HasAlternateKey(e => e.SomeOtherKey); // optional
    }
}
```

- If the database is a document database, do not use navigation properties. Store foreign keys as `Guid` values, not as navigation refs.
- Owned entities use `[Owned]` attribute + `builder.OwnsOne()` / `builder.OwnsMany()`.

## DbContext

The service's EF context lives in `Infrastructure/Persistence/` and is named after the service (for example, `{Service}DbContext`).

- Every entity needs an explicit `DbSet<T>` expression-bodied property: `public DbSet<XxxEntity> Xxxs => Set<XxxEntity>();`
- Model configuration: `modelBuilder.OnAppModelCreating<{Service}DbContext>()`. The .NET backend framework finds the entity configurations automatically.

## Repository Pattern

- Interfaces in the Application layer extend `IRepository<TEntity, TKey>` (or dual-key variant) from the framework.
- Implementations in the Infrastructure layer.
- Repositories are injected directly through the constructor. Do **not** use `IUnitOfWork`.
- Repositories call `SaveChangesAsync` internally after every mutation. Callers must not call it.
- Repositories create mappers internally with `new TMapper()`. Do **not** use `IEntityDomainMappingService`.
- Use the Find + Update pattern. Do not call `UpsertAsync` directly.

## Reference Storage Patterns

An entity can refer to a value that another model owns. Store the reference in one of these ways:

1. **A reference to an entity of this service**: store the `Guid` key of that entity as a foreign key, and configure it with `HasForeignKey`. Example: `Guid HomeStoreId` as the foreign key to `StoreEntity`.
2. **A value that an external system gives as a string** (for example a country code): store the `String` directly. In the mapper, convert it to the domain wrapper through `SharedDomainWrappersConverter` (see [mappers.md](mappers.md)), for example with `.ToDomainCountryCode()`.

When you add a new entity with such a reference, follow the pattern of the closest existing entity in the repo.

## Entity DI Registration

1. Create the mapper class (instantiated internally by the repository via `new TMapper()`).
2. Register the repository standalone in the persistence DI extensions (commonly `PersistenceDependencyInjection.cs`) as `AddScoped<IRepo, Repo>()`.
3. Add `DbSet<T>` to the service's DbContext.
4. If the feature needs an application service, register it as scoped in the Application DI extensions.

## External API Clients

Located in `Infrastructure/External/ApiClients/{Service}/{Feature}/`.

- Inherit from a service-specific base class (for example, `OrderManagementServiceClientBase`).
- Return external-service DTOs directly. Application services convert them to domain models.
- Structured logging: `[{ServiceName}] {Action} {Entity}: {Parameters}`.
- Example service prefixes in class names (use your own): `Oms` (Order Management), `Ps` (Payment), `Inv` (Inventory), and `Cds` (Customer Directory).

## Multiple DB Providers

EF Core runs against the production database provider and one or more test database providers. For example, it can use Cosmos DB in production, and SQLite or the EF Core in-memory provider in tests. Provider selected via configuration/build constants. Migrations must handle all providers or specify `TargetProvider`.

## Cosmos-Specific Gotcha: Multi-Column `ORDER BY` Needs a Composite Index

**This rule is for the Cosmos DB provider of EF Core only.** It is not a general EF Core rule. If the project uses another database provider, skip this section.

`.OrderBy(x).ThenBy(y)` translates to a multi-column `ORDER BY c["x"], c["y"]`. If the indexing policy of the container has no matching composite index, this query fails or behaves incorrectly against the real Cosmos DB provider. A single-column `OrderBy` works, because the default range index covers it.

Tests against the InMemory or SQLite providers **do not show this failure**. These providers sort on the client and never use the indexing policy of Cosmos. The failure shows only against the real Cosmos emulator or a live account.

So, for each repository that supports multi-column ordering, document its composite-index requirements and test them against the Cosmos emulator. A green run on the in-memory or SQLite test double does not prove that the query works.
