# Migration documentation template

Use this template to document a database migration. See `dotnet-backend-dev:add-migration`.

<!-- markdownlint-disable MD040 -->

````markdown
# {ProjectName} - {Migration Name} Migration

Brief description of the migration for DevOps engineers, operations teams,
and support engineers who need to understand the migration process.

---

## Overview

**Migration Name**: `{MigrationClassName}`
**Migration Version**: `{Major}.{Minor}.{Build}.{Revision}`
**Target**: Database container `{ContainerName}`

Describe what this migration does and why it's needed.

**Migration Impact**:

- **Data Transformation**: What data changes
- **Schema Change**: What schema modifications
- **Query Performance**: Impact on queries
- **Backwards Compatibility**: Safe to rollback?

---

## Why This Migration is Needed

### Current Problems

Describe issues with current format:

1. **Problem One**
   - Description of the issue
   - Impact on performance/maintainability

2. **Problem Two**
   - Description of the issue
   - Impact on operations

### New Format Benefits

Describe improvements:

1. **Benefit One**
   - How it addresses the problem
   - Performance improvements

---

## What Changes

### Database Schema

**Before Migration** (Legacy Format):

```txt
{ContainerName}
├─ Id: Type (Primary Key)
├─ Field1: Type
└─ Field2: Type (JSON blob)
```

**After Migration** (New Format):

```txt
{ContainerName}
├─ Id: Type (Primary Key)
├─ Field1: Type
├─ NewField: Type (structured)
└─ EmbeddedData: Object
   ├─ SubField1: Type
   └─ SubField2: Type
```

### Field Mapping

| Legacy Format  | New Format       | Transformation              |
|----------------|------------------|-----------------------------|
| `Field1`       | `Field1`         | Direct copy                 |
| `Field2.SubA`  | `NewField.SubA`  | Extracted from JSON         |

---

## How It Works

### Migration Steps

The migration runs automatically when the service starts if:

- Database schema version is below `{Version}`
- Legacy data exists in the database

**Execution Flow**:

1. **Step One** - Description
2. **Step Two** - Description
3. **Validation** - What gets validated
4. **Completion** - Final state

### Edge Cases Handled

| Scenario              | Migration Behavior                     |
|-----------------------|----------------------------------------|
| Empty database        | Completes successfully, no data change |
| Missing required data | Skips record, logs warning             |
| Invalid JSON          | Skips record, logs error               |
| Already migrated      | Skips (idempotent)                     |

---

## Testing

See `dotnet-backend-dev:create-tests` for migration testing patterns.

### Test Coverage

- Empty database test
- Happy path test
- Invalid data handling
- Idempotency test
- Production data test (when available)

---

## Deployment

### Pre-Deployment Checklist

- [ ] All tests pass in CI/CD pipeline
- [ ] Migration validated in test environment
- [ ] Database backup is recent
- [ ] Rollback procedure documented

### Deployment Process

The migration runs automatically when the service starts.

### Monitoring

**Logs to Review:**

```txt
[Information] Starting migration: {MigrationName} (version {Version})
[Information] Migration completed: X records migrated, Y records skipped
[Information] Database schema version updated to {Version}
```

---

## Troubleshooting

### Migration Does Not Run

**Symptom**: Service starts but migration does not execute.

**Possible Causes**:

1. Database version already at or above migration version
2. Migration disabled via configuration
3. Connection issue to database

### Migration Fails

**Symptom**: Service fails to start, migration error in logs.

**Resolution**:

1. Check logs for specific error
2. Verify database connectivity
3. Check for data corruption
4. Contact support with migration logs

````

<!-- markdownlint-enable MD040 -->
