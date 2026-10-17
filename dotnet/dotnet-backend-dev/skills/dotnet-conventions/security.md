# Security — Sensitive Data Handling

## What Counts as Sensitive

- **Authentication credentials**: Passwords, secret keys, API tokens, access keys
- **Private cryptographic material**: Private keys, certificates with private data
- **Security tokens**: Session tokens, OAuth tokens, refresh tokens

**Not sensitive** (safe to log): Resource IDs, tenant IDs, region names, usernames (without passwords), instance IDs, timestamps, status codes, version numbers.

## Password Generation

Use `ISecurePasswordGenerator` (Domain layer) for generating secure passwords. The default implementation (typically `Domain.Security.SecurePasswordGenerator` within the service) is wired via DI. Never roll custom password generation.

## ToString() — NEVER Expose Secrets

Use `Constants.DefaultErasedPlaceholder` (from the .NET backend framework) for sensitive fields:

```csharp
private static String DefaultErasedPlaceholder => Constants.DefaultErasedPlaceholder;

public override String ToString()
{
    var sb = new StringBuilder(capacity: 256)
        .Append(nameof(UserCredentials))
        .Append(" {")
        .Append(" HashCode = ").Append(GetHashCode())
        .Append(", UserName = ").Append(UserName)
        .Append(", Password = ").Append(DefaultErasedPlaceholder)  // Erased!
        .Append(" }");
    return sb.ToString();
}
```

- `Equals()` and `GetHashCode()` CAN use sensitive data (internal, never logged).
- `ToString()` MUST erase sensitive fields with the placeholder.
- A serializer does not call `ToString()`. For JSON, see the `handle-sensitive-data` skill.

## Logging — NEVER Log Secrets

### Runtime logs (ILogger)

```csharp
// ✅ Structured logging, no secrets
_logger.LogInformation("Authentication attempt for user {Username}", username);

// ❌ NEVER log passwords/tokens
_logger.LogInformation("Auth: {Username}/{Password}", username, password);
```

### Session logs (ISessionLogRepository)

```csharp
// ✅ Safe identifiers only
await _sessionLogRepository.CreateInformationAsync(sessionId,
    StringResources.UserAuthenticatedMessage.SafeFormat(username),
    cancellationToken: cancellationToken);

// ❌ NEVER log credentials in session logs
```

## When in Doubt

Ask the user whether specific data is sensitive. Context matters. Some identifiers that seem sensitive can be safe in this domain.

Use the `handle-sensitive-data` skill for full guidance.
