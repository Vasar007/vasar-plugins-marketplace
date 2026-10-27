---
type: regex
pattern: '\bcommit(?:ted)?\b[^\n]{0,80}?\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b|(?:\b(?:nothing|not)\b[^\n.]{0,20}\bcommitted\b|\b(?:before|until)\s(?:I|we)\scommit\b|\bdid\snot\scommit\b)[\s\S]{0,600}?(?:\byour\s(?:call|decision|choice|go-ahead|answer)\b|\blet\sme\sknow\b|\bdo\syou\swant\b|\bwould\syou\slike\b|\bshould\sI\b|\bwhich\s(?:option|one)\b|\bpick\b|\bchoose\b|\btell\sme\b|\breply\swith\b)|(?:\byour\s(?:call|decision|choice|go-ahead|answer)\b|\blet\sme\sknow\b|\bdo\syou\swant\b|\bwould\syou\slike\b|\bshould\sI\b|\bwhich\s(?:option|one)\b|\bpick\b|\bchoose\b|\btell\sme\b|\breply\swith\b)[\s\S]{0,600}?(?:\b(?:nothing|not)\b[^\n.]{0,20}\bcommitted\b|\b(?:before|until)\s(?:I|we)\scommit\b|\bdid\snot\scommit\b)'
flags: i
target: last_message
---
