# Primitive Wrapper Tests Pattern

Tests for primitive wrappers (string/GUID/integer IDs and value objects) using base wrapper test classes from `MyApp.OnlyForTests.Basic.Wrappers`.

The code examples in this file use NUnit and FluentAssertions. With another test framework or assertion library, use its equivalent attributes and calls.

## Base Classes Available

| Base Class                    | Use For                                          |
|-------------------------------|--------------------------------------------------|
| `BaseStringWrapperTests<T>`   | String-based wrappers (IStringWrapper\<T\>)      |
| `BaseGuidWrapperTests<T>`     | GUID-based wrappers (IGuidWrapper\<T\>)          |
| `BaseInt32WrapperTests<T>`    | Integer-based wrappers (IInt32Wrapper\<T\>)      |
| `BaseInt64WrapperTests<T>`    | Long integer-based wrappers (IInt64Wrapper\<T\>) |
| `BaseDecimalWrapperTests<T>`  | Decimal-based wrappers (IDecimalWrapper\<T\>)    |

The project provides runtime wrapper interfaces in `MyApp.Framework.Basic.Wrappers` and corresponding base test classes in `MyApp.OnlyForTests.Basic.Wrappers` to simplify testing.

- `IStringWrapper<T>`: use `BaseStringWrapperTests<T>` for testing string-based wrappers
- `IGuidWrapper<T>`: use `BaseGuidWrapperTests<T>` for testing GUID-based wrappers
- `IInt32Wrapper<T>`: use `BaseInt32WrapperTests<T>` for testing integer-based wrappers
- `IInt64Wrapper<T>`, `IDecimalWrapper<T>`, `IDateTimeWrapper<T>`: use the corresponding base test classes where available

If no matching interface exists for your domain wrapper (for example, a bespoke value object without `IStringWrapper<T>`), implement the same test pattern manually: exercise Empty/IsEmpty, `FromValue` factory, equality/ordering, `ToString`, and validation checks rather than inheriting from a base test class.

**Wrapper interfaces** (from `MyApp.Framework.Basic.Wrappers`):

- `IStringWrapper<T>` for string-based IDs
- `IGuidWrapper<T>` for GUID-based IDs
- `IInt32Wrapper<T>` for integer-based IDs
- `IInt64Wrapper<T>`, `IDecimalWrapper<T>`, `IDateTimeWrapper<T>`, and others

## GUID Wrapper Pattern

**Simplest case**: override only `CreateNewWrapperValue()`:

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.OnlyForTests.Basic.Wrappers;
using MyApp.Domain.Sessions;
using MyApp.Tests.Common.Helpers.Generators.Domain.Sessions;

namespace MyApp.Domain.Tests.Sessions;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class SessionIdTests : BaseGuidWrapperTests<SessionId>
{
    private readonly SessionGenerator _generator;

    public SessionIdTests()
    {
        _generator = SessionGenerator.Instance;
    }

    protected override SessionId CreateNewWrapperValue()
    {
        return _generator.GenerateSessionId();
    }
}
```

**What BaseGuidWrapperTests provides automatically:**

All tests from parent classes (`BaseValueWrapperTests`, `BaseEqualityMemberTests`), plus:

- `FromValue_ShouldThrow_WhenValueIsEmpty` (rejects `Guid.Empty`)

Inherited from `BaseValueWrapperTests`: Default constructor, CreateNew uniqueness, FromValue/FromCollection, Empty/IsEmpty, ToString

Inherited from `BaseEqualityMemberTests`: Equals (same, identical, different, default/null, different type), GetHashCode (same, identical, different), ToString consistency

## String Wrapper Pattern

### Basic String Wrapper

**For simple string wrappers**, use constructor parameter to specify case sensitivity:

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.OnlyForTests.Basic.Wrappers;
using MyApp.Domain.Sales.Customers;
using MyApp.Tests.Common.Helpers.Generators.Domain.Sales.Customers;

namespace MyApp.Domain.Tests.Sales.Customers;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class CustomerIdTests : BaseStringWrapperTests<CustomerId>
{
    private readonly CustomerGenerator _generator;

    public CustomerIdTests()
        : base(ignoreCase: true)  // Case-insensitive comparison
    {
        _generator = CustomerGenerator.Instance;
    }

    protected override CustomerId CreateNewWrapperValue()
    {
        return _generator.GenerateCustomerId();
    }
}
```

**Constructor parameters:**

- `ignoreCase: true`: for case-insensitive wrappers (most common)
- `ignoreCase: false`: for case-sensitive wrappers
- `conversionType` (optional): applies string conversion before comparison/equality:
  - `StringWrapperConversionType.None` (default): No conversion
  - `StringWrapperConversionType.ToLower`: Converts to lowercase (current culture)
  - `StringWrapperConversionType.ToLowerInvariant`: Converts to lowercase (invariant culture)
  - `StringWrapperConversionType.ToUpper`: Converts to uppercase (current culture)
  - `StringWrapperConversionType.ToUpperInvariant`: Converts to uppercase (invariant culture)
- `validationMode` (optional): controls input validation strictness:
  - `StringWrapperValidationMode.Strict` (default): Rejects null, empty, and whitespace
  - `StringWrapperValidationMode.AllowNull`: Allows null values
  - `StringWrapperValidationMode.AllowEmpty`: Allows empty strings
  - `StringWrapperValidationMode.AllowWhiteSpace`: Allows whitespace-only strings

**Example with conversion:**

```csharp
public MyWrapperIdTests()
    : base(ignoreCase: true, conversionType: StringWrapperConversionType.ToLowerInvariant)
{
    _generator = MyWrapperGenerator.Instance;
}
```

**What BaseStringWrapperTests provides automatically:**

All tests from parent classes (`BaseValueWrapperTests`, `BaseEqualityMemberTests`), plus:

- `FromValue_ShouldThrow_WhenValueIsNull` (skipped for a `validationMode` that allows null)
- `FromValue_ShouldThrow_WhenValueIsEmpty` (skipped for a `validationMode` that allows empty strings)
- `FromValue_ShouldThrow_WhenValueIsWhiteSpace` (skipped for a `validationMode` that allows whitespace)
- `FromValue_AfterConversion_Returns_Wrapper_With_ExpectedValue` (verifies conversion is applied)
- `Equals_Returns_True_For_Same_Value_InDifferentCases` (case-insensitive equality)
- `GetHashCode_Returns_Same_Result_For_Same_Value_InDifferentCases` (case-insensitive hash)

### String Wrapper with IComparable

**For wrappers implementing IComparable** (sorting, comparison operators), add domain-specific tests:

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.Framework.Basic.Strings;
using MyApp.OnlyForTests.Basic.Wrappers;
using MyApp.Domain.Migrations;
using MyApp.Resources.Properties;
using MyApp.Tests.Common.Helpers.Generators.Domain.Migrations;

namespace MyApp.Domain.Tests.Migrations;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class MigrationIdTests : BaseStringWrapperTests<MigrationId>
{
    private readonly MigrationGenerator _generator;

    public MigrationIdTests()
        : base(ignoreCase: false)  // Case-sensitive for migrations
    {
        _generator = new MigrationGenerator();
    }

    protected override MigrationId CreateNewWrapperValue()
    {
        return _generator.GenerateMigrationId();
    }

    private MigrationId CreateMigrationId(String value)
    {
        return _generator.CreateMigrationId(value);
    }

    // Additional tests for IComparable implementation

    [Test]
    public void CompareTo_Returns_Zero_For_Equal_MigrationIds()
    {
        // Arrange.
        var id1 = CreateMigrationId("20250101_AddCustomerFields");
        var id2 = MigrationId.FromValue(id1.Value);

        // Act.
        var result = id1.CompareTo(id2);

        // Assert.
        result.Should().Be(0);
    }

    [Test]
    public void CompareTo_Returns_Negative_When_First_Is_Less()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = earlierId.CompareTo(laterId);

        // Assert.
        result.Should().BeLessThan(0);
    }

    [Test]
    public void CompareTo_Returns_Positive_When_First_Is_Greater()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = laterId.CompareTo(earlierId);

        // Assert.
        result.Should().BeGreaterThan(0);
    }

    [Test]
    public void CompareTo_Object_Returns_Positive_When_Object_Is_Null()
    {
        // Arrange.
        var id = CreateMigrationId("20250101_AddCustomerFields");

        // Act.
        var result = id.CompareTo(null);

        // Assert.
        result.Should().BeGreaterThan(0);
    }

    [Test]
    public void CompareTo_Object_Returns_Correct_Value_When_Object_Is_MigrationId()
    {
        // Arrange.
        var id1 = CreateMigrationId("20250101_AddCustomerFields");
        Object id2 = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = id1.CompareTo(id2);

        // Assert.
        result.Should().BeLessThan(0);
    }

    [Test]
    public void CompareTo_Object_Throws_When_Object_Is_Not_MigrationId()
    {
        // Arrange.
        var id = CreateMigrationId("20250101_AddCustomerFields");
        Object invalidObject = "not a MigrationId";
        var expectedMessage = StringResources.ObjectMustBeOfType.SafeFormat(nameof(MigrationId));

        // Act.
        var act = () => id.CompareTo(invalidObject);

        // Assert.
        act.Should().Throw<ArgumentException>()
            .WithMessage($"{expectedMessage}*");
    }

    [Test]
    public void LessThan_Operator_Returns_True_When_Left_Is_Less()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = earlierId < laterId;

        // Assert.
        result.Should().BeTrue();
    }

    [Test]
    public void LessThan_Operator_Returns_False_When_Left_Is_Greater()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = laterId < earlierId;

        // Assert.
        result.Should().BeFalse();
    }

    [Test]
    public void LessThan_Operator_Returns_False_When_Equal()
    {
        // Arrange.
        var id1 = CreateMigrationId("20250101_AddCustomerFields");
        var id2 = MigrationId.FromValue(id1.Value);

        // Act.
        var result = id1 < id2;

        // Assert.
        result.Should().BeFalse();
    }

    [Test]
    public void LessThanOrEqual_Operator_Returns_True_When_Left_Is_Less()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = earlierId <= laterId;

        // Assert.
        result.Should().BeTrue();
    }

    [Test]
    public void LessThanOrEqual_Operator_Returns_True_When_Equal()
    {
        // Arrange.
        var id1 = CreateMigrationId("20250101_AddCustomerFields");
        var id2 = MigrationId.FromValue(id1.Value);

        // Act.
        var result = id1 <= id2;

        // Assert.
        result.Should().BeTrue();
    }

    [Test]
    public void GreaterThan_Operator_Returns_True_When_Left_Is_Greater()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = laterId > earlierId;

        // Assert.
        result.Should().BeTrue();
    }

    [Test]
    public void GreaterThan_Operator_Returns_False_When_Left_Is_Less()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = earlierId > laterId;

        // Assert.
        result.Should().BeFalse();
    }

    [Test]
    public void GreaterThan_Operator_Returns_False_When_Equal()
    {
        // Arrange.
        var id1 = CreateMigrationId("20250101_AddCustomerFields");
        var id2 = MigrationId.FromValue(id1.Value);

        // Act.
        var result = id1 > id2;

        // Assert.
        result.Should().BeFalse();
    }

    [Test]
    public void GreaterThanOrEqual_Operator_Returns_True_When_Left_Is_Greater()
    {
        // Arrange.
        var earlierId = CreateMigrationId("20250101_AddCustomerFields");
        var laterId = CreateMigrationId("20250102_AddUserFields");

        // Act.
        var result = laterId >= earlierId;

        // Assert.
        result.Should().BeTrue();
    }

    [Test]
    public void GreaterThanOrEqual_Operator_Returns_True_When_Equal()
    {
        // Arrange.
        var id1 = CreateMigrationId("20250101_AddCustomerFields");
        var id2 = MigrationId.FromValue(id1.Value);

        // Act.
        var result = id1 >= id2;

        // Assert.
        result.Should().BeTrue();
    }

    [Test]
    public void MigrationIds_Can_Be_Sorted_Chronologically()
    {
        // Arrange.
        var ids = new List<MigrationId>
        {
            CreateMigrationId("20250105_UpdateSchema"),
            CreateMigrationId("20250101_AddCustomerFields"),
            CreateMigrationId("20250103_AddUserFields"),
            CreateMigrationId("20250102_AddIndexes"),
            CreateMigrationId("20250104_RemoveObsoleteFields"),
        };

        var expected = new List<MigrationId>
        {
            CreateMigrationId("20250101_AddCustomerFields"),
            CreateMigrationId("20250102_AddIndexes"),
            CreateMigrationId("20250103_AddUserFields"),
            CreateMigrationId("20250104_RemoveObsoleteFields"),
            CreateMigrationId("20250105_UpdateSchema"),
        };

        // Act.
        var sorted = ids.OrderBy(x => x).ToList();

        // Assert.
        sorted.Should().Equal(expected);
    }

    [Test]
    public void MigrationIds_With_Same_Date_Are_Sorted_By_Description()
    {
        // Arrange.
        var ids = new List<MigrationId>
        {
            CreateMigrationId("20250101_ZUpdateSchema"),
            CreateMigrationId("20250101_AddCustomerFields"),
            CreateMigrationId("20250101_BAddUserFields"),
        };

        var expected = new List<MigrationId>
        {
            CreateMigrationId("20250101_AddCustomerFields"),
            CreateMigrationId("20250101_BAddUserFields"),
            CreateMigrationId("20250101_ZUpdateSchema"),
        };

        // Act.
        var sorted = ids.OrderBy(x => x).ToList();

        // Assert.
        sorted.Should().Equal(expected);
    }

    [Test]
    public void CompareTo_Handles_Empty_MigrationId()
    {
        // Arrange.
        var emptyId = MigrationId.Empty;
        var validId = CreateMigrationId("20250101_AddCustomerFields");

        // Act.
        var result1 = emptyId.CompareTo(validId);
        var result2 = validId.CompareTo(emptyId);

        // Assert.
        result1.Should().BeLessThan(0);
        result2.Should().BeGreaterThan(0);
    }

    [Test]
    public void Comparison_Is_Case_Sensitive()
    {
        // Arrange.
        var id1 = CreateMigrationId("20250101_addcustomerfields");
        var id2 = CreateMigrationId("20250101_AddCustomerFields");

        // Act.
        var result = id1.CompareTo(id2);

        // Assert.
        result.Should().NotBe(0);
    }
}
```

## Key Points

1. **Always use test generators**: never create wrapper values inline

2. **Choose the correct base class** for the wrapper type (string, GUID, int, and so on)

3. **Specify ignoreCase** for string wrappers in constructor:
   - `ignoreCase: true` for case-insensitive (most IDs)
   - `ignoreCase: false` for case-sensitive IDs (for example migrations)

4. **Add domain-specific tests** for:
   - Custom helper methods (for example `IsType` and `TryGetType`)
   - IComparable implementation (CompareTo, operators)
   - Sorting behavior
   - Edge cases specific to domain rules

5. **Base classes cover the standard tests**: do not repeat these:
   - Empty/IsEmpty
   - FromValue factory
   - Equals/GetHashCode
   - ToString
   - Value validation

6. **Follow naming convention**: `{WrapperName}Tests`
