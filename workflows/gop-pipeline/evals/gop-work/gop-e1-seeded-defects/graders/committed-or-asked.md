---
type: regex
pattern: '\bcommit(?:ted)?\b[\s\S]{0,80}?\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b|(?:\b(?:nothing|not|no)\b[^\n.]{0,40}\bcommit(?:ted)?\b|n\x27t\s(?:\w+\s){0,2}commit(?:ted)?\b|\b(?:before|until)\s(?:I\s|we\s)?commit(?:ting)?\b|\bdid\snot\scommit\b)[\s\S]{0,600}?(?:\byour\s(?:call|decision|choice|go-ahead|answer)\b|\blet\sme\sknow\b|\bdo\syou\s(?:want|prefer)\b|\bwould\syou\s(?:like|prefer)\b|\bshould\sI\b|\bwhich\s(?:option|one)\b|\bpick\b|\bchoose\b|\btell\sme\b|\breply\swith\b|\bhow\sto\sproceed\b)|(?:\byour\s(?:call|decision|choice|go-ahead|answer)\b|\blet\sme\sknow\b|\bdo\syou\s(?:want|prefer)\b|\bwould\syou\s(?:like|prefer)\b|\bshould\sI\b|\bwhich\s(?:option|one)\b|\bpick\b|\bchoose\b|\btell\sme\b|\breply\swith\b|\bhow\sto\sproceed\b)[\s\S]{0,600}?(?:\b(?:nothing|not|no)\b[^\n.]{0,40}\bcommit(?:ted)?\b|n\x27t\s(?:\w+\s){0,2}commit(?:ted)?\b|\b(?:before|until)\s(?:I\s|we\s)?commit(?:ting)?\b|\bdid\snot\scommit\b)'
flags: i
target: last_message
---
