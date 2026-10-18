---
name: update-swagger-spec
description: Add or change an OpenAPI spec with [TBD] descriptions, then run a build to regenerate the API code.
when_to_use: Use it for "update swagger", "add API endpoint", "modify OpenAPI spec", or "add REST operation".
---

# Update the OpenAPI Spec

Add or modify OpenAPI specification files with required [TBD] prefix for all user-facing content, following API-first development approach.

## File Locations

### Primary API Specification

**Primary spec**: the OpenAPI spec of the WebApi project, for example `src/{ProjectName}.WebApi/Spec/ApiDefinition/swagger.json` (or `swagger.yml`)

This is the **source of truth** for the REST API. All controller interfaces and REST models are auto-generated from this spec.

### External Service Clients

**External service clients**: the OpenAPI spec of each client project, for example `src/Clients/{ProjectName}.{ExternalService}.Client/Spec/ApiDefinition/swagger.yml`

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
  "summary": "[TBD] Retrieves a list of retail stores",
  "description": "[TBD] Returns all retail stores for the specified partner organization. Use this endpoint to list stores before performing operations on specific stores.",
  "responses": {
    "200": {
      "description": "[TBD] Successfully retrieved retail stores list"
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
    "/api/v1/retail-stores": {
      "post": {
        "tags": ["Stores"],
        "summary": "[TBD] Creates a new retail store",
        "description": "[TBD] Initiates asynchronous onboarding of a new retail store. Returns a session ID to track operation progress.",
        "operationId": "CreateStore",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CreateStoreRequest"
              }
            }
          }
        },
        "responses": {
          "202": {
            "description": "[TBD] Onboarding started, session created",
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
      "CreateStoreRequest": {
        "type": "object",
        "description": "[TBD] Request to create a new retail store",
        "required": ["organizationId", "name", "warehouseId"],
        "properties": {
          "organizationId": {
            "type": "string",
            "format": "uuid",
            "description": "[TBD] Partner organization ID that owns the store"
          },
          "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "description": "[TBD] Human-readable store name (1-100 characters)"
          },
          "warehouseId": {
            "type": "string",
            "description": "[TBD] ID of the warehouse that ships the orders of the store"
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
      "name": "Stores",
      "x-displayName": "Retail Stores",
      "description": "[TBD] The `/retail-stores` collection represents all retail stores and allows to configure or delete them."
    }
  ]
}
```

## Code Generation Workflow

### How Auto-Generation Works

The build runs the OpenAPI code generator (for example, NSwag through MSBuild) and auto-generates the code. You must **NEVER** run the code generator directly. For NSwag, do not call `nswag`, `NSwagExe`, or any other NSwag tool. The build handles everything.

#### Discovering the Generator Configuration

Before working with code generation, read the `.csproj` file and find the configuration of the code generator. The example below is for NSwag. It uses the `NSwagGeneration` MSBuild item group:

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

- Controller interfaces (for example, `IStoresController`)
- Request/response DTOs
- Enums
- All output goes to the directory specified in `<GeneratedDir>`

### When Regeneration Happens

The build runs the generation. After you change the OpenAPI spec, build the project:

```bash
dotnet build
```

### If the Build Does NOT Update Auto-Generated Files

**CRITICAL**: If you build the project and the auto-generated files are not updated:

1. **STOP**. Do NOT attempt to run the code generator manually.
2. **STOP**. Do NOT call any command of the code generator (for NSwag, `nswag run` or `$(NSwagExe_Net80)`).
3. **ASK the user** to perform the regeneration manually (for example, with Visual Studio Rebuild or other tooling).

## Step-by-Step Workflow

### 1. Modify the OpenAPI Spec

Edit the primary spec (for example, `src/{ProjectName}.WebApi/Spec/ApiDefinition/swagger.json`):

```json
{
  "paths": {
    "/api/v1/retail-stores/{storeId}/configurations": {
      "get": {
        "tags": ["Stores"],
        "summary": "[TBD] Retrieves store configuration",
        "operationId": "GetStoreConfiguration",
        "parameters": [
          {
            "name": "storeId",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "format": "uuid"
            },
            "description": "[TBD] Unique identifier of the retail store"
          }
        ],
        "responses": {
          "200": {
            "description": "[TBD] Configuration retrieved successfully",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/StoreConfiguration"
                }
              }
            }
          },
          "404": {
            "description": "[TBD] Retail store not found"
          },
          "500": {
            "description": "[TBD] Internal server error",
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

### 2. Add Schema Definitions (if needed)

```json
{
  "components": {
    "schemas": {
      "StoreConfiguration": {
        "type": "object",
        "description": "[TBD] Configuration settings for a retail store",
        "properties": {
          "returnWindowDays": {
            "type": "integer",
            "format": "int32",
            "description": "[TBD] Number of days in which customers can return items"
          },
          "giftWrappingEnabled": {
            "type": "boolean",
            "description": "[TBD] Whether gift wrapping is enabled for orders"
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

**IMPORTANT**: Do NOT run the code generator manually. The build handles code generation automatically (for NSwag, through the `NSwagGeneration` MSBuild configuration). If the build does not update auto-generated files, stop and ask the user to regenerate.

### 4. Implement Controller

**IMPORTANT**: Controllers implement auto-generated interfaces.

Create controller in `src/{ProjectName}.WebApi/Controllers/`. The sketch below shows only the link to the generated interface. Write the class itself with [create-controller](../create-controller/SKILL.md). That skill gives the class name, the access modifier, the base class, the `Rest` alias, and the try-catch rule:

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.AspNetCore.Mvc;
using {ProjectNamespace}.WebApi.AutoGenerated;

namespace {ProjectNamespace}.WebApi.Controllers.Retail.Stores;

/// <summary>
/// Controller for retail store configuration operations.
/// </summary>
[ApiController]
public sealed class StoreConfigurationController : ControllerBase, IStoresController
{
    /// <inheritdoc />
    public async Task<IActionResult> GetStoreConfigurationAsync(
        Guid storeId,
        CancellationToken cancellationToken)
    {
        // Implementation
        throw new NotImplementedException();
    }
}
```

**See [create-controller](../create-controller/SKILL.md) for full controller implementation patterns.**

### 5. Verify Generated Code

Read the auto-generated files:

- `src/{ProjectName}.WebApi/AutoGenerated/ControllersAndModels.Generated.cs`
- `tests/{ProjectName}.WebApi.Tests/AutoGenerated/ClientAndModels.Generated.cs`

Look for:

- New controller interface (for example, `IStoresController` with the new method)
- New request/response DTOs
- Correct parameter types and nullability

### 6. Create Tests

Use the generated client in integration tests. The test adds a store to the database first. The reason is that the database is empty after the clean-up of each test. See the success case for an existing resource in [controller-tests.md](../create-tests/examples/controller-tests.md). The example uses NUnit (`[Test]`) and FluentAssertions (`.Should()`). Another test framework or assertion library uses its own equivalents:

```csharp
[Test]
public async Task GetStoreConfiguration_ShouldReturnConfiguration()
{
    // Arrange.
    await using var scope = _webApplicationFactory.Services.CreateAsyncScope();
    var builder = CreateTestStoreRepository(scope);
    var store = await builder.AddStoreAsync();
    await builder.SaveChangesAsync();
    
    // Act.
    var response = await _client.GetStoreConfigurationAsync(store.Id.Value);
    
    // Assert.
    response.Should().NotBeNull();
    response.ReturnWindowDays.Should().BeGreaterThan(0);
}
```

**See [create-tests](../create-tests/SKILL.md) for testing patterns.**

## Common Patterns

### Async Operations (Session-Based)

For long-running operations, return `202 Accepted` with session reference:

```json
{
  "post": {
    "summary": "[TBD] Initiates retail store onboarding",
    "responses": {
      "202": {
        "description": "[TBD] Onboarding started successfully",
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
    "summary": "[TBD] Retrieves retail stores with optional filtering",
    "parameters": [
      {
        "name": "organizationId",
        "in": "query",
        "required": false,
        "schema": {
          "type": "string",
          "format": "uuid"
        },
        "description": "[TBD] Filter by partner organization ID"
      },
      {
        "name": "status",
        "in": "query",
        "required": false,
        "schema": {
          "$ref": "#/components/schemas/StoreStatus"
        },
        "description": "[TBD] Filter by store status"
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
      "StoreStatus": {
        "type": "string",
        "description": "[TBD] Current status of a retail store",
        "enum": [
          "Onboarding",
          "Active",
          "Updating",
          "Closing",
          "Closed",
          "Failed"
        ]
      }
    }
  }
}
```

### Error Responses

Always include standard error responses. Every operation must document the `500` response. If the service returns `503` for its server errors, the operation still lists `500`. Without `500` in the spec, some generated client code can treat an unhandled server exception as a client failure. The shorter examples in this file show only some responses, but each real operation must list `500`.

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
      "description": "[TBD] Internal server error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ProblemDetails"
          }
        }
      }
    },
    "503": {
      "description": "[TBD] Service unavailable",
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
```

## External Service Clients (OpenAPI YAML)

For external services (for example, a customer-portal API), use YAML format:

**File**: for example, `src/Clients/{ProjectName}.{ExternalService}.Client/Spec/ApiDefinition/swagger.yml`

```yaml
openapi: 3.0.1
info:
  title: MyService Customer Portal OpenAPI
  version: v1
paths:
  /api/customer-portal/retail-stores/getUsage/{orgId}:
    get:
      tags:
        - Stores
      summary: Retrieves subscription usage for an organization
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
2. Read the MSBuild output for errors of the code generator
3. Read the `.csproj`. Find out whether the configuration of the code generator (for NSwag, the `NSwagGeneration` item group) exists and whether its paths are correct.
4. If the build does not regenerate the files, **STOP and ask the user** to regenerate them manually

**CRITICAL**: Do NOT run the commands of the code generator directly. For NSwag, do NOT attempt `nswag run`, `$(NSwagExe_Net80)`, or any other manual NSwag invocation.

### Controller Interface Signature Mismatch

If the controller implementation does not match the generated interface:

1. Build project to regenerate
2. Find out whether the parameter names and types in the OpenAPI spec match C# conventions
3. Find out whether each operationId is unique

## Checklist

- [ ] Modified the OpenAPI spec with [TBD] prefix on all new/changed descriptions
- [ ] Added/updated operation summaries and descriptions
- [ ] Defined schema models in `components/schemas`
- [ ] Added standard error responses (400, 404, 500, 503). Every operation must have `500`, because otherwise an unhandled server exception can look like a client failure in some generated client code
- [ ] Rebuilt solution to trigger the code generation
- [ ] Generated code in `AutoGenerated/ControllersAndModels.Generated.cs` reviewed
- [ ] Test client code in `AutoGenerated/ClientAndModels.Generated.cs` reviewed
- [ ] Implemented controller interface (see create-controller skill)
- [ ] Created integration tests using generated client
- [ ] Each long-running operation documented with the session-based pattern

## Related Skills

- [create-controller](../create-controller/SKILL.md): Implement controllers using generated interfaces
- [create-tests](../create-tests/SKILL.md): Test API endpoints using generated client
- [create-string-resource](../create-string-resource/SKILL.md): Similar [TBD] prefix pattern for user-facing strings
- [model-mapping](../model-mapping/SKILL.md): Convert REST models to Domain models
- `dev-essentials:create-documentation`: Documenting REST APIs in Docs/REST API/
