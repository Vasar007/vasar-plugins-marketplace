---
type: regex
pattern: '(?:no (?:existing |matching |related |such |open |prior )?issues?\b|found no\b|found none\b|none found|found nothing|returned nothing|nothing found|did(?: not|n.t) find|neither [^.\n]{0,40}found\b|no (?:hits|results|matches)\b|0 (?:hits|results|matches)\b)[\s\S]{0,1500}\b(?:create|open|file)\b[^\n?]{0,40}\b(?:issue|one|it)\b[^\n?]{0,200}\?|\b(?:create|open|file)\b[^\n?]{0,40}\b(?:issue|one|it)\b[^\n?]{0,200}\?[\s\S]{0,1500}(?:no (?:existing |matching |related |such |open |prior )?issues?\b|found no\b|found none\b|none found|found nothing|returned nothing|nothing found|did(?: not|n.t) find|neither [^.\n]{0,40}found\b|no (?:hits|results|matches)\b|0 (?:hits|results|matches)\b)'
flags: i
target: last_message
---
