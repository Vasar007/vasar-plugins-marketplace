---
name: create-documentation
description: Create or update project documentation Markdown files following established conventions. Use when documenting features, configuration options, REST APIs, migrations, or architectural decisions in any project. Triggers on requests like "create documentation", "document feature", "write docs", "update documentation".
---

# Create Documentation

Create and maintain project documentation in the `Docs/` folder following
established patterns and conventions.

## Documentation Structure

<!-- markdownlint-disable MD013 -->

```txt
Docs/
├── {ProjectName} - {Topic}.md           # Top-level documentation
├── Balancing/                            # Load balancing algorithms
│   └── {ProjectName} - {Algorithm}.md
├── Features/                             # Feature documentation
│   ├── {ProjectName} - Features-Overview.md
│   └── {ProjectName} - {Feature}.md
├── Migrations/                           # Database migration docs
│   └── {Version}/
│       └── {ProjectName} - {Migration}.md
└── REST API/                             # API documentation
    ├── {ProjectName} - REST-API-Overview.md
    └── {ProjectName} - REST-API-{Resource}.md
```

<!-- markdownlint-enable MD013 -->

## File Naming Convention

**Pattern**: `{ProjectName} - {Topic}.md`

- Use title case for topic names
- Separate words with spaces (NOT hyphens in the title part)
- Prefix with `{ServiceName} - {Topic}` for consistency

**Examples**:

- `{ServiceName} - Configuration.md`
- `{ServiceName} - {FeatureName}.md`
- `{ServiceName} - REST-API-{Resource}.md`

## Markdown Guidelines

**CRITICAL**: Follow the [write-markdown](../write-markdown/SKILL.md)
skill for lint-free Markdown.

Key rules:

- Single H1 heading (`#`) as document title
- Blank lines around headings, code blocks, lists, and tables
- Specify language for all fenced code blocks
- No trailing whitespace
- File ends with single newline
- Use `<https://url>` or `[text](url)` for links (no bare URLs)

## Content Conventions

### Rule 1: Describe current state, not a changelog

**Why**: Docs, specs, and code comments are read by someone who has never
seen prior revisions. Change narration ("corrected", "previously",
"WITHDRAWN", "round 2", "OPEN QUESTION -> CLOSED") is noise to that reader
and rots the moment the revision history is forgotten -- it belongs in the
commit message or PR, not in the artifact itself.

**How to apply**:

- Every revision of a doc, plan, spec, or code comment must read as the
  single current state of the thing it describes.
- Strip meta-commentary about what changed: "corrected", "WITHDRAWN",
  "previously/formerly", "round N", "misremembered", "OPEN QUESTION ->
  CLOSED" postmortems. Delete resolved open questions rather than annotating
  them as resolved.
- Code comments describe the code **as it is now** -- never "was X, now Y",
  and never an inline incident/change history; that belongs in the commit
  message or PR.
- Keep comments short and non-redundant: don't restate what the code already
  says; put the high-level "what/why" of a type or method in its XML doc
  summary, not scattered inline.
- Factual provenance is fine to keep -- code/PR/commit references and
  file:line anchors are references, not a changelog entry.

**Anti-patterns**:

- "This section previously said X; it now says Y" left in a spec revision.
- "CONFIRMED (owner ...)" / "WITHDRAWN" markers left in the final doc text.
- A code comment reading `// was synchronous before v3, now async`.
- Annotating a question as "OPEN QUESTION -> CLOSED" instead of stating the
  answer directly and deleting the question.

### Rule 2: Treat docs as living, update them in the same change

**Why**: A doc that is only updated in a later "docs cleanup" pass drifts
from the code it describes, and gotchas discovered mid-task get lost if they
are not captured immediately.

**How to apply**:

- When you change behavior that a doc describes (schedules, cleanup targets,
  category mappings, stages, regions, naming, architecture, workflow),
  update that doc in the **same** change -- never as a separate follow-up
  task.
- When you hit a new gotcha while working, append it to the relevant doc as
  you go, not in a later batch cleanup.
- Treat every maintained doc as a living starting point, not a write-once
  artifact.

**Anti-patterns**:

- Shipping a behavior change and filing "update docs" as a separate backlog
  item.
- Discovering a gotcha, fixing the underlying issue, and not writing it down
  anywhere.
- Letting deeper `docs/` files (architecture, dev workflow, SDK patterns)
  drift from the code because only the top-level doc got touched.

## Document Templates by Type

### Configuration Documentation

For documenting configuration options classes. See `dotnet-backend-dev:add-configuration-option`.

<!-- markdownlint-disable MD013 MD040 -->

````markdown
# {ProjectName} - Configuration

- [How to Specify Configuration Options](#how-to-specify-configuration-options)
- [Configuration Options Sections](#configuration-options-sections)
  - [{OptionsClassName}](#optionsclassname)
- [Environment Variables](#environment-variables)

Brief description of what this configuration document covers.

---

## How to Specify Configuration Options

Describe the configuration sources (appsettings.json, environment variables, etc.)
and their priority order.

## Configuration Options Sections

### {OptionsClassName}

<!-- markdownlint-disable MD013 -->

[File](
../src/{ProjectName}.Configuration/Options/{Path}/
{OptionsClassName}.cs)

Brief description of what this options class configures.

Validation: [Validator](
../src/{ProjectName}.Configuration/Options/{Path}/
{OptionsClassName}Validator.cs)

| Property Name | Description                              | Type   | Default Value | Required |
|---------------|------------------------------------------|--------|---------------|----------|
| PropertyOne   | Description of property one              | string | null          | Yes      |
| PropertyTwo   | Description of property two              | int    | 0             | No       |
| NestedOptions | Nested configuration options             | Type   | new()         | Yes      |

**Example (appsettings.json):**

```json
{
  "{OptionsClassName}": {
    "PropertyOne": "value",
    "PropertyTwo": 42,
    "NestedOptions": {
      "SubProperty": "nested-value"
    }
  }
}
```

**Example (environment variables):**

```txt
{OptionsClassName}__PropertyOne=value
{OptionsClassName}__PropertyTwo=42
{OptionsClassName}__NestedOptions__SubProperty=nested-value
```

## Environment Variables

List of required environment variables for deployment.

````

<!-- markdownlint-enable MD013 MD040 -->

### Feature Documentation

For documenting service features and workflows.

```markdown
# {ProjectName} - {Feature Name}

Brief description of the feature and its purpose.

---

## Overview

High-level explanation of what the feature does and why it exists.

## Workflow

### User Steps (API Calls)

1. **Step One - {Action}**
   - Call:
     `{HTTP_METHOD} /api/v1/{endpoint}`
     Description of request body if applicable.
     Response: `{status}` with description.

2. **Step Two - {Action}**
   - Description of the step
   - Call:
     `{HTTP_METHOD} /api/v1/{endpoint}`
   - Response details

### Internal Steps (Service Logic)

Once triggered, the following internal steps are performed:

1. **{Internal Step Name}**
   - Description of what happens
   - Services/components involved

2. **{Internal Step Name}**
   - Description of what happens
   - Decision points or branching logic

## Configuration Options

| Option Name              | Description                    | Default |
|--------------------------|--------------------------------|---------|
| `Option.PropertyName`    | What this option controls      | value   |

## Edge Cases and Error Handling

Describe error scenarios and how they are handled.

## See Also

- [Related Feature](./{ServiceName}%20-%20RelatedFeature.md)
- [REST API](../REST%20API/{ServiceName}%20-%20REST-API-{Resource}.md)
```

### REST API Documentation

For documenting API endpoints. See `dotnet-backend-dev:update-swagger-spec`.

<!-- markdownlint-disable MD040 -->

````markdown
# {ProjectName} - REST API - {Resource}

- [List {Resources}](#list-resources)
- [Get {Resource} by ID](#get-resource-by-id)
- [Create {Resource}](#create-resource)
- [Update {Resource}](#update-resource)
- [Delete {Resource}](#delete-resource)
- [Models and Responses](#models-and-responses)

Brief description of the API resource and its purpose.

---

## List {Resources}

- **GET** `/api/v1/{resources}`
  **Description:** Retrieves a collection of {resources}.

  **Query Parameters:**

  | Parameter | Type    | Required | Description                          |
  |-----------|---------|----------|--------------------------------------|
  | Offset    | integer | No       | Skip first N items (minimum: 0)      |
  | Limit     | integer | No       | Maximum items to return (minimum: -1)|
  | Filter    | string  | No       | Filter by specific criteria          |

  **Response (200 OK):**

  ```json
  {
    "items": [
      {
        "id": "uuid-value",
        "name": "Resource Name",
        "status": "Active"
      }
    ],
    "totalCount": 1
  }
  ```

## Get {Resource} by ID

- **GET** `/api/v1/{resources}/{resourceId}`
  **Description:** Retrieves a specific {resource}.

  **Path Parameters:**

  | Parameter  | Type | Required | Description            |
  |------------|------|----------|------------------------|
  | resourceId | uuid | Yes      | System ID of {resource}|

  **Response (200 OK):** Returns a [{Resource}](#resource) object.

## Create {Resource}

- **POST** `/api/v1/{resources}`
  **Description:** Creates a new {resource}. This is an asynchronous operation.

  **Request Body:** `{Resource}CreateRequest`

  ```json
  {
    "name": "New Resource",
    "property": "value"
  }
  ```

  **Response (202 Accepted):**

  ```json
  {
    "sessionId": "uuid-value"
  }
  ```

  **Workflow:**

  1. Poll session: `GET /api/v1/sessions/{sessionId}` until `status=Completed`
  2. Check `result` field: `Succeeded`, `Warning`, or `Failed`
  3. Get result: `GET /api/v1/{resources}/sessions/{sessionId}/result`

---

## Models and Responses

### {Resource}

| Property   | Type   | Description              | Required |
|------------|--------|--------------------------|----------|
| id         | uuid   | Unique identifier        | Yes      |
| name       | string | Display name             | Yes      |
| status     | enum   | Current status           | Yes      |
| createdAt  | string | ISO 8601 date-time       | Yes      |

**Status Values:**

- `Active` - Resource is operational
- `Pending` - Resource is being processed
- `Failed` - Operation failed

````

<!-- markdownlint-enable MD040 -->

### Migration Documentation

For documenting database migrations. See `dotnet-backend-dev:add-migration`.

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

## Documentation Checklist

Before submitting documentation:

- [ ] File follows naming convention: `{ProjectName} - {Topic}.md`
- [ ] Single H1 heading as document title
- [ ] Table of Contents with working anchor links
- [ ] All code blocks have language specifiers
- [ ] Tables have blank lines before and after
- [ ] No bare URLs (use `<url>` or `[text](url)`)
- [ ] No trailing whitespace
- [ ] File ends with single newline
- [ ] Internal links use relative paths with URL encoding for spaces
- [ ] Validated with `markdownlint "Docs/**/*.md"`

## Cross-References

When documenting new features, update related documents:

| Document Type     | Update When                                  |
|-------------------|----------------------------------------------|
| Features-Overview | Adding new feature                           |
| REST-API-Overview | Adding new API controller                    |
| Configuration     | Adding new configuration options             |
| Migration folders | Adding database migrations                   |

## Related Skills

- [write-markdown](../write-markdown/SKILL.md) - Markdown conventions
   and linting
- `dotnet-backend-dev:add-configuration-option` -
  Configuration options classes
- `dotnet-backend-dev:add-migration` - Database migration
  implementation
- `dotnet-backend-dev:update-swagger-spec` - OpenAPI
  specification updates
