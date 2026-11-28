---
type: regex
pattern: '\bskip(?:Test|If|Unless)?\b|\bexpectedFailure\b'
flags: i
match: not_contains
target: { source: file, path: tests/test_http_client.py }
---
