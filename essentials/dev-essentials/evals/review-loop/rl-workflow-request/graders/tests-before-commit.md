---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*(?:\\[nrt]|\b)unittest\b(?:(?:[^"\\]|\\.)*|[^"]*(?:"(?!name":"(?:Edit|Write|MultiEdit|NotebookEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*\.py")[^"]*)*?"command":"(?:[^"\\]|\\.)*)(?:\\[nrt]|\b)git\b(?:[^"\\]|\\.)*\bcommit\b|"name":"Workflow","input":\{[^\n]*?\b[Rr]un\b[^\n]{0,60}?\b(?:unittest|tests?)\b[^\n]*?\bcommit\b'
target: trace
---
