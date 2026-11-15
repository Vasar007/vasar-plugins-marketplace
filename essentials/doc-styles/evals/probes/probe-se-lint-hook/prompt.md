---
description: Probe of the hooks. It shows whether the PostToolUse lint hook of the stand-in runs after a Write. The reply quotes the hook message, because the trace of Claude Code 2.1.310 did not hold it.
tags: [probe]
plugins: ["../../../eval-stubs/simple-english"]
allowed_tools: [Read]
---

Use the Write tool to create probe.md. The file holds this one sentence:

```text
You should restart the service.
```

Do not edit probe.md after the write. If a hook sends you a message about probe.md, copy the full message into your reply, word for word, in a fenced `text` block. If no hook sends a message, write `No hook message.` in your reply.
