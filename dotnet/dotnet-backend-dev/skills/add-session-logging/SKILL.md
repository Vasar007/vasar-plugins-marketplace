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

- Long-running operation milestones (onboarding, data import, account closure)
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
StoreOnboardingStartedMessage = [TBD] Store onboarding started.
StoreOnboardingContextMessage = [TBD] Onboarding context: store [{0}] ({1}), warehouse [{2}], plan result [{3}].
StoreOnboardingCompletedMessage = [TBD] Store onboarding completed successfully.
StoreOnboardingFailedMessage = [TBD] Store onboarding failed.
```

**CRITICAL**: Use `[{0}]` (square brackets) for placeholders.

### Step 2: Inject ISessionLogRepository

```csharp
public sealed class StoreOnboardingOrchestrator
{
    private readonly ISessionLogRepository _sessionLogRepository;
    private readonly ILogger<StoreOnboardingOrchestrator> _logger;

    public StoreOnboardingOrchestrator(
        ISessionLogRepository sessionLogRepository,
        ILogger<StoreOnboardingOrchestrator> logger)
    {
        _sessionLogRepository = sessionLogRepository.ThrowIfNull();
        _logger = logger.ThrowIfNull();
    }
}
```

### Step 3: Log Milestones at Key Points

Use `SafeFormat` extension method for string formatting:

```csharp
using {ProjectNamespace}.Common.Strings;

public async Task OnboardStoreAsync(
    SessionId sessionId,
    StoreOnboardingRequest request,
    CancellationToken cancellationToken)
{
    // Runtime log (developers) - use structured logging, NO string interpolation
    _logger.LogInformation(
        "Starting onboarding for store {StoreId} ({StoreName})",
        request.StoreId,
        request.StoreName
    );

    // Session log (portal users) - use SafeFormat
    await _sessionLogRepository.CreateInformationAsync(
        sessionId,
        StringResources.StoreOnboardingStartedMessage,
        cancellationToken: cancellationToken
    );

    await _sessionLogRepository.CreateInformationAsync(
        sessionId,
        StringResources.StoreOnboardingContextMessage.SafeFormat(
            request.StoreId,
            request.StoreName,
            request.WarehouseId,
            request.PlanId
        ),
        cancellationToken: cancellationToken
    );

    try
    {
        // Step 1: Create account
        var account = await CreateAccountAsync(request, cancellationToken);

        await _sessionLogRepository.CreateInformationAsync(
            sessionId,
            StringResources.StoreAccountCreatedMessage.SafeFormat(
                account.AccountId,
                request.StoreId,
                request.StoreName
            ),
            cancellationToken: cancellationToken
        );

        // Step 2: Configure store
        await ConfigureStoreAsync(account, request, cancellationToken);

        // Success
        await _sessionLogRepository.CreateInformationAsync(
            sessionId,
            StringResources.StoreOnboardingCompletedMessage,
            cancellationToken: cancellationToken
        );
    }
    catch (Exception ex)
    {
        // Runtime log (developers - full details)
        _logger.LogError(
            ex,
            "Store onboarding failed for {StoreId} ({StoreName})",
            request.StoreId,
            request.StoreName
        );

        // Session log (portal users - no exception text)
        await _sessionLogRepository.CreateInformationAsync(
            sessionId,
            StringResources.StoreOnboardingFailedMessage,
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
    "Starting onboarding for store {StoreId} ({StoreName})",
    storeId,
    storeName
);

// ❌ Bad - string interpolation loses structure, hurts log aggregation
_logger.LogInformation($"Starting onboarding for store {storeId} ({storeName})");

// ❌ Bad - String.Format also loses structure
_logger.LogInformation(
    String.Format("Starting onboarding for store {0} ({1})", storeId, storeName)
);
```

### Session Logs — Use SafeFormat Extension

```csharp
using MyApp.Framework.Basic.Strings;

// ✅ Good - SafeFormat extension method
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

// ❌ Bad - String.Format (use SafeFormat instead)
String.Format(StringResources.StoreOnboardingContextMessage, storeId, storeName)
```

### Code Formatting — Closing Parenthesis on New Line

```csharp
// ✅ Good - ); on new line, aligned with statement start
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

// ❌ Bad - ); on same line as last argument
await _sessionLogRepository.CreateInformationAsync(
    sessionId,
    StringResources.StoreOnboardingContextMessage.SafeFormat(
        storeId,
        storeName,
        warehouseId,
        planId),
    cancellationToken: cancellationToken);
```

## Best Practices

### 1. Milestone Granularity

Log at meaningful user-visible milestones:

✅ Good milestones:

- "Store onboarding started"
- "Account created"
- "Configuration completed"
- "Store ready"

❌ Too granular:

- "Parsing request"
- "Validating input"
- "Calling database"

### 2. Entity Logging Format

When logging entities with both ID and name, use format: `"ID (name)"`:

```csharp
// For entities with ID and name
var message = StringResources.StoreCreatedMessage.SafeFormat(
    store.StoreId,
    store.StoreName
);
// Results in: "Store [abc-123] (Corner Books) created"
```

### 3. Error Messages

Session log errors must be user-friendly. Do not write a stack trace or the exception text (`ex.Message`) into a session log. Write the exception to `ILogger`:

```csharp
// ✅ Good - user-friendly
StringResources.StoreOnboardingFailedMessage

// ❌ Bad - technical details
$"NullReferenceException at line 42 in OnboardingService.cs"

// ❌ Bad - the exception text can hold technical details or sensitive data
ex.Message
```

### 4. Sensitive Information

**CRITICAL**: Never log sensitive information in session logs or runtime logs.

**See the [handle-sensitive-data](../handle-sensitive-data/SKILL.md) skill for complete guidance on handling sensitive data.**

### 5. Parallel Operations

When logging parallel operations, include identifiers:

```csharp
await _sessionLogRepository.CreateInformationAsync(
    sessionId,
    StringResources.OrderShippingMessage.SafeFormat(orderId),
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
- [ ] An entity with an ID and a name uses the format `"ID (name)"`
- [ ] Code formatting: `);` on new line, aligned with statement start
