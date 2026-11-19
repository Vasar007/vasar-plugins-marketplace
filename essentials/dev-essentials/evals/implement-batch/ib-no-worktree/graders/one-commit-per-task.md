---
type: regex
pattern: '^0{40} ([0-9a-f]{40}) [^\t\n]*\tbranch: Created from [^\n]*\n(?:[^\n]*\n)*?\1 ([0-9a-f]{40}) [^\t\n]*\tcommit: [^\n]*\n(?:[^\n]*\n)*?\2 ([0-9a-f]{40}) [^\t\n]*\tcommit: [^\n]*\n(?:(?:[^\n]*\n)*?\3 ([0-9a-f]{40}) [^\t\n]*\tcommit: [^\n]*\n(?:(?:[^\n]*\n)*[0-9a-f]{40} \4 [^\n]*\n)?|(?:(?:[^\n]*\n)*[0-9a-f]{40} \3 [^\n]*\n)?)$'
target: { source: file, path: .git/logs/refs/heads/eval/retry-and-timeout }
---
