---
name: write-markdown
description: Write Markdown files with no markdownlint warnings.
when_to_use: Use it to create or update any `.md` file, and for "update readme" or "fix markdown warnings".
---

# Write Markdown

Create and maintain Markdown files that pass markdownlint validation with zero warnings.

## Tooling Setup

These are setup notes for the user. Do not install tools or create or change configuration files (`.markdownlint.json`, `.vscode/settings.json`) unless the user asks. Use the existing markdownlint configuration of the repo. If `markdownlint` is not installed, tell the user. Then apply the rules by hand. The [markdownlint rule list](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md) names them.

### Editor Extension

If the editor (for example, VS Code) has a markdownlint extension, install it. For VS Code, install the [vscode-markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) extension:

```bash
code --install-extension DavidAnson.vscode-markdownlint
```

### CLI Tool for Validation

Use [markdownlint-cli](https://github.com/igorshubovych/markdownlint-cli) for command-line validation:

```bash
# Install globally
npm install -g markdownlint-cli

# Lint specific files
markdownlint "Docs/**/*.md"

# Lint with glob patterns (quote on Linux/macOS)
markdownlint '**/*.md' --ignore node_modules

# Auto-fix issues
markdownlint --fix "Docs/**/*.md"

# Use specific config file
markdownlint --config .markdownlint.json "README.md"
```

**Exit Codes:**

- `0` - No errors
- `1` - Linting errors found
- `2-4` - Configuration/runtime errors

### Preferred Validation Workflow

Before you commit a Markdown file:

1. Run auto-fix: `markdownlint --fix "path/to/file.md"`
2. Check: `markdownlint "path/to/file.md"`
3. If the exit code is `1`, fix each reported rule and run `markdownlint` again. Repeat until the exit code is `0`. After three failed fix attempts, or for an error outside the changed code, stop and report the last errors. If `markdownlint` prints its usage text, the path matched no file, even when the exit code is `0`. Fix the path and run it again. If the exit code is `2` to `4`, report the error and do not loop.
4. When the exit code is `0`, review the changes and commit.

## Rules beyond the linter

markdownlint names each rule that a file breaks, so this skill does not repeat the rules. One choice is not a default of markdownlint (the `-` marker, because MD004 defaults to `consistent`). One rule is easy to break by hand (the 2-space indent of MD007, which is the default):

- Use `-` as the list marker. Indent a nested list by 2 spaces.
- Fix a warning in the text, not with a disable comment (see "Inline Suppressions").

For a file over about 100 lines, add a contents list after the title.

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

## Inline Suppressions

**Do not use inline lint-disable comments to suppress warnings.** Fix the underlying formatting issue instead. Tables often trigger this. If a table triggers lint warnings, reformat the table: align the pipes, fix the column counts, and add blank lines around it. Do not add `<!-- markdownlint-disable -->` comments.

If a rule cannot pass, use inline comments as a last resort. One example is a document that needs inline HTML for `<details>`/`<summary>`:

```markdown
<!-- markdownlint-disable-next-line MD013 -->
This is a very long line that exceeds the default 80 character limit but is necessary for this specific case.

<!-- markdownlint-disable MD033 -->
<details>
<summary>Click to expand</summary>

Content with inline HTML that requires disabling the rule.

</details>
<!-- markdownlint-enable MD033 -->
```

**Suppression patterns:**

| Pattern                                         | Scope               |
|-------------------------------------------------|---------------------|
| `<!-- markdownlint-disable-next-line MD### -->` | Next line only      |
| `<!-- markdownlint-disable-line MD### -->`      | Current line only   |
| `<!-- markdownlint-disable MD### -->`           | Until re-enabled    |
| `<!-- markdownlint-enable MD### -->`            | Re-enable rule      |
| `<!-- markdownlint-disable-file MD### -->`      | Entire file         |
| `<!-- markdownlint-capture -->`                 | Save current state  |
| `<!-- markdownlint-restore -->`                 | Restore saved state |

## Configuration File

If the user asks for a configuration and the repo has none, create `.markdownlint.json` in the project root. Then every run uses the same rules:

```json
{
  "default": true,
  "MD013": false,
  "MD024": { "siblings_only": true },
  "MD033": { "allowed_elements": ["details", "summary", "br"] },
  "MD041": false
}
```

**Common rule customizations:**

| Rule  | Default  | Recommended Override  | Reason                                                   |
|-------|----------|-----------------------|----------------------------------------------------------|
| MD013 | 80 chars | `false`               | Many files have long lines                               |
| MD024 | error    | `siblings_only: true` | Allow same heading text in different sections            |
| MD033 | error    | Allow specific tags   | Enable `<details>`, `<summary>` for collapsible sections |
| MD041 | error    | `false`               | Not all files need H1 as first line                      |

## Editor Settings

Set up the editor to lint Markdown as you type and to fix the warnings on save. For VS Code, add this to `.vscode/settings.json`:

```json
{
  "[markdown]": {
    "editor.formatOnSave": true,
    "editor.wordWrap": "on",
    "editor.rulers": [120]
  },
  "markdownlint.run": "onType",
  "editor.codeActionsOnSave": {
    "source.fixAll.markdownlint": "explicit"
  }
}
```

## Cross-References

- [create-documentation](../create-documentation/SKILL.md): Creating project documentation files
