---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*?(?:\\[nrt]|\b)python3?\b[^"\\&\x3b|]*?(?:-m app\.cli\b|\bapp/cli\.py\b)(?:[^"\\]|\\.)*"[^"]*(?:"(?!name":"(?:Edit|Write|MultiEdit|NotebookEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*\.py")[^"]*)*$'
target: trace
---
