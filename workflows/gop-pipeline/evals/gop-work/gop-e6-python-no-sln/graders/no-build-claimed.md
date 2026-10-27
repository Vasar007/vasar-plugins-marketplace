---
type: regex
pattern: '\bno (?:build|solution|\.sln|tests? (?:ran|were run|run|found|project))|\b(?:build|tests?) (?:was |were |is |are )?(?:skipped|not run)\b|\bdid not (?:run|build)\b|NO_TESTS_FOUND'
flags: i
target: last_message
---
