---
type: regex
pattern: '^(?!    |\t| {0,3}```|~~~)[^\n]*(?<!&lt)(?<!&gt)(?<!&amp)(?<!&quot)\x3b(?=[^\n]*(?:\n(?! {0,3}```)[^\n]*)*(?:\n {0,3}```[^\n]*(?:\n(?! {0,3}```)[^\n]*)*\n {0,3}```[^\n]*(?:\n(?! {0,3}```)[^\n]*)*)*(?![\s\S]))'
flags: m
match: not_contains
target: last_message
arm: both
---
