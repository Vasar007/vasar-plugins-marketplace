---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*?\bpython3?\b(?:[^"\\]|\\.)*?(?:\brender\b|\bPRINTER\b|\bapp\.cli\b|\bapp/cli\.py\b)(?:[^"\\]|\\.)*"[^"]*(?:"(?!name":"(?:Edit|Write|MultiEdit|NotebookEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*\.py")[^"]*)*$'
target: trace
---
