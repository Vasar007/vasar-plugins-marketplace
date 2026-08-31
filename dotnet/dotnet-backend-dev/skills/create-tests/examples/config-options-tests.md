# Configuration Options Tests - BaseValidatableObjectTests

Use `BaseValidatableObjectTests` for testing configuration option classes that implement `IValidatableObject`.

## Base Class

Location: `MyApp.OnlyForTests.Basic.Validation.BaseValidatableObjectTests`

Provides assertion helpers for validation results.

## Required Pattern

Every configuration options test class should:

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
using MyApp.Configuration.Options.Deployment;
using MyApp.OnlyForTests.Basic.Validation;

namespace MyApp.Configuration.Tests.Options.Deployment;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class DeploymentOptionsTests : BaseValidatableObjectTests
{
    public DeploymentOptionsTests()
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
            nameof(DeploymentOptions.Appliance.AppDeployment.InstanceKeyPairName),
            nameof(DeploymentOptions.Infrastructure.NetworkCidrBlock),
            nameof(DeploymentOptions.Elasticsearch.CloudId),
            nameof(DeploymentOptions.Elasticsearch.ApiKey)
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
    public void Validate_WithNullAppliance_ReturnsValidationError()
    {
        // Arrange.
        var validOptions = CreateValidOptions();
        var options = validOptions with
        {
            Appliance = null!,
        };
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfFailedValidation(results, nameof(DeploymentOptions.Appliance));
    }

    [Test]
    public void Validate_WithNullInfrastructure_ReturnsValidationError()
    {
        // Arrange.
        var validOptions = CreateValidOptions();
        var options = validOptions with
        {
            Infrastructure = null!,
        };
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfFailedValidation(results, nameof(DeploymentOptions.Infrastructure));
    }

    [TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]
    public void Validate_WithInvalidInstanceKeyPairName_ReturnsValidationError(String? invalidValue)
    {
        // Arrange.
        var validOptions = CreateValidOptions();
        var options = validOptions with
        {
            Appliance = validOptions.Appliance with
            {
                AppDeployment = validOptions.Appliance.AppDeployment with
                {
                    InstanceKeyPairName = invalidValue,
                },
            },
        };
        var validationContext = new ValidationContext(options);

        // Act.
        var results = options.Validate(validationContext);

        // Assert.
        VerifyResultOfFailedValidation(
            results,
            nameof(DeploymentOptions.Appliance.AppDeployment.InstanceKeyPairName)
        );
    }

    // ============ Helper methods ============

    private static DeploymentOptions CreateDefaultOptions()
    {
        return new DeploymentOptions();
    }

    private static DeploymentOptions CreateValidOptions()
    {
        return new DeploymentOptions
        {
            Appliance = new ApplianceDeploymentOptions
            {
                AppDeployment = new AppDeploymentOptions
                {
                    InstanceKeyPairName = "my-key-pair",
                    ElasticCloudAgentSecretName = "elastic-agent-secret",
                },
                Deployment = new DeploymentOptions
                {
                    InstanceKeyPairName = "app-key-pair",
                    ElasticCloudAgentSecretName = "app-elastic-secret",
                },
            },
            Infrastructure = new InfrastructureDeploymentOptions
            {
                NetworkCidrBlock = "10.0.0.0/16",
            },
            Elasticsearch = new ElasticsearchOptions
            {
                CloudId = "my-cloud-id",
                ApiKey = "my-api-key",
            },
        };
    }
}
```

## Standard Tests to Include

1. **Null ValidationContext** - `Validate` throws `ArgumentNullException`

2. **Default options** - `Validate` returns errors for all required fields

3. **Valid options** - `Validate` returns no errors

4. **Individual null properties** - Each required nested object returns validation error when null

5. **String validation** - Use `StringNullOrWhiteSpace_TestCases` for required string properties

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
public sealed class NestedOptionsTests : BaseValidatableObjectTests
{
    // Test nested options independently
}
```

## Key Points

1. **CreateDefaultOptions** - Use default constructor or `new T()` to get empty/default state

2. **CreateValidOptions** - Provide ALL required values to pass validation

3. **Use `with` expressions** - Cleanly create invalid variants from valid options

4. **Test each required property** - Null check for objects, `StringNullOrWhiteSpace_TestCases` for strings

5. **Nameof for member names** - Ensures compile-time checking of property names
