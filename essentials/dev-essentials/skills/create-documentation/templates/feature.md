# Feature documentation template

Use this template to document a service feature and its workflow.

```markdown
# {ProjectName} - {Feature Name}

- [Overview](#overview)
- [Workflow](#workflow)
  - [User Steps (API Calls)](#user-steps-api-calls)
  - [Internal Steps (Service Logic)](#internal-steps-service-logic)
- [Configuration Options](#configuration-options)
- [Edge Cases and Error Handling](#edge-cases-and-error-handling)
- [See Also](#see-also)

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
