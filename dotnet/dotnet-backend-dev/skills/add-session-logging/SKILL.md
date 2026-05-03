---
name: add-session-logging
description: Add user-visible session log milestones for long-running workflows. Use when orchestration flows need progress updates (portal/UI). Triggers on requests like "add session log", "portal milestone", "user progress", "track session progress".
---

# Add Session Logging

Add session log milestones using `ISessionLogRepository` for portal-visible progress tracking.

## Two-Phase Logging Architecture

The project uses two types of logging:

| Type         | Interface               | Purpose                | Audience     |
|--------------|-------------------------|------------------------|--------------|
| Runtime Logs | `ILogger`               | Diagnostics, debugging | Developers   |
| Session Logs | `ISessionLogRepository` | Progress milestones    | Portal users |

## When to Use Session Logs

Use `ISessionLogRepository` for:

- Long-running operation milestones (provisioning, upgrading, deprovisioning)
- Steps that users care about seeing
- Success/failure states visible in portal

Use `ILogger` for:

- Debug information
- Technical diagnostics
- Performance metrics
- Internal state changes

## Adding Session Log Milestones

### Step 1: Add String Resources

Add entries to your string resources file (see create-string-resource skill):

```txt
TenantProvisioningStartedMessage = [TBD] Workload tenant provisioning started.
TenantProvisioningContextMessage = [TBD] Provisioning context: tenant [{0}] ({1}), region [{2}], template result [{3}].
TenantProvisioningCompletedMessage = [TBD] Workload tenant provisioning completed successfully.
TenantProvisioningFailedMessage = [TBD] Workload tenant provisioning failed: {0}
```

**CRITICAL**: Use `[{0}]` (square brackets) for placeholders to improve readability per analyst feedback.

### Step 2: Inject ISessionLogRepository

```csharp
public sealed class ProvisioningOrchestrator
{
    private readonly ISessionLogRepository _sessionLogService;
    private readonly ILogger<ProvisioningOrchestrator> _logger;

    public ProvisioningOrchestrator(
        ISessionLogRepository sessionLogService,
        ILogger<ProvisioningOrchestrator> logger)
    {
        _sessionLogService = sessionLogService.ThrowIfNull();
        _logger = logger.ThrowIfNull();
    }
}
```

### Step 3: Log Milestones at Key Points

Use `SafeFormat` extension method for string formatting:

```csharp
using {ProjectNamespace}.Common.Strings;

public async Task ProvisionTenantAsync(
    SessionId sessionId,
    TenantProvisionRequest request,
    CancellationToken cancellationToken)
{
    // Runtime log (developers) - use structured logging, NO string interpolation
    _logger.LogInformation(
        "Starting provisioning for tenant {TenantId} ({TenantName})",
        request.TenantId,
        request.TenantName
    );

    // Session log (portal users) - use SafeFormat
    await _sessionLogService.CreateInformationAsync(
        sessionId,
        StringResources.TenantProvisioningStartedMessage,
        cancellationToken: cancellationToken
    );

    await _sessionLogService.CreateInformationAsync(
        sessionId,
        StringResources.TenantProvisioningContextMessage.SafeFormat(
            request.TenantId,
            request.TenantName,
            request.RegionId,
            request.TemplateId
        ),
        cancellationToken: cancellationToken
    );

    try
    {
        // Step 1: Allocate appliance
        var appliance = await AllocateApplianceAsync(request, cancellationToken);

        await _sessionLogService.CreateInformationAsync(
            sessionId,
            StringResources.TenantApplianceAllocatedMessage.SafeFormat(
                appliance.InstanceId,
                request.TenantId,
                request.TenantName
            ),
            cancellationToken: cancellationToken
        );

        // Step 2: Configure tenant
        await ConfigureTenantAsync(appliance, request, cancellationToken);

        // Success
        await _sessionLogService.CreateInformationAsync(
            sessionId,
            StringResources.TenantProvisioningCompletedMessage,
            cancellationToken: cancellationToken
        );
    }
    catch (Exception ex)
    {
        // Runtime log (developers - full details)
        _logger.LogError(
            ex,
            "Tenant provisioning failed for {TenantId} ({TenantName})",
            request.TenantId,
            request.TenantName
        );

        // Session log (portal users - sanitized message)
        await _sessionLogService.CreateInformationAsync(
            sessionId,
            StringResources.TenantProvisioningFailedMessage.SafeFormat(ex.Message),
            cancellationToken: cancellationToken
        );

        throw;
    }
}
```

## Logging Best Practices

### Runtime Logs (ILogger) — NEVER Use String Interpolation

```csharp
// ✅ Good - structured logging with placeholders
_logger.LogInformation(
    "Starting provisioning for tenant {TenantId} ({TenantName})",
    tenantId,
    tenantName
);

// ❌ Bad - string interpolation loses structure, hurts log aggregation
_logger.LogInformation($"Starting provisioning for tenant {tenantId} ({tenantName})");

// ❌ Bad - String.Format also loses structure
_logger.LogInformation(
    String.Format("Starting provisioning for tenant {0} ({1})", tenantId, tenantName)
);
```

### Session Logs — Use SafeFormat Extension

```csharp
using MyApp.Framework.Basic.Strings;

// ✅ Good - SafeFormat extension method
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

// ❌ Bad - String.Format (use SafeFormat instead)
String.Format(StringResources.TenantProvisioningContextMessage, tenantId, tenantName)
```

### Code Formatting — Closing Parenthesis on New Line

```csharp
// ✅ Good - ); on new line, aligned with statement start
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

// ❌ Bad - ); on same line as last argument
await _sessionLogService.CreateInformationAsync(
    sessionId,
    StringResources.TenantProvisioningContextMessage.SafeFormat(
        tenantId,
        tenantName,
        regionId,
        templateId),
    cancellationToken: cancellationToken);
```

## Best Practices

### 1. Milestone Granularity

Log at meaningful user-visible milestones:

✅ Good milestones:

- "Workload tenant provisioning started"
- "Appliance allocated"
- "Configuration completed"
- "Tenant ready"

❌ Too granular:

- "Parsing request"
- "Validating input"
- "Calling database"

### 2. Entity Logging Format

When logging entities with both ID and name, use format: `"ID (name)"`:

```csharp
// For entities with ID and name
var message = StringResources.TenantCreatedMessage.SafeFormat(
    tenant.TenantId,
    tenant.TenantName
);
// Results in: "Tenant [abc-123] (My Tenant) created"
```

### 3. Error Messages

Session log errors should be user-friendly (no stack traces):

```csharp
// ✅ Good - user-friendly
StringResources.TenantProvisioningFailedMessage.SafeFormat("Unable to allocate resources")

// ❌ Bad - technical details
$"NullReferenceException at line 42 in ProvisioningService.cs"
```

### 4. Sensitive Information

**CRITICAL**: Never log sensitive information in session logs or runtime logs.

**See the [handle-sensitive-data](../handle-sensitive-data/SKILL.md) skill for complete guidance on handling sensitive data.**

### 5. Parallel Operations

When logging parallel operations, include identifiers:

```csharp
await _sessionLogService.CreateInformationAsync(
    sessionId,
    StringResources.ApplianceDeployingMessage.SafeFormat(applianceId),
    cancellationToken: cancellationToken
);
```

## ISessionLogRepository API

The repository interface exposes `AddAsync(CreateSessionLogRequest, ...)`. Convenience extension methods in `ExtensionMethodsSessionLogRepository` provide shorthand for common log levels:

```csharp
// Extension methods (from ExtensionMethodsSessionLogRepository)
await _sessionLogRepository.CreateInformationAsync(sessionId, message, cancellationToken: ct);
await _sessionLogRepository.CreateWarningAsync(sessionId, message, cancellationToken: ct);
await _sessionLogRepository.CreateErrorAsync(sessionId, message, details: ex.ToString(), ct);
```

## Checklist

- [ ] String resources added with `[TBD]` prefix and CamelCase naming
- [ ] Placeholders use square brackets: `[{0}]` not `'{0}'`
- [ ] `ISessionLogRepository` injected into orchestrator
- [ ] `SafeFormat` extension used (NOT `String.Format`)
- [ ] Runtime logs use structured logging (NO string interpolation)
- [ ] Milestones logged at user-meaningful points
- [ ] Both `ILogger` (runtime) and `ISessionLogRepository` (portal) used appropriately
- [ ] Error messages are user-friendly (no technical details)
- [ ] Entity format: `"ID (name)"` when both available
- [ ] Code formatting: `);` on new line, aligned with statement start
