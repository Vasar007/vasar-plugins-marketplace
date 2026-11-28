---
type: regex
pattern: '"file_path":"[^"]*tests/[^"]*\.py","(?:old_string":"(?:[^"\\]|\\.)*","new_string|content)":"(?:[^"\\]|\\.)*total_pages\(\s*\w+\s*,\s*(?:size\s*=\s*)?(?:[1-9]\d{3,}|[2-9]\d\d|1(?:0[1-9]|[1-9]\d)|MAX_PAGE_SIZE\s*\+)'
target: trace
---
