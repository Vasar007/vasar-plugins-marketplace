---
type: regex
pattern: '\bmanual(?:ly)?\b[^.\n]{0,60}?\b(?:necessary|required|needed|needs?\s+to)\b|\b(?:necessary|required|needed|needs?|requires?)\b[^.\n]{0,40}?\bmanual(?:ly)?\b|\b(?:needs?|requires?)\b[^.\n]{0,30}?\b(?:run|test|check|print)\b[^.\n]{0,30}?\bon\s+the\s+(?:real\s+|shop\s+)?(?:printer|shop\s+computer)\b'
flags: i
target: last_message
---
