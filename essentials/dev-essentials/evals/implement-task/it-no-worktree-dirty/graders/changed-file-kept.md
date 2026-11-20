---
type: regex
pattern: '^"""Settings of the users app\."""\n\nHTTP_RETRY_LIMIT = 5\nTIMEOUT_SECONDS = 45\n(?![\s\S])'
target: { source: file, path: config/settings.py }
---
