# Configuration documentation template

Use this template to document the configuration options classes of a .NET service. See `dotnet-backend-dev:add-configuration-option`.

<!-- markdownlint-disable MD013 MD040 -->

````markdown
# {ProjectName} - Configuration

- [How to Specify Configuration Options](#how-to-specify-configuration-options)
- [Configuration Options Sections](#configuration-options-sections)
  - [{OptionsClassName}](#optionsclassname)
- [Environment Variables](#environment-variables)

Brief description of what this configuration document covers.

---

## How to Specify Configuration Options

Describe the configuration sources (appsettings.json, environment variables, etc.)
and their priority order.

## Configuration Options Sections

### {OptionsClassName}

<!-- markdownlint-disable MD013 -->

[File](
../src/{ProjectName}.Configuration/Options/{Path}/
{OptionsClassName}.cs)

Brief description of what this options class configures.

Validation: [Validator](
../src/{ProjectName}.Configuration/Options/{Path}/
{OptionsClassName}Validator.cs)

| Property Name | Description                              | Type   | Default Value | Required |
|---------------|------------------------------------------|--------|---------------|----------|
| PropertyOne   | Description of property one              | string | null          | Yes      |
| PropertyTwo   | Description of property two              | int    | 0             | No       |
| NestedOptions | Nested configuration options             | Type   | new()         | Yes      |

**Example (appsettings.json):**

```json
{
  "{OptionsClassName}": {
    "PropertyOne": "value",
    "PropertyTwo": 42,
    "NestedOptions": {
      "SubProperty": "nested-value"
    }
  }
}
```

**Example (environment variables):**

```txt
{OptionsClassName}__PropertyOne=value
{OptionsClassName}__PropertyTwo=42
{OptionsClassName}__NestedOptions__SubProperty=nested-value
```

## Environment Variables

List of required environment variables for deployment.

````

<!-- markdownlint-enable MD013 MD040 -->
