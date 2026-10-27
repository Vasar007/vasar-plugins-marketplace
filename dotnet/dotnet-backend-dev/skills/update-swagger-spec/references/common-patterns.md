# Common Spec Patterns

Spec examples for a session-based operation, a list filter, an enum, the error responses, and the spec of an external client. `SKILL.md` points here.

## Contents

- Async Operations (Session-Based)
- List Operations with Filtering
- Enums
- Error Responses
- External Service Clients (OpenAPI YAML)

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
