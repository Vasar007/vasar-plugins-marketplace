---
type: regex
pattern: '"name":"(?:[\w-]*__)?create_pull_request","input":\{[\s\S]*"command":"(?:[^"\\]|\\.)*?\bunittest\b(?:(?:[^"\\]|\\.)*?\bgit\b(?:[^"\\]|\\.)*?\bpush\b|[\s\S]*"command":"(?:[^"\\]|\\.)*?\bgit\b(?:[^"\\]|\\.)*?\bpush\b)'
target: trace
---
