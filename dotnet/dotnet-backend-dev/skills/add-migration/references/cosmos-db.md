# Cosmos DB Migrations

## Cosmos DB Specific Considerations

If the project does not use Cosmos DB, skip this section.

### Partition Key Cannot Change

Once a container is created with a partition key, **you cannot change it**.

If you need a different partition key:

1. Create a new container with the new partition key
2. Migrate data from old container to new container
3. Update DbContext to use new container
4. Make sure that the new container has all the data. Then ask the user before you delete the old container, and delete it only after the user agrees. The delete removes all documents in the old container.

### No Schema Enforcement

Cosmos DB does not enforce a schema, so:

- Old documents can coexist with new schema
- Migrations must handle documents that can lack the new fields
- Each time you read a property that can be missing, test it for `null`

### Container Configuration

If the partition key of an entity changes, use this section. It creates a separate container on purpose. The example uses the Cosmos DB provider of EF Core:

```csharp
modelBuilder.Entity<MyNewEntity>()
    .ToContainer("MyNewEntities")
    .HasPartitionKey(e => e.CustomerId); // Choose appropriate partition key

modelBuilder.Entity<MyNewEntity>()
    .HasKey(e => e.Id);

// If using composite keys
modelBuilder.Entity<MyNewEntity>()
    .HasKey(e => new { e.Id, e.SecondaryKey });
```
