---
name: create-primitive-wrapper
description: Create strongly-typed primitive wrappers (IDs, value objects) following standard conventions. Use when creating readonly record structs implementing wrapper interfaces. Triggers on requests like "create ID type", "add wrapper type", "strongly-typed identifier".
---

# Create Primitive Wrapper

Create strongly-typed primitive wrappers in `{ProjectNamespace}.Domain` for type-safe identifiers and value objects.

## Structure

Primitive wrappers are `readonly record struct` implementing wrapper interfaces following the `I{Type}Wrapper<T>` pattern:

**Common wrapper interfaces:**

- `IStringWrapper<T>` for string-based IDs
- `IGuidWrapper<T>` for GUID-based IDs  
- `IInt32Wrapper<T>` for integer-based IDs
- `IInt64Wrapper<T>`, `IDecimalWrapper<T>`, `IDateTimeWrapper<T>`, etc.

**If no matching interface exists, no interface is needed** - just implement the pattern without interface.

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

5. **Add domain-specific helpers** if needed (e.g., `IsType()`, `TryGetType()`)

## Example: String Wrapper

```csharp
// Copyright (c) Vasily Vasilyev

using System.ComponentModel.DataAnnotations;
using MyApp.Framework.Assertions;
using MyApp.Framework.Basic.Wrappers;
using MyApp.Framework.Constants;

namespace MyApp.Domain.Backend.Regions;

/// <summary>
/// Represents a strongly-typed identifier for a .NET backend data region.
/// </summary>
public readonly record struct DataRegionId : IStringWrapper<DataRegionId>
{
    /// <summary>
    /// Gets the default string comparer for data region identifiers.
    /// </summary>
    private static StringComparer DefaultStringComparer => Constants.DefaultStringComparer;

    /// <summary>
    /// Represents an empty instance of .NET backend data region identifier.
    /// </summary>
    public static DataRegionId Empty { get; } = new();

    /// <summary>
    /// Gets the underlying string value of the data region identifier.
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
    public DataRegionId()
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
    private DataRegionId(String value)
    {
        Value = value.ThrowIfNullOrWhiteSpace();
    }

    /// <summary>
    /// Creates a <see cref="DataRegionId"/> from the specified string value.
    /// </summary>
    public static DataRegionId FromValue(String value) => new(value);

    /// <summary>
    /// Creates from the specified <see cref="DataRegionType"/>.
    /// </summary>
    public static DataRegionId FromType(DataRegionType type) => new(type.ToString());

    /// <inheritdoc />
    public override String ToString() => Value;

    /// <inheritdoc />
    public Boolean Equals(DataRegionId other) => DefaultStringComparer.Equals(Value, other.Value);

    /// <inheritdoc />
    public override Int32 GetHashCode() => DefaultStringComparer.GetHashCode(Value);

    /// <summary>
    /// Determines whether the identifier represents the specified type.
    /// </summary>
    public Boolean IsType(DataRegionType type) => DefaultStringComparer.Equals(Value, type.ToString());

    /// <summary>
    /// Tries to parse the identifier as a <see cref="DataRegionType"/>.
    /// </summary>
    public Boolean TryGetType(out DataRegionType type) => Enum.TryParse(Value, ignoreCase: true, out type);
}
```

## Key Requirements

1. **Private constructor** with validation (public parameterless for Empty only)
2. **Static FromValue** factory method for creation; **CreateNew()** additionally for GUID wrappers
3. **Static Empty** property and **IsEmpty** check
4. **[Required]** attribute on Value property
5. **String comparer** for string equality - choose based on domain:
   - `Constants.DefaultStringComparer` for case-insensitive (most common)
   - `StringComparer.Ordinal` for case-sensitive when domain requires exact matching
6. **XML documentation** on all public members

## Common Domain Helpers

Add when wrapper represents an enum-compatible value:

- `FromType(TEnum type)` - Create from enum
- `IsType(TEnum type)` - Check if matches enum
- `TryGetType(out TEnum type)` - Try parse to enum

## Sensitive Information

**If wrapper contains sensitive data**, you must handle it securely.

**See the [handle-sensitive-data](../handle-sensitive-data/SKILL.md) skill for complete guidance on handling sensitive data.**

## Tests

Create wrapper tests extending base wrapper test classes from `MyApp.OnlyForTests.Basic.Wrappers`.

**See the [create-tests](../create-tests/SKILL.md) skill for complete testing guidance, including [wrapper-tests.md](../create-tests/examples/wrapper-tests.md) for detailed patterns and examples.**

## Checklist

- [ ] `readonly record struct`
- [ ] Implements correct `IWrapper<T>` interface
- [ ] Private constructor with validation
- [ ] Public `FromValue()` factory
- [ ] `Empty` property and `IsEmpty` check
- [ ] `[Required]` on Value
- [ ] XML docs on all members
- [ ] Equals/GetHashCode use DefaultStringComparer (for strings)
