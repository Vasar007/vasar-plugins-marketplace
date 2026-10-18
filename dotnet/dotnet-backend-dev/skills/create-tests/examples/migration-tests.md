# Migration Testing Patterns

Testing patterns for database and product migrations using Framework migration system.

The code examples in this file use NUnit, FluentAssertions, and AutoFixture. With another test framework, assertion library, or test data library, use its equivalent attributes and calls.

## Overview

Migration tests verify:

- Empty database (idempotency with nothing to migrate)
- Successful data transformation (happy path)
- Idempotency (running twice produces same result)
- Invalid data handling (graceful skipping/error handling)
- Multiple records/sessions
- Production data compatibility

## Test Fixture Structure

### TestDbContextFactory Requirement

Migration tests MUST run through the `TestDbContextFactory_DiSafeCases` fixture source (for example, `[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]` in NUnit) because:

- DbContext comes from DI container (via `IMigrationContext`)
- Migration engine retrieves services from `IServiceProvider`
- Must test against each test database provider of the project (for example, InMemory, SQLite, and a document database)

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
[TestFixtureSource(typeof(TestDbContextFactory_DiSafeCases))]
public sealed class EmbedLineItemsInOrderSummaryMigrationTests<TTestDbContextFactory> : BaseMockTest
    where TTestDbContextFactory : ITestDbContextFactory, new()
{
    private readonly TTestDbContextFactory _testDbContextFactory;

    public EmbedLineItemsInOrderSummaryMigrationTests()
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
private EmbedLineItemsInOrderSummaryMigration CreateMigration()
{
    var logger = TestLoggerBuilder.CreateWithoutSetup<EmbedLineItemsInOrderSummaryMigration>(Fixture);
    return new EmbedLineItemsInOrderSummaryMigration(logger);
}
```

## Essential Test Scenarios

### 1. Empty Database (Idempotency Check)

Test that the migration completes without errors on an empty database:

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
    var newSummaries = await dbContext.OrderSummaries.ToListAsync();
    newSummaries.Should().BeEmpty();
}
```

### 2. Happy Path (Successful Migration)

Verify migration successfully transforms records:

```csharp
[Test]
public async Task ExecuteAsync_ShouldMigratePlacedOnlyRecord()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var placedResult = GenerateOrderPlacedResult();
    var legacyRecord = CreateLegacyPlacedRecord(session.Id, placedResult);
    await dbContext.OrderEventsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newSummaries = await dbContext.OrderSummaries.ToListAsync();
    newSummaries.Should().HaveCount(1);

    var newSummary = newSummaries[0];
    newSummary.Id.Should().Be(legacyRecord.Id);
    newSummary.SessionId.Should().Be(session.Id.Value);
    newSummary.PlacedDetails.Should().NotBeNull();
    newSummary.PlacedResult.Should().NotBeNull();
    newSummary.LineItems.Should().BeEmpty();

    // Verify legacy record was removed.
    var legacyRecords = await dbContext.OrderEventsLegacy.ToListAsync();
    legacyRecords.Should().BeEmpty();
}
```

### 3. Complex Transformation

Test migration with multiple related records:

```csharp
[Test]
public async Task ExecuteAsync_ShouldMigratePlacedAndPaidRecords()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var placedResult = GenerateOrderPlacedResult();
    var paidResult = GenerateOrderPaidResult(lineItemCount: 2);

    var legacyPlacedRecord = CreateLegacyPlacedRecord(session.Id, placedResult);
    var legacyPaidRecord = CreateLegacyPaidRecord(session.Id, paidResult);

    await dbContext.OrderEventsLegacy.AddRangeAsync(legacyPlacedRecord, legacyPaidRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newSummaries = await dbContext.OrderSummaries.ToListAsync();
    newSummaries.Should().HaveCount(1);

    var newSummary = newSummaries[0];
    newSummary.Id.Should().Be(legacyPlacedRecord.Id);
    newSummary.SessionId.Should().Be(session.Id.Value);
    newSummary.PlacedDetails.Should().NotBeNull();
    newSummary.PlacedResult.Should().NotBeNull();
    newSummary.LineItems.Should().HaveCount(2);

    // Verify line items were migrated.
    foreach (var lineItem in newSummary.LineItems)
    {
        lineItem.Id.Should().NotBeEmpty();
        lineItem.ProductCode.Should().NotBeNullOrWhiteSpace();
        lineItem.ProductName.Should().NotBeNullOrWhiteSpace();
    }

    // Verify legacy records were removed.
    var legacyRecords = await dbContext.OrderEventsLegacy.ToListAsync();
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

    var placedResult = GenerateOrderPlacedResult();
    var legacyRecord = CreateLegacyPlacedRecord(session.Id, placedResult);

    await dbContext.OrderEventsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    var newSummariesAfterFirstRun = await dbContext.OrderSummaries.ToListAsync();
    var firstRunCount = newSummariesAfterFirstRun.Count;

    // Run migration again.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newSummariesAfterSecondRun = await dbContext.OrderSummaries.ToListAsync();
    newSummariesAfterSecondRun.Should().HaveCount(firstRunCount);
    newSummariesAfterSecondRun[0].Id.Should().Be(newSummariesAfterFirstRun[0].Id);
}
```

### 5. Invalid Data Handling

Verify migration skips records with missing required data:

```csharp
[Test]
public async Task ExecuteAsync_ShouldSkipRecord_WhenPlacedRecordIsMissing()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    // Only Paid record, no Placed record.
    var paidResult = GenerateOrderPaidResult(lineItemCount: 1);
    var legacyRecord = CreateLegacyPaidRecord(session.Id, paidResult);

    await dbContext.OrderEventsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newSummaries = await dbContext.OrderSummaries.ToListAsync();
    newSummaries.Should().BeEmpty();

    // Legacy record should remain since migration skipped it.
    var legacyRecords = await dbContext.OrderEventsLegacy.ToListAsync();
    legacyRecords.Should().HaveCount(1);
}
```

### 6. Malformed JSON Handling

Verify migration handles invalid JSON gracefully:

```csharp
[Test]
public async Task ExecuteAsync_ShouldSkipRecord_WhenPlacedResultJsonIsInvalid()
{
    // Arrange.
    await using var serviceProvider = SetupServiceProvider();
    await using var scope = serviceProvider.CreateAsyncScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<ServiceDbContext>();
    await TestDbHelper.ClearDatabaseAsync(dbContext);

    var sessionRepository = TestSessionRepository.CreateFromScope(scope);

    var session = await sessionRepository.AddSessionAsync(CreateSession());
    await sessionRepository.SaveChangesAsync();

    var legacyRecord = CreateLegacyPlacedRecordWithRawResult(session.Id, "{ invalid json }");

    await dbContext.OrderEventsLegacy.AddAsync(legacyRecord);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newSummaries = await dbContext.OrderSummaries.ToListAsync();
    newSummaries.Should().BeEmpty();

    var legacyRecords = await dbContext.OrderEventsLegacy.ToListAsync();
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

    var placedResult1 = GenerateOrderPlacedResult();
    var placedResult2 = GenerateOrderPlacedResult();
    var placedResult3 = GenerateOrderPlacedResult();

    await dbContext.OrderEventsLegacy.AddRangeAsync(
        CreateLegacyPlacedRecord(session1.Id, placedResult1),
        CreateLegacyPlacedRecord(session2.Id, placedResult2),
        CreateLegacyPlacedRecord(session3.Id, placedResult3)
    );
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Assert.
    var newSummaries = await dbContext.OrderSummaries.ToListAsync();
    newSummaries.Should().HaveCount(3);

    var legacyRecords = await dbContext.OrderEventsLegacy.ToListAsync();
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
        jsonFileName: "MyService_OrderEvents_seed.json",
        expectedTotalRecords: 162,
        expectedSessionCount: 86
    );

    // Assert.
    result.MigratedSummaries.Should().HaveCount(86, "each unique session should have one migrated summary");

    // Verify all summaries have PlacedDetails and PlacedResult.
    result.MigratedSummaries.Should().AllSatisfy(t =>
    {
        t.PlacedDetails.Should().NotBeNull("all production records have Placed data");
        t.PlacedResult.Should().NotBeNull("all production records have Placed results");
    });

    // Verify line items were migrated for summaries that had Paid records.
    var summariesWithLineItems = result.MigratedSummaries.Where(t => t.LineItems.IsNotEmpty()).ToList();
    summariesWithLineItems.Should().HaveCount(35, "35 sessions have Paid records with non empty line items");

    // Verify all line items have required fields.
    foreach (var summary in summariesWithLineItems)
    {
        summary.LineItems.Should().AllSatisfy(lineItem =>
        {
            lineItem.Id.Should().NotBeEmpty();
            lineItem.ProductCode.Should().NotBeNullOrWhiteSpace();
            lineItem.ProductName.Should().NotBeNullOrWhiteSpace();
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
        "Orders",
        "Summaries",
        jsonFileName
    );
    var jsonText = await File.ReadAllTextAsync(jsonFilePath);
    var productionRecords = JsonSerializer.Deserialize<List<OrderEventLegacyRecord>>(jsonText);
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
    var legacyRecords = new List<OrderEventLegacyEntity>();
    foreach (var record in productionRecords)
    {
        var mappedSessionId = sessionIdMap[record.SessionId];
        legacyRecords.Add(new OrderEventLegacyEntity
        {
            Id = record.Id,
            SessionId = mappedSessionId.Value,
            ResultType = record.ResultType == 1
                ? OrderEventTypeLegacyEntity.Placed
                : OrderEventTypeLegacyEntity.Paid,
            Result = record.Result,
        });
    }

    await dbContext.OrderEventsLegacy.AddRangeAsync(legacyRecords);
    await dbContext.SaveChangesAsync();

    var migration = CreateMigration();
    var migrationContext = CreateMigrationContext(serviceProvider);

    // Act.
    await migration.ExecuteAsync(migrationContext, CancellationToken.None);

    // Gather results.
    var migratedSummaries = await dbContext.OrderSummaries.ToListAsync();
    var legacyRecordsAfterMigration = await dbContext.OrderEventsLegacy.ToListAsync();

    return new ProductionMigrationResult(migratedSummaries, legacyRecordsAfterMigration);
}

private sealed record ProductionMigrationResult(
    List<OrderSummaryEntity> MigratedSummaries,
    List<OrderEventLegacyEntity> LegacyRecordsAfterMigration
);
```

## Test Data Helpers

### Session Creation

```csharp
private Session CreateSession()
{
    return _sessionGenerator.GenerateSessionPartially(
        type: SessionType.OrderImport,
        status: SessionStatus.Completed,
        result: SessionResult.Succeeded
    );
}
```

### Legacy Result Generation

```csharp
private OrderPlacedLegacyResult GenerateOrderPlacedResult()
{
    return _orderLegacyGenerator.GenerateOrderPlacedResult();
}

private OrderPaidLegacyResult GenerateOrderPaidResult(Int32 lineItemCount)
{
    return _orderLegacyGenerator.GenerateOrderPaidResult(lineItemCount: lineItemCount);
}
```

### Legacy Record Creation

```csharp
private OrderEventLegacyEntity CreateLegacyPlacedRecord(
    SessionId sessionId,
    OrderPlacedLegacyResult placedResult)
{
    return new OrderEventLegacyEntity
    {
        Id = GenerateOrderEventId().Value,
        SessionId = sessionId.Value,
        ResultType = OrderEventTypeLegacyEntity.Placed,
        Result = SerializeToJsonString(placedResult).Value,
    };
}

private OrderEventLegacyEntity CreateLegacyPlacedRecordWithRawResult(
    SessionId sessionId,
    String rawResult)
{
    return new OrderEventLegacyEntity
    {
        Id = GenerateOrderEventId().Value,
        SessionId = sessionId.Value,
        ResultType = OrderEventTypeLegacyEntity.Placed,
        Result = rawResult,
    };
}

private OrderEventLegacyEntity CreateLegacyPaidRecord(
    SessionId sessionId,
    OrderPaidLegacyResult paidResult)
{
    return new OrderEventLegacyEntity
    {
        Id = GenerateOrderEventId().Value,
        SessionId = sessionId.Value,
        ResultType = OrderEventTypeLegacyEntity.Paid,
        Result = SerializeToJsonString(paidResult).Value,
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
- [ ] All test database providers through the fixture source (for example, InMemory, SQLite, and a document database)

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

- [repository-tests.md](repository-tests.md): Database testing patterns
- [generators.md](generators.md): Test data generation
- [mock-builders.md](mock-builders.md): Complex mock setups
