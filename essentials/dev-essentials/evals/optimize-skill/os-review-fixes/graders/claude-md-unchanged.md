---
type: regex
pattern: '^# Rules\r?\n\r?\n- Commit messages: one summary line, a blank line, and a body\.\r?\n- No CHANGELOG\.\r?\n(?![\s\S])'
target: { source: file, path: CLAUDE.md }
---
