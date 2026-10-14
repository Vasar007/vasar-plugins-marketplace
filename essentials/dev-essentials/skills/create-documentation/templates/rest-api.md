# REST API documentation template

Use this template to document the endpoints of one API resource. See `dotnet-backend-dev:update-swagger-spec`.

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
