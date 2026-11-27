---
type: regex
pattern: '"name":"Agent","input":\{(?:[^C\n]|C(?!lassify each finding as))*?Review made by(?:[^C\n]|C(?!lassify each finding as))*"parent_tool_use_id":null|"name":"Workflow","input":\{(?:(?=[^\n]*?(?:[Dd][Oo] [Nn][Oo][Tt] edit|[Rr]ead-only))(?=[^\n]*?\bAPPLY\b)|(?:[^C\n]|C(?!lassify each finding as))*?Review made by(?:[^C\n]|C(?!lassify each finding as))*"parent_tool_use_id":null)|"name":"Workflow","input":\{(?=[^\n]*?(?:[Dd][Oo] [Nn][Oo][Tt] edit|[Rr]ead-only))(?![^\n]*?\bAPPLY\b)[\s\S]*?"name":"(?:Workflow|Agent)","input":\{[^\n]*?(?:\bAPPLY\b|Classify each finding as)'
target: trace
---
