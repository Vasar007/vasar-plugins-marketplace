---
type: regex
pattern: '^# Review notes\n\n- Ask the team: must page 0 raise an error\?\n- The page size of the admin list is 50, not 20\.\n(?![\s\S])'
target: { source: file, path: tmp/review-notes.md }
---
