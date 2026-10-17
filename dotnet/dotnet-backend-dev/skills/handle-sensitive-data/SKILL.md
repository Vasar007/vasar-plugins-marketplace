---
name: handle-sensitive-data
description: Keep credentials, secrets, and PII out of logs and out of the string form and the serialized form of objects in .NET code. Serialized forms include JSON in logs, API responses, caches, and messages.
when_to_use: Use it for "handle credentials", "sensitive information", "password handling", or "mask a secret in JSON".
---

# Handle Sensitive Data

Guidelines for securely handling sensitive information in code to prevent accidental exposure in logs, debugging output, ToString() representations, or serialized output such as JSON.

## What is Sensitive Information?

**Sensitive data includes:**

- **Authentication credentials**: Passwords, secret keys, API tokens, access keys
- **Private cryptographic material**: Private keys, certificates with private data, signing keys
- **Personal Identifiable Information (PII)**: When not necessary for the operation
- **Security-critical identifiers**: Session tokens, OAuth tokens, refresh tokens

**NOT sensitive (usually safe to log):**

- Public identifiers: Resource IDs, tenant IDs, region names
- Non-secret metadata: Usernames (without passwords), instance IDs, timestamps
- System state: Status codes, operation types, version numbers

If the lists above do not settle whether specific data is sensitive, ask the user. Context matters. Some identifiers that seem sensitive can be safe to log in your domain.

## The Golden Rule

| Operation | Sensitive Data Allowed? | Reason |
| --- | --- | --- |
| `ToString()` | ❌ NO. Use the placeholder. | The output can be logged, shown in a debugger, or exposed externally. |
| `Equals()` | ✅ YES. Safe to use. | Internal comparison, never exposed externally. |
| `GetHashCode()` | ✅ YES. Safe to use. | Internal hashing, never exposed externally. |
| Logging (`ILogger`, `ISessionLogRepository`) | ❌ NO. Never log it. | Logs are persistent and searchable, and they can be shared. |
| Serialization (JSON in logs, API responses, caches, and messages) | ❌ NO. Mask it, leave it out, or encrypt it. | A serializer reads the public properties. It does not call `ToString()`. |

## Erasing Sensitive Data in ToString()

### Standard Erased Placeholder

Use the standard placeholder from framework constants:

```csharp
using MyApp.Framework.Constants;

private static String DefaultErasedPlaceholder => Constants.DefaultErasedPlaceholder;
```

### Example: Domain Model with Credentials

```csharp
using System.ComponentModel.DataAnnotations;
using System.Text;
using MyApp.Framework.Assertions;
using MyApp.Framework.Basic;
using MyApp.Framework.Constants;

namespace MyApp.Domain.Authentication;

/// <summary>
/// Represents user credentials for authentication.
/// </summary>
public sealed record UserCredentials : IStaticEquatable<UserCredentials>
{
    private static StringComparer DefaultStringComparer => StringComparer.Ordinal;
    private static String DefaultErasedPlaceholder => Constants.DefaultErasedPlaceholder;

    [Required]
    public String UserName { get; init; }

    [Required]
    public String Password { get; init; }

    public UserCredentials(String userName, String password)
    {
        UserName = userName.ThrowIfNullOrWhiteSpace();
        Password = password.ThrowIfNullOrWhiteSpace();
    }

    // ✅ Safe - comparison is internal, never logged
    public Boolean Equals(UserCredentials? other)
    {
        if (other is null) return false;
        if (ReferenceEquals(this, other)) return true;

        return DefaultStringComparer.Equals(UserName, other.UserName)
            && DefaultStringComparer.Equals(Password, other.Password);
    }

    // ✅ Safe - hash is internal, never logged
    public override Int32 GetHashCode()
    {
        var hashCode = new HashCode();
        hashCode.Add(UserName, DefaultStringComparer);
        hashCode.Add(Password, DefaultStringComparer);
        return hashCode.ToHashCode();
    }

    // ✅ CRITICAL - password is ERASED, not exposed
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
}
```

**Key points:**

- `Password` is **ERASED** in `ToString()` with placeholder
- `Password` is **USED** in `Equals()` and `GetHashCode()` (safe, internal)
- Including `HashCode` in `ToString()` helps debugging without exposing sensitive data

### Example: Primitive Wrapper with Secret

```csharp
using System.ComponentModel.DataAnnotations;
using MyApp.Framework.Assertions;
using MyApp.Framework.Basic.Wrappers;
using MyApp.Framework.Constants;

namespace MyApp.Domain.Security;

/// <summary>
/// Represents a strongly-typed API secret token.
/// </summary>
public readonly record struct ApiSecretToken : IStringWrapper<ApiSecretToken>
{
    private static StringComparer DefaultStringComparer => StringComparer.Ordinal;
    private static String DefaultErasedPlaceholder => Constants.DefaultErasedPlaceholder;

    public static ApiSecretToken Empty { get; } = new();

    [Required]
    public String Value { get; init; }

    public Boolean IsEmpty => this == Empty;

    public ApiSecretToken() { Value = String.Empty; }
    private ApiSecretToken(String value) { Value = value.ThrowIfNullOrWhiteSpace(); }

    public static ApiSecretToken FromValue(String value) => new(value);

    // ✅ Safe - comparison is internal
    public Boolean Equals(ApiSecretToken other) => 
        DefaultStringComparer.Equals(Value, other.Value);

    // ✅ Safe - hash is internal
    public override Int32 GetHashCode() => 
        DefaultStringComparer.GetHashCode(Value);

    // ✅ CRITICAL - never expose actual token
    public override String ToString()
    {
        return DefaultErasedPlaceholder;
    }
}
```

## Erasing Sensitive Data in Serialized Output

A serializer turns an object into text, for example JSON. Code serializes objects for logs, API responses, caches, and messages. A serializer does not call `ToString()`. It reads the public properties. So the `ToString()` override above does not protect the JSON form. Without more code, `System.Text.Json` writes `ApiSecretToken.FromValue("s3cr3t")` as `{"Value":"s3cr3t","IsEmpty":false}`.

The raw value must never go into serialized output. Mask it, leave it out, or encrypt it. The table in "Mask, Leave Out, or Encrypt" below says which one to use.

### Example: JSON Converter for a Secret Wrapper

This example uses `System.Text.Json`, the JSON serializer that ships with .NET. ASP.NET Core uses it for JSON responses by default. If the project uses another serializer, add the same mask to that serializer.

```csharp
using System.Text.Json;
using System.Text.Json.Serialization;
using MyApp.Framework.Constants;

namespace MyApp.Domain.Security;

/// <summary>
/// Writes the erased placeholder in place of the value of an <see cref="ApiSecretToken"/>.
/// </summary>
public sealed class ApiSecretTokenJsonConverter : JsonConverter<ApiSecretToken>
{
    private static String DefaultErasedPlaceholder => Constants.DefaultErasedPlaceholder;

    // ✅ CRITICAL - the JSON gets the placeholder, never the token
    public override void Write(
        Utf8JsonWriter writer,
        ApiSecretToken value,
        JsonSerializerOptions options)
    {
        writer.WriteStringValue(DefaultErasedPlaceholder);
    }

    // No round trip - the placeholder is not the token
    public override ApiSecretToken Read(
        ref Utf8JsonReader reader,
        Type typeToConvert,
        JsonSerializerOptions options)
    {
        throw new NotSupportedException(
            $"{nameof(ApiSecretToken)} cannot be read from JSON. Its JSON form holds only the placeholder.");
    }
}

// Register the converter on the wrapper type
[JsonConverter(typeof(ApiSecretTokenJsonConverter))]
public readonly record struct ApiSecretToken : IStringWrapper<ApiSecretToken>
{
    // Members as in "Example: Primitive Wrapper with Secret"
}
```

```csharp
var json = JsonSerializer.Serialize(new
{
    Endpoint = "https://api.example.com",
    Token = ApiSecretToken.FromValue("s3cr3t"),
});
// {"Endpoint":"https://api.example.com","Token":"<the placeholder>"}
```

**Key points:**

- `Write()` writes the placeholder, never the value
- `Read()` throws `NotSupportedException`, because the placeholder is not the value. A silent read gives a wrong token.
- `[JsonConverter]` on the type applies everywhere the serializer finds the type. A converter in `JsonSerializerOptions.Converters` or a `[JsonConverter]` on a property wins over it. Do not register another converter for the type.

A team that keeps the Domain layer free of serializer attributes can skip `[JsonConverter]` on the type. It can add the converter to `JsonSerializerOptions.Converters` at the composition root instead.

### Models with a Secret in a Plain String

If a model holds a secret in a plain `String` property, for example `UserCredentials.Password`, put `[JsonIgnore]` on the property. The serializer then leaves out the property. A better fix is a wrapper type for the secret with a converter as above.

If you cannot change the type, for example a generated model, add a modifier to `DefaultJsonTypeInfoResolver.Modifiers` in the serializer options. The modifier removes the property from `JsonTypeInfo.Properties`.

### Mask, Leave Out, or Encrypt

| Destination | Needs the value back? | What to do |
| --- | --- | --- |
| Logs | No | Do not log the object. If a log call writes the object as JSON with `System.Text.Json`, the converter writes the placeholder. |
| API responses | No | Leave out the secret. The response model has no field for it. If the client must know that a value exists, send the placeholder. |
| Caches | Yes | Encrypt the value, or do not cache it. |
| Messages, for example queue messages and events | Yes | Send a reference to the secret, for example its name in the secret store. Or encrypt the value. |

A mask breaks the round trip. If a cache or a message must give the value back, do not serialize the wrapper type. Map it to a storage model that holds the encrypted value in a `String` property. Use the encryption API of the project, for example the ASP.NET Core Data Protection API (`IDataProtector.Protect()` and `IDataProtector.Unprotect()`). If you do not know which encryption API or secret store the project uses, ask the user.

Some logging libraries build a structure from the properties of an object and do not use the converter. An example is the `@` operator of Serilog. Do not pass an object with sensitive data to such a call. By default, the `[LogProperties]` attribute of the .NET logging extensions calls `ToString()` on each property, so a wrapper type keeps its placeholder.

## Never Log Sensitive Data

### Session Logs (ISessionLogRepository)

```csharp
// ❌ NEVER log credentials
await _sessionLogRepository.CreateInformationAsync(
    sessionId,
    $"User credentials: {username}/{password}",  // NEVER!
    cancellationToken: cancellationToken
);

// ❌ NEVER log API tokens
await _sessionLogRepository.CreateInformationAsync(
    sessionId,
    $"Using API key: {apiKey}",  // NEVER!
    cancellationToken: cancellationToken
);

// ✅ Log username WITHOUT password
await _sessionLogRepository.CreateInformationAsync(
    sessionId,
    StringResources.UserAuthenticatedMessage.SafeFormat(username),
    cancellationToken: cancellationToken
);

// ✅ Log non-sensitive identifiers
await _sessionLogRepository.CreateInformationAsync(
    sessionId,
    StringResources.ApiConnectionEstablishedMessage.SafeFormat(apiEndpoint),
    cancellationToken: cancellationToken
);
```

### Runtime Logs (ILogger)

```csharp
// ❌ NEVER log credentials
_logger.LogInformation("Authenticating user {Username} with password {Password}", username, password);

// ❌ NEVER log secret keys
_logger.LogDebug("API key: {ApiKey}", apiKey);

// ✅ Log authentication attempts WITHOUT credentials
_logger.LogInformation("Authentication attempt for user {Username}", username);

// ✅ Log connection info WITHOUT secrets
_logger.LogDebug("Connecting to {ApiEndpoint} with authentication", apiEndpoint);
```

## When Username Alone is Sensitive

In some contexts, even usernames can be sensitive, for example internal account names. Always consider these points:

1. **Public vs Internal Systems**: Internal usernames can reveal the structure of the organization
2. **Compliance Requirements**: GDPR and HIPAA can classify usernames as PII
3. **Security Policies**: Your organization's data classification

```csharp
// If username is also sensitive, erase it too
public override String ToString()
{
    var sb = new StringBuilder(capacity: 256)
        .Append(nameof(UserCredentials))
        .Append(" {")
        .Append(" HashCode = ").Append(GetHashCode())
        .Append(", UserName = ").Append(DefaultErasedPlaceholder)  // Also erased!
        .Append(", Password = ").Append(DefaultErasedPlaceholder)
        .Append(" }");

    return sb.ToString();
}
```

## Questions for the User

If you are not sure whether data is sensitive, ask the user about these points before you implement:

1. **What data is sensitive in your domain?**
   - Some GUIDs/IDs can be public identifiers (safe)
   - Others can be security-critical tokens (sensitive)

2. **What are the compliance requirements?**
   - GDPR, HIPAA, SOC2, PCI-DSS requirements
   - Data retention and logging policies

3. **What is the deployment environment?**
   - Production logs can be shared with support teams
   - Development logs can have fewer restrictions

4. **What is the debugging impact?**
   - Erasing too much makes debugging harder
   - Erasing too little creates security risks

5. **Where does serialized data go?**
   - A cache or a message that needs the value back needs encryption or a reference
   - Which encryption API or secret store does the project use?

## Common Patterns

### Pattern 1: Credentials Pair (Username + Password)

```csharp
// Erase password, keep username (if username is not PII)
.Append(", UserName = ").Append(UserName)
.Append(", Password = ").Append(DefaultErasedPlaceholder)
```

### Pattern 2: API Key/Token (Single Secret)

```csharp
// Erase entire token
public override String ToString()
{
    return DefaultErasedPlaceholder;
}
```

### Pattern 3: Certificate with Private Key

```csharp
// Show thumbprint (public), erase private key
.Append(", Thumbprint = ").Append(Thumbprint)
.Append(", PrivateKey = ").Append(DefaultErasedPlaceholder)
```

### Pattern 4: Connection String

```csharp
// Show server/database, erase credentials
.Append(", Server = ").Append(Server)
.Append(", Database = ").Append(Database)
.Append(", Credentials = ").Append(DefaultErasedPlaceholder)
```

## Why Equals() and GetHashCode() Can Use Sensitive Data

**These methods are safe because:**

1. **Internal operations**: Used for collections (Dictionary, HashSet), never exposed externally
2. **No logging**: Results are never logged or displayed
3. **Required for correctness**: Two credentials with same username/password MUST be equal
4. **No security risk**: Hash codes do not reveal the original sensitive data

**Example:**

```csharp
var creds1 = new UserCredentials("admin", "secret123");
var creds2 = new UserCredentials("admin", "secret123");

// Must be true - requires comparing passwords
var areEqual = creds1.Equals(creds2);  // Safe, internal comparison

// Must work in Dictionary - requires hashing password
var dict = new Dictionary<UserCredentials, String>();
dict[creds1] = "session-id";  // Safe, internal hashing
```

## Security Review Checklist

- [ ] Identified all sensitive properties in model/wrapper
- [ ] Asked the user about each item of data that the lists did not clearly classify
- [ ] `ToString()` uses `DefaultErasedPlaceholder` for sensitive fields
- [ ] Each wrapper type with a secret has a JSON converter that writes `DefaultErasedPlaceholder`
- [ ] Each plain `String` property with a secret has `[JsonIgnore]`
- [ ] API response models have no field for sensitive data
- [ ] Caches and messages hold encrypted values or references, never raw values
- [ ] `Equals()` compares sensitive data correctly (safe)
- [ ] `GetHashCode()` includes sensitive data in hash (safe)
- [ ] Session logs never expose sensitive data
- [ ] Runtime logs never expose sensitive data
- [ ] String resources for logging avoid placeholders for sensitive data
- [ ] Tests verify that `ToString()` does not leak sensitive data
- [ ] Tests make sure that the JSON of each wrapper type with a secret holds only the placeholder
- [ ] Documentation warns about sensitive data handling

## References

- [create-domain-model](../create-domain-model/SKILL.md): domain model conventions
- [create-primitive-wrapper](../create-primitive-wrapper/SKILL.md): primitive wrapper conventions
- [add-session-logging](../add-session-logging/SKILL.md): logging best practices
- [create-tests](../create-tests/SKILL.md): testing conventions
