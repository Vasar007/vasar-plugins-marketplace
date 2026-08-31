---
name: model-mapping
description: Create model mapping converters using Riok.Mapperly with proper attributes and patterns. Use when converting between REST/Domain models, External API models, or any other model transformations. Triggers on requests like "create converter", "add mapper", "map models", "convert between types".
---

# Create Riok.Mapperly Converter

Create compile-time safe model converters using Riok.Mapperly source generators.

## What is Riok.Mapperly?

Riok.Mapperly is a compile-time source generator that creates type-safe mapping code:

- **Zero runtime reflection** - all mapping code generated at compile time
- **Type-safe** - compile errors for invalid mappings
- **High performance** - direct property assignments
- **Explicit control** - attributes for custom mapping rules

## File Location

Place converters near their usage:

| Usage                | Location                                                                               |
|----------------------|----------------------------------------------------------------------------------------|
| REST API             | `src/{ProjectName}.WebApi/Converters/{Feature}/`                                       |
| External API Clients | `src/{ProjectName}.Infrastructure/External/ApiClients/{Service}/{Feature}/Converters/` |
| EF/Persistence       | `src/{ProjectName}.Infrastructure/Persistence/{Feature}/Entities/`                     |
| Internal Services    | `src/{ProjectName}.Application/{Feature}/Converters/`                                  |

## Basic Converter Structure

```csharp
// Copyright (c) Vasily Vasilyev

using Riok.Mapperly.Abstractions;
using {SourceNamespace};
using {TargetNamespace};

namespace {ConverterNamespace};

/// <summary>
/// Converts between {Source} and {Target} models.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
internal static partial class {Feature}Converter
{
    /// <summary>
    /// Converts {Source} to {Target}.
    /// </summary>
    public static partial {Target} To{Target}({Source} source);
}
```

## Required Attributes

### Mapper Attribute (ALWAYS Required)

**ALWAYS use these settings on every converter:**

```csharp
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
```

- `EnumMappingStrategy.ByName` - Maps enums by name (not numeric value)
- `EnumMappingIgnoreCase = true` - Case-insensitive enum matching

**Why required:**

- Ensures enums map correctly even with different casing conventions
- Prevents subtle bugs from enum value mismatches
- Works across different naming conventions (PascalCase, camelCase, snake_case)

## Reusing Other Converters

### SharedDomainWrappersConverter (Common)

Use when converting SDK domain wrappers (Guid, String, DateTime, etc.):

```csharp
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
internal static partial class {Feature}Converter
{
    // Automatically converts:
    // - Guid ↔ GuidWrapper types
    // - String ↔ StringWrapper types  
    // - DateTime/DateTimeOffset ↔ wrapper types
}
```

**From:** `MyApp.Framework.Infrastructure.External.Shared.Converters`

### Reusing Multiple Converters

```csharp
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
[UseStaticMapper(typeof(OtherFeatureConverter))]
[UseStaticMapper(typeof(YetAnotherConverter))]
internal static partial class ComplexConverter
{
    // Can use mappings from all referenced converters
}
```

## Advanced Mapping Scenarios

### Ignoring Source Properties

Use when source has properties that shouldn't be mapped:

```csharp
[MapperIgnoreSource(nameof(Source.PropertyName))]
public static partial Target ToTarget(Source source);
```

**Example:**

```csharp
[MapperIgnoreSource(nameof(Appliance.Region))]
[MapperIgnoreSource(nameof(Appliance.DefaultUserCredentials))]
[MapperIgnoreSource(nameof(Appliance.Certificate))]
public static partial RestAppliance ToRestAppliance(Appliance appliance);
```

### Custom Property Mapping

Use when property names differ:

```csharp
[MapProperty(nameof(Source.SourceProp), nameof(Target.TargetProp))]
public static partial Target ToTarget(Source source);
```

**Example:**

```csharp
[MapProperty(nameof(Appliance.Id), nameof(RestAppliance.ApplianceId))]
public static partial RestAppliance ToRestAppliance(Appliance appliance);
```

### Custom Mapping Method

Use when property needs transformation:

```csharp
[MapProperty(nameof(Source.Version), nameof(Target.Version), Use = nameof(ConvertVersion))]
public static partial Target ToTarget(Source source);

private static TargetVersion ConvertVersion(SourceVersion version)
{
    return new TargetVersion(version.Major, version.Minor, version.Build);
}
```

**Example:**

```csharp
[MapProperty(nameof(Appliance.Version), nameof(RestAppliance.Version), Use = nameof(ToRestProductVersion))]
public static partial RestAppliance ToRestAppliance(Appliance appliance);

public static RestProductVersion ToRestProductVersion(ApplianceVersion version) 
    => version.ToProductVersion().ToRestProductVersion();
```

### Nested Property Mapping

Use when mapping from nested property to top-level:

```csharp
[MapProperty(nameof(Source.Nested.PropertyName), nameof(Target.PropertyName))]
public static partial Target ToTarget(Source source);
```

**Example:**

```csharp
[MapProperty(nameof(Request.TenantDetails.TenantName), nameof(RestRequest.TenantName))]
public static partial RestRequest ToRestRequest(Request request);
```

## When to Use Manual Mapping

**IMPORTANT**: If model mapping becomes too complex and generates many Riok.Mapperly errors, prefer manual mapping over fighting with attributes.

### Signs You Should Use Manual Mapping

- Multiple complex nested property transformations
- Many `[MapperIgnore*]` attributes needed
- Constructor parameters don't match properties
- Complex conditional logic required
- Riok.Mapperly generates compilation errors that are hard to resolve

### Manual Mapping Pattern

```csharp
/// <summary>
/// Converts {Source} to {Target}.
/// </summary>
public static {Target} To{Target}({Source} source)
{
    // TODO: Consider refactoring to use Riok.Mapperly when mapping becomes simpler
    // or when time permits to configure proper attributes
    return new {Target}(
        property1: source.Property1,
        property2: TransformProperty2(source),
        property3: source.Nested?.Property3 ?? default
    );
}

private static {Type} TransformProperty2({Source} source)
{
    // Complex transformation logic
    return /* ... */;
}
```

**Key points:**

- Leave a `TODO` comment (or regular comment if TODO raises errors) indicating future refactoring opportunity
- Manual mapping is **acceptable and preferred** over complex attribute gymnastics
- Developer should revisit later when they have time or when mapping requirements simplify
- Keep manual mapping methods clean and well-structured

### Example: Complex Manual Mapping

```csharp
public Appliance ToDomainAppliance(
    ApplianceEntity entity,
    ComputeInstance computeInstance,
    DeployableRegion region)
{
    // Manual mapping: constructor requires additional parameters not in entity
    // TODO: Evaluate if partial auto-generation is possible with custom property mappings
    entity.ThrowIfNull();
    computeInstance.ThrowIfNull();
    region.ThrowIfNull();

    return new Appliance(
        id: entity.Id.ToDomainApplianceId(),
        computeInstance: computeInstance,  // External parameter
        region: region,      // External parameter
        defaultUserCredentials: _applianceUserCredentialsMapper.ToDomainUserCredentials(entity.DefaultUserCredentials),
        certificate: ToDomainApplianceCertificate(entity.Certificate),
        version: _applianceVersionMapper.ToDomainApplianceVersion(entity.Version),
        deploymentResources: ToDomainApplianceResourceIds(entity.DeploymentResources)
    );
}
```

## Converter Naming Conventions

### REST API Converters

Use separate converters for requests vs responses:

```csharp
// Requests: REST → Domain
internal static partial class {Entity}RestRequestsConverter
{
    public static partial {DomainRequest} ToDomain{Request}({RestRequest} request);
}

// Responses: Domain → REST
internal static partial class {Entity}RestResponsesConverter
{
    public static partial {RestResponse} ToRest{Entity}({DomainEntity} entity);
    public static partial {RestPage} ToRest{Entity}Page({DomainPage} page);
}
```

### External API Converters

Name after the service:

```csharp
// Deployment Service
internal static partial class Ds{Feature}RequestsConverter
{
    public static partial RestDs.{Request} ToRest{Request}({DomainRequest} request);
}

// Infrastructure Deployment Service
internal static partial class Ids{Feature}ResponsesConverter
{
    public static partial {DomainResponse} ToDomain{Response}(RestIds.{Response} response);
}
```

### EF Entity Mappers

Non-static mappers for EF Core entity mapping, instantiated internally by the repository:

```csharp
// Entity mapper pattern
public sealed partial class {Entity}Mapper
{
    public {Entity}Mapper() { }
    
    // Domain → Entity (for new records)
    public partial {Entity}Entity ToEntity{Entity}({Entity} domain);
    
    // Entity → Domain (for reading)
    public partial {Entity} ToDomain{Entity}({Entity}Entity entity);
    
    // Update existing entity (for tracked updates, skip primary keys)
    [MapperIgnoreSource(nameof({Entity}.Id))]
    [MapperIgnoreTarget(nameof({Entity}Entity.Id))]
    public partial void UpdateEntity{Entity}({Entity} domain, {Entity}Entity entity);
}
```

**Key patterns:**

- Sealed partial class (non-static, created internally by repository via `new {Entity}Mapper()`)
- `{Entity}Mapper` naming convention
- Three core methods: `ToEntity`, `ToDomain`, `UpdateEntity`
- `UpdateEntity` ignores immutable properties (IDs, timestamps)
- No separate DI registration — repositories create mappers in their constructor

## Real-World Examples

### REST API Response Converter

```csharp
using Riok.Mapperly.Abstractions;
using MyApp.Domain.Workload.Tenants;
using MyApp.WebApi.AutoGenerated;
using MyApp.Framework.Infrastructure.External.Shared.Converters;

namespace MyApp.WebApi.Converters.Workload.Tenants;

/// <summary>
/// Converts domain tenant models to REST responses.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
internal static partial class TenantRestResponsesConverter
{
    public static partial Rest.Tenant ToRestTenant(this Tenant tenant);
    
    public static partial Rest.TenantsPage ToRestTenantsPage(this TenantsPage page);
}
```

### External Service Request Converter

```csharp
using Riok.Mapperly.Abstractions;
using MyApp.Domain.Workload.Tenants.Update;
using MyApp.Framework.Infrastructure.External.Shared.Converters;

using RestDs = MyApp.DeploymentService.Client.AutoGenerated;

namespace MyApp.Infrastructure.External.ApiClients.DeploymentService.Workload.Tenants.Converters;

/// <summary>
/// Converts tenant update requests to deployment-service API format.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
public static partial class DsTenantsRequestsConverter
{
    [MapProperty(nameof(TenantUpdateRequest.TenantDetails.TenantName), nameof(RestDs.TenantUpdateSpec.TenantName))]
    public static partial RestDs.TenantUpdateSpec ToRestUpdateSpec(TenantUpdateRequest request);
    
    [MapperIgnoreSource(nameof(TenantUpdateIamRolesRequest.TenantId))]
    public static partial RestDs.IamRolesUpdateSpec ToRestIamRolesUpdateSpec(TenantUpdateIamRolesRequest request);
}
```

### EF Entity ↔ Domain Converter

**Non-static mapper for EF Core entity mapping:**

```csharp
using Riok.Mapperly.Abstractions;
using MyApp.Domain.Sessions;
using MyApp.Framework.Domain.Sessions;
using MyApp.Framework.Infrastructure.External.Shared.Converters;

namespace MyApp.Infrastructure.Persistence.Sessions.Entities;

/// <summary>
/// Maps between Session domain models and EF entities.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
public sealed partial class SessionMapper
{
    public SessionMapper()
    {
    }

    public partial SessionEntity ToEntitySession(Session session);

    public partial Session ToDomainSession(SessionEntity entity);

    // Update an existing entity with values from a record (for tracked updates).
    // Session ID is a primary key and should not be updated.
    // Session CreatedTime is an immutable characteristic and should not be updated.
    [MapperIgnoreSource(nameof(Session.Id))]
    [MapperIgnoreTarget(nameof(SessionEntity.Id))]
    [MapperIgnoreSource(nameof(Session.CreatedTime))]
    [MapperIgnoreTarget(nameof(SessionEntity.CreatedTime))]
    public partial void UpdateEntitySession(Session session, SessionEntity entity);

    public partial SessionTypeEntity ToEntitySessionType(SessionType type);
    public partial SessionType ToDomainSessionType(SessionTypeEntity entityType);

    public partial SessionStatusEntity ToEntitySessionStatus(SessionStatus status);
    public partial SessionStatus ToDomainSessionStatus(SessionStatusEntity entityStatus);

    public partial SessionResultEntity ToEntitySessionResult(SessionResult result);
    public partial SessionResult ToDomainSessionResult(SessionResultEntity entityResult);
}
```

**Key patterns:**

- Non-static class (EF mappers are registered in DI)
- `UpdateEntity{Name}()` method for updating tracked entities
- `[MapperIgnoreSource]` + `[MapperIgnoreTarget]` to skip immutable/primary key properties
- Maps domain models, entities, and enum wrappers

### Non-Static Converter with [UseMapper]

**When you need to inject other (non-static) mappers:**

```csharp
using Riok.Mapperly.Abstractions;
using MyApp.Domain.Appliances;
using MyApp.Sdk.Domain.Compute;
using MyApp.Sdk.Domain.Regions.Deployment;
using MyApp.Framework.Assertions;
using MyApp.Framework.Infrastructure.External.Shared.Converters;

namespace MyApp.Infrastructure.Persistence.Appliances.Entities;

/// <summary>
/// Maps appliances between domain and EF entities.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
public sealed partial class ApplianceMapper : IApplianceEntityMapper<Appliance, ApplianceEntity>
{
    [UseMapper]
    private readonly ApplianceUserCredentialsMapper _applianceUserCredentialsMapper;

    [UseMapper]
    private readonly ApplianceVersionMapper _applianceVersionMapper;

    public ApplianceMapper(
        ApplianceUserCredentialsMapper applianceUserCredentialsMapper,
        ApplianceVersionMapper applianceVersionMapper)
    {
        _applianceUserCredentialsMapper = applianceUserCredentialsMapper.ThrowIfNull();
        _applianceVersionMapper = applianceVersionMapper.ThrowIfNull();
    }

    [MapperIgnoreSource(nameof(Appliance.ComputeInstance))]
    [MapperIgnoreTarget(nameof(ApplianceEntity.ComputeInstanceId))]
    [MapperIgnoreSource(nameof(Appliance.Region))]
    [MapperIgnoreTarget(nameof(ApplianceEntity.RegionId))]
    public partial ApplianceEntity ToEntityAppliance(Appliance appliance);

    public Appliance ToDomainAppliance(
        ApplianceEntity entity,
        ComputeInstance computeInstance,
        DeployableRegion region)
    {
        // Manual mapping when automatic generation isn't suitable
        entity.ThrowIfNull();
        computeInstance.ThrowIfNull();
        region.ThrowIfNull();

        return new Appliance(
            id: entity.Id.ToDomainApplianceId(),
            computeInstance: computeInstance,
            region: region,
            defaultUserCredentials: _applianceUserCredentialsMapper.ToDomainUserCredentials(entity.DefaultUserCredentials),
            certificate: ToDomainApplianceCertificate(entity.Certificate),
            version: _applianceVersionMapper.ToDomainApplianceVersion(entity.Version),
            deploymentResources: ToDomainApplianceResourceIds(entity.DeploymentResources)
        );
    }

    [MapperIgnoreSource(nameof(Appliance.Id))]
    [MapperIgnoreTarget(nameof(ApplianceEntity.Id))]
    [MapperIgnoreTarget(nameof(ApplianceEntity.ComputeInstanceId))]
    [MapperIgnoreSource(nameof(Appliance.ComputeInstance))]
    [MapperIgnoreTarget(nameof(ApplianceEntity.RegionId))]
    [MapperIgnoreSource(nameof(Appliance.Region))]
    public partial void UpdateEntityAppliance(Appliance appliance, ApplianceEntity entity);

    public partial ApplianceCertificateEntity ToEntityApplianceCertificate(ApplianceCertificate certificate);
    public partial ApplianceCertificate ToDomainApplianceCertificate(ApplianceCertificateEntity entity);
}
```

**Key patterns:**

- `[UseMapper]` attribute on fields for injecting non-static mappers
- Constructor receives mapper dependencies
- Mix of auto-generated partial methods and manual implementations
- Manual method when constructor parameters differ from properties

## Tests

Always create unit tests for converters.

**See the [create-tests](../create-tests/SKILL.md) skill for complete unit and integration testing guidance.**

## Checklist

- [ ] Converter is `static partial class` (for REST/External API) OR `sealed partial class` (for EF/DI)
- [ ] `[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]` attribute
- [ ] `[UseStaticMapper(typeof(SharedDomainWrappersConverter))]` if converting SDK wrappers
- [ ] `[UseMapper]` fields + constructor for non-static mapper dependencies (if needed)
- [ ] XML documentation on converter class
- [ ] XML documentation on public mapping methods
- [ ] Method signatures are `public static partial` (static) OR `public partial` (non-static)
- [ ] Custom mapping methods are private (if needed) OR manual public methods
- [ ] `[MapperIgnoreSource]` / `[MapperIgnoreTarget]` for properties that shouldn't be mapped
- [ ] `[MapProperty]` for property name differences or transformations
- [ ] `UpdateEntity{Name}()` method for EF tracked entity updates (if applicable)
- [ ] Converter file name matches class name
- [ ] Appropriate namespace for usage location
- [ ] EF mappers instantiated internally by repository (no separate DI registration)
