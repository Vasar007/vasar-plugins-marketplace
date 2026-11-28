---
type: regex
pattern: 'Review by AI Agent \(Round-\d+\)[^\n]*?\\n\|(?:(?!\\n)[^\n])*(?:\b(?:oldest|biggest|table[- ]driven|(?:each|every|all|other|remaining)(?: (?:two|three|2|3))?(?: sort)? (?:keys?|labels?)|(?:one|1) of the (?:three|3) keys)\b(?:(?!\\n)[^\n])*\btests?\b|\btests?\b(?:(?!\\n)[^\n])*\b(?:oldest|biggest|table[- ]driven|(?:each|every|all|other|remaining)(?: (?:two|three|2|3))?(?: sort)? (?:keys?|labels?)|(?:one|1) of the (?:three|3) keys)\b)'
flags: i
match: not_contains
target: trace
---
