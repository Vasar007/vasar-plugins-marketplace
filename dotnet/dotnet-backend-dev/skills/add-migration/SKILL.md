---
name: add-migration
description: Add a database migration. In a standard EF Core repo, it runs `dotnet ef migrations add`. A repo can have the `IDatabaseMigration` and `IProductMigration` interfaces of the framework. There, it writes a migration class for a schema change, a data change, or a product upgrade.
when_to_use: Use it for "add migration", "schema change", "data transformation", or "product upgrade".
---

# Add Migration

Add a migration for a schema change, a data transformation, or a product upgrade. A repo uses one of these migration systems: the standard migrations of EF Core, or the migration system of the framework (`IDatabaseMigration` and `IProductMigration`). Find out which system the repo uses before you write code.

The templates use the private shared framework of the `MyApp.Framework` namespaces. If the repo does not use it, follow the closest existing code of the repo.

## Choose the Migration System

Search the repo for the files and the names below. Then use the row that matches. If the first two rows both match, ask the user which system to use. "Provider" means the database provider that the app uses in production, not a test provider such as SQLite or InMemory:

| The repo has | Use |
| --- | --- |
| A model snapshot of EF Core: a `*ModelSnapshot.cs` file, usually in a `Migrations/` folder | [Standard EF Core Migrations](#standard-ef-core-migrations) for a schema change, or for a data transformation in the `Up` and `Down` methods of a migration |
| Classes that implement `IDatabaseMigration` or `IProductMigration` | The [Framework Migration System](#framework-migration-system), for a schema change, a data transformation, a product upgrade, or a change on a document database |
| Neither, and a relational production provider (for example, SQL Server, PostgreSQL, or SQLite) | [Standard EF Core Migrations](#standard-ef-core-migrations). The first migration also writes the model snapshot |
| Neither, and a document database as the production provider (for example, Cosmos DB) | No migration system. Stop and ask the user. The EF Core provider for Cosmos DB does not support schema migrations |

Do not add the framework interfaces to a repo that does not reference the framework. The build then fails with `CS0246`, because the types do not exist.

## Standard EF Core Migrations

The `dotnet ef` tool writes the migration file and updates the model snapshot. Do not change the snapshot by hand, because it must match the model of the `DbContext`. You can add custom code to the `Up` and `Down` methods of a migration, for example a data backfill with `migrationBuilder.Sql(...)`.

The tool needs the `dotnet-ef` .NET tool, and the startup project needs a reference to the `Microsoft.EntityFrameworkCore.Design` package. If `dotnet ef --version` fails, install the tool. If it shows another major version than the EF Core packages of the repo, run the same command with `update` in place of `install`:

```bash
dotnet tool install --global dotnet-ef --version "<major>.*"
```

`<major>` is the major version of the EF Core packages of the repo, so that the tool matches them.

If the repo lists `dotnet-ef` in a tool manifest (`.config/dotnet-tools.json`), run `dotnet tool restore` instead.

1. Change the entity classes and their configuration first. The tool compares the model with the snapshot and writes the difference.
2. Add the migration. `<Name>` is a PascalCase name for the change, for example `AddOrderDiscount`. `--project` names the project with the `DbContext`. `--startup-project` names the project that starts the app, for example the WebApi project:

   ```bash
   dotnet ef migrations add <Name> --project src/{ProjectName}.Infrastructure --startup-project src/{ProjectName}.WebApi
   ```

   If the repo has more than one `DbContext`, add `--context <DbContextName>`.
3. Read the new migration file. Make sure that `Up` and `Down` hold only the change of step 1. If they also hold other changes, the model and the snapshot were different before your change. Tell the user, and do not remove these changes without approval. If your own change is wrong, run `dotnet ef migrations remove` with the same `--project` and `--startup-project` options. Then fix the model, and go back to step 2. Do not add `--force`, because it also reverts the migration in the database.
4. Build the changed projects with `dotnet build` (see `dev-essentials:dotnet-build-test`). If the build fails, fix the errors and build again.
5. Do not run `dotnet ef database update` unless the user asks for it. The command changes a database.

The [Framework Migration System](#framework-migration-system) section and the [Checklist](#checklist) are for the framework migration system only.

## Framework Migration System

Read [references/framework-migrations.md](references/framework-migrations.md) before you write a framework migration class. If the repo uses Cosmos DB, also read [references/cosmos-db.md](references/cosmos-db.md). For grouping, batches, and legacy data, read [references/common-patterns.md](references/common-patterns.md).

Hard rules of the framework system:

- The ID format is `"YYYYMMDD_Description"`, and each ID is unique.
- The version is higher than the stored version.
- `ExecuteAsync` is idempotent.
- If a Cosmos DB partition key changes, ask the user before you delete the old container.

Build the changed projects, then run the migration tests with a filter (see `dev-essentials:dotnet-build-test`). If the build or a test fails, fix the migration and go back to step 5 of [references/framework-migrations.md](references/framework-migrations.md). Repeat until the build and the migration tests pass. After three failed fix attempts, or for an error outside the changed code, stop and report the last errors. Report the result lines of the last build and the last test run.

## Checklist

This checklist is for the framework migration system. For a standard EF Core migration, use the steps of [Standard EF Core Migrations](#standard-ef-core-migrations).

- [ ] Determined migration type (IDatabaseMigration or IProductMigration)
- [ ] Created migration class in `Infrastructure/Persistence/Migration/{Feature}/`
- [ ] Used correct MigrationId format: `"YYYYMMDD_Description"`
- [ ] Set Version to match product version (for example, "1.1.0.0")
- [ ] Implemented idempotent ExecuteAsync logic
- [ ] Added logging for start, progress, and completion
- [ ] Handled CancellationToken properly
- [ ] For new entity types, added a `DbSet` property to DbContext
- [ ] For new entity types on a document database, added an entity configuration that sets the service container
- [ ] Created a test class that runs against each database provider (NUnit: `[TestFixtureSource]`)
- [ ] Tested empty database scenario
- [ ] Tested happy path (successful migration)
- [ ] Tested idempotency (running twice)
- [ ] Tested invalid/malformed data handling
- [ ] Tested with production data (where available)
- [ ] Tested the removal of legacy data (if applicable)
- [ ] Added XML documentation to migration class
- [ ] Reviewed for performance (batch processing for large datasets)
- [ ] The changed projects build, the migration tests pass, and the report gives the result lines of the last build and test run

## Related Skills

- [create-tests](../create-tests/SKILL.md): Testing patterns for migrations (BaseMockTest, a test fixture for each database provider)
- [create-ef-entity](../create-ef-entity/SKILL.md): Creating entities and repositories
- `dev-essentials:generate-xml-docs`: XML documentation standards
- `dev-essentials:create-documentation`: Documenting migrations in Docs/Migrations/
