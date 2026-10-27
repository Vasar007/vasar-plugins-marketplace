---
name: create-domain-model
description: Create a .NET domain model as a sealed record with validation and equality members.
when_to_use: Use it for "create domain model", "add domain record", or "new entity in Domain layer".
---

# Create Domain Model

Create domain models in your domain project (for example, `src/{ProjectName}.Domain`) following project conventions.

The templates use the private shared framework of the `MyApp.Framework` namespaces. If the repo does not use it, follow the closest existing code of the repo.

## Structure

Domain models are `sealed record` types that implement `IStaticEquatable<T>`. This marker interface comes from the internal framework of the project. If your project does not have it, use `IEquatable<T>, IEqualityOperators<T, T, Boolean>` instead:

```csharp
public sealed record {ModelName} : IStaticEquatable<{ModelName}>
{
    // 1. Properties with [Required] and XML docs
    [Required]
    public {Type} {Property} { get; init; }

    // 2. Constructor with validation
    public {ModelName}({parameters})
    {
        // Validation
    }

    // 3. Equals override (only when a case of domain-models.md applies)
    public Boolean Equals({ModelName}? other) { ... }

    // 4. GetHashCode override (only when a case of domain-models.md applies)
    public override Int32 GetHashCode() { ... }

    // 5. ToString override with StringBuilder (only when a case of domain-models.md applies)
    public override String ToString() { ... }
}
```

## Steps

1. **Create file** at `src/{ProjectName}.Domain/{Feature}/{ModelName}.cs`

2. **Add required usings**:

   ```csharp
   using System.ComponentModel.DataAnnotations;
   using System.Numerics; // Only with the IEqualityOperators fallback.
   using System.Text; // Only when you override ToString.
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

5. **Keep the generated `Equals`, `GetHashCode`, and `ToString` of the record**, unless a case in [domain-models.md](../dotnet-conventions/domain-models.md) ("When to override") applies. The generated equality compares strings with ordinal, case-sensitive rules. If a model needs another comparison, that is the "explicitly asks" case of `domain-models.md`, and you override `Equals` and `GetHashCode` explicitly. If a case applies, override `Equals` and `GetHashCode` together with the same field set and comparers, and build `ToString()` with `StringBuilder`.

6. **Create unit tests** extending `BaseEqualityMemberTests<T>` (see create-tests skill)

## Example

```csharp
// Copyright (c) Vasily Vasilyev

using System.ComponentModel.DataAnnotations;
using {ProjectNamespace}.Common.Assertions;
using {ProjectNamespace}.Common;

namespace {ProjectNamespace}.Domain.{Feature};

/// <summary>
/// Represents an order item that was successfully cancelled.
/// </summary>
public sealed record CancelledOrderItem : IStaticEquatable<CancelledOrderItem>
{
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
}
```

## Validation Rules

- Constructor parameters must validate all inputs
- Use `ThrowIfNull()` not null-coalescing for explicit errors
- If you override `Equals`, `GetHashCode` must use the same field set
- If you override `ToString`, it must include all fields, for debugging. For each field with sensitive information, write the erased placeholder as its value (see [Sensitive Information](#sensitive-information))

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
