---
name: general-conventions
description: Load when writing or reviewing Markdown documentation or PowerShell scripts in the project repository. Indexes two reference files — one for markdownlint-clean Markdown authoring, one for PowerShell script structure, output, and error handling conventions.
---

# General Conventions

Cross-product reference set covering conventions that apply across any .NET or scripting repo.

| Topic | File | Load when |
|---|---|---|
| Markdown authoring | `documentation.md` | Creating/editing `.md` files |
| PowerShell scripts | `powershell.md` | Creating/editing `.ps1` files |

Each file stands alone — open the one matching your current task.

## How this skill is used

- **Auto-invoked**: when Claude detects Markdown or PowerShell work in a project repo.
- **Manually invoked**: reference via `/general-conventions` or by name when you want to consult the conventions directly.
- **Referenced by other skills**: skills such as `write-markdown` point here for the quick-rules summary.
