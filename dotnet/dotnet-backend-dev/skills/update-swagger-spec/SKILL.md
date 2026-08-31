---
name: update-swagger-spec
description: Add/modify OpenAPI spec with [TBD] descriptions, NSwag regeneration workflow - API-first development approach. Use when adding REST endpoints, modifying API contracts, or updating OpenAPI documentation. Triggers on requests like "update swagger", "add API endpoint", "modify OpenAPI spec", "add REST operation".
---

# Update Swagger Spec

Add or modify OpenAPI specification files with required [TBD] prefix for all user-facing content, following API-first development approach.

## When to Use

Use this skill when:

- Adding new REST API endpoints
- Modifying existing API operations (request/response models)
- Updating API documentation (summaries, descriptions)
- Adding new OpenAPI schemas or parameters
- Changing API contracts

## File Locations

### Primary API Specification

**Primary spec**: `src/{ProjectName}.WebApi/Spec/ApiDefinition/swagger.json` (or `swagger.yml`)

This is the **source of truth** for the REST API. All controller interfaces and REST models are auto-generated from this spec.

### External Service Clients

**External service clients**: `src/Clients/{ProjectName}.{ExternalService}.Client/Spec/ApiDefinition/swagger.yml`

Used to generate client code for calling external service endpoints.

## Required [TBD] Prefix

**CRITICAL**: ALL new or modified user-facing content MUST start with `[TBD]` prefix.

This applies to:

- Operation summaries
- Operation descriptions
- Schema descriptions
- Property descriptions
- Parameter descriptions
- Example values that users see
- Tag descriptions

```json
{
  "summary": "[TBD] Retrieves a list of workload tenants",
  "description": "[TBD] Returns all workload tenants for the specified .NET backend organization. Use this endpoint to list tenants before performing operations on specific tenants.",
  "responses": {
    "200": {
      "description": "[TBD] Successfully retrieved workload tenants list"
    }
  }
}
```

**Why [TBD]?** This prefix indicates content needs review by analysts and technical writers before release. See [create-string-resource](../create-string-resource/SKILL.md) for similar pattern.

## OpenAPI Spec Structure

### Path Operations

```json
{
  "paths": {
    "/api/v1/workload-tenants": {
      "post": {
        "tags": ["Tenants"],
        "summary": "[TBD] Creates a new workload tenant",
        "description": "[TBD] Initiates asynchronous provisioning of a new workload tenant. Returns a session ID to track operation progress.",
        "operationId": "CreateTenant",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CreateTenantRequest"
              }
            }
          }
        },
        "responses": {
          "202": {
            "description": "[TBD] Provisioning started, session created",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SessionReference"
                }
              }
            }
          },
          "400": {
            "description": "[TBD] Invalid request parameters",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ProblemDetails"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### Schema Definitions

```json
{
  "components": {
    "schemas": {
      "CreateTenantRequest": {
        "type": "object",
        "description": "[TBD] Request to create a new workload tenant",
        "required": ["organizationId", "name", "regionId"],
        "properties": {
          "organizationId": {
            "type": "string",
            "format": "uuid",
            "description": "[TBD] .NET backend organization ID that owns the tenant"
          },
          "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "description": "[TBD] Human-readable tenant name (1-100 characters)"
          },
          "regionId": {
            "type": "string",
            "description": "[TBD] cloud region ID where tenant infrastructure will be deployed"
          }
        }
      }
    }
  }
}
```

### Tags

```json
{
  "tags": [
    {
      "name": "Tenants",
      "x-displayName": "Workload Tenants",
      "description": "[TBD] The `/workload-tenants` collection represents all deployed workload tenants and allows to configure or delete them."
    }
  ]
}
```

## NSwag Auto-Generation Workflow

### How Auto-Generation Works

This project uses **MSBuild-integrated NSwag generation** — code is auto-generated during the build. You must **NEVER** call `nswag`, `NSwagExe`, or any NSwag tool directly. The build handles everything.

#### Discovering NSwag Configuration

Before working with code generation, read the `.csproj` file and find the `NSwagGeneration` MSBuild item group:

```xml
<!-- Configure NSwag code generation. -->
<!-- This generates C# controllers and models from OpenAPI specifications using NSwag during the build. -->
<ItemGroup>
  <NSwagGeneration Include="Service_ControllersAndModels" Visible="false">
    <GeneratedDir>$(ProjectDir)AutoGenerated</GeneratedDir>
    <InputTemplate>$(ProjectDir)Spec/NSwag/controller_template_Service.nswag</InputTemplate>
  </NSwagGeneration>
</ItemGroup>
```

This tells you:

- **Include name**: identifies the generation task
- **GeneratedDir**: where auto-generated files are written
- **InputTemplate**: the NSwag template that controls generation

#### What Gets Generated

- Controller interfaces (e.g., `ITenantsController`)
- Request/response DTOs
- Enums
- All output goes to the directory specified in `<GeneratedDir>`

### When Regeneration Happens

Auto-generation triggers automatically during the build. After modifying `swagger.json`, simply build the project:

```bash
dotnet build
```

### If the Build Does NOT Update Auto-Generated Files

**CRITICAL**: If you build the project and the auto-generated files are not updated:

1. **STOP** — Do NOT attempt to run NSwag manually
2. **STOP** — Do NOT call `nswag run`, `$(NSwagExe_Net80)`, or any NSwag command
3. **ASK the user** to perform the regeneration manually (e.g., via Visual Studio Rebuild or other tooling)

## Step-by-Step Workflow

### 1. Modify swagger.json

Edit `src/{ProjectName}.WebApi/Spec/ApiDefinition/swagger.json`:

```json
{
  "paths": {
    "/api/v1/workload-tenants/{tenantId}/configurations": {
      "get": {
        "tags": ["Tenants"],
        "summary": "[TBD] Retrieves tenant configuration",
        "operationId": "GetTenantConfiguration",
        "parameters": [
          {
            "name": "tenantId",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "format": "uuid"
            },
            "description": "[TBD] Unique identifier of the workload tenant"
          }
        ],
        "responses": {
          "200": {
            "description": "[TBD] Configuration retrieved successfully",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TenantConfiguration"
                }
              }
            }
          },
          "404": {
            "description": "[TBD] Workload tenant not found"
          }
        }
      }
    }
  }
}
```

### 2. Add Schema Definitions (if needed)

```json
{
  "components": {
    "schemas": {
      "TenantConfiguration": {
        "type": "object",
        "description": "[TBD] Configuration settings for a workload tenant",
        "properties": {
          "backupRetentionDays": {
            "type": "integer",
            "format": "int32",
            "description": "[TBD] Number of days to retain backups"
          },
          "encryptionEnabled": {
            "type": "boolean",
            "description": "[TBD] Whether encryption is enabled for backups"
          }
        }
      }
    }
  }
}
```

### 3. Regenerate Code

Build the solution to trigger auto-generation:

```bash
dotnet build
```

**IMPORTANT**: Do NOT run NSwag manually. The build handles code generation automatically via the `NSwagGeneration` MSBuild configuration. If the build does not update auto-generated files, stop and ask the user to regenerate.

### 4. Implement Controller

**IMPORTANT**: Controllers implement auto-generated interfaces.

Create controller in `src/{ProjectName}.WebApi/Controllers/`:

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.AspNetCore.Mvc;
using {ProjectNamespace}.WebApi.AutoGenerated;

namespace {ProjectNamespace}.WebApi.Controllers.Workload.Tenants;

/// <summary>
/// Controller for workload tenant configuration operations.
/// </summary>
[ApiController]
public sealed class TenantConfigurationController : ControllerBase, ITenantsController
{
    /// <inheritdoc />
    public async Task<IActionResult> GetTenantConfigurationAsync(
        Guid tenantId,
        CancellationToken cancellationToken)
    {
        // Implementation
        throw new NotImplementedException();
    }
}
```

**See [create-controller](../create-controller/SKILL.md) for full controller implementation patterns.**

### 5. Verify Generated Code

Check auto-generated files:

- `src/{ProjectName}.WebApi/AutoGenerated/ControllersAndModels.Generated.cs`
- `tests/{ProjectName}.WebApi.Tests/AutoGenerated/ClientAndModels.Generated.cs`

Look for:

- New controller interface (e.g., `ITenantsController` with new method)
- New request/response DTOs
- Correct parameter types and nullability

### 6. Create Tests

Use generated client in integration tests:

```csharp
[Test]
public async Task GetTenantConfiguration_ShouldReturnConfiguration()
{
    // Arrange.
    var tenantId = Guid.NewGuid();
    
    // Act.
    var response = await Client.GetTenantConfigurationAsync(tenantId);
    
    // Assert.
    response.Should().NotBeNull();
    response.BackupRetentionDays.Should().BeGreaterThan(0);
}
```

**See [create-tests](../create-tests/SKILL.md) for testing patterns.**

## Common Patterns

### Async Operations (Session-Based)

For long-running operations, return `202 Accepted` with session reference:

```json
{
  "post": {
    "summary": "[TBD] Initiates workload tenant provisioning",
    "responses": {
      "202": {
        "description": "[TBD] Provisioning started successfully",
        "content": {
          "application/json": {
            "schema": {
              "$ref": "#/components/schemas/SessionReference"
            }
          }
        }
      }
    }
  }
}
```

### List Operations with Filtering

```json
{
  "get": {
    "summary": "[TBD] Retrieves workload tenants with optional filtering",
    "parameters": [
      {
        "name": "organizationId",
        "in": "query",
        "required": false,
        "schema": {
          "type": "string",
          "format": "uuid"
        },
        "description": "[TBD] Filter by .NET backend organization ID"
      },
      {
        "name": "status",
        "in": "query",
        "required": false,
        "schema": {
          "$ref": "#/components/schemas/TenantStatus"
        },
        "description": "[TBD] Filter by tenant status"
      }
    ]
  }
}
```

### Enums

```json
{
  "components": {
    "schemas": {
      "TenantStatus": {
        "type": "string",
        "description": "[TBD] Current status of a workload tenant",
        "enum": [
          "Provisioning",
          "Active",
          "Updating",
          "Terminating",
          "Terminated",
          "Failed"
        ]
      }
    }
  }
}
```

### Error Responses

Always include standard error responses:

```json
{
  "responses": {
    "400": {
      "description": "[TBD] Invalid request parameters",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ProblemDetails"
          }
        }
      }
    },
    "404": {
      "description": "[TBD] Resource not found"
    },
    "500": {
      "description": "[TBD] Internal server error"
    }
  }
}
```

## External Service Clients (swagger.yml)

For external services (for example, a customer-portal API), use YAML format:

**File**: `src/Clients/{ProjectName}.{ExternalService}.Client/Spec/ApiDefinition/swagger.yml`

```yaml
openapi: 3.0.1
info:
  title: MyService Customer Portal OpenAPI
  version: v1
paths:
  /api/customer-portal/workload-tenants/getUsage/{orgId}:
    get:
      tags:
        - Tenants
      summary: Retrieves storage usage for an organization
      parameters:
        - name: orgId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Successfully retrieved usage data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsageResponse'
```

## Troubleshooting

### Generated Code Not Updated

1. Build the project: `dotnet build`
2. Check MSBuild output for NSwag errors
3. Read the `.csproj` and verify the `NSwagGeneration` item group exists and paths are correct
4. If the build does not regenerate — **STOP and ask the user** to regenerate manually

**CRITICAL**: Do NOT run NSwag commands directly. Do NOT attempt `nswag run`, `$(NSwagExe_Net80)`, or any manual NSwag invocation.

### Controller Interface Signature Mismatch

If controller implementation doesn't match generated interface:

1. Build project to regenerate
2. Check swagger.json parameter names/types match C# conventions
3. Verify operationId uniqueness

## Checklist

- [ ] Modified `swagger.json` or `swagger.yml` with [TBD] prefix on all new/changed descriptions
- [ ] Added/updated operation summaries and descriptions
- [ ] Defined schema models in `components/schemas`
- [ ] Added standard error responses (400, 404, 500)
- [ ] Rebuilt solution to trigger NSwag auto-generation
- [ ] Verified generated code in `AutoGenerated/ControllersAndModels.Generated.cs`
- [ ] Verified test client code in `AutoGenerated/ClientAndModels.Generated.cs`
- [ ] Implemented controller interface (see create-controller skill)
- [ ] Created integration tests using generated client
- [ ] Documented async operations with session-based pattern if needed

## Related Skills

- [create-controller](../create-controller/SKILL.md) - Implement controllers using generated interfaces
- [create-tests](../create-tests/SKILL.md) - Test API endpoints using generated client
- [create-string-resource](../create-string-resource/SKILL.md) - Similar [TBD] prefix pattern for user-facing strings
- [model-mapping](../model-mapping/SKILL.md) - Convert REST models to Domain models
- `dev-essentials:create-documentation` - Documenting REST APIs in Docs/REST API/
