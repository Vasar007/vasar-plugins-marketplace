---
type: regex
pattern: 'def get\(url, retries=HTTP_RETRY_LIMIT\)'
target: { source: file, path: app/http_client.py }
---
