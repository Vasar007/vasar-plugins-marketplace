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

## Frontmatter Scalar Quoting

A frontmatter value (`description:`, `argument-hint:`, etc.) that starts with a YAML
flow-indicator character (`[`, `{`, `*`, `&`, `!`, `|`, `>`, `%`, `@`, backtick) or
contains an unquoted `: ` (colon-space) sequence can break YAML parsing — and the
failure is silent: the parser drops the entire frontmatter block instead of raising a
visible error, so the command/skill loads with no `description` or `argument-hint` at
all. Always wrap such a value in double quotes.

**Before** (breaks — `argument-hint` starts with `[`, a flow-sequence indicator):

```yaml
---
argument-hint: [<folder> ...] [exclude=<substring>[,<substring>...]]
---
```

**After** (quoted — parses correctly):

```yaml
---
argument-hint: "[<folder> ...] [exclude=<substring>[,<substring>...]]"
---
```

The same applies to an unquoted colon inside a plain scalar, e.g.
`description: Safe by default: skips inactive items.` — the second `:` is read as a new
key, not text. Quote the value, or reword to avoid the mid-sentence colon.

Validate with `claude plugin validate` after touching any frontmatter — it is silent
when frontmatter parses and loads correctly, so a passing run is the confirmation this
class of break did not slip through.

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
