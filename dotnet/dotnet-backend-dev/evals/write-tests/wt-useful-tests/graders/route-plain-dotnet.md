---
type: tool_used
tool: Bash
input_match: '(?:"command":\s*"|\\n|[\x3b&|({])(?:\s|\\t)*(?:(?:!|if|then|else|do|while|until|time|env|\w+=(?:[^ "\\\x3b&|]|\\")*|timeout(?: +-[^ "\\]+)* +[^ "\\]+) +)*dotnet (?:build|test)(?![\w-])(?!(?:[^"\\]|\\.)*?(?:-m|-maxcpucount)[:= ]1\b)'
min: 0
max: 0
---
