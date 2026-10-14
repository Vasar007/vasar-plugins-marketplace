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

Records already generate correct implementations for all three. **Do NOT override** them by default. Override them only in these cases:

- **A property's type does not implement value equality** (most commonly a reference-typed collection like `IReadOnlyList<T>` or `IDictionary<K, V>`, which uses reference equality by default). In that case, override `Equals` and `GetHashCode` together. Compare the collection element-wise in `Equals`, and use the same elements in `GetHashCode`.
- **A property must be intentionally excluded from equality**, for example a timestamp or an audit field. Two models that differ only in this field are equal.
- **A property carries secrets** (password, token, private key), and the default `ToString()` leaks them. Override `ToString()` and redact them with `Constants.DefaultErasedPlaceholder` (see `security.md`). If no other case of this list applies, you can keep the default `Equals` and `GetHashCode`.
- **The reviewer / author explicitly asks** for a non-default equality or string shape.

When overriding, keep `Equals` and `GetHashCode` consistent (same field set, same comparers) and use `StringBuilder` for `ToString()` to stay allocation-lean.

## ID Wrapper Types

Strongly-typed IDs are `readonly record struct` implementing wrapper interfaces from the .NET backend framework.

### IGuidWrapper Pattern

```csharp
public readonly record struct OrderId : IGuidWrapper<OrderId>
{
    public static OrderId Empty { get; } = new();
    [Required] public Guid Value { get; init; }
    public Boolean IsEmpty => this == Empty;
    public OrderId() { Value = Guid.Empty; }
    private OrderId(Guid value) { Value = value.ThrowIfEmpty(); }
    public static OrderId CreateNew() => new(Guid.NewGuid());
    public static OrderId FromValue(Guid value) => new(value);
}
```

### IStringWrapper Pattern

```csharp
public readonly record struct ShippingMethodId : IStringWrapper<ShippingMethodId>
{
    public static StringComparer DefaultStringComparer => Constants.DefaultStringComparer;
    public static ShippingMethodId Empty { get; } = new();
    [Required] public String Value { get; init; }
    public Boolean IsEmpty => this == Empty;
    public ShippingMethodId() { Value = String.Empty; }
    private ShippingMethodId(String value) { Value = value.ThrowIfNullOrWhiteSpace(); }
    public static ShippingMethodId FromValue(String value) => new(value);
    public Boolean Equals(ShippingMethodId other) => DefaultStringComparer.Equals(Value, other.Value);
    public override Int32 GetHashCode() => DefaultStringComparer.GetHashCode(Value);
}
```

### Wrappers From a Shared SDK

A wrapper type that a shared SDK already defines is **not** redefined per project. Example: `MyApp.Sdk.Domain.Geography.CountryCode`. To convert a string from an external-client DTO, use `CountryCode.FromValue("US")` or the `.ToDomainCountryCode()` extension.

## Domain Exceptions

Custom exceptions inherit from `Exception` or from another exception type, for example `ArgumentException`:

- 3 standard constructors (parameterless, message, message + inner).
- Optional `sealed` modifier.
- Optional static factory methods with `StringResources` messages.
- File location: `Domain/Exceptions/` or `Domain/{Feature}/Exceptions/`.

## Domain Enums

Defined in the Domain layer. Use `ThrowIfUndefined()` for validation in constructors.

## Domain Areas

Domain areas (subfolders of `Domain/`) are project-specific. Explore the existing structure before you create a new area. Before you add a new top-level area, find out whether the code fits an existing area. If it fits, use the existing area.

## Sensitive Data

If a domain model or wrapper contains secrets (passwords, tokens, private keys), see the `security.md` rule and the `handle-sensitive-data` skill.
