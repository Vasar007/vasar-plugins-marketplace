---
description: Probe of the hooks. It shows whether the PostToolUse lint hook of doc-styles runs after a Write.
tags: [probe]
plugins: ["../../.."]
allowed_tools: [Read]
---

Use the Write tool to create probe.md. The file holds this text:

```markdown
# probe

probe - test file for the lint hook

## DESCRIPTION

The `probe` utility prints the text that you give it.
```
