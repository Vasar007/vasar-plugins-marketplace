# Configuration Binding Tests - BaseConfigurationBindingTests\<T\>

Use `BaseConfigurationBindingTests<T>` for testing that configuration options classes correctly bind from JSON and environment variables.

The code examples in this file use NUnit and FluentAssertions. With another test framework or assertion library, use its equivalent attributes and calls.

## Base Class

Location: `MyApp.Framework.Tests.ForTests.BaseConfigurationBindingTests<T>`

Inherits from: `BaseTest`

## Required Override

```csharp
// The configuration section name used to bind the options
protected abstract String SectionName { get; }
```

## Available Helper Methods

```csharp
// Build configuration from JSON string
protected static IConfigurationRoot BuildConfigurationFromJson(String json);

// Build configuration from key-value pairs (simulates environment variables)
protected static IConfigurationRoot BuildConfigurationFromKeyValuePairs(
    IEnumerable<KeyValuePair<String, String?>> keyValuePairs);

// Bind options from IConfigurationRoot
protected TOptions BindOptions(IConfigurationRoot configuration);

// Bind options directly from JSON
protected TOptions BindOptionsFromJson(String json);

// Bind options from key-value pairs
protected TOptions BindOptionsFromKeyValuePairs(
    IEnumerable<KeyValuePair<String, String?>> keyValuePairs);

// Create action for testing binding exceptions
protected Action BindOptionsFromJsonAction(String json);
protected Action BindOptionsFromKeyValuePairsAction(
    IEnumerable<KeyValuePair<String, String?>> keyValuePairs);

// Verify missing config parameter exception
protected static void VerifyMissingConfigParameterException(Action act, String parameterName);
```

## Base Class Definition

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.Extensions.Configuration;
using MyApp.Framework.Constants;

namespace MyApp.Framework.Tests.ForTests;

/// <summary>
/// Base class for testing configuration binding of options classes.
/// Provides helper methods to build configuration from JSON and key-value pairs.
/// </summary>
/// <typeparam name="TOptions">The type of the options class being tested.</typeparam>
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public abstract class BaseConfigurationBindingTests<TOptions> : BaseTest
    where TOptions : class, new()
{
    /// <summary>
    /// Gets the configuration section name used to bind the options.
    /// </summary>
    protected abstract String SectionName { get; }

    protected BaseConfigurationBindingTests()
    {
    }

    #region Configuration Building

    protected static IConfigurationRoot BuildConfigurationFromJson(String json)
    {
        using var stream = new MemoryStream(Constants.DefaultEncoding.GetBytes(json));

        return new ConfigurationBuilder()
            .AddJsonStream(stream)
            .Build();
    }

    protected static IConfigurationRoot BuildConfigurationFromKeyValuePairs(
        IEnumerable<KeyValuePair<String, String?>> keyValuePairs)
    {
        return new ConfigurationBuilder()
            .AddInMemoryCollection(keyValuePairs)
            .Build();
    }

    protected static IConfigurationRoot BuildConfigurationFromKeyValuePairs(
        params KeyValuePair<String, String?>[] keyValuePairs)
    {
        return BuildConfigurationFromKeyValuePairs(keyValuePairs.AsEnumerable());
    }

    #endregion

    #region Options Binding

    protected TOptions BindOptions(IConfigurationRoot configuration)
    {
        configuration.ThrowIfNull();

        var options = new TOptions();
        configuration.GetSection(SectionName).Bind(options);

        return options;
    }

    protected TOptions BindOptionsFromJson(String json)
    {
        var configuration = BuildConfigurationFromJson(json);
        return BindOptions(configuration);
    }

    protected TOptions BindOptionsFromKeyValuePairs(
        IEnumerable<KeyValuePair<String, String?>> keyValuePairs)
    {
        var configuration = BuildConfigurationFromKeyValuePairs(keyValuePairs);
        return BindOptions(configuration);
    }

    protected Action BindOptionsFromJsonAction(String json)
    {
        return () => BindOptionsFromJson(json);
    }

    protected Action BindOptionsFromKeyValuePairsAction(
        IEnumerable<KeyValuePair<String, String?>> keyValuePairs)
    {
        return () => BindOptionsFromKeyValuePairs(keyValuePairs);
    }

    #endregion

    #region Verification Helpers

    protected static void VerifyMissingConfigParameterException(Action act, String parameterName)
    {
        act.Should().Throw<InvalidOperationException>()
            .WithMessage($"*'{parameterName}'*no matching config*");
    }

    #endregion
}
```

## Complete Example

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.Framework.Infrastructure.Migrations.Options;

namespace MyApp.Framework.Tests.Infrastructure.Migrations.Options;

/// <summary>
/// Tests configuration binding for <see cref="MigrationOptions"/> from appsettings JSON.
/// These tests verify that the options can be correctly deserialized from configuration.
/// </summary>
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class MigrationOptionsConfigurationBindingTests : BaseConfigurationBindingTests<MigrationOptions>
{
    /// <inheritdoc />
    protected override String SectionName => nameof(MigrationOptions);

    public MigrationOptionsConfigurationBindingTests()
    {
    }

    #region Minimal Configuration

    [Test]
    public void Bind_MinimalConfiguration_UsesDefaults()
    {
        // Arrange.
        var json = """
            {
                "MigrationOptions": {
                }
            }
            """;

        // Act.
        var options = BindOptionsFromJson(json);

        // Assert.
        options.EnableMigrationEngine.Should().BeFalse("default is false");
        options.Timeout.Should().Be(TimeSpan.FromMinutes(5), "default is 5 minutes");
        options.FailOnError.Should().BeTrue("default is true");
        options.SkipDatabaseMigrations.Should().BeFalse("default is false");
        options.SkipProductMigrations.Should().BeFalse("default is false");
        options.UseReflectionDiscovery.Should().BeTrue("default is true");
        options.EnableVersionSeeding.Should().BeFalse("default is false");
        options.SeedDatabaseVersion.Should().BeNull("default is null");
        options.SeedProductMigrationVersion.Should().BeNull("default is null");
    }

    [Test]
    public void Bind_MinimalConfiguration_WithEnableOnly()
    {
        // Arrange.
        var json = """
            {
                "MigrationOptions": {
                    "EnableMigrationEngine": true
                }
            }
            """;

        // Act.
        var options = BindOptionsFromJson(json);

        // Assert.
        options.EnableMigrationEngine.Should().BeTrue();
        options.Timeout.Should().Be(TimeSpan.FromMinutes(5));
        options.FailOnError.Should().BeTrue();
    }

    #endregion

    #region Partial Configuration - Basic Properties

    [Test]
    public void Bind_PartialConfiguration_BindsBooleanProperties()
    {
        // Arrange.
        var json = """
            {
                "MigrationOptions": {
                    "EnableMigrationEngine": true,
                    "FailOnError": false,
                    "SkipDatabaseMigrations": true,
                    "SkipProductMigrations": true,
                    "UseReflectionDiscovery": false
                }
            }
            """;

        // Act.
        var options = BindOptionsFromJson(json);

        // Assert.
        options.EnableMigrationEngine.Should().BeTrue();
        options.FailOnError.Should().BeFalse();
        options.SkipDatabaseMigrations.Should().BeTrue();
        options.SkipProductMigrations.Should().BeTrue();
        options.UseReflectionDiscovery.Should().BeFalse();
    }

    [Test]
    public void Bind_PartialConfiguration_BindsTimeSpanFromString()
    {
        // Arrange.
        var json = """
            {
                "MigrationOptions": {
                    "Timeout": "00:10:00"
                }
            }
            """;

        // Act.
        var options = BindOptionsFromJson(json);

        // Assert.
        options.Timeout.Should().Be(TimeSpan.FromMinutes(10));
    }

    #endregion

    #region Nested Objects Binding

    [Test]
    public void Bind_VersionSeeding_WithNestedObject_BindsCorrectly()
    {
        // Arrange.
        var json = """
            {
                "MigrationOptions": {
                    "EnableVersionSeeding": true,
                    "SeedDatabaseVersion": {
                        "Version": "2.0.0.0",
                        "FailbackVersionLabel": "2.0.0"
                    }
                }
            }
            """;

        // Act.
        var options = BindOptionsFromJson(json);

        // Assert.
        options.EnableVersionSeeding.Should().BeTrue();
        options.SeedDatabaseVersion.Should().NotBeNull();
        options.SeedDatabaseVersion!.Version.Should().Be(new Version("2.0.0.0"));
        options.SeedDatabaseVersion.FailbackVersionLabel.Should().Be("2.0.0");
    }

    [Test]
    public void Bind_VersionSeeding_WithPartialNestedObject_ThrowsInvalidOperationException()
    {
        // Arrange.
        // VersionInfo has a required FailbackVersionLabel, so binding with partial properties fails.
        var json = """
            {
                "MigrationOptions": {
                    "EnableVersionSeeding": true,
                    "SeedDatabaseVersion": {
                        "Version": "3.0.0.0"
                    }
                }
            }
            """;

        // Act & Assert.
        // Configuration binding requires all constructor parameters.
        var act = BindOptionsFromJsonAction(json);

        VerifyMissingConfigParameterException(act, "failbackVersionLabel");
    }

    #endregion

    #region Full Configuration

    [Test]
    public void Bind_FullConfiguration_BindsAllProperties()
    {
        // Arrange.
        var json = """
            {
                "MigrationOptions": {
                    "EnableMigrationEngine": true,
                    "Timeout": "00:15:00",
                    "FailOnError": false,
                    "SkipDatabaseMigrations": true,
                    "SkipProductMigrations": false,
                    "UseReflectionDiscovery": true,
                    "EnableVersionSeeding": true,
                    "SeedDatabaseVersion": {
                        "Version": "2.5.0.0",
                        "FailbackVersionLabel": "2.5.0"
                    },
                    "SeedProductMigrationVersion": {
                        "Version": "1.0.0.0",
                        "FailbackVersionLabel": "1.0.0"
                    }
                }
            }
            """;

        // Act.
        var options = BindOptionsFromJson(json);

        // Assert.
        // All basic properties.
        options.EnableMigrationEngine.Should().BeTrue();
        options.Timeout.Should().Be(TimeSpan.FromMinutes(15));
        options.FailOnError.Should().BeFalse();
        options.SkipDatabaseMigrations.Should().BeTrue();
        options.SkipProductMigrations.Should().BeFalse();
        options.UseReflectionDiscovery.Should().BeTrue();
        options.EnableVersionSeeding.Should().BeTrue();

        // VersionInfo properties.
        options.SeedDatabaseVersion.Should().NotBeNull();
        options.SeedDatabaseVersion!.Version.Should().Be(new Version("2.5.0.0"));
        options.SeedDatabaseVersion.FailbackVersionLabel.Should().Be("2.5.0");

        options.SeedProductMigrationVersion.Should().NotBeNull();
        options.SeedProductMigrationVersion!.Version.Should().Be(new Version("1.0.0.0"));
        options.SeedProductMigrationVersion.FailbackVersionLabel.Should().Be("1.0.0");
    }

    #endregion

    #region Environment Variable Binding

    [Test]
    public void Bind_EnvironmentVariables_BindsBooleanProperties()
    {
        // Arrange.
        // Simulates environment variable binding using key-value pairs.
        var keyValuePairs = new[]
        {
            new KeyValuePair<String, String?>("MigrationOptions:EnableMigrationEngine", "true"),
            new KeyValuePair<String, String?>("MigrationOptions:FailOnError", "false"),
            new KeyValuePair<String, String?>("MigrationOptions:SkipDatabaseMigrations", "true"),
        };

        // Act.
        var options = BindOptionsFromKeyValuePairs(keyValuePairs);

        // Assert.
        options.EnableMigrationEngine.Should().BeTrue();
        options.FailOnError.Should().BeFalse();
        options.SkipDatabaseMigrations.Should().BeTrue();
    }

    [Test]
    public void Bind_EnvironmentVariables_BindsNestedObjects()
    {
        // Arrange.
        // Uses colon notation for nested properties.
        var keyValuePairs = new[]
        {
            new KeyValuePair<String, String?>("MigrationOptions:EnableVersionSeeding", "true"),
            new KeyValuePair<String, String?>("MigrationOptions:SeedDatabaseVersion:Version", "2.0.0.0"),
            new KeyValuePair<String, String?>("MigrationOptions:SeedDatabaseVersion:FailbackVersionLabel", "2.0.0"),
        };

        // Act.
        var options = BindOptionsFromKeyValuePairs(keyValuePairs);

        // Assert.
        options.EnableVersionSeeding.Should().BeTrue();
        options.SeedDatabaseVersion.Should().NotBeNull();
        options.SeedDatabaseVersion!.Version.Should().Be(new Version("2.0.0.0"));
        options.SeedDatabaseVersion.FailbackVersionLabel.Should().Be("2.0.0");
    }

    #endregion
}
```

## Test Patterns

### 1. Minimal Configuration (Defaults)

```csharp
[Test]
public void Bind_MinimalConfiguration_UsesDefaults()
{
    // Arrange.
    var json = """
        {
            "MyOptions": {
            }
        }
        """;

    // Act.
    var options = BindOptionsFromJson(json);

    // Assert.
    options.PropertyWithDefault.Should().Be(expectedDefault, "default is X");
    options.NullableProperty.Should().BeNull("default is null");
}
```

### 2. Boolean Properties

```csharp
[Test]
public void Bind_PartialConfiguration_BindsBooleanProperties()
{
    // Arrange.
    var json = """
        {
            "MyOptions": {
                "IsEnabled": true,
                "UseFeature": false
            }
        }
        """;

    // Act.
    var options = BindOptionsFromJson(json);

    // Assert.
    options.IsEnabled.Should().BeTrue();
    options.UseFeature.Should().BeFalse();
}
```

### 3. TimeSpan Binding

```csharp
[Test]
public void Bind_PartialConfiguration_BindsTimeSpanFromString()
{
    // Arrange.
    var json = """
        {
            "MyOptions": {
                "Timeout": "00:10:00"
            }
        }
        """;

    // Act.
    var options = BindOptionsFromJson(json);

    // Assert.
    options.Timeout.Should().Be(TimeSpan.FromMinutes(10));
}
```

### 4. Nested Objects with Required Parameters

```csharp
[Test]
public void Bind_NestedObject_WithMissingRequiredParameter_Throws()
{
    // Arrange.
    var json = """
        {
            "MyOptions": {
                "NestedObject": {
                    "OptionalParam": "value"
                }
            }
        }
        """;

    // Act.
    var act = BindOptionsFromJsonAction(json);

    // Assert.
    VerifyMissingConfigParameterException(act, "requiredParam");
}
```

### 5. Environment Variable Binding

```csharp
[Test]
public void Bind_EnvironmentVariables_BindsProperties()
{
    // Arrange.
    // Uses colon notation for nested properties.
    var keyValuePairs = new[]
    {
        new KeyValuePair<String, String?>("MyOptions:IsEnabled", "true"),
        new KeyValuePair<String, String?>("MyOptions:Nested:Value", "test"),
    };

    // Act.
    var options = BindOptionsFromKeyValuePairs(keyValuePairs);

    // Assert.
    options.IsEnabled.Should().BeTrue();
    options.Nested.Value.Should().Be("test");
}
```

## Key Points

1. **SectionName property**: Must match the options class name or configured section name

2. **Test defaults first**: Verify empty configuration uses expected defaults

3. **Test partial binding**: Verify individual properties bind correctly

4. **Test nested objects**: Verify complex hierarchies bind correctly

5. **Test required parameters**: Use `VerifyMissingConfigParameterException` for constructor parameters

6. **Test environment variables**: Use colon notation (`Section:Property`) for key-value pairs

7. **Use raw string literals**: Use `"""` for multi-line JSON for readability
