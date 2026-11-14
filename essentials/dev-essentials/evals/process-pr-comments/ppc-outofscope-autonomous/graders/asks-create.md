---
type: regex
pattern: '(?:no (?:existing |matching |related |such |open |prior )?issues?\b|found no\b|found nothing|returned nothing|nothing found|did(?: not|n.t) find|no (?:hits|results|matches)\b|0 (?:hits|results|matches)\b)[\s\S]{0,400}\b(?:create|open|file)\b[^\n?]{0,200}\?|\b(?:create|open|file)\b[^\n?]{0,200}\?[\s\S]{0,400}(?:no (?:existing |matching |related |such |open |prior )?issues?\b|found no\b|found nothing|returned nothing|nothing found|did(?: not|n.t) find|no (?:hits|results|matches)\b|0 (?:hits|results|matches)\b)'
flags: i
target: last_message
---
