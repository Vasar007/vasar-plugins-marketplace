---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*?(?:\\[nrt]|\b)python3?\b(?:[^"\\]|\\.)*?(?:\brender\(|\bmain\(|\bapp\.cli\b|\bapp/cli\.py\b)(?:[^"\\]|\\.)*"[^"]*(?:"(?!name":"(?:Edit|Write|MultiEdit|NotebookEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*\.py")[^"]*)*$'
target: trace
---
