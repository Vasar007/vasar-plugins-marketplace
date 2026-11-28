---
type: regex
pattern: '"file_path":"[^"]*tests/[^"]*\.py","(?:old_string":"(?:[^"\\]|\\.)*","new_string|content)":"(?:[^"\\]|\\.)*(?:sort_label\(\\"(?:oldest|biggest)|SORT_LABELS)'
match: not_contains
target: trace
---
