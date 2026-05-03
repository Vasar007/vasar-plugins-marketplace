# Application Layer — Service Conventions

## Directory Structure

```text
Application/
  {Domain}/
    Services/
      I{Name}Service.cs        (interface)
      {Name}Service.cs          (sealed implementation)
    Requests/
      {Name}Request.cs          (request/query DTOs)
    Repositories/
      I{Entity}Repository.cs    (repository interface)
    Converters/
      {Entity}Converter.cs      (Mapperly converters)
```

## Service Class Pattern

```csharp
public sealed class {Name}Service : I{Name}Service
{
    private readonly ILogger<{Name}Service> _logger;
    private readonly I{Entity}Repository _{entity}Repository;

    public {Name}Service(
        ILogger<{Name}Service> logger,
        I{Entity}Repository {entity}Repository)
    {
        _logger = logger.ThrowIfNull();
        _{entity}Repository = {entity}Repository.ThrowIfNull();
    }
}
```

Repositories are injected directly via constructor — do **not** use `IUnitOfWork` to access them.

## Query vs Command Separation

### Queries (read-only)

- `FindByPrimaryKeyAsync(id, ct)` — returns `T?` (nullable, safe lookup).
- `GetByPrimaryKeyAsync(id, ct)` — returns `T`, throws `NotFoundException` if missing.
- `GetAllAsync(ct)` — returns `IReadOnlyList<T>`.
- `GetAllByQueryAsync(query, ct)` — returns `ItemsPage<T>` (pagination).
- Query interfaces may inherit `IFinder<T, TId>` from the framework.

### Commands (mutations)

- `CreateAsync(request, ct)` — returns `T`.
- `UpdateAsync(entity, ct)` — returns `void` or `T`.
- `AddAsync(entity, ct)` — returns `void`.
- `DeleteByPrimaryKeyAsync(id, ct)` — returns `void`.
- **Repositories call `SaveChangesAsync` internally** — callers must NOT call it. One save per logical operation happens inside the repository method.

## Repository Access — Direct Injection

```csharp
// CORRECT — inject repositories directly via constructor
public MyService(ISessionRepository sessionRepository)
{
    _sessionRepository = sessionRepository.ThrowIfNull();
}

var entity = await _sessionRepository.FindByPrimaryKeyAsync(id, ct);

// WRONG — IUnitOfWork no longer exists
public MyService(IUnitOfWork unitOfWork) // ❌ REMOVED
```

## Input Validation

- All input parameters: `.ThrowIfNull()`.
- Enum parameters: `.ThrowIfUndefined()`.
- CancellationToken: `cancellationToken.ThrowIfCancellationRequested()` at entry.
- Delegate domain validation to entity methods (e.g., `session.ChangeStatus(newStatus)`).

## Error Handling

- `FindByPrimaryKeyAsync()` returns `null` — caller decides.
- `GetByPrimaryKeyAsync()` throws `NotFoundException` — when entity must exist.
- Domain exceptions propagate naturally — services do not catch them.
- User-facing messages from `StringResources`.
- Document exceptions in interface XML docs:

```csharp
/// <exception cref="NotFoundException">The session has not been found.</exception>
/// <exception cref="OperationCanceledException">The token has had cancellation requested.</exception>
```

## DI Registration

Located in the Application layer's DI extensions (commonly `Application/Configuration/ApplicationDependencyInjection.cs`):

```csharp
serviceCollection.AddScoped<ISessionService, SessionService>();
```

- **Scoped** (default): services with repository access.
- **Singleton**: stateless services or caches (e.g., token providers).

## Background Task Orchestration

For long-running operations (provisioning/deprovisioning):

1. Create a `Session` immediately and return it to the caller.
2. Queue background work via `IBackgroundTaskQueue`.
3. Create a new DI scope with `IServiceScopeFactory` for the background task.
4. Use app-level `CancellationTokenSource.Token` — never the request's cancellation token.

```csharp
var session = await _sessionRepository.AddAsync(request, cancellationToken);

_ = _backgroundTaskQueue.Queue(
    () => DoWorkOnBackgroundAsync(session, request, _cancellationTokenSource.Token),
    _cancellationTokenSource.Token);

return session;  // Return immediately

private async Task DoWorkOnBackgroundAsync(...)
{
    await using var scope = _scopeFactory.CreateAsyncScope();
    var service = scope.ServiceProvider.GetRequiredService<IProvisionService>();
    await service.ProvisionAsync(session, request, cancellationToken);
}
```

## Domain Logic Delegation

Services orchestrate — domain validates. Delegate business rules to entity methods:

```csharp
// CORRECT — domain entity validates status transition
session.ChangeStatus(newStatus);

// WRONG — service implements domain logic
if (session.Status == SessionStatus.Running && newStatus == SessionStatus.Completed) // ❌
```
