---
type: regex
pattern: '\n[0-9a-f]{40} \b4be08abc09b3[0-9a-f]{28} [^\t\n]*\tsquash_task: move to the task base\n[^\n]*\tcommit: [^\n]*\n$'
target: { source: file, path: .git/logs/HEAD }
---
