---
type: regex
pattern: '(?:"name":"(?:Edit|Write|MultiEdit)","input":\{(?:"replace_all":(?:true|false),)?"file_path":"(?:[^"\\]|\\.)*\.py"|"command":"(?:[^"\\]|\\.)*?(?:\b(?:sed(?:\s+-[A-Za-z]+)*\s+-i|perl(?:\s+-\w+)*\s+-p?i)\S*\s(?:[^"\\&\x3b|]|\\[^n])*?|>>?\s*|\btee\s+(?:-a\s+)?)[\w./-]*\.py\b(?:(?!(?:\\[nrt]|\b)unittest\b)(?:[^"\\]|\\.))*")(?:(?!"command":"(?:[^"\\]|\\.)*(?:\\[nrt]|\b)unittest\b)[\s\S])*"command":"(?:(?!(?:\\[nrt]|\b)unittest\b)(?:[^"\\]|\\.))*(?:\\[nrt]|\b)git\b(?:[^"\\]|\\.)*\bcommit\b|"command":"(?:[^"\\]|\\.)*?(?:\b(?:sed(?:\s+-[A-Za-z]+)*\s+-i|perl(?:\s+-\w+)*\s+-p?i)\S*\s(?:[^"\\&\x3b|]|\\[^n])*?|>>?\s*|\btee\s+(?:-a\s+)?)[\w./-]*\.py\b(?:(?!(?:\\[nrt]|\b)unittest\b)(?:[^"\\]|\\.))*(?:\\[nrt]|\b)git\b(?:[^"\\]|\\.)*\bcommit\b'
match: not_contains
target: trace
---
