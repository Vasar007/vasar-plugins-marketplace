---
name: create-string-resource
description: Add StringResources.resx entries for user-facing strings with [TBD] prefix for localization. Use when adding session log messages, exception messages, or API responses that users will see. Triggers on requests like "add string resource", "user-facing message", "session log message", "localized string".
---

# Create String Resource

Add entries to `StringResources.resx` for all user-facing strings with the required `[TBD]` prefix.

## When to Use

ALL user-facing strings MUST go in StringResources.resx:

- Session log messages (visible in portal)
- Exception messages shown to users
- API response messages
- Validation error messages

## File Location

`src/{ProjectName}.Resources/Properties/StringResources.resx`

## Adding Entries

### 1. Open StringResources.resx

The file contains Name-Value pairs for localized strings.

### 2. Add Entry with [TBD] Prefix

**CRITICAL**: ALL new entries MUST start with `[TBD]` prefix.

| Name                                           | Value                                                                       |
|------------------------------------------------|-----------------------------------------------------------------------------|
| `TenantProvisioningStartedMessage`     | `[TBD] Workload tenant provisioning started.`                               |
| `TenantProvisioningContextMessage`     | `[TBD] Provisioning context: tenant [{0}] ({1}), region [{2}].`         |
| `TenantProvisioningCompletedMessage`   | `[TBD] Workload tenant [{0}] ({1}) provisioned successfully.`               |
| `NotFoundTenantMessage`                | `[TBD] Workload tenant with ID [{0}] was not found.`                        |

### 3. Naming Conventions

Use **CamelCase** names ending with `Message`:

```txt
{DomainModel}{Feature}{Action}Message
```

Examples:

- `TenantProvisioningStartedMessage`
- `TenantProvisioningCompletedMessage`
- `ApplianceDeploymentStartedMessage`
- `NotFoundTenantMessage`
- `InvalidOrganizationIdMessage`
- `CannotChangeCompletedTenantStatusMessage`

**NOTE**: No explicit "SessionLog_" prefix — the naming should be domain-specific.

### 4. Use Square Brackets for Placeholders

**CRITICAL**: Use `[{0}]` (square brackets) for clarity per analyst feedback:

```txt
TenantProvisioningContextMessage = [TBD] Provisioning context: tenant [{0}] ({1}), region [{2}], template [{3}].
TenantCreatedMessage = [TBD] Workload tenant [{0}] ({1}) created successfully.
NotFoundTenantMessage = [TBD] Workload tenant with ID [{0}] was not found.
```

**NOT** single quotes:

```txt
// ❌ Bad - harder to read in logs
TenantCreatedMessage = [TBD] Workload tenant '{0}' ({1}) created successfully.
```

## Usage in Code

Access via the generated `StringResources` class using `SafeFormat` extension:

```csharp
using {ProjectNamespace}.Resources.Properties;
using MyApp.Framework.Basic.Strings;

// Simple string (no placeholders)
var message = StringResources.TenantProvisioningStartedMessage;

// With formatting - use SafeFormat extension
var message = StringResources.TenantProvisioningContextMessage.SafeFormat(
    tenantId,
    tenantName,
    regionId,
    templateId
);
```

### Code Formatting — Closing Parenthesis on New Line

```csharp
// ✅ Good - ); on new line, aligned with statement start
var message = StringResources.TenantProvisioningContextMessage.SafeFormat(
    tenantId,
    tenantName,
    regionId,
    templateId
);

// ❌ Bad - ); on same line as last argument
var message = StringResources.TenantProvisioningContextMessage.SafeFormat(
    tenantId,
    tenantName,
    regionId,
    templateId);
```

## Runtime Logs vs Session Logs

### Runtime Logs (ILogger) — NEVER Use StringResources or Interpolation

```csharp
// ✅ Good - structured logging with placeholders
_logger.LogInformation(
    "Starting provisioning for tenant {TenantId} ({TenantName})",
    tenantId,
    tenantName
);

// ❌ Bad - string interpolation loses structure
_logger.LogInformation($"Starting provisioning for tenant {tenantId} ({tenantName})");

// ❌ Bad - StringResources not needed for runtime logs
_logger.LogInformation(StringResources.SomeMessage.SafeFormat(tenantId));
```

### Session Logs (ISessionLogRepository) — Use StringResources + SafeFormat

```csharp
// ✅ Good - StringResources with SafeFormat
await _sessionLogService.CreateInformationAsync(
    sessionId,
    StringResources.TenantProvisioningContextMessage.SafeFormat(
        tenantId,
        tenantName,
        regionId,
        templateId
    ),
    cancellationToken: cancellationToken
);
```

## Regenerating StringResources Class

After adding entries to `StringResources.resx`, the auto-generated `StringResources.Designer.cs` file must be updated to access new values in code.

### Discovering Resource Configuration

Before working with string resources, read the `.csproj` file and find the `EmbeddedResource` MSBuild section:

```xml
<ItemGroup>
  <EmbeddedResource Update="Properties\StringResources.resx">
    <Generator>MSBuild:Compile</Generator>
    <StronglyTypedLanguage>CSharp</StronglyTypedLanguage>
    <StronglyTypedClassName>StringResources</StronglyTypedClassName>
    <StronglyTypedNamespace>MyApp.Resources.Properties</StronglyTypedNamespace>
    <StronglyTypedFileName>Properties\StringResources.Designer.cs</StronglyTypedFileName>
    <PublicClass>true</PublicClass>
  </EmbeddedResource>
</ItemGroup>
```

This tells you:

- **Generator**: `MSBuild:Compile` — the build auto-generates the Designer.cs file
- **StronglyTypedClassName**: the generated class name
- **StronglyTypedNamespace**: the namespace of the generated class
- **StronglyTypedFileName**: where the generated file is written

### How to Regenerate

Build the project — the `MSBuild:Compile` generator handles everything automatically:

```bash
dotnet build
```

**IMPORTANT**: Do NOT run `resgen`, `PublicResXFileCodeGenerator`, or any other tool directly. The build handles code generation automatically via the `EmbeddedResource` MSBuild configuration.

### If Values Don't Appear

**CRITICAL**: If new string resources don't appear after building:

1. **STOP** — Do NOT manually modify `StringResources.Designer.cs`
2. **STOP** — Do NOT run `resgen` or any resource generation tool directly
3. **ASK the user** to regenerate the file (e.g., via Visual Studio or other tooling)
4. The file is auto-generated and will be overwritten

The Designer.cs file contains code like:

```csharp
/// <summary>
///   Looks up a localized string similar to [TBD] Workload tenant provisioning started.
/// </summary>
public static string TenantProvisioningStartedMessage {
    get {
        return ResourceManager.GetString("TenantProvisioningStartedMessage", resourceCulture);
    }
}
```

## `[TBD]` Prefix Purpose

The `[TBD]` prefix indicates:

- String is pending review by analysts/tech writers
- Content may change before release
- DO NOT remove prefix yourself — analysts will remove after review

## Example Workflow

1. Developer adds new session log requirement
2. Add entry to `StringResources.resx`: `TenantFeatureActionMessage = [TBD] Description with [{0}] placeholders.`
3. Regenerate `StringResources.Designer.cs` (save .resx or build project)
4. Use in code via `StringResources.TenantFeatureActionMessage.SafeFormat(...)`
5. Analyst reviews and removes `[TBD]` prefix
6. Tech writer may refine wording

## Real Examples from Codebase

```xml
<data name="TenantProvisioningStartedMessage" xml:space="preserve">
  <value>[TBD] Workload tenant provisioning started.</value>
</data>
<data name="TenantProvisioningContextMessage" xml:space="preserve">
  <value>[TBD] Provisioning context: tenant {0} ({1}), region [{2}], template result [{3}].</value>
</data>
<data name="NotFoundTenantMessage" xml:space="preserve">
  <value>[TBD] Workload tenant with ID [{0}] was not found.</value>
</data>
<data name="InvalidTenantIdMessage" xml:space="preserve">
  <value>[TBD] Invalid workload tenant ID: [{0}].</value>
</data>
```

## Checklist

- [ ] Entry added to StringResources.resx
- [ ] Name uses CamelCase ending with `Message` (e.g., `TenantProvisioningStartedMessage`)
- [ ] Value starts with `[TBD]` prefix
- [ ] Placeholders use square brackets: `[{0}]` not `'{0}'`
- [ ] `StringResources.Designer.cs` regenerated (save .resx or build project)
- [ ] New property appears in IntelliSense
- [ ] Code uses `StringResources.{Name}.SafeFormat(...)` to access
- [ ] Code formatting: `);` on new line, aligned with statement start
- [ ] Runtime logs do NOT use StringResources (use structured logging instead)
