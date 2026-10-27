---
name: create-primitive-wrapper
description: Create a strongly-typed .NET primitive wrapper (an ID or a value object) as a readonly record struct.
when_to_use: Use it for "create ID type", "add wrapper type", or "strongly-typed identifier".
---

# Create Primitive Wrapper

Create strongly-typed primitive wrappers in `{ProjectNamespace}.Domain` for type-safe identifiers and value objects.

The templates use the private shared framework of the `MyApp.Framework` namespaces, and `MyApp.OnlyForTests` in test code. If the repo does not use it, follow the closest existing code of the repo.

## Structure

Primitive wrappers are `readonly record struct` implementing wrapper interfaces following the `I{Type}Wrapper<T>` pattern:

**Common wrapper interfaces:**

- `IStringWrapper<T>` for string-based IDs
- `IGuidWrapper<T>` for GUID-based IDs  
- `IInt32Wrapper<T>` for integer-based IDs
- `IInt64Wrapper<T>`, `IDecimalWrapper<T>`, `IDateTimeWrapper<T>`, and others

**If no matching interface exists, no interface is needed.** Implement the pattern without an interface.

```csharp
public readonly record struct {WrapperName} : IStringWrapper<{WrapperName}>
{
    // 1. Static comparer (for string wrappers)
    private static StringComparer DefaultStringComparer => Constants.DefaultStringComparer;

    // 2. Empty instance
    public static {WrapperName} Empty { get; } = new();

    // 3. Value property with [Required]
    [Required]
    public String Value { get; init; }

    // 4. IsEmpty check
    public Boolean IsEmpty => this == Empty;

    // 5. Public parameterless constructor (for Empty)
    public {WrapperName}() { Value = String.Empty; }

    // 6. Private constructor with validation
    private {WrapperName}(String value) { Value = value.ThrowIfNullOrWhiteSpace(); }

    // 7. Static factory methods
    public static {WrapperName} FromValue(String value) => new(value);
    // For GUID wrappers also add: public static {WrapperName} CreateNew() => new(Guid.NewGuid());

    // 8. ToString, Equals, GetHashCode overrides
}
```

## Steps

1. **Create file** at `src/{ProjectName}.Domain/{Feature}/{WrapperName}.cs`

2. **Add required usings**:

   ```csharp
   using System.ComponentModel.DataAnnotations;
   using MyApp.Framework.Assertions;
   using MyApp.Framework.Basic.Wrappers;
   using MyApp.Framework.Constants;
   ```

3. **Choose wrapper interface**:
   - `IStringWrapper<T>` for string-based IDs (most common)
   - `IGuidWrapper<T>` for GUID-based IDs
   - `IInt32Wrapper<T>` for integer-based IDs

4. **Implement required members** with XML documentation

5. **Add domain-specific helpers** as needed, for example `IsType()` and `TryGetType()`

## Example: String Wrapper

```csharp
// Copyright (c) Vasily Vasilyev

using System.ComponentModel.DataAnnotations;
using MyApp.Framework.Assertions;
using MyApp.Framework.Basic.Wrappers;
using MyApp.Framework.Constants;

namespace MyApp.Domain.Shipping;

/// <summary>
/// Represents a strongly-typed identifier for a shipping method.
/// </summary>
public readonly record struct ShippingMethodId : IStringWrapper<ShippingMethodId>
{
    /// <summary>
    /// Gets the default string comparer for shipping method identifiers.
    /// </summary>
    private static StringComparer DefaultStringComparer => Constants.DefaultStringComparer;

    /// <summary>
    /// Represents an empty shipping method identifier.
    /// </summary>
    public static ShippingMethodId Empty { get; } = new();

    /// <summary>
    /// Gets the underlying string value of the shipping method identifier.
    /// </summary>
    [Required]
    public String Value { get; init; }

    /// <summary>
    /// Gets a value indicating whether this identifier is empty.
    /// </summary>
    public Boolean IsEmpty => this == Empty;

    /// <summary>
    /// Initializes a new instance with an empty value.
    /// </summary>
    public ShippingMethodId()
    {
        Value = String.Empty;
    }

    /// <summary>
    /// Initializes a new instance with the specified string value.
    /// </summary>
    /// <exception cref="ArgumentNullException">
    /// <paramref name="value" /> is <see langword="null" />.
    /// </exception>
    /// <exception cref="ArgumentException">
    /// <paramref name="value" /> is empty or whitespace.
    /// </exception>
    private ShippingMethodId(String value)
    {
        Value = value.ThrowIfNullOrWhiteSpace();
    }

    /// <summary>
    /// Creates a <see cref="ShippingMethodId"/> from the specified string value.
    /// </summary>
    public static ShippingMethodId FromValue(String value) => new(value);

    /// <summary>
    /// Creates from the specified <see cref="ShippingMethodType"/>.
    /// </summary>
    public static ShippingMethodId FromType(ShippingMethodType type) => new(type.ToString());

    /// <inheritdoc />
    public override String ToString()
    {
        return Value;
    }

    /// <inheritdoc />
    public Boolean Equals(ShippingMethodId other) => DefaultStringComparer.Equals(Value, other.Value);

    /// <inheritdoc />
    public override Int32 GetHashCode() => DefaultStringComparer.GetHashCode(Value);

    /// <summary>
    /// Determines whether the identifier represents the specified type.
    /// </summary>
    public Boolean IsType(ShippingMethodType type)
    {
        return DefaultStringComparer.Equals(Value, type.ToString());
    }

    /// <summary>
    /// Tries to parse the identifier as a <see cref="ShippingMethodType"/>.
    /// </summary>
    public Boolean TryGetType(out ShippingMethodType type)
    {
        return Enum.TryParse(Value, ignoreCase: true, out type);
    }
}
```

## Key Requirements

1. **Private constructor** with validation (public parameterless for Empty only)
2. **Static FromValue** factory method for creation. GUID wrappers also need **CreateNew()**.
3. **Static Empty** property and **IsEmpty** check
4. **[Required]** attribute on Value property
5. **String comparer** for string equality. Choose the comparer that the domain needs:
   - `Constants.DefaultStringComparer` for case-insensitive (most common)
   - `StringComparer.Ordinal` for case-sensitive comparison (a domain that requires an exact match)
6. **XML documentation** on all public members
7. **Method bodies**: wrapper factories (`FromValue`, `FromType`, `CreateNew`) and equality members (`Equals`, `GetHashCode`) use `=>`. Every other method uses a block body.

## Common Domain Helpers

Add when wrapper represents an enum-compatible value:

- `FromType(TEnum type)`: creates the wrapper from the enum value
- `IsType(TEnum type)`: tests whether the value matches the enum value
- `TryGetType(out TEnum type)`: tries to parse the value to the enum

## Sensitive Information

**If wrapper contains sensitive data**, you must handle it securely.

**See the [handle-sensitive-data](../handle-sensitive-data/SKILL.md) skill for complete guidance on handling sensitive data.**

## Build

Build the changed projects with `dotnet build` (see `dev-essentials:dotnet-build-test`). If the build fails, fix the errors and build again. Repeat until the build passes. Report the result line of the last build.

## Tests

Create wrapper tests extending base wrapper test classes from `MyApp.OnlyForTests.Basic.Wrappers`.

**See the [create-tests](../create-tests/SKILL.md) skill for complete testing guidance, including [wrapper-tests.md](../create-tests/examples/wrapper-tests.md) for detailed patterns and examples.**

## Checklist

- [ ] `readonly record struct`
- [ ] Implements the matching `I{Type}Wrapper<T>` interface. No match means no interface.
- [ ] Private constructor with validation
- [ ] Public `FromValue()` factory
- [ ] `Empty` property and `IsEmpty` check
- [ ] `[Required]` on Value
- [ ] XML docs on all members
- [ ] Equals/GetHashCode use DefaultStringComparer (for strings)
- [ ] The changed projects build, and the report gives the result line of the last build
