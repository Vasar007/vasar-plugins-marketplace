---
type: regex
pattern: '(?:rule[ -]candidates?|candidate rules?|draft rule)[\s\S]{0,400}?(?:snake[ _-]?case|camel[ _-]?case)|(?:snake[ _-]?case|camel[ _-]?case)[\s\S]{0,400}?(?:rule[ -]candidates?|candidate rules?|draft rule)'
flags: i
target: last_message
---
