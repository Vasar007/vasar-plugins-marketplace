---
name: generate-xml-docs
description: Generate XML documentation comments for C# types, members, and parameters.
when_to_use: Use it for missing XML docs, and for "add XML docs", "document this class", or "add XML comments".
---

# Generate XML Documentation

Generate XML documentation for C# types, methods, properties, and parameters following standard conventions.

The examples guard parameters with the fluent extension style of a shared guard library, for example `request.ThrowIfNull()`. The same documentation rules apply to the guards of the .NET base library, such as `ArgumentNullException.ThrowIfNull(request)`.

## Required Documentation

**All public, protected, and internal types, methods, and properties must have XML documentation** (except tests).

This includes:

- Classes, interfaces, structs, enums
- Constructors, methods, properties
- Parameters, return values, exceptions
- Generic type parameters

## Structure

```csharp
/// <summary>
/// Brief description of what this type/member does.
/// </summary>
/// <remarks>
/// Additional details, usage notes, or important information.
/// Use this for comments from the method header or type declaration.
/// </remarks>
/// <param name="parameterName">Description of the parameter.</param>
/// <typeparam name="T">Description of the generic type parameter.</typeparam>
/// <returns>Description of the return value.</returns>
/// <exception cref="ExceptionType">
/// Condition when this exception is thrown.
/// </exception>
public ReturnType MethodName<T>(Type parameterName)
{
    // Implementation
}
```

## Exception Documentation Formats

### ArgumentNullException (ThrowIfNull)

**1 parameter:**

```xml
<exception cref="ArgumentNullException">
<paramref name="value" /> is <see langword="null" />.
</exception>
```

**2+ parameters:**

```xml
<exception cref="ArgumentNullException">
<paramref name="value1" /> is <see langword="null" />. -or-
<paramref name="value2" /> is <see langword="null" />.
</exception>
```

### ArgumentException for Empty Strings (ThrowIfNullOrEmpty)

Use ArgumentNullException format PLUS:

**1 parameter:**

```xml
<exception cref="ArgumentException">
<paramref name="value" /> presents empty string.
</exception>
```

**2+ parameters:**

```xml
<exception cref="ArgumentException">
<paramref name="value1" /> presents empty string. -or-
<paramref name="value2" /> presents empty string.
</exception>
```

### ArgumentException for Whitespace (ThrowIfNullOrWhiteSpace)

Use ArgumentNullException format PLUS:

**1 parameter:**

```xml
<exception cref="ArgumentException">
<paramref name="value" /> presents empty string or contains only whitespaces.
</exception>
```

**2+ parameters:**

```xml
<exception cref="ArgumentException">
<paramref name="value1" /> presents empty string or contains only whitespaces. -or-
<paramref name="value2" /> presents empty string or contains only whitespaces.
</exception>
```

### ArgumentException for Empty GUIDs (ThrowIfEmpty)

**1 parameter:**

```xml
<exception cref="ArgumentException">
<paramref name="id" /> presents empty <see cref="Guid"/>.
</exception>
```

**2+ parameters:**

```xml
<exception cref="ArgumentException">
<paramref name="id1" /> presents empty <see cref="Guid"/>. -or-
<paramref name="id2" /> presents empty <see cref="Guid"/>.
</exception>
```

### ArgumentException for Empty Collections (ThrowIfNullOrEmpty/ThrowIfEmpty)

Use ArgumentNullException format PLUS:

**1 parameter:**

```xml
<exception cref="ArgumentException">
<paramref name="items" /> presents empty collection.
</exception>
```

**2+ parameters:**

```xml
<exception cref="ArgumentException">
<paramref name="items1" /> presents empty collection. -or-
<paramref name="items2" /> presents empty collection.
</exception>
```

## CancellationToken Documentation

For `CancellationToken` parameters:

```xml
<param name="cancellationToken">A cancellation token that can be used by other objects or threads to receive notice of cancellation.</param>
```

If method uses the token (calls `ThrowIfCancellationRequested()`):

```xml
<exception cref="OperationCanceledException">The token has had cancellation requested.</exception>
```

## Special Keywords

Use `<see langword="..."/>` for language keywords:

- `<see langword="null"/>` for null
- `<see langword="true"/>` for true
- `<see langword="false"/>` for false

## Example: Method with Full Documentation

```csharp
/// <summary>
/// Creates a new order with the specified items.
/// </summary>
/// <remarks>
/// This operation is asynchronous and tracked via a session-like handle.
/// </remarks>
/// <param name="request">The request containing order contents and metadata.</param>
/// <param name="cancellationToken">A cancellation token that can be used by other objects or threads to receive notice of cancellation.</param>
/// <returns>A session response containing the session ID for tracking the operation.</returns>
/// <exception cref="ArgumentNullException">
/// <paramref name="request" /> is <see langword="null" />.
/// </exception>
/// <exception cref="OperationCanceledException">The token has had cancellation requested.</exception>
public async Task<SessionResponse> CreateOrderAsync(
    OrderCreateRequest request,
    CancellationToken cancellationToken = default)
{
    request.ThrowIfNull();
    cancellationToken.ThrowIfCancellationRequested();

    // Implementation
}
```

## Example: Constructor Documentation

```csharp
/// <summary>
/// Initializes a new instance of the <see cref="OrderService"/> class.
/// </summary>
/// <param name="orderRepository">The repository for order persistence.</param>
/// <param name="sessionRepository">The repository for session persistence.</param>
/// <param name="logger">The logger for diagnostic logging.</param>
/// <exception cref="ArgumentNullException">
/// <paramref name="orderRepository" /> is <see langword="null" />. -or-
/// <paramref name="sessionRepository" /> is <see langword="null" />. -or-
/// <paramref name="logger" /> is <see langword="null" />.
/// </exception>
public OrderService(
    IOrderRepository orderRepository,
    ISessionRepository sessionRepository,
    ILogger<OrderService> logger)
{
    _orderRepository = orderRepository.ThrowIfNull();
    _sessionRepository = sessionRepository.ThrowIfNull();
    _logger = logger.ThrowIfNull();
}
```

## Example: Property Documentation

```csharp
/// <summary>
/// Gets the unique identifier for the order.
/// </summary>
[Required]
public OrderId Id { get; init; }

/// <summary>
/// Gets the current processing status of the order.
/// </summary>
/// <remarks>
/// Status transitions follow the order lifecycle state machine.
/// </remarks>
public OrderStatus Status { get; init; }
```

## Example: Type Documentation

```csharp
/// <summary>
/// Represents an order placed in the system.
/// </summary>
/// <remarks>
/// An order is a logical grouping of line items owned by a single customer.
/// </remarks>
public sealed record Order : IEquatable<Order>
{
    // Members
}
```

## Remarks Section Usage

Use `<remarks>` for:

- Additional context or usage notes
- Important warnings or constraints
- Comments from the method/type header (non-body comments)
- State machine or workflow information
- Performance considerations

## Key Rules

1. **All public and protected members, and all internal types, methods, and properties, need XML docs** (except tests)
2. **Document exceptions based on validation** in method body
3. **Use standard formats** for common validation exceptions
4. **Include CancellationToken docs**: if a method has a `CancellationToken` parameter, document it with the standard text
5. **Use `<see langword="..."/>` for keywords** (null, true, false)
6. **Put header comments in `<remarks>`** section
7. **Be concise but complete**: describe what, not how
8. **Use proper grammar**: capitalize, punctuate correctly
9. **Do not delete any constants, fields, methods, or properties**: only add or edit documentation. Fix or replace invalid or incorrect existing XML docs.
10. **Search for examples**: if you find no specific rule, search the project for similar classes and follow their documentation patterns

## Checklist

Build the changed projects with `-p:GenerateDocumentationFile=true` (see `dev-essentials:dotnet-build-test`). Find the CS1591 warnings for the files that you changed. Add the missing docs and build again until none is left for these files. The option is for this build only. Do not add it to a project file. CS1591 covers only members that are visible outside the assembly, so the checklist below stays the test for internal members (rule 1 of Key Rules).

- [ ] Type has `<summary>` describing its purpose
- [ ] All public, protected, and internal methods have `<summary>`
- [ ] All parameters documented with `<param>`
- [ ] Return values documented with `<returns>`
- [ ] Generic type parameters documented with `<typeparam>`
- [ ] Exceptions documented based on validation in method body
- [ ] CancellationToken has standard description
- [ ] `OperationCanceledException` documented for a method that uses the token
- [ ] Used `<see langword="null"/>` for null references
- [ ] Header comments moved to `<remarks>` section
- [ ] Follows standard exception formats
