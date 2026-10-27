---
name: model-mapping
description: Create converters between REST, domain, external API, and EF models in .NET.
when_to_use: Use it for "create converter", "add mapper", "map models", or "convert between types". Not for the EF Core mapping of an entity property to a column. Use create-ef-entity for that.
---

# Create a Model Converter

Create compile-time safe model converters with the mapping library (for example, Riok.Mapperly). The examples in this skill use Riok.Mapperly attributes. Another mapping library uses its own equivalent attributes or calls.

The templates use the private shared framework of the `MyApp.Framework` namespaces. If the repo does not use it, follow the closest existing code of the repo.

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

### Mapper Attribute (Always Required)

**Always map enums by name, case-insensitive, in every converter.** With Riok.Mapperly, use these settings on every converter:

```csharp
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
```

- `EnumMappingStrategy.ByName` - Maps enums by name (not numeric value)
- `EnumMappingIgnoreCase = true` - Case-insensitive enum matching

## Reusing Other Converters

### SharedDomainWrappersConverter (Common)

Use it for SDK domain wrappers, for example Guid, String, and DateTime wrappers:

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

Use it for source properties that must not be mapped:

```csharp
[MapperIgnoreSource(nameof(Source.PropertyName))]
public static partial Target ToTarget(Source source);
```

**Example:**

```csharp
[MapperIgnoreSource(nameof(Customer.HomeStore))]
[MapperIgnoreSource(nameof(Customer.DefaultPaymentMethod))]
[MapperIgnoreSource(nameof(Customer.MembershipCard))]
public static partial RestCustomer ToRestCustomer(Customer customer);
```

### Custom Property Mapping

Use when property names differ:

```csharp
[MapProperty(nameof(Source.SourceProp), nameof(Target.TargetProp))]
public static partial Target ToTarget(Source source);
```

**Example:**

```csharp
[MapProperty(nameof(Customer.Id), nameof(RestCustomer.CustomerId))]
public static partial RestCustomer ToRestCustomer(Customer customer);
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
[MapProperty(nameof(Customer.Tier), nameof(RestCustomer.Tier), Use = nameof(ToRestLoyaltyTier))]
public static partial RestCustomer ToRestCustomer(Customer customer);

public static RestLoyaltyTier ToRestLoyaltyTier(CustomerTier tier)
{
    return tier.ToLoyaltyTier().ToRestLoyaltyTier();
}
```

### Nested Property Mapping

Use when mapping from nested property to top-level. Plain `nameof(A.B.C)` returns only `C`. Give the path as an array of names, or as a dot-separated string.

```csharp
[MapProperty([nameof(Source.Nested), nameof(Source.Nested.PropertyName)], nameof(Target.PropertyName))]
public static partial Target ToTarget(Source source);
```

**Example:**

```csharp
[MapProperty([nameof(Request.StoreDetails), nameof(Request.StoreDetails.StoreName)], nameof(RestRequest.StoreName))]
public static partial RestRequest ToRestRequest(Request request);
```

## When to Use Manual Mapping

If model mapping becomes too complex and the mapping library generates many errors, prefer manual mapping over fighting with attributes.

### Signs You Should Use Manual Mapping

- Multiple complex nested property transformations
- Many ignore attributes needed (for example, `[MapperIgnore*]` in Riok.Mapperly)
- Constructor parameters do not match properties
- Complex conditional logic required
- The mapping library generates compilation errors that are hard to resolve

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

- Leave a `TODO` comment that marks the mapping for a later refactoring. If a `TODO` comment raises errors, use a regular comment.
- Manual mapping is **acceptable and preferred** over complex attribute gymnastics
- A developer can revisit the mapping later, after the requirements become simpler or as time allows.
- Keep manual mapping methods clean and well-structured
- For a full example inside a mapper class, see `ToDomainCustomer` in the section "Non-Static Converter with [UseMapper]".

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
// Order Management Service
internal static partial class Oms{Feature}RequestsConverter
{
    public static partial RestOms.{Request} ToRest{Request}({DomainRequest} request);
}

// Payment Service
internal static partial class Ps{Feature}ResponsesConverter
{
    public static partial {DomainResponse} ToDomain{Response}(RestPs.{Response} response);
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
- No separate DI registration. Repositories create mappers in their constructor

## Full Examples

These examples use Riok.Mapperly.

### REST API Response Converter

```csharp
using Riok.Mapperly.Abstractions;
using MyApp.Domain.Sales.Stores;
using Rest = MyApp.WebApi.AutoGenerated;
using MyApp.Framework.Infrastructure.External.Shared.Converters;

namespace MyApp.WebApi.Converters.Sales.Stores;

/// <summary>
/// Converts domain store models to REST responses.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
internal static partial class StoreRestResponsesConverter
{
    public static partial Rest.Store ToRestStore(this Store store);
    
    public static partial Rest.StoresPage ToRestStoresPage(this StoresPage page);
}
```

### External Service Request Converter

```csharp
using Riok.Mapperly.Abstractions;
using MyApp.Domain.Sales.Stores.Update;
using MyApp.Framework.Infrastructure.External.Shared.Converters;

using RestOms = MyApp.OrderManagementService.Client.AutoGenerated;

namespace MyApp.Infrastructure.External.ApiClients.OrderManagementService.Sales.Stores.Converters;

/// <summary>
/// Converts store update requests to the API format of the order management service.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
public static partial class OmsStoresRequestsConverter
{
    [MapProperty([nameof(StoreUpdateRequest.StoreDetails), nameof(StoreUpdateRequest.StoreDetails.StoreName)], nameof(RestOms.StoreUpdateSpec.StoreName))]
    public static partial RestOms.StoreUpdateSpec ToRestUpdateSpec(StoreUpdateRequest request);
    
    [MapperIgnoreSource(nameof(StoreUpdateManagersRequest.StoreId))]
    public static partial RestOms.ManagersUpdateSpec ToRestManagersUpdateSpec(StoreUpdateManagersRequest request);
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

- Non-static class. The repository creates it with `new SessionMapper()`. It has no DI registration.
- `UpdateEntity{Name}()` method for updating tracked entities
- `[MapperIgnoreSource]` + `[MapperIgnoreTarget]` to skip immutable/primary key properties
- Maps domain models, entities, and enum wrappers

### Non-Static Converter with [UseMapper]

**When you need to inject other (non-static) mappers:**

```csharp
using Riok.Mapperly.Abstractions;
using MyApp.Domain.Customers;
using MyApp.Domain.Loyalty;
using MyApp.Domain.Stores;
using MyApp.Framework.Assertions;
using MyApp.Framework.Infrastructure.External.Shared.Converters;

namespace MyApp.Infrastructure.Persistence.Customers.Entities;

/// <summary>
/// Maps customers between domain and EF entities.
/// </summary>
[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]
[UseStaticMapper(typeof(SharedDomainWrappersConverter))]
public sealed partial class CustomerMapper : ICustomerEntityMapper<Customer, CustomerEntity>
{
    [UseMapper]
    private readonly CustomerPaymentMethodMapper _customerPaymentMethodMapper;

    [UseMapper]
    private readonly CustomerTierMapper _customerTierMapper;

    public CustomerMapper(
        CustomerPaymentMethodMapper customerPaymentMethodMapper,
        CustomerTierMapper customerTierMapper)
    {
        _customerPaymentMethodMapper = customerPaymentMethodMapper.ThrowIfNull();
        _customerTierMapper = customerTierMapper.ThrowIfNull();
    }

    [MapperIgnoreSource(nameof(Customer.LoyaltyAccount))]
    [MapperIgnoreTarget(nameof(CustomerEntity.LoyaltyAccountId))]
    [MapperIgnoreSource(nameof(Customer.HomeStore))]
    [MapperIgnoreTarget(nameof(CustomerEntity.HomeStoreId))]
    public partial CustomerEntity ToEntityCustomer(Customer customer);

    public Customer ToDomainCustomer(
        CustomerEntity entity,
        LoyaltyAccount loyaltyAccount,
        Store homeStore)
    {
        // Manual mapping: constructor requires additional parameters not in entity
        // TODO: Evaluate if partial auto-generation is possible with custom property mappings
        entity.ThrowIfNull();
        loyaltyAccount.ThrowIfNull();
        homeStore.ThrowIfNull();

        return new Customer(
            id: entity.Id.ToDomainCustomerId(),
            loyaltyAccount: loyaltyAccount,
            homeStore: homeStore,
            defaultPaymentMethod: _customerPaymentMethodMapper.ToDomainPaymentMethod(entity.DefaultPaymentMethod),
            membershipCard: ToDomainCustomerMembershipCard(entity.MembershipCard),
            tier: _customerTierMapper.ToDomainCustomerTier(entity.Tier),
            orderIds: ToDomainCustomerOrderIds(entity.OrderIds)
        );
    }

    [MapperIgnoreSource(nameof(Customer.Id))]
    [MapperIgnoreTarget(nameof(CustomerEntity.Id))]
    [MapperIgnoreTarget(nameof(CustomerEntity.LoyaltyAccountId))]
    [MapperIgnoreSource(nameof(Customer.LoyaltyAccount))]
    [MapperIgnoreTarget(nameof(CustomerEntity.HomeStoreId))]
    [MapperIgnoreSource(nameof(Customer.HomeStore))]
    public partial void UpdateEntityCustomer(Customer customer, CustomerEntity entity);

    public partial CustomerMembershipCardEntity ToEntityCustomerMembershipCard(CustomerMembershipCard membershipCard);
    public partial CustomerMembershipCard ToDomainCustomerMembershipCard(CustomerMembershipCardEntity entity);
}
```

**Key patterns:**

- `[UseMapper]` attribute on fields for injecting non-static mappers
- Constructor receives mapper dependencies
- Mix of auto-generated partial methods and manual implementations
- A manual method for a constructor whose parameters differ from the properties

## Tests

Always create unit tests for converters.

**See the [create-tests](../create-tests/SKILL.md) skill for complete unit and integration testing guidance**.

## Checklist

- [ ] Converter is `static partial class` (for REST/External API) or `sealed partial class` (for EF and other non-static mappers)
- [ ] Enums map by name, case-insensitive (Riok.Mapperly: `[Mapper(EnumMappingStrategy = EnumMappingStrategy.ByName, EnumMappingIgnoreCase = true)]`)
- [ ] For SDK wrapper conversions: reuse `SharedDomainWrappersConverter` (Riok.Mapperly: `[UseStaticMapper(typeof(SharedDomainWrappersConverter))]`)
- [ ] If a mapper needs non-static mapper dependencies, add constructor parameters for them (Riok.Mapperly: `[UseMapper]` fields)
- [ ] XML documentation on converter class
- [ ] XML documentation on public mapping methods
- [ ] Method signatures are `public static partial` (static) or `public partial` (non-static)
- [ ] Custom mapping methods are private (if needed) or manual public methods
- [ ] Properties that must not be mapped are ignored (Riok.Mapperly: `[MapperIgnoreSource]` / `[MapperIgnoreTarget]`)
- [ ] Explicit property mappings for name differences or transformations (Riok.Mapperly: `[MapProperty]`)
- [ ] `UpdateEntity{Name}()` method for EF tracked entity updates (if applicable)
- [ ] Converter file name matches class name
- [ ] Appropriate namespace for usage location
- [ ] EF mappers instantiated internally by repository (no separate DI registration)
