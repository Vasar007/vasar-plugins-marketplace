---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*(?:\\[nrt]|\b)unittest\b(?:(?:[^"\\]|\\.)*|[^"]*(?:"(?!name":"(?:Edit|Write|MultiEdit|NotebookEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*\.py")[^"]*)*?"command":"(?:[^"\\]|\\.)*)(?:\\[nrt]|\b)git\b(?:[^"\\]|\\.)*\bcommit\b|"name":"Workflow","input":\{[^\n]*?\b[Rr]un\b[^\n]{0,60}?\b(?:unittest|tests?|Phase 6|commands?)\b[^\n]*?\b[Cc]ommit\b|"name":"Workflow","input":\{(?=[^\n]*?\bAPPLY\b)[^\n]*?\b[Rr]un\b[^\n]{0,60}?\b(?:unittest|tests?|Phase 6|commands?)\b[\s\S]*?"command":"(?:[^"\\]|\\.)*?\bgit\b(?:[^"\\]|\\.)*?\bcommit\b'
target: trace
---
