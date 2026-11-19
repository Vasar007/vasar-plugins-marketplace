# Exception Tests - BaseExceptionTests\<T\>

Use `BaseExceptionTests<T>` for testing custom exception classes to ensure they follow standard exception patterns.

## Contents

- Base Class
- Required Overrides
- Provided Tests
- Complete Example
- Additional Tests to Add
- Key Points

The code examples in this file use NUnit and FluentAssertions. With another test framework or assertion library, use its equivalent attributes and calls.

## Base Class

Location: `MyApp.Framework.Tests.ForTests.BaseExceptionTests<T>`

Inherits from: `BaseTest`

## Required Overrides

```csharp
// Create exception using default constructor
protected abstract TException Create();

// Create exception with message
protected abstract TException Create(String? message);

// Create exception with message and inner exception
protected abstract TException Create(String? message, Exception? inner);
```

## Provided Tests

The base class automatically tests:

- Exception inherits from `Exception`
- Default constructor creates valid exception
- Message constructor sets message correctly
- Message + inner exception constructor sets both properties
- Null message handling
- Empty message handling
- Null inner exception handling

## Complete Example

### Base Class Definition

```csharp
// Copyright (c) Vasily Vasilyev

namespace MyApp.Framework.Tests.ForTests;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public abstract class BaseExceptionTests<TException> : BaseTest
    where TException : Exception
{
    protected BaseExceptionTests()
    {
    }

    [Test]
    public void CustomException_ShouldInheritFrom_Exception()
    {
        // Arrange & Act.
        var ex = Create();

        // Assert.
        ex.Should().BeAssignableTo<Exception>();
    }

    [Test]
    public void DefaultConstructor_CreatesException()
    {
        // Arrange & Act.
        var ex = Create();

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().NotBeNull();
    }

    [Test]
    public void Constructor_WithMessage_SetsMessage()
    {
        // Arrange.
        var expectedMessage = "Error occurred";

        // Act.
        var ex = Create(expectedMessage);

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().Be(expectedMessage);
    }

    [Test]
    public void Constructor_WithMessageAndInnerException_SetsProperties()
    {
        // Arrange.
        var expectedMessage = "Error occurred";
        var inner = new InvalidOperationException("inner exception");

        // Act.
        var ex = Create(expectedMessage, inner);

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().Be(expectedMessage);
        ex.InnerException.Should().Be(inner);
    }

    [Test]
    public void Constructor_WithNullMessage_SetsNullMessage()
    {
        // Arrange.
        String? expectedMessage = null;

        // Act.
        var ex = Create(expectedMessage);

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().NotBeNull(); // Exception always has a message, even if null is passed
    }

    [Test]
    public void Constructor_WithEmptyMessage_SetsEmptyMessage()
    {
        // Arrange.
        var expectedMessage = String.Empty;

        // Act.
        var ex = Create(expectedMessage);

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().Be(expectedMessage);
    }

    [Test]
    public void Constructor_WithNullInnerException_SetsNullInnerException()
    {
        // Arrange.
        var expectedMessage = "Error occurred";
        Exception? inner = null;

        // Act.
        var ex = Create(expectedMessage, inner);

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().Be(expectedMessage);
        ex.InnerException.Should().BeNull();
    }

    protected abstract TException Create();
    protected abstract TException Create(String? message);
    protected abstract TException Create(String? message, Exception? inner);
}
```

### Test Implementation

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.Framework.Basic.Strings;
using MyApp.Framework.Domain.Exceptions;
using MyApp.Framework.Properties;

namespace MyApp.Framework.Tests.Domain.Exceptions;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class MissingOutputExceptionTests : BaseExceptionTests<MissingOutputException>
{
    public MissingOutputExceptionTests()
    {
    }

    [Test]
    public void Create_WithIdOrName_ReturnsExceptionWithFormattedMessage()
    {
        // Arrange.
        var expectedEntityId = "entity-123";
        var expectedMessage = SharedStringResources.MissingOutputMessage.SafeFormat(expectedEntityId);

        // Act.
        var ex = MissingOutputException.Create(expectedEntityId);

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().Be(expectedMessage);
    }

    [Test]
    public void Create_WithIdOrNameAndInnerException_ReturnsExceptionWithInnerException()
    {
        // Arrange.
        var expectedEntityId = "entity-456";
        var expectedMessage = SharedStringResources.MissingOutputMessage.SafeFormat(expectedEntityId);

        // Act.
        var inner = new Exception("inner");
        var ex = MissingOutputException.Create(expectedEntityId, inner);

        // Assert.
        ex.Should().NotBeNull();
        ex.Message.Should().Be(expectedMessage);
        ex.InnerException.Should().BeSameAs(inner);
    }

    protected override MissingOutputException Create()
    {
        return new MissingOutputException();
    }

    protected override MissingOutputException Create(String? message)
    {
        return new MissingOutputException(message);
    }

    protected override MissingOutputException Create(String? message, Exception? inner)
    {
        return new MissingOutputException(message, inner);
    }
}
```

## Additional Tests to Add

Beyond the base class tests, add tests for:

### Static Factory Methods

If your exception has static `Create()` factory methods:

```csharp
[Test]
public void Create_WithEntityId_ReturnsExceptionWithFormattedMessage()
{
    // Arrange.
    var entityId = "entity-123";
    var expectedMessage = StringResources.MyExceptionMessage.SafeFormat(entityId);

    // Act.
    var ex = MyException.Create(entityId);

    // Assert.
    ex.Should().NotBeNull();
    ex.Message.Should().Be(expectedMessage);
}

[Test]
public void Create_WithEntityIdAndInnerException_SetsInnerException()
{
    // Arrange.
    var entityId = "entity-456";
    var inner = new Exception("inner");

    // Act.
    var ex = MyException.Create(entityId, inner);

    // Assert.
    ex.InnerException.Should().BeSameAs(inner);
}
```

### Custom Properties

If your exception has additional properties:

```csharp
[Test]
public void Constructor_SetsEntityId()
{
    // Arrange.
    var expectedEntityId = "entity-123";

    // Act.
    var ex = new MyException(expectedEntityId, "message");

    // Assert.
    ex.EntityId.Should().Be(expectedEntityId);
}
```

## Key Points

1. **Implement all Create overrides**: default, message-only, and message+inner

2. **Test factory methods separately**: test each static `Create()` factory method of your exception

3. **Use StringResources**: exception messages must use localized resources

4. **Test custom properties**: test each property that your exception has in addition to the message and the inner exception

5. **Do not repeat base tests**: the base class covers the standard exception patterns
