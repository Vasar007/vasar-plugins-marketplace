# Riok.Mapperly Mapper & Converter Patterns

## ALWAYS Use Riok.Mapperly

Do NOT use AutoMapper, hand-written `.Select()` projections, or manual mapping when Mapperly can handle it. Only fall back to manual mapping when Mapperly attributes become too complex (many errors, constructor mismatches).

## Required Attributes — Every Mapper

```csharp
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
```

This is MANDATORY on every converter/mapper. Ensures enums map by name, case-insensitive.

## SharedDomainWrappersConverter

From the .NET backend framework (`MyApp.Framework.Infrastructure.External.Shared.Converters`). Use it for SDK wrapper conversions (Guid↔GuidWrapper, String↔StringWrapper, DateTime conversions):

```csharp
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
```

## Converter Types by Location

| Usage                | Class Style                                        | Location                                                             |
|----------------------|----------------------------------------------------|----------------------------------------------------------------------|
| REST API             | `internal static partial class`                    | `WebApi/Converters/{Feature}/`                                       |
| External API Clients | `public static partial class`                      | `Infrastructure/External/ApiClients/{Service}/{Feature}/Converters/` |
| EF/Persistence       | `public sealed partial class` (non-static, for DI) | `Infrastructure/Persistence/{Feature}/Entities/`                     |
| Internal Services    | `internal static partial class`                    | `Application/{Feature}/Converters/`                                  |

## EF Entity Mappers — Non-Static

EF mappers are non-static sealed partial classes instantiated internally by their repository via `new TMapper()`. They are **not** registered in DI:

```csharp
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
public sealed partial class SessionMapper
{
    public SessionMapper() { }

    public partial SessionEntity ToEntitySession(Session session);
    public partial Session ToDomainSession(SessionEntity entity);

    // Update tracked entity — skip immutable keys
    [MapperIgnoreSource(nameof(Session.Id))]
    [MapperIgnoreTarget(nameof(SessionEntity.Id))]
    public partial void UpdateEntitySession(Session session, SessionEntity entity);
}
```

Three core methods: `ToEntity`, `ToDomain`, `UpdateEntity`.

Repositories create the mapper in their constructor: `_mapper = new SessionMapper();`

## [UseMapper] for Non-Static Dependencies

When one mapper needs another non-static mapper:

```csharp
[UseMapper]
private readonly ApplianceUserCredentialsMapper _credentialsMapper;

public ApplianceMapper(ApplianceUserCredentialsMapper credentialsMapper)
{
    _credentialsMapper = credentialsMapper.ThrowIfNull();
}
```

## REST Converter Naming

- **Requests** (REST → Domain): `{Entity}RestRequestsConverter`
- **Responses** (Domain → REST): `{Entity}RestResponsesConverter`
- **External service**: `{ServicePrefix}{Feature}RequestsConverter` / `...ResponsesConverter`

Example service prefixes used in converter class names (illustrative — substitute your own): `Ds` (Deployment), `Ids` (Infrastructure Deployment), `Sms` (Storage Management), `Dcs` (Data Collector).

## Project-Local DomainWrappersConverter

Each service may keep its own `DomainWrappersConverter` (typically under `Infrastructure/External/ApiClients/Shared/Converters/`) for project-specific wrapper conversions: `ToDomainMaintenanceWindowId`, `ToDomainManagementRegionId`, etc.

Use it alongside the framework one:

```csharp
[UseStaticMapper(typeof(DomainWrappersConverter))]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
```

## Common Attributes

- `[MapperIgnoreSource(nameof(...))]` — skip source property
- `[MapperIgnoreTarget(nameof(...))]` — skip target property
- `[MapProperty(source, target)]` — map different property names
- `[MapProperty(source, target, Use = nameof(Method))]` — custom transform

## Manual Mapping Fallback

If Mapperly generates too many errors, use manual mapping with a TODO comment:

```csharp
public XxxModel ToDomainXxx(XxxEntity entity)
{
    // Manual mapping: constructor requires additional parameters not in entity
    return new XxxModel(
        id: entity.Id.ToDomainXxxId(),
        otherParam: externalParam
    );
}
```

This is acceptable and preferred over fighting complex attribute gymnastics.
