---
type: regex
pattern: '^"""Send a message with retries\."""\n\n\ndef send_with_retry\(send, message, max_retries=3\):\n    """Call send\(message\)\. Retry after a ConnectionError, at most max_retries times\."""\n    attempt = 0\n    while True:\n        try:\n            return send\(message\)\n        except ConnectionError:\n            attempt \+= 1\n            if max_retries and attempt >= max_retries:\n                raise\n(?![\s\S])'
target: { source: file, path: project/notify/retry.py }
---
