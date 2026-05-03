# EF Core & Infrastructure Patterns

## Cosmos DB Container

All entities in a .NET backend service typically use a single Cosmos container named after the service. Its name constant lives in a `DbStorages` static class in the Infrastructure/Persistence/Configuration folder.

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
        builder.ToContainer(DbStorages.{ServiceContainerConstant});
        builder.ToTable("TableName");
        builder.HasUniversalKey(e => e.Id);          // primary key (framework extension)
        builder.HasAlternateKey(e => e.SomeOtherKey); // optional
    }
}
```

- No navigation properties (NoSQL best practice).
- Foreign keys stored as `Guid`, not navigation refs.
- Owned entities use `[Owned]` attribute + `builder.OwnsOne()` / `builder.OwnsMany()`.

## DbContext

The service's EF context lives in `Infrastructure/Persistence/` and is named after the service (e.g. `{Service}DbContext`).

- Every entity needs an explicit `DbSet<T>` expression-bodied property: `public DbSet<XxxEntity> Xxxs => Set<XxxEntity>();`
- Model config: `modelBuilder.OnAppModelCreating<{Service}DbContext>()` (.NET backend framework auto-discovers entity configs).

## Repository Pattern

- Interfaces in the Application layer extend `IRepository<TEntity, TKey>` (or dual-key variant) from the framework.
- Implementations in the Infrastructure layer.
- Repositories are injected directly via constructor — do **not** use `IUnitOfWork`.
- Repositories call `SaveChangesAsync` internally after every mutation — callers must NOT call it.
- Repositories create mappers internally via `new TMapper()` — do **not** use `IEntityDomainMappingService`.
- Use Find + Update pattern — no direct `UpsertAsync`.

## RegionId Storage — Two Patterns

1. **Appliance-like entities** that relate to a deployable region: store `Guid RegionId` as FK to `DeployableRegionEntity` with `HasForeignKey`.
2. **Cloud-resource deployment entities** (VPC, subnet, and similar infrastructure records whose region is stored as a provider string): store `String` directly and convert via `SharedDomainWrappersConverter.ToDomainRegionId()`.

When adding new entities with region, follow the pattern of the closest existing entity in the repo.

## Entity DI Registration

1. Create the mapper class (instantiated internally by the repository via `new TMapper()`).
2. Register the repository standalone in the persistence DI extensions (commonly `PersistenceDependencyInjection.cs`) as `AddScoped<IRepo, Repo>()`.
3. Add `DbSet<T>` to the service's DbContext.
4. Register the application service in the Application DI extensions (scoped, if needed).

## External API Clients

Located in `Infrastructure/External/ApiClients/{Service}/{Feature}/`.

- Inherit from a service-specific base class (e.g., `InfrastructureDeploymentServiceClientBase`).
- Return external-service DTOs directly — conversion to domain models happens in Application services.
- Structured logging: `[{ServiceName}] {Action} {Entity}: {Parameters}`.
- Example service prefixes used in class names (illustrative — substitute your own): `Ids` (Infrastructure Deployment), `Ds` (Deployment), `Sms` (Storage Management), `Dcs` (Data Collector).

## Multiple DB Providers

EF Core runs against Cosmos DB (production), SQLite, or in-memory (tests). Provider selected via configuration/build constants. Migrations must handle all providers or specify `TargetProvider`.
