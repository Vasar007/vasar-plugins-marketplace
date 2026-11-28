---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*?\bunittest\b(?:[^"\\]|\\.)*?\bgit\b(?:[^"\\]|\\.)*?\bpush\b|"command":"(?:[^"\\]|\\.)*?\bunittest\b[\s\S]*?(?:\\n|\b)OK\b[\s\S]*?"command":"(?:[^"\\]|\\.)*?\bgit\b(?:[^"\\]|\\.)*?\bpush\b'
target: trace
---
