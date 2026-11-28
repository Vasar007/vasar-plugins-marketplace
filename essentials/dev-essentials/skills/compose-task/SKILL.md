---
name: compose-task
description: "Write a task description or a GitHub issue at the architecture level. The default writes a local Markdown draft. On request, it returns the text in chat, or creates the GitHub issue and reads it back."
when_to_use: "Use it for 'draft an issue', 'write a task description', 'compose an issue', or 'create a GitHub issue'. Not for a PR description. Use compose-pr for that."
---

# Compose a Task Description

Write concise task descriptions at the architecture level for project planning. Draft and edit them, and create them as GitHub issues only on an explicit request. Never implement the changes.

Focus on **what** and **why**, not on implementation details. The maximum length is **2000 characters** in all modes.

The modes `draft` and `response` need only file tools. The mode `create` needs the GitHub MCP tools (`mcp__plugin_github_github__*`). If they are missing, stop, and ask the user to reconnect them with `/mcp` (`dev-essentials:github-mcp-conventions` Rule 5).

## Mode Parameter

Every invocation operates in one of these modes:

| Mode | Side effects | Output |
|------|--------------|--------|
| **`draft`** (DEFAULT) | writes `Tasks/<file>.md` in the notes folder | tells user the file path |
| **`response`** | none | the markdown text itself, in chat |
| **`create`** | creates and verifies a real GitHub issue | real issue number + URL from API response |

In `draft` mode, the user creates the issue. If the user explicitly asks for text only, use `response` mode. Examples: the user wants to paste the text into a GitHub issue form or another tool.

**Trigger phrases:**

- `draft`: "draft a task description", "write a task draft", "compose a task", or any unqualified request ("write a task", "update", "edit", "change", "fix"). **`draft` is the default. `response` requires an explicit opt-in.** "Preview", "just show me", and similar phrases still route to `draft`. `draft` already shows a brief preview after it writes the file.
- `response`: "give me the description text", "return the description in chat", or "no file, just the text". Also "show me the task description directly", "preview without saving", or "do not write a file".
- `create`: "publish", "create a GitHub issue", "add to GitHub", "create the issue".

A calling skill or a brief can also name the mode, for example `mode: response`.

## Task Documentation Structure

Begin with **Task Title** (H1, single line, suitable for issue tracker).

Then these sections:

### Current State Analysis

- Current system state and why it is a problem
- Key limitations or technical debt
- Impact on development / performance / maintainability
- For a bug: numbered steps to repeat it, the actual result, the expected result, and the version or the commit. If the input does not give the version or the commit, write `unknown`. Do not guess it.

### Changes to Do

- **Each change item must be under 10 words**
- **High-level architectural changes only** (see Critical Rule 4)
- General abstraction needs, patterns, or dependencies
- API contract changes (endpoints, parameters, response formats)
- Component interaction modifications at a conceptual level

## Workflow

### 1. Creating a Draft or Response (`mode: draft` / `mode: response`)

Both modes produce the same Markdown content, in the form of "Task Documentation Structure". Only the destination differs.

First, look for an issue template of the repository: `Glob` the pattern `.github/ISSUE_TEMPLATE/*`. If the input names a template, use it. Else use the one template whose name and `about` text fit the task. If none fits, or several fit, use the form of "Task Documentation Structure", and name the templates in your final reply.

If you use a template:

- Use its headings in their order, instead of the two sections of the form. For a form file (`.yml`), use the `label` of each field as a heading.
- Read each HTML comment as the instruction for its section. Do what it says, and leave the comment out.
- Write the H1 title in the form of the `title` of its front matter.
- Name the `labels` of its front matter in your final reply. `mode: create` passes them as labels.
- For a bug, put each bug field above that the template has no heading for into the section that fits best.
- The length limit and the Critical Rules still apply.

**`mode: draft` output:** Write the content to `Tasks/task-{feature-name}.md` in the notes folder, with a kebab-case file name. Confirm with the file path and a brief preview of the structure.

The notes folder is the folder that `${CLAUDE_PLUGIN_ROOT}/references/notes-root.md` gives. Read that file before the first read or write in the notes folder.

**`mode: response` output:** Return the Markdown content directly in the chat response. Write no file. Confirm with a one-line note that no file was created, for example "Here is the description (no file written):".

### 2. Editing a Draft

An edit request without an explicit `mode: create` changes the local Markdown file only, and it **never creates a GitHub issue**. Read the current draft file, and apply the requested changes. If the user received a `response`-mode output and now wants to edit it, run `mode: response` again with the requested changes. Do not create a file unless the user asks for one.

### 3. Creating in GitHub (`mode: create`)

Before you call a GitHub tool, read [references/create-mode.md](references/create-mode.md). It has the pre-flight conditions, the create call, the read-back, and the report.

## Critical Rules

1. **Never create an issue without explicit `mode: create`.** `draft` and `response` modes never call any GitHub MCP tool (read or write).
2. **No invented issue numbers or URLs.** Only report issue numbers and URLs that appear in actual API responses. If the read-back fails, report the failure.
3. **Never infer or substitute `owner/repo`.** Use the values that the user supplied, verbatim (see `dev-essentials:github-mcp-conventions` Rule 1).
4. **No implementation details**: no line-by-line code changes, no implementation steps, no code blocks or snippets, no file paths, and no specific class or interface names. Do not use jargon such as "inject", "inherit from", or "implement interface".
5. **No prioritization, effort estimates, or steps that create tickets.**

## Example Task Structure

```markdown
# Add async processing for order export

## Current State Analysis

The order export currently uses synchronous polling which blocks request threads and limits scalability. This causes resource contention under load and prevents efficient handling of long-running exports.

## Changes to Do

- Add async processing infrastructure for exports
- Implement background export service
- Add export status change notifications
- Update API endpoints for async patterns
- Add export progress tracking
```

## Response Style

- Confirm actions: "Created `<notes folder>/Tasks/task-foo.md`", "Here is the description (no file written):" (for `mode: response`), "Created GitHub issue #12345 (verified): `<html_url>`".
- Ask for clarification only for a missing required input: `owner/repo` in `create` mode. In the main session, ask the user. In a subagent, put the question in your final reply, so that the caller asks the user.
