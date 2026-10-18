# Markdown Documentation Conventions

## Use the Skill

For the full markdownlint rules, the suppression patterns, and the `markdownlint` commands, follow the `write-markdown` skill. For the file names and the folder layout of project documentation, follow the `create-documentation` skill. If the repository already has a documentation layout, use it.

## Quick Rules

- **Single H1** (`#`) as document title.
- **Blank lines** around headings, code blocks, lists, and tables.
- **Language identifier** on all fenced code blocks (for example `csharp` or `json`).
- **No trailing whitespace**, no multiple consecutive blank lines.
- **File ends with exactly one newline**.
- **No bare URLs**. Use `<https://url>` or `[text](url)`.
- **Consistent list markers**. Use `-` (not `*`), and a 2-space indent for nesting.
- **No inline lint-disable comments**. Fix the formatting instead. The `write-markdown` skill names the rare exceptions.

## Frontmatter Scalar Quoting

Wrap a frontmatter value (`description:`, `argument-hint:`, and others) in double quotes in two cases:

- The value starts with a YAML indicator character: `[`, `{`, `*`, `&`, `!`, `|`, `>`, `%`, `@`, or backtick.
- The value contains an unquoted colon followed by a space.

Such a value can break YAML parsing, and the failure is silent. The parser drops the whole frontmatter block and shows no visible error. The command or the skill then loads with no `description` and no `argument-hint`.

**Before** (breaks, because `argument-hint` starts with `[`, a flow-sequence indicator):

```yaml
---
argument-hint: [<folder> ...] [exclude=<substring>[,<substring>...]]
---
```

**After** (quoted, parses correctly):

```yaml
---
argument-hint: "[<folder> ...] [exclude=<substring>[,<substring>...]]"
---
```

The same applies to an unquoted colon inside a plain scalar. Example: in `description: Safe by default: skips inactive items.`, YAML reads the second `:` as a new key, not as text. Quote the value, or reword it to remove the colon in the middle of the sentence.

After you change any frontmatter, run `claude plugin validate`. A passing run does not prove that the YAML parses. The validator can pass a value that is not valid YAML, and it can miss errors in the frontmatter of a command or an agent. If you are not sure about a value, parse it yourself, or run it through a YAML linter.
