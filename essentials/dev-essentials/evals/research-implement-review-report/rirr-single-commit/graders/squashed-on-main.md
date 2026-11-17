---
type: regex
pattern: '\n[0-9a-f]{40} \b4be08abc09b3[0-9a-f]{28} [^\t\n]*\t(?:squash_task: move to the task base|reset: moving to [^\n]*)\n[^\n]*\tcommit: [^\n]*\n$'
target: { source: file, path: .git/logs/HEAD }
---
