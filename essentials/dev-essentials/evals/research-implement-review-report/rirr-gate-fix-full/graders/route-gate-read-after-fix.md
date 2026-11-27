---
type: regex
pattern: '"name":"(?:[\w-]*__)?create_pull_request","input":\{[\s\S]*"command":"(?:[^"\\]|\\.)*?\bgit\b(?:[^"\\]|\\.)*?\bpush\b[\s\S]*"name":"(?:[\w-]*__)?pull_request_read","input":\{(?:[^}\\]|\\.)*?"method":"get_check_runs"'
target: trace
---
