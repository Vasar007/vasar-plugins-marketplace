# Configuration — Options & Validation

## Directory Structure

```text
Configuration/
  Options/
    {Domain}/
      {Name}Options.cs                 (sealed record, IValidatableObject)
      {Name}OptionsValidator.cs        (FluentValidation, AbstractValidator<T>)
```

Domain subfolders are project-specific (e.g., `Deployment/`, `Services/`, `Workload/`, `Logging/`). Nest deeper for sub-features as the project already does.

## Options Class Pattern

```csharp
public sealed record {Name}Options : IValidatableObject
{
    /// <summary>
    /// Gets or sets the property description.
    /// </summary>
    public String PropertyName { get; set; } = "default";

    /// <summary>
    /// Nested options for sub-feature.
    /// </summary>
    public NestedOptions Nested { get; set; } = new();

    public {Name}Options()
    {
    }

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        validationContext.ThrowIfNull();

        var validator = new {Name}OptionsValidator();
        var result = validator.Validate(this);

        return result.ToSystemValidationResultCollection();
    }
}
```

Key requirements:

- `sealed record` implementing `IValidatableObject`.
- Properties use `{ get; set; }` with sensible defaults.
- Parameterless constructor (required for configuration binding).
- `Validate()` delegates to the FluentValidation validator.
- Uses `result.ToSystemValidationResultCollection()` to bridge FluentValidation to DataAnnotations.

## Validator Pattern

```csharp
public sealed class {Name}OptionsValidator : AbstractValidator<{Name}Options>
{
    public {Name}OptionsValidator()
    {
        var errorBuilder = ValidationErrorBuilder.Default;

        RuleFor(x => x.PropertyName)
            .NotEmpty().WithMessage(x => errorBuilder.CreateValueRequiredMessage(x.PropertyName));

        // Nested options — validate with child validator
        RuleFor(x => x.Nested)
            .NotNull().WithMessage(x => errorBuilder.CreateValueRequiredMessage(x.Nested))
            .SetValidator(new NestedOptionsValidator());
    }
}
```

Key requirements:

- `sealed class` inheriting `AbstractValidator<T>`.
- Use `ValidationErrorBuilder.Default` for error messages.
- Validate nested options with `.SetValidator(new ChildValidator())`.
- If the .NET backend framework exposes a shared base validator for service options (e.g. a `Base*ServiceOptionsValidator<T>`), prefer inheriting from it over reimplementing the same rules.

## Nested Options

Root options compose child options via properties initialized with `new()`:

```csharp
public NestedOptions Child { get; set; } = new();
```

Validators cascade — the root validator uses `.SetValidator()` for each nested child.

## Computed Properties

Expression-bodied readonly members for derived values:

```csharp
/// <summary>
/// Gets the computed maximum items per region.
/// </summary>
public Int32 MaxItemsPerRegion => MaxRetries * TimeoutSeconds;
```

## DI Registration

Options are registered in the host application builder extensions (commonly `WebApi/Services/Builders/ExtensionMethodsHostApplicationBuilder.cs`):

```csharp
builder.ConfigureOptionsAndEnableValidation<DeploymentOptions>();
```

`ConfigureOptionsAndEnableValidation` is a framework helper that binds options from configuration and enables `IValidatableObject` validation on startup.

## Consuming Options

Services inject `IOptionsMonitor<T>` (not `IOptions<T>`):

```csharp
private readonly IOptionsMonitor<DeploymentOptions> _deploymentOptions;

// Access current value
var options = _deploymentOptions.CurrentValue;
```

## Adding a New Options Class

1. Create `{Name}Options.cs` — sealed record, `IValidatableObject`, with defaults.
2. Create `{Name}OptionsValidator.cs` — `AbstractValidator` with rules.
3. If top-level: register in the project's host-builder extension method (e.g. `ConfigureXxxOptionsAndEnableValidation`).
4. If nested: add as a property on the parent options and validate via `.SetValidator()` in the parent validator.
