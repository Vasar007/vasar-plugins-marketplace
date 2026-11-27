---
type: regex
pattern: '"id":"(toolu_\w+)","name":"Agent","input":\{[^\n]*?Review made by[\s\S]*"name":"(?:Edit|Write|MultiEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"[^"\n]*src/pager\.py"[^\n]*"parent_tool_use_id":"\1"'
match: not_contains
target: trace
---
