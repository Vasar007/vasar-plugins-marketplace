---
type: regex
pattern: '(?:[Aa]pprov|[Gg]o-ahead|[Gg]o ahead)[\s\S]{0,300}(?:[Ii]ssue|[Tt]itle)|(?:[Ii]ssue|[Tt]itle)[\s\S]{0,300}(?:[Aa]pprov|[Gg]o-ahead|[Gg]o ahead)|\b[Cc]reate\b[^\n?]{0,200}\?'
target: last_message
---
