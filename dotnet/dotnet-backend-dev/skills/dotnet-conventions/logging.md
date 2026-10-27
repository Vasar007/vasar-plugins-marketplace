# Logging Conventions

## Contents

- Two Logging Channels
- ILogger Patterns
- ISessionLogRepository Patterns
- Dual Logging Example
- Sensitive Data in Logs

## Two Logging Channels

| Channel                 | Audience              | Persistence                    | Purpose                             |
|-------------------------|-----------------------|--------------------------------|-------------------------------------|
| `ILogger<T>`            | Developers / Ops      | Runtime log files              | Diagnostic, flow tracing, debugging |
| `ISessionLogRepository` | End users (portal UI) | Database (session log entries) | Business milestones, audit trail    |

Use **both** in orchestration services: `ILogger` for the internal flow, and `ISessionLogRepository` for the progress that users see.

## ILogger Patterns

### Log Levels

- **LogInformation**: business milestones, state changes, success events.
- **LogWarning**: degraded states, skipped operations, fallbacks, timeouts.
- **LogDebug**: low-level decisions, quota checks, plan updates, polling iterations.
- **LogError**: exceptions caught at the service level. This is rare, because exceptions usually propagate up.

### Structured Logging (Mandatory)

Use **named placeholders**. Never use composite formatting or string interpolation:

```csharp
// CORRECT — structured
_logger.LogInformation("Onboarding store {StoreId} ({StoreName}).", storeId, storeName);

// WRONG — interpolation (loses structured data)
_logger.LogInformation($"Onboarding store {storeId}.");

// WRONG — composite formatting
_logger.LogInformation("Onboarding store {0}.", storeId);
```

### Event IDs

Each service owns a `{Service}LogEvents` static class (by convention under `Domain/Logging/Events/`) exposing `EventId` constants for significant milestones:

```csharp
_logger.LogInformation(
    {Service}LogEvents.OrderShipmentStarted,
    "Shipping {OrderDescription} [{OrderId}] for session [{SessionId}].",
    orderDescription, orderId, session.Id);
```

If an existing event ID fits, use it. Add a new event ID only for a new milestone.

### Placeholder Naming Conventions

- Use **PascalCase**: `{StoreId}`, `{OrderId}`, `{SessionId}`, `{Count}`, `{Status}`.
- Wrap IDs in **brackets** in the message template: `[{SessionId}]`, `[{OrderId}]`.

## ISessionLogRepository Patterns

### Convenience Methods

Convenience extension methods are in `ExtensionMethodsSessionLogRepository` (framework-provided):

```csharp
await _sessionLogRepository.CreateInformationAsync(sessionId, message, cancellationToken: ct);
await _sessionLogRepository.CreateWarningAsync(sessionId, message, cancellationToken: ct);
await _sessionLogRepository.CreateErrorAsync(sessionId, message, details: ex.ToString(), ct);
```

### Messages from StringResources

All user-facing session log messages must come from the service's `StringResources.resx`. Use `.SafeFormat()` for parameters:

```csharp
await _sessionLogRepository.CreateInformationAsync(
    session.Id,
    StringResources.CatalogSyncReceivedCountMessage.SafeFormat(response.TotalCount),
    cancellationToken: cancellationToken);
```

### Error Details

Pass exception details in the `details` parameter. Never put raw exceptions in the `message`:

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
    {Service}LogEvents.OrderShipmentStarted,
    "Shipping {OrderDescription} [{OrderId}] through the shipping service for session [{SessionId}].",
    orderDescription, orderId, session.Id);

// ISessionLogRepository — user-visible progress
await _sessionLogRepository.CreateInformationAsync(
    session.Id,
    StringResources.OrderShipmentStartedMessage.SafeFormat(orderDescription, orderId),
    cancellationToken: cancellationToken);
```

## Sensitive Data in Logs

- **Never** log passwords, tokens, secrets, or private keys via either channel.
- Log only safe identifiers: resource IDs, tenant IDs, region names, usernames (without passwords).
- See `security.md` for `ToString()` erasing patterns with `Constants.DefaultErasedPlaceholder`.
