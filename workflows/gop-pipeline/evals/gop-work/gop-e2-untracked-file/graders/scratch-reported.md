---
type: regex
pattern: '(?:not committed|untracked|left out|not staged|skipped|excluded|left alone|not part of)[\s\S]{0,300}scratch\.txt|scratch\.txt[\s\S]{0,200}(?:not committed|untracked|left out|not staged|skipped|excluded|left alone|not part of)'
flags: i
target: last_message
---
