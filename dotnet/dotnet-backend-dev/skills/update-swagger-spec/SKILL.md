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

All new or modified user-facing content must start with `[TBD]` prefix.

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

The build runs the OpenAPI code generator (for example, NSwag through MSBuild) and auto-generates the code. You must **never** run the code generator directly. For NSwag, do not call `nswag`, `NSwagExe`, or any other NSwag tool. The build handles everything.

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

### If the Build Does Not Update Auto-Generated Files

If you build the project and the auto-generated files are not updated:

1. **Stop**. Do not attempt to run the code generator manually.
2. **Stop**. Do not call any command of the code generator (for NSwag, `nswag run` or `$(NSwagExe_Net80)`).
3. **ASK the user** to perform the regeneration manually (for example, with Visual Studio Rebuild or other tooling).

## Step-by-Step Workflow

### 1. Modify the OpenAPI Spec

Every operation lists the `500` response. Without `500` in the spec, some generated client code can treat an unhandled server exception as a client failure.

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

Do not run the code generator manually. The build handles code generation automatically (for NSwag, through the `NSwagGeneration` MSBuild configuration). If the build does not update auto-generated files, stop and ask the user to regenerate.

### 4. Implement Controller

The controller class implements the interface that the build of step 3 generated. Write the class in `src/{ProjectName}.WebApi/Controllers/` with the [create-controller](../create-controller/SKILL.md) skill. That skill gives the class name, the access modifier, the base class, the `Rest` alias, and the try-catch rule.

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

Read [references/common-patterns.md](references/common-patterns.md) for these cases: a session-based operation, a list filter, an enum, the error responses, or the spec of an external client.

## Troubleshooting

### Generated Code Not Updated

1. Build the project: `dotnet build`
2. Read the MSBuild output for errors of the code generator
3. Read the `.csproj`. Find out whether the configuration of the code generator (for NSwag, the `NSwagGeneration` item group) exists and whether its paths are correct.
4. If the build does not regenerate the files, **stop and ask the user** to regenerate them manually

Do not run the commands of the code generator directly. For NSwag, do not attempt `nswag run`, `$(NSwagExe_Net80)`, or any other manual NSwag invocation.

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
