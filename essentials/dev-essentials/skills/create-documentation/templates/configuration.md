# Configuration documentation template

Use this template to document the configuration options classes of a .NET
service. See `dotnet-backend-dev:add-configuration-option`.

`{OptionsPath}` is the folder of the options class under `src/`. For example,
it is `{ProjectName}.Configuration/Options/{Path}`.

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

[File](../src/{OptionsPath}/{OptionsClassName}.cs)

Brief description of what this options class configures.

Validation: [Validator](../src/{OptionsPath}/{OptionsClassName}Validator.cs)

| Property      | Description                  | Type   | Default | Required |
|---------------|------------------------------|--------|---------|----------|
| PropertyOne   | Description of property one  | string | null    | Yes      |
| PropertyTwo   | Description of property two  | int    | 0       | No       |
| NestedOptions | Nested configuration options | Type   | new()   | Yes      |

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
