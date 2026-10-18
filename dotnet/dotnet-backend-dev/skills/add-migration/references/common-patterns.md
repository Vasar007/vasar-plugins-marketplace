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

If the batch removes or changes the records that the query filters on, do not use `Skip`. The next page will skip records that the migration did not process. Query the records that still need the migration instead. The filter must leave out every migrated record, so each query takes a new batch. This works for any key type, for example `Guid`, because it does not compare keys.

The migration can skip a record, for example because its data is invalid. A skipped record still matches the filter. If it stays in the result, the loop never ends. Keep the keys of skipped records in a list, and leave them out of the query. Each record then either leaves the filter or enters the list, so every pass makes progress.

```csharp
const Int32 batchSize = 100;
var skippedIds = new List<Guid>();

while (true)
{
    var batch = await dbContext.LegacyRecords
        .Where(r => !r.IsMigrated)
        .Where(r => !skippedIds.Contains(r.Id))
        .OrderBy(r => r.Id)
        .Take(batchSize)
        .ToListAsync(cancellationToken);

    if (batch.Count == 0)
    {
        break;
    }

    foreach (var record in batch)
    {
        if (!IsValid(record))
        {
            skippedIds.Add(record.Id);
            continue;
        }

        // Migrate the record. Set IsMigrated, or remove the record.
    }

    await dbContext.SaveChangesAsync(cancellationToken);
}
```

`IsMigrated` stands for the real condition that marks a migrated record. If the database provider cannot translate `Contains` on a list, mark the skipped record with a status field and filter on that field.
