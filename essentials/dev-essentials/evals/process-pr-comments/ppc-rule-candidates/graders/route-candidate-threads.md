---
type: regex
pattern: '(?<!\bno )(?:rule[ -]candidates?|candidate rules?|draft rule)\b(?![^\S\n]*(?:\(0\)|:[^\S\n]*none))[\s\S]{0,300}^(?:(?=[^\n]*9201)(?=[^\n]*9202)(?=[^\n]*9203)|(?=[^\n]*9201[^\S\n]*(?:–|-|to)[^\S\n]*(?:T#)?9203))|^(?:(?=[^\n]*9201)(?=[^\n]*9202)(?=[^\n]*9203)|(?=[^\n]*9201[^\S\n]*(?:–|-|to)[^\S\n]*(?:T#)?9203))[^\n]*(?:\n[^\n]*){0,2}?(?<!\bno )(?:rule[ -]candidates?|candidate rules?|draft rule)\b(?![^\S\n]*(?:\(0\)|:[^\S\n]*none))'
flags: im
target: last_message
---
