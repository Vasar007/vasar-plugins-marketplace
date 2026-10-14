# Configuration — Options & Validation

## Directory Structure

```text
Configuration/
  Options/
    {Domain}/
      {Name}Options.cs                 (sealed record, IValidatableObject)
      {Name}OptionsValidator.cs        (FluentValidation, AbstractValidator<T>)
```

Domain subfolders are project-specific, for example `Shipping/`, `Services/`, `Sales/`, and `Logging/`. Nest deeper for sub-features as the project already does.

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
- The .NET backend framework can have a shared base validator for service options, for example a `Base*ServiceOptionsValidator<T>`. If it has one, prefer inheriting from it over reimplementing the same rules.

## Nested Options

Root options compose child options via properties initialized with `new()`:

```csharp
public NestedOptions Child { get; set; } = new();
```

Validators cascade. The root validator uses `.SetValidator()` for each nested child.

## Computed Properties

Expression-bodied readonly members for derived values:

```csharp
/// <summary>
/// Gets the total retry timeout in seconds.
/// </summary>
public Int32 TotalRetryTimeoutSeconds => MaxRetries * TimeoutSeconds;
```

## DI Registration

Options are registered in the host application builder extensions (commonly `WebApi/Services/Builders/ExtensionMethodsHostApplicationBuilder.cs`):

```csharp
builder.ConfigureOptionsAndEnableValidation<ShippingOptions>();
```

`ConfigureOptionsAndEnableValidation` is a framework helper that binds options from configuration and enables `IValidatableObject` validation on startup.

## Consuming Options

Services inject `IOptionsMonitor<T>` (not `IOptions<T>`):

```csharp
private readonly IOptionsMonitor<ShippingOptions> _shippingOptions;

// Access current value
var options = _shippingOptions.CurrentValue;
```

## Adding a New Options Class

1. Create `{Name}Options.cs`: a sealed record that implements `IValidatableObject` and has defaults.
2. Create `{Name}OptionsValidator.cs`: an `AbstractValidator` with rules.
3. If the options class is top-level, register it in the host-builder extension method of the project (for example, `ConfigureXxxOptionsAndEnableValidation`).
4. If the options class is nested, add it as a property of the parent options class. Validate it with `.SetValidator()` in the parent validator.
