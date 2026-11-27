---
type: regex
pattern: '(?:rule[ -]candidates?|candidate rules?|(?:draft|proposed|possible|suggested|new) rules?|rules? to add|add (?:a|the|this) rule)[\s\S]{0,400}?(?:snake[ _-]?case|camel[ _-]?case|underscores?|naming|function names?)|(?:snake[ _-]?case|camel[ _-]?case|underscores?|naming|function names?)[\s\S]{0,400}?(?:rule[ -]candidates?|candidate rules?|(?:draft|proposed|possible|suggested|new) rules?|rules? to add|add (?:a|the|this) rule)'
flags: i
target: last_message
---
