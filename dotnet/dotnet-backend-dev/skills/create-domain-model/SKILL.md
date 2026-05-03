---
name: create-domain-model
description: Create domain models as sealed records with equality members and validation. Use when creating domain entities in any .NET project. Triggers on requests like "create domain model", "add domain record", "new entity in Domain layer".
---

# Create Domain Model

Create domain models in your domain project (e.g., `src/{ProjectName}.Domain`) following project conventions.

## Structure

Domain models are `sealed record` types implementing `IStaticEquatable<T>` (a framework-internal marker — substitute `IEquatable<T>` if your project does not provide it):

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

5. **Override Equals** (REQUIRED when model has collections or computed properties):
   - Use only identity fields for comparison
   - Handle null and reference equality first
   - Use `DefaultStringComparer` for string comparisons - choose based on domain:
     - `StringComparer.OrdinalIgnoreCase` for case-insensitive (most common)
     - `StringComparer.Ordinal` for case-sensitive when domain requires exact matching

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
/// Represents a provisioned cloud resource that was successfully deleted.
/// </summary>
public sealed record DeletedProvisionedResource : IStaticEquatable<DeletedProvisionedResource>
{
    private static StringComparer DefaultStringComparer => StringComparer.OrdinalIgnoreCase;

    /// <summary>
    /// The type of the deleted resource.
    /// </summary>
    [Required]
    public ProvisionedResourceType ResourceType { get; init; }

    /// <summary>
    /// The unique identifier of the deleted resource.
    /// </summary>
    [Required]
    public String ResourceId { get; init; }

    /// <summary>
    /// Initializes a new instance of the <see cref="DeletedProvisionedResource"/> class.
    /// </summary>
    /// <param name="resourceType">The type of the deleted resource.</param>
    /// <param name="resourceId">The unique identifier of the deleted resource.</param>
    /// <exception cref="ArgumentOutOfRangeException">
    /// <paramref name="resourceType"/> is not a valid <see cref="ProvisionedResourceType"/> value.
    /// </exception>
    /// <exception cref="ArgumentException">
    /// <paramref name="resourceId"/> is <see langword="null"/>, empty, or whitespace.
    /// </exception>
    public DeletedProvisionedResource(
        ProvisionedResourceType resourceType,
        String resourceId)
    {
        ResourceType = resourceType.ThrowIfUndefined();
        ResourceId = resourceId.ThrowIfNullOrWhiteSpace();
    }

    public Boolean Equals(DeletedProvisionedResource? other)
    {
        if (other is null)
            return false;
        if (ReferenceEquals(this, other))
            return true;

        return ResourceType == other.ResourceType
            && DefaultStringComparer.Equals(ResourceId, other.ResourceId);
    }

    public override Int32 GetHashCode()
    {
        return HashCode.Combine(ResourceType, DefaultStringComparer.GetHashCode(ResourceId));
    }

    public override String ToString()
    {
        var sb = new StringBuilder(capacity: 128)
            .Append(nameof(DeletedProvisionedResource))
            .Append(" {")
            .Append(" ResourceType = ").Append(ResourceType)
            .Append(", ResourceId = ").Append(ResourceId)
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
- **Exposing sensitive data in ToString()** - use erased placeholder instead

## Tests

Create unit tests for domain models following project conventions.

**See the [create-tests](../create-tests/SKILL.md) skill for complete unit and integration testing guidance.**
