---
name: add-configuration-option
description: Add a .NET options class with validation and DI registration.
when_to_use: Use it for "add configuration", "add options", "add setting", or "configurable value".
---

# Add Configuration Option

Add configuration options in your service configuration project with validators of the validation library (for example, FluentValidation). The examples use FluentValidation. Another validation library uses its own validator base class and rule calls.

## Architecture

```text
Options Class (mutable config model with init/set)
    ↓ validated by
Validator (validation library)
    ↓ registered in
DI Container (IOptions<T> / IOptionsSnapshot<T> / IOptionsMonitor<T>)
    ↓ bound from
appsettings.json
```

## File Structure

```txt
src/{ServiceName}.Configuration/
├── Options/
│   └── {Feature}/
│       ├── {Feature}Options.cs           # Options class
│       └── {Feature}OptionsValidator.cs  # Validator
```

## Step 1: Options Class

**CRITICAL**:

- Properties MUST have `{ get; set; }` (preferred) or `{ get; init; }`, NOT just `{ get; }`.
- Prefer `{ get; set; }` to allow customizing options via ASP.NET's `.Configure()` method.

### Validation Flow

1. Model is created and bound from configuration
2. DataAnnotations attributes (for example, `[Required]` and `[Range]`) are validated
3. `Validate()` method is called for complex validation logic

`[Required]` has an effect only on a reference type, for example `String`, or on a nullable value type, for example `Int32?`. A plain value type such as `Int32` always has a value, so `[Required]` never fails on it. For a number that the configuration must set, use `Int32?` with `[Required]`. Use `[Range]` for the allowed values.

```csharp
// Copyright (c) Vasily Vasilyev

using System.ComponentModel.DataAnnotations;
using {ProjectNamespace}.Common.Validation;

namespace {ProjectNamespace}.Configuration.Options.{Feature};

/// <summary>
/// Configuration options for {feature}.
/// </summary>
public sealed record {Feature}Options : IValidatableObject
{
    /// <summary>
    /// Gets or sets the timeout in seconds.
    /// </summary>
    public Int32 TimeoutSeconds { get; set; } = 30;

    /// <summary>
    /// Gets or sets the maximum retry count.
    /// </summary>
    [Range(1, 10)]
    public Int32 MaxRetries { get; set; } = 3;

    /// <summary>
    /// Gets or sets the service endpoint URL.
    /// </summary>
    [Required]
    public String EndpointUrl { get; set; } = String.Empty;

    /// <summary>
    /// Gets or sets whether the feature is enabled.
    /// </summary>
    public Boolean IsEnabled { get; set; } = true;

    /// <summary>
    /// Gets the computed maximum items per order.
    /// </summary>
    /// <remarks>
    /// Computed properties derive values from other options. Use expression-bodied members
    /// with no setter — they are NOT bound from configuration.
    /// </remarks>
    public Int32 MaxItemsPerOrder => MaxRetries * TimeoutSeconds;

    /// <summary>
    /// Initializes a new instance of the <see cref="{Feature}Options"/> class.
    /// </summary>
    public {Feature}Options()
    {
    }

    /// <summary>
    /// Validates the current instance of <see cref="{Feature}Options"/>.
    /// </summary>
    /// <param name="validationContext">The context information about the object being validated.</param>
    /// <returns>A collection of <see cref="ValidationResult"/> objects that describe any validation failures.</returns>
    /// <exception cref="ArgumentNullException">
    /// <paramref name="validationContext" /> is <see langword="null" />.
    /// </exception>
    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        validationContext.ThrowIfNull();

        var validator = new {Feature}OptionsValidator();
        var result = validator.Validate(this);

        return result.ToSystemValidationResultCollection();
    }
}
```

### Example Options Class (Replace With Your Domain)

```csharp
public sealed record {Feature}Options : IValidatableObject
{
    public {NestedOptions} NestedOptions { get; set; } = new();

    public {Feature}Options()
    {
    }

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        validationContext.ThrowIfNull();

        var validator = new {Feature}OptionsValidator();
        var result = validator.Validate(this);

        return result.ToSystemValidationResultCollection();
    }
}
```

## Step 2: Validator

Use `ValidationErrorBuilder.Default` with `CreateValueRequiredMessage()` for a rule that requires a value, for example `NotEmpty` or `NotNull`. A range rule, for example `GreaterThan` or `InclusiveBetween`, keeps the default message of the validation library. The value of such a property is present but out of range, so a message that says that the value is required is wrong.

### Cascade Mode

Use `.Cascade(CascadeMode.Stop)` on rule chains. If an earlier rule fails, the later rules of the chain do not run:

```csharp
// Copyright (c) Vasily Vasilyev

using FluentValidation;
using {ProjectNamespace}.Common.Validation.Errors;

namespace {ProjectNamespace}.Configuration.Options.{Feature};

/// <summary>
/// Validator for <see cref="{Feature}Options"/>.
/// </summary>
public sealed class {Feature}OptionsValidator : AbstractValidator<{Feature}Options>
{
    public {Feature}OptionsValidator()
    {
        ClassLevelCascadeMode = CascadeMode.Stop;

        var errorBuilder = ValidationErrorBuilder.Default;

        // Use Cascade(CascadeMode.Stop) to prevent running further rules if earlier ones fail
        RuleFor(x => x.TimeoutSeconds).Cascade(CascadeMode.Stop).GreaterThan(0);

        RuleFor(x => x.MaxRetries).Cascade(CascadeMode.Stop).InclusiveBetween(1, 10);

        RuleFor(x => x.EndpointUrl).Cascade(CascadeMode.Stop)
            .NotEmpty()
            .WithMessage(x => errorBuilder.CreateValueRequiredMessage(x.EndpointUrl));

        // Only if the options class has nested options (see "Example Options Class" below)
        // For nested options, use SetValidator
        RuleFor(x => x.NestedOptions).Cascade(CascadeMode.Stop)
            .NotNull().WithMessage(x => errorBuilder.CreateValueRequiredMessage(x.NestedOptions))
            .SetValidator(new NestedOptionsValidator());
    }
}
```

### Example Validator (Replace With Your Domain)

```csharp
public sealed class {Feature}OptionsValidator : AbstractValidator<{Feature}Options>
{
    public {Feature}OptionsValidator()
    {
        ClassLevelCascadeMode = CascadeMode.Stop;

        var errorBuilder = ValidationErrorBuilder.Default;

        RuleFor(x => x.Items).Cascade(CascadeMode.Stop)
            .NotEmpty().WithMessage(x => errorBuilder.CreateValueRequiredMessage(x.Items))
            .ForEach(x => x.NotEmpty().WithMessage(errorBuilder.CreateStringRequiredMessage(nameof({Feature}Options.Items))));
    }
}
```

### Why Use Cascade Mode?

**Without Cascade Mode**: If a collection is `null`, `.ForEach()` will throw `NullReferenceException`.

**With Cascade Mode**: If `.NotNull()` fails, `.ForEach()` is skipped, preventing crashes.

## Step 3: DI Registration

Use the extension method in `ExtensionMethodsHostApplicationBuilder.cs`:

```csharp
// In src/{ServiceName}.WebApi/Services/Builders/ExtensionMethodsHostApplicationBuilder.cs
internal static class ExtensionMethodsHostApplicationBuilder
{
    public static void Configure{ServiceName}OptionsAndEnableValidation(this IHostApplicationBuilder builder)
    {
        builder.ThrowIfNull();

        // Add your new options here
        builder.ConfigureOptionsAndEnableValidation<{Feature}Options>();

        // Existing registrations
        builder.ConfigureOptionsAndEnableValidation<BillingOptions>();
        builder.ConfigureOptionsAndEnableValidation<ShippingOptions>();
        // ...
    }
}
```

**NOTE**: The `ConfigureOptionsAndEnableValidation<T>()` extension handles binding, the validator of the validation library, and startup validation automatically.

## Step 4: Configuration Sources

### appsettings.json (Project Defaults)

`appsettings.json` provides **default values** for the project:

```json
{
  "{Feature}Options": {
    "TimeoutSeconds": 30,
    "MaxRetries": 3,
    "EndpointUrl": "https://api.example.com",
    "IsEnabled": true
  }
}
```

The section name is the name of the options class. It is the same name that `ConfigureOptionsAndEnableValidation<T>()` binds.

**NOTE**: These are **project-wide defaults**. Your deployment system (for example, Helm) must override the important options.

### Deployment Configuration (Environment-Specific)

**CRITICAL**: Important configuration options MUST be exposed in your deployment system (for example, Helm, Kustomize, or Terraform) for CI/CD.

#### 1. Add to deployment values

```yaml
tenant:
  settings:
    # Add your new settings here
    {Feature}Options__TimeoutSeconds:
    {Feature}Options__EndpointUrl:
    {Feature}Options__IsEnabled:
```

**NOTE**: Use `__` between the levels of a nested configuration key (ASP.NET Core convention).

#### 2. Update deployment validation (if applicable)

Add validation for the required values. In this example, the deployment system maps the key `{Feature}Options__EndpointUrl` to the shell variable `FEATURE_OPTIONS_ENDPOINT_URL`. Use the variable names that your deployment system creates.

```bash
if [ -n "$FEATURE_OPTIONS_ENDPOINT_URL" ]; then
    echo "FEATURE_OPTIONS_ENDPOINT_URL: $FEATURE_OPTIONS_ENDPOINT_URL"
else
    echo "FEATURE_OPTIONS_ENDPOINT_URL is missing."
    exit 1
fi

if [ -n "$FEATURE_OPTIONS_TIMEOUT_SECONDS" ]; then
    echo "FEATURE_OPTIONS_TIMEOUT_SECONDS: $FEATURE_OPTIONS_TIMEOUT_SECONDS"
else
    echo "FEATURE_OPTIONS_TIMEOUT_SECONDS is missing."
    exit 1
fi
```

**NOTE**: The Platform team will add actual values to the CI/CD pipeline variables.

### Configuration Priority

ASP.NET Core configuration sources (highest to lowest priority):

1. **Environment variables** (set by the deployment system, for example Helm)
2. **appsettings.{Environment}.json** (environment-specific)
3. **appsettings.json** (project defaults)

Environment variables from the deployment system **override** appsettings.json values.

## Using Options in Code

**TIP**: Use a computed property (for example, `Options => _options.Value`) as a shortcut instead of repeatedly accessing `.Value` or `.CurrentValue` throughout your code. This improves readability and reduces repetition.

Inject `IOptionsMonitor<T>` (see [configuration.md](../dotnet-conventions/configuration.md)). Use `IOptions<T>` or `IOptionsSnapshot<T>` only where the existing code of the repository already does.

### Via IOptionsMonitor\<T\> (singleton, change notifications)

```csharp
public sealed class MyService
{
    private readonly IOptionsMonitor<{Feature}Options> _options;

    private {Feature}Options Options => _options.CurrentValue;

    public MyService(
        IOptionsMonitor<{Feature}Options> options)
    {
        _options = options.ThrowIfNull();
    }

    public void DoWork()
    {
        // Always gets current value
        var timeout = Options.TimeoutSeconds;
    }
}
```

### Via IOptions\<T\> (singleton, read once at startup)

```csharp
public sealed class MyService
{
    private readonly {Feature}Options _options;

    public MyService(
        IOptions<{Feature}Options> options)
    {
        _options = options.ThrowIfNull().Value;
    }
}
```

### Via IOptionsSnapshot\<T\> (scoped, reloads per request)

```csharp
public sealed class MyService
{
    private readonly IOptionsSnapshot<{Feature}Options> _options;

    private {Feature}Options Options => _options.Value;

    public MyService(
        IOptionsSnapshot<{Feature}Options> options)
    {
        _options = options.ThrowIfNull();
    }

    public void DoWork()
    {
        // Gets current value for this scope/request
        var timeout = Options.TimeoutSeconds;
    }
}
```

## BuildEnvironment Pattern

For compile-time environment-specific configuration, use the `BuildEnvironment` + `BuildEnvironmentInfo` pattern:

### Step 1: BuildEnvironment Static Class

```csharp
// BuildEnvironment.cs
public static class BuildEnvironment
{
    public const Boolean IsDebugConst =
#if DEBUG
        true;
#else
        false;
#endif

    public const Boolean UseFeatureXConst =
#if USE_FEATURE_X
        true;
#else
        false;
#endif
}
```

### Step 2: BuildEnvironmentInfo Singleton (for DI/testing)

```csharp
// BuildEnvironmentInfo.cs
public sealed class BuildEnvironmentInfo : I{ServiceName}BuildEnvironmentInfo
{
    public static BuildEnvironmentInfo Instance { get; } = new();

    /// <inheritdoc cref="BuildEnvironment.IsDebugConst"/>
    public Boolean IsDebugBuild => BuildEnvironment.IsDebugConst;

    /// <inheritdoc cref="BuildEnvironment.UseFeatureXConst"/>
    public Boolean UseFeatureX => BuildEnvironment.UseFeatureXConst;

    private BuildEnvironmentInfo()
    {
    }
}
```

### Step 3: Interface for Testing

```csharp
// I{ServiceName}BuildEnvironmentInfo.cs
public interface I{ServiceName}BuildEnvironmentInfo
{
    Boolean IsDebugBuild { get; }
    Boolean UseFeatureX { get; }
}
```

**IMPORTANT**: Avoid `#if` pragmas in business code. Inject `I{ServiceName}BuildEnvironmentInfo` instead:

```csharp
// ✅ Good - testable
public sealed class MyService
{
    private readonly I{ServiceName}BuildEnvironmentInfo _buildInfo;

    public MyService(
        I{ServiceName}BuildEnvironmentInfo buildInfo)
    {
        _buildInfo = buildInfo.ThrowIfNull();
    }

    public void DoWork()
    {
        if (_buildInfo.UseFeatureX)
        {
            // Feature X logic
        }
    }
}

// ❌ Bad - not testable
public sealed class MyService
{
    public void DoWork()
    {
#if USE_FEATURE_X
        // Feature X logic
#endif
    }
}
```

## Tests

Create configuration options tests following project conventions.

**See the [create-tests](../create-tests/SKILL.md) skill for complete unit and integration testing guidance.**

## Checklist

- [ ] Options class inherits `IValidatableObject` with `Validate()` method
- [ ] Properties use `{ get; set; }` (preferred) or `{ get; init; }`
- [ ] Properties have sensible defaults
- [ ] `[Required]`, `[Range]`, and other attributes on properties as needed
- [ ] Validator of the validation library, with `ValidationErrorBuilder.Default.CreateValueRequiredMessage()` on each rule that requires a value
- [ ] Validator stops at the first failed rule (FluentValidation: `ClassLevelCascadeMode = CascadeMode.Stop`)
- [ ] Rule chains stop at the first failed rule to prevent invalid validation calls (FluentValidation: `.Cascade(CascadeMode.Stop)`)
- [ ] Nested options use the child-validator call (FluentValidation: `.SetValidator(new NestedOptionsValidator())`)
- [ ] Registration added to `Configure{ServiceName}OptionsAndEnableValidation()`
- [ ] appsettings.json section added (project defaults)
- [ ] Important options exposed in the deployment values (for Helm, `helm/values.yaml`)
- [ ] Validation of required values added to the deployment script (for Helm, `helm/deploy.sh`)
- [ ] XML documentation on class and properties

## Related Skills

- [create-tests](../create-tests/SKILL.md): Testing configuration options and validation
- `dev-essentials:create-documentation`: Documenting configuration in project documentation
