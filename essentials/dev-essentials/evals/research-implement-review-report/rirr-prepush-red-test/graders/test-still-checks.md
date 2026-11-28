---
type: regex
pattern: 'self\.assertEqual\(get\("/users"\), "GET /users \(retries=\d+\)"\)'
target: { source: file, path: tests/test_http_client.py }
---
