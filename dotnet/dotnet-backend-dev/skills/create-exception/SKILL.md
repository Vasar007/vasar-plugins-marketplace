---
name: create-exception
description: Create custom exception classes with standard constructors and optional factory methods. Use when implementing domain-specific exceptions in any .NET project. Triggers on requests like "create exception", "add custom exception", "new exception class", "implement exception type".
---

# Create Custom Exception

Create custom exception classes in `{ProjectNamespace}.Domain` for domain-specific error conditions.

## Structure

Custom exceptions inherit from `Exception` (or another appropriate base exception):

```csharp
public class {ExceptionName}Exception : Exception
{
    // 3 standard constructors
    
    // Optional: Static factory methods
}
```

**Optional: Use `sealed`** if the exception will not be further inherited.

## Required Constructors

ALL custom exceptions MUST implement 3 standard constructors:

1. **Parameterless constructor**
2. **Constructor with message**
3. **Constructor with message and inner exception**

```csharp
/// <summary>
/// Initializes a new instance of the <see cref="{ExceptionName}Exception"/> class.
/// </summary>
public {ExceptionName}Exception()
{
}

/// <summary>
/// Initializes a new instance of the <see cref="{ExceptionName}Exception"/> class with a specified error message.
/// </summary>
/// <param name="message">The error message that explains the reason for the exception.</param>
public {ExceptionName}Exception(
    String? message)
    : base(message)
{
}

/// <summary>
/// Initializes a new instance of the <see cref="{ExceptionName}Exception"/> class with a specified error message and a reference to the inner exception that is the cause of this exception.
/// </summary>
/// <param name="message">The error message that explains the reason for the exception.</param>
/// <param name="innerException">The exception that is the cause of the current exception, or <see langword="null"/> if not specified.</param>
public {ExceptionName}Exception(
    String? message,
    Exception? innerException)
    : base(message, innerException)
{
}
```

## File Location

Place custom exceptions in `src/{ProjectName}.Domain/Exceptions/` or within the relevant feature folder:

- `Domain/Exceptions/` for general domain exceptions
- `Domain/{Feature}/Exceptions/` for feature-specific exceptions

## Example: Complete Exception Class

```csharp
// Copyright (c) Vasily Vasilyev

using {ProjectNamespace}.Common.Assertions;
using {ProjectNamespace}.Common.Strings;
using {ProjectNamespace}.Resources.Properties;

namespace {ProjectNamespace}.Domain.Exceptions;

/// <summary>
/// Represents an exception that is thrown when the expected output for an entity or resource is missing.
/// </summary>
/// <remarks>
/// This exception is typically used to indicate that a requested output or result could not be found or generated.
/// </remarks>
public class MissingOutputException : Exception
{
    /// <summary>
    /// Initializes a new instance of the <see cref="MissingOutputException"/> class.
    /// </summary>
    public MissingOutputException()
    {
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="MissingOutputException"/> class with a specified error message.
    /// </summary>
    /// <param name="message">The error message that explains the reason for the exception.</param>
    public MissingOutputException(
        String? message)
        : base(message)
    {
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="MissingOutputException"/> class with a specified error message and a reference to the inner exception that is the cause of this exception.
    /// </summary>
    /// <param name="message">The error message that explains the reason for the exception.</param>
    /// <param name="innerException">The exception that is the cause of the current exception, or <see langword="null"/> if not specified.</param>
    public MissingOutputException(
        String? message,
        Exception? innerException)
        : base(message, innerException)
    {
    }

    /// <summary>
    /// Creates a new <see cref="MissingOutputException"/> for the specified entity information.
    /// </summary>
    /// <typeparam name="T">The type of the entity information.</typeparam>
    /// <param name="entityInfo">The information about the entity for which output is missing.</param>
    /// <param name="innerException">The exception that is the cause of the current exception, or <see langword="null"/> if not specified.</param>
    /// <returns>A new <see cref="MissingOutputException"/> instance with a formatted missing output message.</returns>
    /// <exception cref="ArgumentNullException">
    /// <paramref name="entityInfo" /> is <see langword="null" />.
    /// </exception>
    public static MissingOutputException Create<T>(
        T entityInfo,
        Exception? innerException = null)
    {
        entityInfo.ThrowIfNullValue();

        var missingOutputMessage = StringResources.MissingOutputMessage.SafeFormat(entityInfo);
        return new MissingOutputException(missingOutputMessage, innerException);
    }
}
```

## Static Factory Methods (Optional)

Add static factory methods when:

- Exception requires complex initialization
- Message formatting uses StringResources
- Need to construct exception with specific entity context

```csharp
/// <summary>
/// Creates a new exception for the specified entity.
/// </summary>
/// <param name="entityId">The identifier of the entity.</param>
/// <param name="innerException">The exception that is the cause of the current exception, or <see langword="null"/> if not specified.</param>
/// <returns>A new exception instance with formatted message.</returns>
/// <exception cref="ArgumentNullException">
/// <paramref name="entityId" /> is <see langword="null" />.
/// </exception>
public static {ExceptionName}Exception Create(
    EntityId entityId,
    Exception? innerException = null)
{
    entityId.ThrowIfNull();
    
    var message = StringResources.SomeErrorMessage.SafeFormat(entityId);
    return new {ExceptionName}Exception(message, innerException);
}
```

## User-Facing Messages

**ALL exception messages MUST use StringResources** with `[TBD]` prefix:

```csharp
// In StringResources.resx
[TBD] Missing output for {0}

// In exception class
var message = StringResources.MissingOutputMessage.SafeFormat(entityInfo);
```

**See the [create-string-resource](../create-string-resource/SKILL.md) skill for string resource management.**

## XML Documentation

ALL exceptions require comprehensive XML documentation:

- Class-level `<summary>` and `<remarks>`
- Constructor documentation
- Factory method documentation with `<typeparam>`, `<param>`, `<returns>`, `<exception>`

**See the `dev-essentials:generate-xml-docs` skill for XML documentation patterns.**

## Tests

Create exception tests extending `BaseExceptionTests<T>`.

**See the [create-tests](../create-tests/SKILL.md) skill for complete testing guidance.**

## Key Rules

1. **3 standard constructors required** (parameterless, message, message+inner)
2. **Inherit from `Exception`** (or appropriate base like `ArgumentException`)
3. **Optional `sealed`** if no further inheritance needed
4. **XML documentation required** on all public members
5. **Use StringResources** for user-facing messages with `[TBD]` prefix
6. **Static factory methods** for complex construction or formatting
7. **Validate parameters** in factory methods (use `ThrowIfNull()`, etc.)
8. **File location**: `Domain/Exceptions/` or `Domain/{Feature}/Exceptions/`

## Common Exception Patterns

### Domain Business Rule Violation

```csharp
public class InvalidTenantStateException : Exception
{
    // 3 standard constructors
    
    public static InvalidTenantStateException Create(
        TenantStatus currentStatus,
        TenantStatus expectedStatus)
    {
        var message = StringResources.InvalidTenantStateMessage.SafeFormat(currentStatus, expectedStatus);
        return new InvalidTenantStateException(message);
    }
}
```

### Resource Not Found

```csharp
public class TenantNotFoundException : Exception
{
    // 3 standard constructors
    
    public static TenantNotFoundException Create(TenantId tenantId)
    {
        tenantId.ThrowIfNull();
        
        var message = StringResources.TenantNotFoundMessage.SafeFormat(tenantId);
        return new TenantNotFoundException(message);
    }
}
```

### Operation Not Supported

```csharp
public class UnsupportedOperationException : Exception
{
    // 3 standard constructors
    
    public static UnsupportedOperationException Create(String operationName)
    {
        operationName.ThrowIfNullOrWhiteSpace();
        
        var message = StringResources.UnsupportedOperationMessage.SafeFormat(operationName);
        return new UnsupportedOperationException(message);
    }
}
```

## Checklist

- [ ] Class name ends with "Exception"
- [ ] 3 standard constructors implemented
- [ ] XML documentation on class and all constructors
- [ ] Factory methods have parameter validation
- [ ] Factory methods use StringResources with `[TBD]` prefix
- [ ] Factory methods documented with XML comments
- [ ] File located in `Domain/Exceptions/` or feature folder
- [ ] Tests created extending `BaseExceptionTests<T>`
