---
type: tool_used
tool: Bash
input_match: '"command":"(?:[^"\\]|\\.)*?(?:switch(?: +-[\w-]+)*? +(?:-[a-zA-Z]*[cC]|--create|--force-create)|checkout(?: +-[\w-]+)*? +-[a-zA-Z]*[bB]|(?:(?<=:")|\\n|[\x3b&|({])(?:\s|\\t)*(?:git|\$\{?\w+\}?)(?: +(?:-[cC] +(?:\\"(?:[^"\\]|\\.)*?\\"|''[^'']*''|[^\s"\\]+)|-[\w-]+(?:=[^\s"\\]+)?))* +branch +(?![-\d])(?:[\w.'']|\\")|\bbranch +(?:-[a-zA-Z]*f|--force)\b)'
min: 0
max: 0
---
