# Domain Layer Conventions

## No External Dependencies

The Domain layer has ZERO external dependencies. No references to Infrastructure, Application, WebApi, or external NuGet packages beyond the framework base.

## Domain Models — Sealed Records

Domain models are `sealed record` types implementing `IStaticEquatable<T>`:

```csharp
public sealed record XxxModel : IStaticEquatable<XxxModel>
{
    [Required]
    public XxxType Type { get; init; }

    [Required]
    public String Name { get; init; }

    public XxxModel(XxxType type, String name)
    {
        Type = type.ThrowIfUndefined();
        Name = name.ThrowIfNullOrWhiteSpace();
    }
}
```

Key requirements:

- `[Required]` on all required properties.
- `{ get; init; }` pattern.
- Constructor validates ALL inputs: `ThrowIfNull()`, `ThrowIfNullOrWhiteSpace()`, `ThrowIfUndefined()`.
- `IStaticEquatable<T>` is a framework-internal marker interface used by the project's shared library (`MyApp.Framework.*`). If your project does not provide this interface, drop it or substitute `IEquatable<T>`. Records still provide `Equals`, `GetHashCode`, and `ToString` automatically.

### When to override `Equals` / `GetHashCode` / `ToString`

Records already generate correct implementations for all three. **Do NOT override** them by default. Override only when one of the following applies:

- **A property's type does not implement value equality** (most commonly a reference-typed collection like `IReadOnlyList<T>` or `IDictionary<K, V>`, which uses reference equality by default). In that case, override `Equals` and `GetHashCode` together to compare the collection element-wise (and mirror it in the struct's `GetHashCode`).
- **A property must be intentionally excluded from equality** — e.g., a timestamp or audit field that should not distinguish two otherwise-equal models.
- **A property carries secrets** (password, token, private key) and the default `ToString()` would leak them. Override `ToString()` to redact with `Constants.DefaultErasedPlaceholder` (see `security.md`). You may still keep `Equals` / `GetHashCode` default unless other reasons above apply.
- **The reviewer / author explicitly asks** for a non-default equality or string shape.

When overriding, keep `Equals` and `GetHashCode` consistent (same field set, same comparers) and use `StringBuilder` for `ToString()` to stay allocation-lean.

## ID Wrapper Types

Strongly-typed IDs are `readonly record struct` implementing wrapper interfaces from the .NET backend framework.

### IGuidWrapper Pattern

```csharp
public readonly record struct MaintenanceWindowId : IGuidWrapper<MaintenanceWindowId>
{
    public static MaintenanceWindowId Empty { get; } = new();
    [Required] public Guid Value { get; init; }
    public Boolean IsEmpty => this == Empty;
    public MaintenanceWindowId() { Value = Guid.Empty; }
    private MaintenanceWindowId(Guid value) { Value = value.ThrowIfEmpty(); }
    public static MaintenanceWindowId CreateNew() => new(Guid.NewGuid());
    public static MaintenanceWindowId FromValue(Guid value) => new(value);
}
```

### IStringWrapper Pattern

```csharp
public readonly record struct ManagementRegionId : IStringWrapper<ManagementRegionId>
{
    public static StringComparer DefaultStringComparer => Constants.DefaultStringComparer;
    public static ManagementRegionId Empty { get; } = new();
    [Required] public String Value { get; init; }
    public Boolean IsEmpty => this == Empty;
    public ManagementRegionId() { Value = String.Empty; }
    private ManagementRegionId(String value) { Value = value.ThrowIfNullOrWhiteSpace(); }
    public static ManagementRegionId FromValue(String value) => new(value);
    public Boolean Equals(ManagementRegionId other) => DefaultStringComparer.Equals(Value, other.Value);
    public override Int32 GetHashCode() => DefaultStringComparer.GetHashCode(Value);
}
```

### RegionId — From SDK

`MyApp.Sdk.Domain.Regions.RegionId` comes from the shared infrastructure SDK and is **not** redefined per project. Use `RegionId.FromValue("us-east-1")` or the `.ToDomainRegionId()` extension when converting from strings in external-client DTOs.

## Domain Exceptions

Custom exceptions inherit from `Exception` (or `ArgumentException` etc.):

- 3 standard constructors (parameterless, message, message + inner).
- Optional `sealed` modifier.
- Optional static factory methods with `StringResources` messages.
- File location: `Domain/Exceptions/` or `Domain/{Feature}/Exceptions/`.

## Domain Enums

Defined in the Domain layer. Use `ThrowIfUndefined()` for validation in constructors.

## Domain Areas

Domain areas (subfolders of `Domain/`) are project-specific. Explore the existing structure before creating new ones; do not introduce a new top-level area without checking whether it fits an existing one.

## Sensitive Data

If a domain model or wrapper contains secrets (passwords, tokens, private keys), see the `security.md` rule and the `handle-sensitive-data` skill.
