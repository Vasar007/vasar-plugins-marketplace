# Migration Testing Patterns

Testing patterns for database and product migrations using Framework migration system.

## Overview

Migration tests verify:

- Empty database scenario (idempotency when nothing to migrate)
- Successful data transformation (happy path)
- Idempotency (running twice produces same result)
- Invalid data handling (graceful skipping/error handling)
- Multiple records/sessions
- Production data compatibility

## Test Fixture Structure

### TestDbContextFactory Requirement

Migration tests MUST use `[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]` because:

- DbContext comes from DI container (via `IMigrationContext`)
- Migration engine retrieves services from `IServiceProvider`
- Must test against InMemory, SQLite, and the document-database provider

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]
public sealed class EmbedCustomerAccountsInTemplateMigrationTests<TTestDbContextFactory> : BaseMockTest
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    private readonly TTestDbContextFactory _testDbContextFactory;

    public EmbedCustomerAccountsInTemplateMigrationTests()
    {
        _testDbContextFactory = new TTestDbContextFactory();
    }

    // Tests...
}
```

## Required Helper Methods

### SetupServiceProvider

Configure DI container with all required services:

```csharp
private ServiceProvider SetupServiceProvider()
{
    var services = new ServiceCollection();
    services.AddLogging();
    services.AddHttpClientWithOptions();
    services.AddSharedInfrastructureServices();
    services.AddSharedDomainServices();
    services.AddPersistenceServices();

    var databaseOptions = _testDbContextFactory.CreateDatabaseOptions();
    services.Configure<DatabaseOptions>(options =>
    {
        options.ProviderType = databaseOptions.ProviderType;
        options.InMemory = databaseOptions.InMemory;
        options.Sqlite = databaseOptions.Sqlite;
        options.DocumentDb = databaseOptions.DocumentDb;
    });

    services.AddDbContextWithConfiguredOptions<ServiceDbContext>();

    return services.BuildServiceProvider();
}
```

### CreateMigrationContext

Create migration context for migration execution:

```csharp
private static IMigrationContext CreateMigrationContext(IServiceProvider serviceProvider)
{
    var optionsMonitor = serviceProvider.GetRequiredService<IOptionsMonitor<DatabaseOptions>>();

    return new MigrationContext<ServiceDbContext>(
        serviceProvider: serviceProvider,
        databaseOptions: optionsMonitor
    );
}
```

### CreateMigration

Instantiate migration with mocked logger:

```csharp
private EmbedCustomerAccountsInTemplateMigration CreateMigration()
{
    var logger = TestLoggerBuilder.CreateWithoutSetup<EmbedCustomerAccountsInTemplateMigration>(Fixture);
    return new EmbedCustomerAccountsInTemplateMigration(logger);
}
```

## Essential Test Scenarios

### 1. Empty Database (Idempotency Check)

Verify migration completes without errors when no data exists:

```csharp
[Test]
public async Task ExecuteAsync_ShouldComplete_WhenDatabaseIsEmpty()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newTemplates = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    newTemplates.Should().BeEmpty();
}
```

### 2. Happy Path (Successful Migration)

Verify migration successfully transforms records:

```csharp
[Test]
public async Task ExecuteAsync_ShouldMigrateGenerateOnlyRecord()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var generateResult = _templateLegacyGenerator.GenerateCloudResourceGenerateResult();
    var legacyRecord = CreateLegacyGenerateRecord(session.Id, generateResult);
    await dbContext.CloudResourceOperationResultsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newTemplates = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    newTemplates.Should().HaveCount(1);

    var newTemplate = newTemplates[0];
    newTemplate.Id.Should().Be(legacyRecord.Id);
    newTemplate.SessionId.Should().Be(session.Id.Value);
    newTemplate.GenerateParameters.Should().NotBeNull();
    newTemplate.GenerateResult.Should().NotBeNull();
    newTemplate.CustomerAccounts.Should().BeEmpty();

    // Verify legacy record was removed.
    var legacyRecords = await dbContext.CloudResourceOperationResultsLegacy.ToListAsync();
    legacyRecords.Should().BeEmpty();
}
```

### 3. Complex Transformation

Test migration with multiple related records:

```csharp
[Test]
public async Task ExecuteAsync_ShouldMigrateGenerateAndApplicationRecords()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var generateResult = _templateLegacyGenerator.GenerateCloudResourceGenerateResult();
    var applicationResult = _templateLegacyGenerator.GenerateCloudResourceApplicationResult(customerAccountCount: 2);

    var legacyGenerateRecord = CreateLegacyGenerateRecord(session.Id, generateResult);
    var legacyApplicationRecord = CreateLegacyApplicationRecord(session.Id, applicationResult);

    await dbContext.CloudResourceOperationResultsLegacy.AddRangeAsync(legacyGenerateRecord, legacyApplicationRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newTemplates = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    newTemplates.Should().HaveCount(1);

    var newTemplate = newTemplates[0];
    newTemplate.Id.Should().Be(legacyGenerateRecord.Id);
    newTemplate.SessionId.Should().Be(session.Id.Value);
    newTemplate.GenerateParameters.Should().NotBeNull();
    newTemplate.GenerateResult.Should().NotBeNull();
    newTemplate.CustomerAccounts.Should().HaveCount(2);

    // Verify customer accounts were migrated.
    foreach (var account in newTemplate.CustomerAccounts)
    {
        account.Id.Should().NotBeEmpty();
        account.AccountId.Should().NotBeNullOrWhiteSpace();
        account.RoleName.Should().NotBeNullOrWhiteSpace();
    }

    // Verify legacy records were removed.
    var legacyRecords = await dbContext.CloudResourceOperationResultsLegacy.ToListAsync();
    legacyRecords.Should().BeEmpty();
}
```

### 4. Idempotency

Verify running twice produces same result:

```csharp
[Test]
public async Task ExecuteAsync_ShouldBeIdempotent()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var generateResult = _templateLegacyGenerator.GenerateCloudResourceGenerateResult();
    var legacyRecord = CreateLegacyGenerateRecord(session.Id, generateResult);

    await dbContext.CloudResourceOperationResultsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    var newTemplatesAfterFirstRun = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    var firstRunCount = newTemplatesAfterFirstRun.Count;

    // Run migration again.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newTemplatesAfterSecondRun = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    newTemplatesAfterSecondRun.Should().HaveCount(firstRunCount);
    newTemplatesAfterSecondRun[0].Id.Should().Be(newTemplatesAfterFirstRun[0].Id);
}
```

### 5. Invalid Data Handling

Verify migration skips records with missing required data:

```csharp
[Test]
public async Task ExecuteAsync_ShouldSkipRecord_WhenGenerateRecordIsMissing()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    // Only Application record, no Generate record.
    var applicationResult = _templateLegacyGenerator.GenerateCloudResourceApplicationResult(customerAccountCount: 1);
    var legacyRecord = CreateLegacyApplicationRecord(session.Id, applicationResult);

    await dbContext.CloudResourceOperationResultsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newTemplates = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    newTemplates.Should().BeEmpty();

    // Legacy record should remain since migration skipped it.
    var legacyRecords = await dbContext.CloudResourceOperationResultsLegacy.ToListAsync();
    legacyRecords.Should().HaveCount(1);
}
```

### 6. Malformed JSON Handling

Verify migration handles invalid JSON gracefully:

```csharp
[Test]
public async Task ExecuteAsync_ShouldSkipRecord_WhenGenerateResultJsonIsInvalid()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var legacyRecord = new CloudResourceOperationResultLegacyEntity
    {
        Id = GenerateCloudResourceOperationResultId().Value,
        SessionId = session.Id.Value,
        ResultType = CloudResourceOperationResultTypeLegacyEntity.Generate,
        Result = "{ invalid json }",
    };

    await dbContext.CloudResourceOperationResultsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newTemplates = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    newTemplates.Should().BeEmpty();

    var legacyRecords = await dbContext.CloudResourceOperationResultsLegacy.ToListAsync();
    legacyRecords.Should().HaveCount(1);
}
```

### 7. Multiple Sessions

Test batch processing across multiple sessions:

```csharp
[Test]
public async Task ExecuteAsync_ShouldMigrateMultipleSessions()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session1 = await sessionRepository.AddSessionAsync(CreateSession());
    var session2 = await sessionRepository.AddSessionAsync(CreateSession());
    var session3 = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var generateResult1 = _templateLegacyGenerator.GenerateCloudResourceGenerateResult();
    var generateResult2 = _templateLegacyGenerator.GenerateCloudResourceGenerateResult();
    var generateResult3 = _templateLegacyGenerator.GenerateCloudResourceGenerateResult();

    await dbContext.CloudResourceOperationResultsLegacy.AddRangeAsync(
        CreateLegacyGenerateRecord(session1.Id, generateResult1),
        CreateLegacyGenerateRecord(session2.Id, generateResult2),
        CreateLegacyGenerateRecord(session3.Id, generateResult3)
    );
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newTemplates = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    newTemplates.Should().HaveCount(3);

    var legacyRecords = await dbContext.CloudResourceOperationResultsLegacy.ToListAsync();
    legacyRecords.Should().BeEmpty();
}
```

## Production Data Testing

### Loading Production Data from JSON

Test migration against real production data exported from database:

```csharp
[Test]
public async Task ExecuteAsync_ShouldMigrateRealProductionData()
{
    // Arrange & Act.
    var result = await RunMigrationWithProductionDataAsync(
        jsonFileName: "MyService_CloudResourceOperationResults_seed.json",
        expectedTotalRecords: 162,
        expectedSessionCount: 86
    );

    // Assert.
    result.MigratedTemplates.Should().HaveCount(86, "each unique session should have one migrated template");

    // Verify all templates have GenerateParameters and GenerateResult.
    result.MigratedTemplates.Should().AllSatisfy(t =>
    {
        t.GenerateParameters.Should().NotBeNull("all production records have Generate data");
        t.GenerateResult.Should().NotBeNull("all production records have Generate results");
    });

    // Verify customer accounts were migrated for templates that had Application records.
    var templatesWithAccounts = result.MigratedTemplates.Where(t => t.CustomerAccounts.IsNotEmpty()).ToList();
    templatesWithAccounts.Should().HaveCount(35, "35 sessions have Application records with non empty customer accounts");

    // Verify all customer accounts have required fields.
    foreach (var template in templatesWithAccounts)
    {
        template.CustomerAccounts.Should().AllSatisfy(account =>
        {
            account.Id.Should().NotBeEmpty();
            account.AccountId.Should().NotBeNullOrWhiteSpace();
            account.RoleName.Should().NotBeNullOrWhiteSpace();
        });
    }

    // Verify legacy records were removed.
    result.LegacyRecordsAfterMigration.Should().BeEmpty("all legacy records should be removed after successful migration");
}
```

### Helper Method for Production Data

```csharp
private async Task<ProductionMigrationResult> RunMigrationWithProductionDataAsync(
    String jsonFileName,
    Int32 expectedTotalRecords,
    Int32 expectedSessionCount)
{
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    // Load real production data from JSON file.
    var jsonFilePath = Path.Combine(
        TestContext.CurrentContext.WorkDirectory,
        "Persistence",
        "Migration",
        "CloudResources",
        "Templates",
        jsonFileName
    );
    var jsonText = await File.ReadAllTextAsync(jsonFilePath);
    var productionRecords = JsonSerializer.Deserialize<List<CloudResourceOperationResultLegacyRecord>>(jsonText);
    productionRecords.Should().NotBeNull();
    productionRecords.Should().HaveCount(expectedTotalRecords, $"the exported file contains {expectedTotalRecords} records");
    productionRecords.ThrowIfNull();

    // Group by SessionId to create sessions and legacy records.
    var sessionGroups = productionRecords
        .GroupBy(r => r.SessionId)
        .ToList();

    sessionGroups.Should().HaveCount(expectedSessionCount, $"there are {expectedSessionCount} unique sessions in the production data");

    // Create all sessions first.
    var sessionIdMap = new Dictionary<Guid, SessionId>();
    foreach (var group in sessionGroups)
    {
        var session = await sessionRepository.AddSessionAsync(CreateSession());
        sessionIdMap[group.Key] = session.Id;
    }
    await sessionRepository.SaveChangesAsync();

    // Create legacy records using the mapped session IDs.
    var legacyRecords = new List<CloudResourceOperationResultLegacyEntity>();
    foreach (var record in productionRecords)
    {
        var mappedSessionId = sessionIdMap[record.SessionId];
        legacyRecords.Add(new CloudResourceOperationResultLegacyEntity
        {
            Id = record.Id,
            SessionId = mappedSessionId.Value,
            ResultType = record.ResultType == 1
                ? CloudResourceOperationResultTypeLegacyEntity.Generate
                : CloudResourceOperationResultTypeLegacyEntity.Application,
            Result = record.Result,
        });
    }

    await dbContext.CloudResourceOperationResultsLegacy.AddRangeAsync(legacyRecords);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Gather results.
    var migratedTemplates = await dbContext.CloudResourceDeploymentResults.ToListAsync();
    var legacyRecordsAfterMigration = await dbContext.CloudResourceOperationResultsLegacy.ToListAsync();

    return new ProductionMigrationResult(migratedTemplates, legacyRecordsAfterMigration);
}

private sealed record ProductionMigrationResult(
    List<CloudResourceDeploymentResultEntity> MigratedTemplates,
    List<CloudResourceOperationResultLegacyEntity> LegacyRecordsAfterMigration
);
```

## Test Data Helpers

### Session Creation

```csharp
private Session CreateSession()
{
    return _sessionGenerator.GenerateSessionPartially(
        type: SessionType.CloudResourceGenerate,
        status: SessionStatus.Completed,
        result: SessionResult.Succeeded
    );
}
```

### Legacy Record Creation

```csharp
private CloudResourceOperationResultLegacyEntity CreateLegacyGenerateRecord(
    SessionId sessionId,
    CloudResourceGenerateLegacyResult generateResult)
{
    return new CloudResourceOperationResultLegacyEntity
    {
        Id = GenerateCloudResourceOperationResultId().Value,
        SessionId = sessionId.Value,
        ResultType = CloudResourceOperationResultTypeLegacyEntity.Generate,
        Result = SerializeToJsonString(generateResult).Value,
    };
}

private CloudResourceOperationResultLegacyEntity CreateLegacyApplicationRecord(
    SessionId sessionId,
    CloudResourceApplicationLegacyResult applicationResult)
{
    return new CloudResourceOperationResultLegacyEntity
    {
        Id = GenerateCloudResourceOperationResultId().Value,
        SessionId = sessionId.Value,
        ResultType = CloudResourceOperationResultTypeLegacyEntity.Application,
        Result = SerializeToJsonString(applicationResult).Value,
    };
}

private static JsonString SerializeToJsonString<TValue>(TValue? value)
{
    return JsonString.Serialize(value);
}
```

## Testing Checklist

- [ ] Empty database scenario (migration completes without errors)
- [ ] Happy path (successful data transformation)
- [ ] Idempotency (running twice produces same result)
- [ ] Invalid data handling (missing required fields)
- [ ] Malformed JSON handling (deserialization failures)
- [ ] Multiple records/sessions (batch processing)
- [ ] Partial migration (some records succeed, others fail)
- [ ] Legacy data removal (if applicable)
- [ ] Production data testing (if available)
- [ ] All database providers (InMemory, SQLite, document database via TestFixtureSource)

## Common Assertions

```csharp
// Verify migration completed
migratedRecords.Should().HaveCount(expectedCount);

// Verify data transformation
migratedRecord.NewField.Should().Be(expectedValue);

// Verify legacy data removed
legacyRecords.Should().BeEmpty();

// Verify idempotency
secondRunCount.Should().Be(firstRunCount);

// Verify production data
productionRecords.Should().AllSatisfy(r => r.RequiredField.Should().NotBeNull());
```

## Related Patterns

- [repository-tests.md](repository-tests.md) - Database testing patterns
- [generators.md](generators.md) - Test data generation
- [mock-builders.md](mock-builders.md) - Complex mock setups
