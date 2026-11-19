---
type: regex
pattern: 'assertEqual\(get\("/users"\), f?"GET /users \(retries=(?:3|\{(?:\w+\.)?HTTP_RETRY_LIMIT\})\)"\)'
target: { source: file, path: tests/test_http_client.py }
---
