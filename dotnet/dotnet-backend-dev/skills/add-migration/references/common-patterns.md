# Common Migration Patterns

Code patterns for the `ExecuteAsync` method of a migration. Step 5 of `SKILL.md` points here.

## Grouping Records by Key

```csharp
var groupedBySession = legacyRecords.GroupBy(r => r.SessionId);

foreach (var sessionGroup in groupedBySession)
{
    var sessionId = sessionGroup.Key;
    var records = sessionGroup.ToList();
    
    // Process group...
}
```

## JSON Deserialization in Migrations

```csharp
private static Boolean TryDeserializeJsonResult<TValue>(
    String json,
    [NotNullWhen(true)] out TValue? result)
    where TValue : class
{
    result = null;

    try
    {
        result = JsonSerializer.Deserialize<TValue>(json, DefaultJsonSerializerOptions);
        return result is not null;
    }
    catch (JsonException)
    {
        return false;
    }
}
```

## Progress Logging

```csharp
_logger.LogInformation(
    "Processing batch {Current}/{Total}...",
    currentBatch,
    totalBatches
);

_logger.LogInformation(
    "Migration completed: [migrated={Migrated}, skipped={Skipped}, errors={Errors}].",
    migratedCount, skippedCount, errorCount
);
```

## Removing Legacy Data After Migration

```csharp
if (legacyRecordsToRemove.Count > 0)
{
    dbContext.LegacyRecords.RemoveRange(legacyRecordsToRemove);
    _logger.LogInformation("Marking {Count} legacy records for removal.", legacyRecordsToRemove.Count);
}

await dbContext.SaveChangesAsync(cancellationToken);
```

## Batch Processing (Large Datasets)

```csharp
const Int32 batchSize = 100;
var totalRecords = await dbContext.LegacyRecords.CountAsync(cancellationToken);
var totalBatches = (totalRecords + batchSize - 1) / batchSize;

for (var batchIndex = 0; batchIndex < totalBatches; ++batchIndex)
{
    var batch = await dbContext.LegacyRecords
        .Skip(batchIndex * batchSize)
        .Take(batchSize)
        .ToListAsync(cancellationToken);

    // Process batch...
    
    await dbContext.SaveChangesAsync(cancellationToken);
    
    _logger.LogInformation("Processed batch {Current}/{Total}.", batchIndex + 1, totalBatches);
}
```
