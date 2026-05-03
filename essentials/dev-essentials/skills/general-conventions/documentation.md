# Markdown Documentation Conventions

## Use the Skill

When creating or editing `.md` files, follow the `write-markdown` skill for full markdownlint rules.

## Quick Rules

- **Single H1** (`#`) as document title.
- **Blank lines** around headings, code blocks, lists, and tables.
- **Language identifier** on all fenced code blocks (```csharp, ```json, etc.).
- **No trailing whitespace**, no multiple consecutive blank lines.
- **File ends with exactly one newline**.
- **No bare URLs** — use `<https://url>` or `[text](url)`.
- **Consistent list markers** — use `-` (not `*`), 2-space indent for nesting.

## File Naming

Project documentation naming convention (when a project uses one): `{ProjectName} - {Topic}.md` (title case, spaces in topic).

Repo-specific doc folder layouts vary — common pattern is a top-level `Docs/` with per-topic subfolders (features, REST API, migrations, etc.). Use the layout already present in the repo rather than introducing a new one.

## Suppressions

**Do NOT use inline lint-disable comments** — fix the formatting instead. For tables, reformat (align pipes, fix column counts, add blank lines) rather than suppressing warnings.

Only when a rule genuinely cannot be satisfied (e.g., inline HTML for `<details>`), use inline comments as a last resort:

```markdown
<!-- markdownlint-disable-next-line MD013 -->
Long line here...
```

## Validate Before Committing

```bash
markdownlint "path/to/file.md"
markdownlint --fix "path/to/file.md"
```
