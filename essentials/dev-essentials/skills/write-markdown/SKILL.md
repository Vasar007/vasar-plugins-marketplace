---
name: write-markdown
description: Write Markdown files with no markdownlint warnings.
when_to_use: Use it to create or update any `.md` file, and for "update readme" or "fix markdown warnings".
---

# Write Markdown

Create and maintain Markdown files that pass markdownlint validation with zero warnings.

## Tooling Setup

These are setup notes for the user. Do not install tools or create or change configuration files (`.markdownlint.json`, `.vscode/settings.json`) unless the user asks. Use the existing markdownlint configuration of the repo. If `markdownlint` is not installed, tell the user, and check the rules by hand.

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
3. If the exit code is `0`, review the changes and commit.

## Essential Rules to Follow

### Headings (MD001, MD003, MD022, MD025)

```markdown
<!-- ✅ Good - single H1, incremental levels, blank lines around -->
# Document Title

## Section One

### Subsection

## Section Two

<!-- ❌ Bad - multiple H1, skipped levels, no blank lines -->
# Title
# Another Title
### Skipped H2
Content without blank line after heading
```

### Lists (MD004, MD007, MD030, MD032)

```markdown
<!-- ✅ Good - consistent markers, proper indentation, blank lines around -->
Before the list.

- Item one
- Item two
  - Nested item (2 spaces indent)
  - Another nested
- Item three

After the list.

<!-- ❌ Bad - mixed markers, wrong indent, no surrounding blank lines -->
Before the list.
* Item one
- Item two
    * Wrong indent (4 spaces)
After the list.
```

### Code Blocks (MD031, MD040, MD046, MD048)

````markdown
<!-- ✅ Good - language specified, blank lines around, consistent fence style -->
Some text before.

```json
{
  "key": "value"
}
```

Some text after.

<!-- ❌ Bad - no language, no blank lines, inconsistent fences -->
Some text before.
```
{
  "key": "value"
}
~~~
Some text after.
````

### Links and URLs (MD034, MD039, MD042)

```markdown
<!-- ✅ Good - proper link syntax, no bare URLs -->
See the [Configuration Guide](./config.md) for details.

Visit <https://example.com> for more information.

<!-- ❌ Bad - bare URL, spaces in link text, empty link -->
Visit https://example.com for more information.

See the [ Configuration Guide ](./config.md) for details.

Click [here]() for nothing.
```

### Tables (MD055, MD056, MD058)

```markdown
<!-- ✅ Good - consistent pipes, correct columns, blank lines around -->
Description of the table.

| Column A | Column B | Column C |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |

More content after.

<!-- ❌ Bad - inconsistent pipes, wrong column count -->
Description of the table.
Column A | Column B | Column C
---------|----------|----------
Value 1  | Value 2
Value 4  | Value 5  | Value 6  | Extra
More content after.
```

### Whitespace (MD009, MD012, MD047)

```markdown
<!-- ✅ Good - no trailing spaces, single blank lines, ends with newline -->
Line one.

Line two after single blank line.
<!-- File ends with exactly one newline -->

<!-- ❌ Bad - trailing spaces, multiple blank lines -->
Line one with trailing spaces.   


Line two after multiple blank lines.
<!-- No newline at end of file -->
```

### Emphasis and Code Spans (MD037, MD038)

```markdown
<!-- ✅ Good - no spaces inside markers -->
This is **bold** and *italic* text.

Use `inline code` for code.

<!-- ❌ Bad - spaces inside markers -->
This is ** bold ** and * italic * text.

Use ` inline code ` for code.
```

## File Structure Template

```markdown
# Document Title

Brief description of what this document covers.

---

## Table of Contents

- [Section One](#section-one)
- [Section Two](#section-two)
  - [Subsection A](#subsection-a)
- [Section Three](#section-three)

---

## Section One

Content for section one.

## Section Two

Content for section two.

### Subsection A

Content for subsection.

## Section Three

Final section content.
```

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

## Quick Reference

### Most Common Violations

| Rule  | Name                    | Fix                                         |
|-------|-------------------------|---------------------------------------------|
| MD009 | no-trailing-spaces      | Remove trailing whitespace                  |
| MD012 | no-multiple-blanks      | Use single blank lines                      |
| MD022 | blanks-around-headings  | Add blank line before/after headings        |
| MD031 | blanks-around-fences    | Add blank line before/after code blocks     |
| MD032 | blanks-around-lists     | Add blank line before/after lists           |
| MD034 | no-bare-urls            | Wrap URLs: `<https://...>` or `[text](url)` |
| MD040 | fenced-code-language    | Add language identifier to code blocks      |
| MD047 | single-trailing-newline | End the file with one newline               |

### Auto-Fixable Rules

These rules can be fixed automatically with `markdownlint --fix`:

- MD004, MD005, MD007 (list formatting)
- MD009, MD010, MD012 (whitespace)
- MD018-MD021 (heading spaces)
- MD022, MD023, MD026, MD027 (heading/blockquote formatting)
- MD030, MD031, MD032 (list/fence spacing)
- MD034, MD037-MD039 (URLs, emphasis, code spans)
- MD047, MD049, MD050 (newlines, emphasis style)

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
