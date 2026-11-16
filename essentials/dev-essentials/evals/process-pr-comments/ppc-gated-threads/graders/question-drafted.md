---
type: regex
pattern: '\[AI\]\[Draft\]|Post this \[Question\] reply|[Pp]ost (?:this|the) answer\b(?:[^\n?.]|\.(?!\s)){0,40}\?|(?:\[Question\]|T#9102)(?:(?!T#)[^\n]){0,200}[Pp]ost this reply\b[^\n?]{0,40}\?|[Pp]ost this reply\b(?:(?!T#)[^\n?]){0,40}T#9102[^\n?]{0,40}\?|T#9102[^\n]*\n(?:>[^\n]*\n)+(?:[ \t]*\n)*[^\n]{0,20}[Pp]ost this reply\b[^\n?]{0,40}\?|[Rr]eply[^\n?]{0,200}\? ?\(yes / edit / skip\)'
target: last_message
---
