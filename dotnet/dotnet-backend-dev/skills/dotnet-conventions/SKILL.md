---
name: dotnet-conventions
description: Hub of .NET backend conventions for Clean Architecture, DDD, and EF Core. It covers API controllers, application services, configuration and options, domain models, EF Core persistence, logging, object mappers, security, and testing.
when_to_use: If you write or review .NET backend code, load it.
---

# .NET Backend Conventions

Reference set for .NET Clean Architecture backends. Each file covers one topic and stands alone. Load the file that matches your current task.

| Topic | File | Load when |
|---|---|---|
| API controllers / WebApi / the OpenAPI code generator (for example, NSwag) | `api-controllers.md` | Writing or reviewing a WebApi controller or the OpenAPI spec |
| Application services / CQRS / background work | `application-services.md` | Writing services in the Application layer |
| Configuration / Options / the validation library (for example, FluentValidation) | `configuration.md` | Adding/editing options classes |
| Domain models / DDD / sealed records / wrappers | `domain-models.md` | Working in the Domain layer |
| EF Core / repository / entity configuration | `ef-patterns.md` | Touching Infrastructure/Persistence |
| Logging / ILogger / session logs | `logging.md` | Adding log calls |
| Object mappers / the mapping library (for example, Riok.Mapperly) / converters | `mappers.md` | Creating or editing mappers |
| Security / sensitive data / ToString | `security.md` | Any code touching credentials, tokens, or private keys |
| Testing / the test framework (for example, NUnit) / mock builders / generators | `testing.md` | Writing or reviewing tests |

## Project-specific details

Examples in each file use generic placeholder names. `MyService` is the service, and `ShippingOptions` is an options class. `Store`, `Order`, and `Customer` are domain entities. `Oms`, `Ps`, `Inv`, and `Cds` are prefixes of external services. In your code, use the actual names of your repo. Do not copy the placeholder names. If your project does not have a framework type of these files, use the closest standard .NET equivalent. For example, use `IEquatable<T>, IEqualityOperators<T, T, Boolean>` for `IStaticEquatable<T>`, and `AbstractValidator<T>` from FluentValidation for `Base*ServiceOptionsValidator<T>`.

Many templates of this plugin use a private shared framework: the `MyApp.Framework` namespaces, and `MyApp.OnlyForTests` in test code. If the repo does not reference that framework, follow the closest existing code of the repo, or use the standard .NET equivalent. Name each gap in the final report.
