---
name: compose-task
description: "Write a task description or a GitHub issue at the architecture level. The default writes a local Markdown draft. On request, it returns the text in chat, or creates the GitHub issue and reads it back."
when_to_use: "Use it for 'draft an issue', 'write a task description', 'compose an issue', or 'create a GitHub issue'. Not for a PR description. Use compose-pr for that."
---

# Compose a Task Description

Write concise task descriptions at the architecture level for project planning. Draft and edit them, and create them as GitHub issues only on an explicit request. Never implement the changes. Document the necessary changes in a fixed structure. The agent `dev-essentials:task-composer` preloads this skill, so a workflow can also hand the work to a subagent.

Focus on **what** and **why**, not on implementation details. The maximum length is **2000 characters** in all three modes.

The modes `draft` and `response` need only file tools. The mode `create` needs the GitHub MCP tools (`mcp__plugin_github_github__*`). If they are missing, stop, and ask the user to reconnect them with `/mcp` (`dev-essentials:github-mcp-conventions` Rule 5).

## Mode Parameter

Every invocation operates in one of three modes:

| Mode | Side effects | Output |
|------|--------------|--------|
| **`draft`** (DEFAULT) | writes `Notes/Tasks/<file>.md` | tells user the file path |
| **`response`** | none | the markdown text itself, in chat |
| **`create`** | creates and verifies a real GitHub issue | real issue number + URL from API response |

`draft` and `response` never call a GitHub MCP tool, for a read or for a write. In `draft` mode, the user creates the issue. If the user explicitly asks for text only, use `response` mode. Examples: the user wants to paste the text into a GitHub issue form or another tool.

**Trigger phrases:**

- `draft`: "draft a task description", "write a task draft", "compose a task", or any unqualified request ("write a task", "update", "edit", "fix"). **`draft` is the default. `response` requires an explicit opt-in.** "Preview", "just show me", and similar phrases still route to `draft`. `draft` already shows a brief preview after it writes the file.
- `response`: "give me the description text", "return the description in chat", or "no file, just the text". Also "show me the task description directly", "preview without saving", or "do not write a file".
- `create`: "publish", "create a GitHub issue", "add to GitHub", "create the issue".

A calling skill or a brief can also name the mode, for example `mode: response`.

## Task Documentation Structure

Begin with **Task Title** (H1, single line, suitable for issue tracker).

Then two sections:

### Current State Analysis

- Current system state and why it is a problem
- Key limitations or technical debt
- Impact on development / performance / maintainability

### Changes to Do

- **Each change item must be under 10 words**
- **High-level architectural changes only** (no code snippets, no specific class/interface names)
- General abstraction needs, patterns, or dependencies
- API contract changes (endpoints, parameters, response formats)
- Component interaction modifications at a conceptual level

## Workflow

### 1. Creating a Draft or Response (`mode: draft` / `mode: response`)

Both modes produce the same Markdown content: the H1 title, the H2 "Current State Analysis", and the H2 "Changes to Do" with bullet points. Only the destination differs.

**`mode: draft` output:** Write the content to `Notes/Tasks/task-{feature-name}.md`, with a kebab-case file name. All paths are relative to the root of the repository. If the folder does not exist, create it. Confirm with the file path and a brief preview of the structure.

**`mode: response` output:** Return the Markdown content directly in the chat response. Write no file. Confirm with a one-line note that no file was created, for example "Here is the description (no file written):".

### 2. Editing a Draft

An edit request without an explicit `mode: create` changes the local Markdown file only. "Update", "edit", "change", and "fix" mean `mode: draft`, unless the user explicitly asked for `mode: response`. If the user received a `response`-mode output and now wants to edit it, run `mode: response` again with the requested changes. Do not create a file unless the user asks for one.

- Read the current draft file.
- Apply the requested changes.
- Iterate based on feedback.
- **Never create a GitHub issue** during this workflow.

### 3. Creating in GitHub (`mode: create`)

Before you call a GitHub tool, read [references/create-mode.md](references/create-mode.md). It has the pre-flight conditions, the create call, the read-back, and the report. `create` mode always creates, then reads back. Never report a result that did not come from the API.

## Critical Rules

1. **Never create an issue without explicit `mode: create`.** `draft` and `response` modes never call any GitHub MCP tool (read or write).
2. **No invented issue numbers or URLs.** Only report issue numbers and URLs that appear in actual API responses. If the read-back fails, report the failure.
3. **No fabricated relationship confirmations.** Report a parent or sub-issue link as set up only after `mcp__plugin_github_github__issue_read` with `method: "get_parent"` shows it.
4. **Never infer or substitute `owner/repo`.** Use the values that the user supplied, verbatim (see `dev-essentials:github-mcp-conventions` Rule 1).
5. **Markdown in all three modes**, also for the GitHub issue body. GitHub renders Markdown, so no HTML conversion is needed.
6. **No implementation details** (no "change line 42", no code blocks, no specific class/interface names).
7. **No prioritization or estimation.**

## Good Change Examples

- "Add notification capability to controllers"
- "Separate authentication from profile management services"
- "Add pagination to items endpoint"
- "Extract retry logic into shared infrastructure component"

## What to Avoid in the Description

- Line-by-line code changes
- Verbose explanations
- Implementation steps or specific class/interface names
- Code snippets or file paths
- Steps that create tickets, and effort estimates
- Technical jargon like "inject", "inherit from", "implement interface"

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

- Be concise.
- Confirm actions: "Created `Notes/Tasks/task-foo.md`", "Here is the description (no file written):" (for `mode: response`), "Created GitHub issue #12345 (verified): `<html_url>`".
- Ask for clarification only for a missing required input: `owner/repo` in `create` mode. In the main session, ask the user. In a subagent, put the question in your final reply, so that the caller asks the user.
