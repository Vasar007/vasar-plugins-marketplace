---
type: regex
pattern: '\b(s[i]mply|j[u]st|e[a]sily|p[o]werful|r[o]bust|s[e]amless|l[e]verage|pl[e]ase)\b|!(?!=)'
flags: i
match: not_contains
target: { source: file, path: docs/snapsync.conf.md }
arm: both
---
