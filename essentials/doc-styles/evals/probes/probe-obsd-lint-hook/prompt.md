---
description: Probe of the hooks. It shows whether the PostToolUse lint hook of doc-styles runs after a Write. The reply quotes the hook message, because the trace does not hold it.
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

Do not edit probe.md after the write. If a hook sends you a message about probe.md, copy the full message into your reply, word for word, in a fenced `text` block. If no hook sends a message, write `No hook message.` in your reply.
