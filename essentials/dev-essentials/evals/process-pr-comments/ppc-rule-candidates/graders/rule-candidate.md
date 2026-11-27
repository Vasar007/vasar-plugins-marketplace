---
type: regex
pattern: '(?<!\bno )(?:rule[ -]candidates?|candidate rules?|(?:draft|proposed|possible|suggested|new) rules?|rules? to add|add (?:a|the|this) rule)\b(?![^\S\n]*(?:\(0\)|:[^\S\n]*none))[\s\S]{0,400}?(?:snake[ _-]?case|camel[ _-]?case|under[ _]?scores?|naming|function names?)|(?:snake[ _-]?case|camel[ _-]?case|under[ _]?scores?|naming|function names?)[\s\S]{0,400}?(?<!\bno )(?:rule[ -]candidates?|candidate rules?|(?:draft|proposed|possible|suggested|new) rules?|rules? to add|add (?:a|the|this) rule)\b(?![^\S\n]*(?:\(0\)|:[^\S\n]*none))'
flags: i
target: last_message
---
