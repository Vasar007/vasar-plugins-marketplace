---
name: create-string-resource
description: Add a user-facing .NET string to the .resx string resource file of the project, with the [TBD] prefix.
when_to_use: Use it for "add string resource", "user-facing message", "session log message", or "localized string".
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

| Name | Value |
| --- | --- |
| `StoreOnboardingStartedMessage` | `[TBD] Store onboarding started.` |
| `StoreOnboardingContextMessage` | `[TBD] Onboarding context: store [{0}] ({1}), warehouse [{2}].` |
| `StoreOnboardingCompletedMessage` | `[TBD] Store [{0}] ({1}) onboarded successfully.` |
| `NotFoundStoreMessage` | `[TBD] Store with ID [{0}] was not found.` |

### 3. Naming Conventions

Use **CamelCase** names ending with `Message`:

```txt
{DomainModel}{Feature}{Action}Message
```

Examples:

- `StoreOnboardingStartedMessage`
- `StoreOnboardingCompletedMessage`
- `OrderShipmentStartedMessage`
- `NotFoundStoreMessage`
- `InvalidOrganizationIdMessage`
- `CannotChangeCompletedOrderStatusMessage`

**NOTE**: Do not add a "SessionLog_" prefix. Use a domain-specific name.

### 4. Use Square Brackets for Placeholders

**CRITICAL**: Use `[{0}]` (square brackets) for placeholders:

```txt
StoreOnboardingContextMessage = [TBD] Onboarding context: store [{0}] ({1}), warehouse [{2}], plan [{3}].
StoreCreatedMessage = [TBD] Store [{0}] ({1}) created successfully.
NotFoundStoreMessage = [TBD] Store with ID [{0}] was not found.
```

**NOT** single quotes:

```txt
// ❌ Bad - harder to read in logs
StoreCreatedMessage = [TBD] Store '{0}' ({1}) created successfully.
```

## Usage in Code

Access via the generated `StringResources` class using `SafeFormat` extension:

```csharp
using {ProjectNamespace}.Resources.Properties;
using MyApp.Framework.Basic.Strings;

// Simple string (no placeholders)
var message = StringResources.StoreOnboardingStartedMessage;

// With formatting - use SafeFormat extension
var message = StringResources.StoreOnboardingContextMessage.SafeFormat(
    storeId,
    storeName,
    warehouseId,
    planId
);
```

### Code Formatting — Closing Parenthesis on New Line

```csharp
// ✅ Good - ); on new line, aligned with statement start
var message = StringResources.StoreOnboardingContextMessage.SafeFormat(
    storeId,
    storeName,
    warehouseId,
    planId
);

// ❌ Bad - ); on same line as last argument
var message = StringResources.StoreOnboardingContextMessage.SafeFormat(
    storeId,
    storeName,
    warehouseId,
    planId);
```

## Runtime Logs vs Session Logs

### Runtime Logs (ILogger) — NEVER Use StringResources or Interpolation

```csharp
// ✅ Good - structured logging with placeholders
_logger.LogInformation(
    "Starting onboarding for store {StoreId} ({StoreName})",
    storeId,
    storeName
);

// ❌ Bad - string interpolation loses structure
_logger.LogInformation($"Starting onboarding for store {storeId} ({storeName})");

// ❌ Bad - StringResources not needed for runtime logs
_logger.LogInformation(StringResources.SomeMessage.SafeFormat(storeId));
```

### Session Logs (ISessionLogRepository) — Use StringResources + SafeFormat

```csharp
// ✅ Good - StringResources with SafeFormat
await _sessionLogRepository.CreateInformationAsync(
    sessionId,
    StringResources.StoreOnboardingContextMessage.SafeFormat(
        storeId,
        storeName,
        warehouseId,
        planId
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

- **Generator**: `MSBuild:Compile`. The build generates the Designer.cs file automatically
- **StronglyTypedClassName**: the generated class name
- **StronglyTypedNamespace**: the namespace of the generated class
- **StronglyTypedFileName**: where the generated file is written

### How to Regenerate

Build the project. The `MSBuild:Compile` generator does the code generation:

```bash
dotnet build
```

**IMPORTANT**: Do NOT run `resgen`, `PublicResXFileCodeGenerator`, or any other tool directly. The build handles code generation automatically via the `EmbeddedResource` MSBuild configuration.

### If Values Don't Appear

**CRITICAL**: If new string resources do not appear after the build:

1. **STOP**. Do NOT manually modify `StringResources.Designer.cs`.
2. **STOP**. Do NOT run `resgen` or any resource generation tool directly.
3. **ASK the user** to regenerate the file (for example, with Visual Studio or another tool).
4. The file is auto-generated, and the next generation overwrites it.

The Designer.cs file contains code like:

```csharp
/// <summary>
///   Looks up a localized string similar to [TBD] Store onboarding started.
/// </summary>
public static string StoreOnboardingStartedMessage {
    get {
        return ResourceManager.GetString("StoreOnboardingStartedMessage", resourceCulture);
    }
}
```

## `[TBD]` Prefix Purpose

The `[TBD]` prefix indicates:

- String is pending review by analysts/tech writers
- The content can change before the release
- DO NOT remove the prefix yourself. Analysts remove it after their review

## Example Workflow

1. Developer adds new session log requirement
2. Add entry to `StringResources.resx`: `StoreFeatureActionMessage = [TBD] Description with [{0}] placeholders.`
3. Regenerate `StringResources.Designer.cs` (build the project)
4. Use in code via `StringResources.StoreFeatureActionMessage.SafeFormat(...)`
5. Analyst reviews and removes `[TBD]` prefix
6. A tech writer can refine the wording

## Example `.resx` Entries

```xml
<data name="StoreOnboardingStartedMessage" xml:space="preserve">
  <value>[TBD] Store onboarding started.</value>
</data>
<data name="StoreOnboardingContextMessage" xml:space="preserve">
  <value>[TBD] Onboarding context: store [{0}] ({1}), warehouse [{2}], plan result [{3}].</value>
</data>
<data name="NotFoundStoreMessage" xml:space="preserve">
  <value>[TBD] Store with ID [{0}] was not found.</value>
</data>
<data name="InvalidStoreIdMessage" xml:space="preserve">
  <value>[TBD] Invalid store ID: [{0}].</value>
</data>
```

## Checklist

- [ ] Entry added to StringResources.resx
- [ ] Name uses CamelCase ending with `Message` (for example, `StoreOnboardingStartedMessage`)
- [ ] Value starts with `[TBD]` prefix
- [ ] Placeholders use square brackets: `[{0}]` not `'{0}'`
- [ ] `StringResources.Designer.cs` regenerated (build the project)
- [ ] The new property is in the generated `StringResources.Designer.cs`
- [ ] Code uses `StringResources.{Name}.SafeFormat(...)` to access
- [ ] Code formatting: `);` on new line, aligned with statement start
- [ ] Runtime logs do NOT use StringResources (use structured logging instead)
