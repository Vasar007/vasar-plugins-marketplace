---
name: create-domain-model
description: Create a .NET domain model as a sealed record with validation and equality members. Use for requests like "create domain model", "add domain record", or "new entity in Domain layer".
---

# Create Domain Model

Create domain models in your domain project (for example, `src/{ProjectName}.Domain`) following project conventions.

## Structure

Domain models are `sealed record` types that implement `IStaticEquatable<T>`. This marker interface comes from the internal framework of the project. If your project does not have it, use `IEquatable<T>` instead:

```csharp
public sealed record {ModelName} : IStaticEquatable<{ModelName}>
{
    // 1. Static comparers (if needed for string properties)
    private static StringComparer DefaultStringComparer => StringComparer.OrdinalIgnoreCase;

    // 2. Properties with [Required] and XML docs
    [Required]
    public {Type} {Property} { get; init; }

    // 3. Constructor with validation
    public {ModelName}({parameters})
    {
        // Validation
    }

    // 4. Equals override (required for collections/computed properties)
    public Boolean Equals({ModelName}? other) { ... }

    // 5. GetHashCode override
    public override Int32 GetHashCode() { ... }

    // 6. ToString override with StringBuilder
    public override String ToString() { ... }
}
```

## Steps

1. **Create file** at `src/{ProjectName}.Domain/{Feature}/{ModelName}.cs`

2. **Add required usings**:

   ```csharp
   using System.ComponentModel.DataAnnotations;
   using System.Text;
   using MyApp.Framework.Assertions;
   using MyApp.Framework.Basic;
   ```

3. **Define properties** with:
   - `[Required]` attribute on all required properties
   - XML documentation comments (`/// <summary>`)
   - `{ get; init; }` pattern

4. **Implement constructor** with validation:
   - `ThrowIfNull()` for reference types
   - `ThrowIfNullOrWhiteSpace()` for strings
   - `ThrowIfUndefined()` for enums
   - `ThrowIfValueIsOutOfRange()` for numeric constraints
   - Add XML docs with `<exception>` tags

5. **Override Equals**. If the model has collections or computed properties, this override is REQUIRED:
   - Use only identity fields for comparison
   - Handle null and reference equality first
   - Use `DefaultStringComparer` for string comparisons. Choose the comparer that the domain needs:
     - `StringComparer.OrdinalIgnoreCase` for case-insensitive (most common)
     - `StringComparer.Ordinal` for case-sensitive comparison (a domain that requires an exact match)

6. **Override GetHashCode**:
   - Use `HashCode.Combine()` with same fields as Equals
   - Use `DefaultStringComparer.GetHashCode()` for strings (must match Equals comparer)

7. **Override ToString**:
   - Use `StringBuilder` with initial capacity
   - Include ALL properties for debugging
   - Format: `{TypeName} { Prop1 = val1, Prop2 = val2 }`

8. **Create unit tests** extending `BaseEqualityMemberTests<T>` (see create-tests skill)

## Example

```csharp
// Copyright (c) Vasily Vasilyev

using System.ComponentModel.DataAnnotations;
using System.Text;
using {ProjectNamespace}.Common.Assertions;
using {ProjectNamespace}.Common;

namespace {ProjectNamespace}.Domain.{Feature};

/// <summary>
/// Represents an order item that was successfully cancelled.
/// </summary>
public sealed record CancelledOrderItem : IStaticEquatable<CancelledOrderItem>
{
    private static StringComparer DefaultStringComparer => StringComparer.OrdinalIgnoreCase;

    /// <summary>
    /// The type of the cancelled item.
    /// </summary>
    [Required]
    public OrderItemType ItemType { get; init; }

    /// <summary>
    /// The unique identifier of the cancelled item.
    /// </summary>
    [Required]
    public String ItemId { get; init; }

    /// <summary>
    /// Initializes a new instance of the <see cref="CancelledOrderItem"/> class.
    /// </summary>
    /// <param name="itemType">The type of the cancelled item.</param>
    /// <param name="itemId">The unique identifier of the cancelled item.</param>
    /// <exception cref="ArgumentOutOfRangeException">
    /// <paramref name="itemType"/> is not a valid <see cref="OrderItemType"/> value.
    /// </exception>
    /// <exception cref="ArgumentException">
    /// <paramref name="itemId"/> is <see langword="null"/>, empty, or whitespace.
    /// </exception>
    public CancelledOrderItem(
        OrderItemType itemType,
        String itemId)
    {
        ItemType = itemType.ThrowIfUndefined();
        ItemId = itemId.ThrowIfNullOrWhiteSpace();
    }

    public Boolean Equals(CancelledOrderItem? other)
    {
        if (other is null)
            return false;
        if (ReferenceEquals(this, other))
            return true;

        return ItemType == other.ItemType
            && DefaultStringComparer.Equals(ItemId, other.ItemId);
    }

    public override Int32 GetHashCode()
    {
        return HashCode.Combine(ItemType, DefaultStringComparer.GetHashCode(ItemId));
    }

    public override String ToString()
    {
        var sb = new StringBuilder(capacity: 128)
            .Append(nameof(CancelledOrderItem))
            .Append(" {")
            .Append(" ItemType = ").Append(ItemType)
            .Append(", ItemId = ").Append(ItemId)
            .Append(" }");

        return sb.ToString();
    }
}
```

## Validation Rules

- Constructor parameters must validate ALL inputs
- Use `ThrowIfNull()` not null-coalescing for explicit errors
- Equals must use ONLY identity fields (not computed properties)
- GetHashCode must match Equals field usage
- ToString must include ALL fields for debugging

## Sensitive Information

**If domain model contains sensitive data**, you must handle it securely.

**See the [handle-sensitive-data](../handle-sensitive-data/SKILL.md) skill for complete guidance on handling sensitive data.**

## Common Mistakes

- Forgetting `[Required]` attribute
- Missing XML documentation
- Using collection expressions for equality (use `.All()` or `.SequenceEqual()`)
- Not handling null in Equals
- Inconsistent fields between Equals and GetHashCode
- **Exposing sensitive data in ToString()**: use an erased placeholder instead

## Tests

Create unit tests for domain models following project conventions.

**See the [create-tests](../create-tests/SKILL.md) skill for complete unit and integration testing guidance.**
