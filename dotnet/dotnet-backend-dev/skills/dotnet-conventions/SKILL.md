---
name: dotnet-conventions
description: Load when writing or reviewing .NET backend code (Clean Architecture with DDD, EF Core, NSwag, Riok.Mapperly, NUnit). Indexes nine reference files covering API controllers, application services, configuration/options, domain models, EF patterns, logging, object mappers, security, and testing conventions used across the .NET backend services.
---

# .NET Backend Conventions

Reference set for .NET Clean Architecture backends. Each file covers one topic and stands alone — load the file matching your current task.

| Topic | File | Load when |
|---|---|---|
| API controllers / WebApi / NSwag | `api-controllers.md` | Writing or reviewing a WebApi controller or the swagger spec |
| Application services / CQRS / background work | `application-services.md` | Writing services in the Application layer |
| Configuration / Options / FluentValidation | `configuration.md` | Adding/editing options classes |
| Domain models / DDD / sealed records / wrappers | `domain-models.md` | Working in the Domain layer |
| EF Core / repository / entity configuration | `ef-patterns.md` | Touching Infrastructure/Persistence |
| Logging / ILogger / session logs | `logging.md` | Adding log calls |
| Object mappers / Riok.Mapperly / converters | `mappers.md` | Creating or editing mappers |
| Security / sensitive data / ToString | `security.md` | Any code touching credentials, tokens, or private keys |
| Testing / NUnit / mock builders / generators | `testing.md` | Writing or reviewing tests |

## How this skill is used

- **Auto-invoked**: when Claude detects .NET backend work (based on solution/csproj naming, framework markers like `IStaticEquatable`/`IEquatable<T>` records, session-log repositories).
- **Manually invoked**: `/dotnet-conventions` or by name.
- **Referenced by other skills**: `create-*` skills link to specific files here for the long-form convention.

## Project-specific details

Examples in each file use generic placeholder names (e.g. `MyService` for the service, `DeploymentOptions` for an options class, `Tenant`/`Appliance` for domain entities, `Ds`/`Ids`/`Sms`/`Dcs` for external-service prefixes). Substitute your repo's actual names when applying these rules — do not hand-propagate the placeholder names. If your project lacks the framework types referenced here (e.g. `IStaticEquatable<T>`, `Base*ServiceOptionsValidator<T>`), use the closest standard .NET equivalent (`IEquatable<T>`, `AbstractValidator<T>` from FluentValidation).
