---
type: regex
pattern: 'approve[\s\S]{0,80}?(?:finali[sz]ation|push|\bPR\b|pull request)|request changes'
flags: i
target: last_message
---
