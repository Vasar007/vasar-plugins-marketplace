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
        .OrderBy(r => r.Id)
        .Skip(batchIndex * batchSize)
        .Take(batchSize)
        .ToListAsync(cancellationToken);

    // Process batch...
    
    await dbContext.SaveChangesAsync(cancellationToken);
    
    _logger.LogInformation("Processed batch {Current}/{Total}.", batchIndex + 1, totalBatches);
}
```

If the batch removes or changes the records that the query filters on, do not use `Skip`. The next page will skip records that the migration did not process. Page by key instead. Each query takes the records after the last key that the migration processed. The migration can skip a record, for example because its data is invalid. Paging by key also works then. A skipped record must not stay in the result, or the loop never ends.

```csharp
var lastId = 0L;

var batch = await dbContext.LegacyRecords
    .Where(r => r.Id > lastId)
    .OrderBy(r => r.Id)
    .Take(batchSize)
    .ToListAsync(cancellationToken);

while (batch.Count > 0)
{
    // Process batch. Remove, change, or skip the records.

    await dbContext.SaveChangesAsync(cancellationToken);

    lastId = batch[^1].Id;

    batch = await dbContext.LegacyRecords
        .Where(r => r.Id > lastId)
        .OrderBy(r => r.Id)
        .Take(batchSize)
        .ToListAsync(cancellationToken);
}
```
