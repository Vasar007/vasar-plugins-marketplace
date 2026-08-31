# Logging Conventions

## Two Logging Channels

| Channel                 | Audience              | Persistence                    | Purpose                             |
|-------------------------|-----------------------|--------------------------------|-------------------------------------|
| `ILogger<T>`            | Developers / Ops      | Runtime log files              | Diagnostic, flow tracing, debugging |
| `ISessionLogRepository` | End users (portal UI) | Database (session log entries) | Business milestones, audit trail    |

Use **both** in orchestration services — `ILogger` for internal flow, `ISessionLogRepository` for user-visible progress.

## ILogger Patterns

### Log Levels

- **LogInformation** — Business milestones, state changes, success events.
- **LogWarning** — Degraded states, skipped operations, fallbacks, timeouts.
- **LogDebug** — Low-level decisions, quota checks, plan updates, polling iterations.
- **LogError** — Exceptions caught at service level (rare; usually propagated up).

### Structured Logging (Mandatory)

Use **named placeholders** — never composite formatting or string interpolation:

```csharp
// CORRECT — structured
_logger.LogInformation("Deploying resources for tenant {TenantId} ({TenantName}).", tenantId, tenantName);

// WRONG — interpolation (loses structured data)
_logger.LogInformation($"Deploying resources for tenant {tenantId}.");

// WRONG — composite formatting
_logger.LogInformation("Deploying resources for tenant {0}.", tenantId);
```

### Event IDs

Each service owns a `{Service}LogEvents` static class (by convention under `Domain/Logging/Events/`) exposing `EventId` constants for significant milestones:

```csharp
_logger.LogInformation(
    {Service}LogEvents.ProvisionedResourceDeletionStarted,
    "Deleting {ResourceDescription} [{DeploymentId}] for session [{SessionId}].",
    resourceDescription, deploymentId, session.Id);
```

Use an existing event ID where one fits; only add a new one for a genuinely new milestone.

### Placeholder Naming Conventions

- Use **PascalCase**: `{TenantId}`, `{ResourceId}`, `{SessionId}`, `{Count}`, `{Status}`.
- Wrap IDs in **brackets** in the message template: `[{SessionId}]`, `[{DeploymentId}]`.

## ISessionLogRepository Patterns

### Convenience Methods

Convenience extension methods are in `ExtensionMethodsSessionLogRepository` (framework-provided):

```csharp
await _sessionLogRepository.CreateInformationAsync(sessionId, message, cancellationToken: ct);
await _sessionLogRepository.CreateWarningAsync(sessionId, message, cancellationToken: ct);
await _sessionLogRepository.CreateErrorAsync(sessionId, message, details: ex.ToString(), ct);
```

### Messages from StringResources

All user-facing session log messages MUST come from the service's `StringResources.resx`. Use `.SafeFormat()` for parameters:

```csharp
await _sessionLogRepository.CreateInformationAsync(
    session.Id,
    StringResources.RegionSyncReceivedCountMessage.SafeFormat(response.TotalCount),
    cancellationToken: cancellationToken);
```

### Error Details

Pass exception details via the `details` parameter — never include raw exceptions in the `message`:

```csharp
await _sessionLogRepository.CreateErrorAsync(
    session.Id,
    StringResources.AccountCreationFailedMessage,
    details: ex.ToString(),
    CancellationToken.None);
```

## Dual Logging Example

Orchestration services typically log to both channels at each milestone:

```csharp
// ILogger — internal diagnostic
_logger.LogInformation(
    {Service}LogEvents.ProvisionedResourceDeletionStarted,
    "Deleting {ResourceDescription} [{DeploymentId}] via the infrastructure deployment service for session [{SessionId}].",
    resourceDescription, deploymentId, session.Id);

// ISessionLogRepository — user-visible progress
await _sessionLogRepository.CreateInformationAsync(
    session.Id,
    StringResources.ProvisionedResourceDeletionStartedMessage.SafeFormat(resourceDescription, deploymentId),
    cancellationToken: cancellationToken);
```

## Sensitive Data in Logs

- **NEVER** log passwords, tokens, secrets, or private keys via either channel.
- Log only safe identifiers: resource IDs, tenant IDs, region names, usernames (without passwords).
- See `security.md` for `ToString()` erasing patterns with `Constants.DefaultErasedPlaceholder`.
