---
type: regex
pattern: '"name":"(?:Edit|Write|MultiEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*?/(?:src|tests)/[^"]*\.py"'
match: not_contains
target: trace
---
