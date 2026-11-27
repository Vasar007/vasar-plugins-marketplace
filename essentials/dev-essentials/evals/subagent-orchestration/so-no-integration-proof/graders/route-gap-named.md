---
type: regex
pattern: '\b(?:add|adding|write|writing|create|creating|introduce|introducing|build|building)\b[^.\n\x3b]{0,40}?\b(?:integration|end[- ]to[- ]end|e2e|smoke|functional|system)\b(?:\s*(?:[,/]\s*)?(?:(?:or|and|nor)\s+)?(?:an?\s+)?(?:integration|end[- ]to[- ]end|e2e|smoke|functional|system)\b)*[\s-]+(?:tests?|suites?|runs?|checks?|coverage|testing)\b'
flags: i
target: last_message
---
