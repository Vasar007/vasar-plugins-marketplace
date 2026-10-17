---
name: dotnet-conventions
description: Hub of .NET backend conventions (Clean Architecture, DDD, EF Core, NSwag, Riok.Mapperly, NUnit). Load it when you write or review .NET backend code. It indexes one reference file for each topic.
---

# .NET Backend Conventions

Reference set for .NET Clean Architecture backends. Each file covers one topic and stands alone. Load the file that matches your current task.

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

## Project-specific details

Examples in each file use generic placeholder names. `MyService` is the service, and `ShippingOptions` is an options class. `Store`, `Order`, and `Customer` are domain entities. `Oms`, `Ps`, `Inv`, and `Cds` are prefixes of external services. In your code, use the actual names of your repo. Do not copy the placeholder names. If your project does not have a framework type of these files, use the closest standard .NET equivalent. For example, use `IEquatable<T>` for `IStaticEquatable<T>`, and `AbstractValidator<T>` from FluentValidation for `Base*ServiceOptionsValidator<T>`.
