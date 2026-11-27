---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*?(?:\b(?:unittest|pytest)\b[^"\\&\x3b|]*?\bintegration\b|\bpython3?\b[^"\\&\x3b|]*?(?:\bintegration/test_\w+\.py\b|-m app\.cli\b|\bapp/cli\.py\b)|\bcd\b[^"\\&\x3b|]*?\bintegration\b[^"\\]*?\b(?:unittest|pytest)\b)(?:[^"\\]|\\.)*"[^"]*(?:"(?!name":"(?:Edit|Write|MultiEdit|NotebookEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*\.(?:py|txt)")[^"]*)*$'
target: trace
---
