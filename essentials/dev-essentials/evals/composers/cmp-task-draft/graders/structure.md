---
type: regex
pattern: '^# \S[^\n]*\n[\s\S]*^## Current State Analysis[ \t]*$[\s\S]*^## Changes to Do[ \t]*$'
flags: m
target: { source: file, path: notes/Tasks/task-customer-index.md }
---
