# Configuration Options Tests - BaseValidatableObjectTests

Use `BaseValidatableObjectTests` for testing configuration option classes that implement `IValidatableObject`.

The code examples in this file use NUnit and FluentAssertions. With another test framework or assertion library, use its equivalent attributes and calls.

## Base Class

Location: `MyApp.OnlyForTests.Basic.Validation.BaseValidatableObjectTests`

Provides assertion helpers for validation results.

## Required Pattern

Every test class for configuration options must:

1. Inherit from `BaseValidatableObjectTests`
2. Implement `CreateDefaultOptions()` - creates options with default/empty values
3. Implement `CreateValidOptions()` - creates fully valid options
4. Test validation behavior for each property

## Available Assertion Methods

```csharp
// Single field validation failure
protected void VerifyResultOfFailedValidation(
    IEnumerable<ValidationResult> results,
    String memberName);

// Multiple field validation failures
protected void VerifyResultOfFailedValidationForSeveral(
    IEnumerable<ValidationResult> results,
    params String[] memberNames);

// Successful validation (no errors)
protected void VerifyResultOfSuccessfulValidation(
    IEnumerable<ValidationResult> results);
```

## Complete Example

```csharp
// Copyright (c) Vasily Vasilyev

using System.ComponentModel.DataAnnotations;
using MyApp.Configuration.Options.Shop;
using MyApp.OnlyForTests.Basic.Validation;

namespace MyApp.Configuration.Tests.Options.Shop;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class ShopOptionsTests : BaseValidatableObjectTests
{
    public ShopOptionsTests()
    {
    }

    [Test]
    public void Validate_WithNullValidationContext_ThrowsArgumentNullException()
    {
        // Arrange.
        var options = CreateDefaultOptions();
        ValidationContext? validationContext = null;

        var act = () => options.Validate(validationContext!);

        // Act & Assert.
        act.Should().Throw<ArgumentNullException>();
    }

    [Test]
    public void Validate_WithDefaultOptions_ReturnsValidationErrorsForRequiredFields()
    {
        // Arrange.
        var options = CreateDefaultOptions();
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfFailedValidationForSeveral(
            results,
            nameof(ShopOptions.Shipping.PrimaryCarrier.CarrierCode),
            nameof(ShopOptions.Billing.CurrencyCode),
            nameof(ShopOptions.Notifications.SenderAddress),
            nameof(ShopOptions.Notifications.TemplateName)
        );
    }

    [Test]
    public void Validate_WithValidOptions_ReturnsNoValidationErrors()
    {
        // Arrange.
        var options = CreateValidOptions();
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfSuccessfulValidation(results);
    }

    [Test]
    public void Validate_WithNullShipping_ReturnsValidationError()
    {
        // Arrange.
        var validOptions = CreateValidOptions();
        var options = validOptions with
        {
            Shipping = null!,
        };
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfFailedValidation(results, nameof(ShopOptions.Shipping));
    }

    [Test]
    public void Validate_WithNullBilling_ReturnsValidationError()
    {
        // Arrange.
        var validOptions = CreateValidOptions();
        var options = validOptions with
        {
            Billing = null!,
        };
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfFailedValidation(results, nameof(ShopOptions.Billing));
    }

    [TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]
    public void Validate_WithInvalidCarrierCode_ReturnsValidationError(String? invalidValue)
    {
        // Arrange.
        var validOptions = CreateValidOptions();
        var options = validOptions with
        {
            Shipping = validOptions.Shipping with
            {
                PrimaryCarrier = validOptions.Shipping.PrimaryCarrier with
                {
                    CarrierCode = invalidValue,
                },
            },
        };
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfFailedValidation(
            results,
            nameof(ShopOptions.Shipping.PrimaryCarrier.CarrierCode)
        );
    }

    private static ShopOptions CreateDefaultOptions()
    {
        return new ShopOptions();
    }

    private static ShopOptions CreateValidOptions()
    {
        return new ShopOptions
        {
            Shipping = new ShippingOptions
            {
                PrimaryCarrier = new PrimaryCarrierOptions
                {
                    CarrierCode = "primary-carrier",
                    ServiceLevel = "standard",
                },
                FallbackCarrier = new FallbackCarrierOptions
                {
                    CarrierCode = "fallback-carrier",
                    ServiceLevel = "economy",
                },
            },
            Billing = new BillingOptions
            {
                CurrencyCode = "USD",
            },
            Notifications = new NotificationOptions
            {
                SenderAddress = "orders@example.com",
                TemplateName = "order-confirmation",
            },
        };
    }
}
```

## Standard Tests to Include

1. **Null ValidationContext**: `Validate` throws `ArgumentNullException`

2. **Default options**: `Validate` returns errors for all required fields

3. **Valid options**: `Validate` returns no errors

4. **Individual null properties**: a null value in a required nested object gives a validation error

5. **String validation**: Use `StringNullOrWhiteSpace_TestCases` for required string properties

## Nested Options Pattern

For hierarchical configuration (options containing options):

```csharp
// Test parent's validation of nested options
[Test]
public void Validate_WithNullNestedOptions_ReturnsValidationError()
{
    // Arrange.
    var validOptions = CreateValidOptions();
    var options = validOptions with { NestedOptions = null! };
    var validationContext = new ValidationContext(options);

    // Act.
    var results = options.Validate(validationContext);

    // Assert.
    VerifyResultOfFailedValidation(results, nameof(ParentOptions.NestedOptions));
}

// Create separate test class for nested options
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class NestedOptionsTests : BaseValidatableObjectTests
{
    // Test nested options independently
}
```

## Key Points

1. **CreateDefaultOptions**: Use default constructor or `new T()` to get empty/default state

2. **CreateValidOptions**: Provide all required values to pass validation

3. **Use `with` expressions**: Cleanly create invalid variants from valid options

4. **Test each required property**: Null check for objects, `StringNullOrWhiteSpace_TestCases` for strings

5. **Nameof for member names**: the compiler finds a wrong property name
