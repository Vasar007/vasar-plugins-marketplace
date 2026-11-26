# Guide Drafts and Publishing

The section "Guide Drafts and Publishing" of `SKILL.md` points here. A guide is concise documentation outside the `Docs/` layout of the project, for example a how-to guide.

## Documentation Style

Follow this style:

- **Structure**: Use H1 for the main title, H2 for sections, H3 for subsections.
- **Introduction**: Start with a brief overview explaining the topic.
- **Lists**: Numbered lists for steps/procedures, bullet points for features/options.
- **Code blocks**: Use appropriate language tags, for example `shell`, `json`, or `yaml`.
- **Tables**: For structured data comparisons.
- **Examples**: Include practical, real-world examples.
- **Warnings**: Use a blockquote for an important warning or note.

## Workflow

### 1. Creating Documentation

When the user requests a guide on a topic:

1. Create a Markdown file in `Docs/` of the notes folder. If the repository uses a different drafts folder, for example `docs/drafts/`, use that folder instead. The notes folder is the folder that `references/notes-root.md` at the root of this plugin gives. From the base folder of this skill, its path is `../../references/notes-root.md`.
2. Use kebab-case for the filename: `topic-name.md`.
3. Write the content in the style of "Documentation Style" above.

### 2. Editing Documentation

All edit requests without the explicit "publish" command relate to the local Markdown draft in the drafts folder. The words "update", "edit", "change", and "fix" mean the local file only.

### 3. Publishing

**If the user does not explicitly say "publish", do not publish.**

Get these values from the user. If a required value is missing, stop and ask for it. In a subagent, put the question in your final reply, so that the caller asks the user:

- Target platform, for example Confluence cloud, Confluence self-hosted, or Notion (required).
- Page title or name (required).
- Parent page ID or folder (optional, depends on the platform).

Before publishing:

1. Make sure that the heading levels follow "Documentation Style".
2. Find the MCP servers that are available in the current session. Look for tool names that match `mcp__<server>__*`. Pick the server that matches the target platform. Typical names:
   - `mcp__mcp-atlassian-cloud__*`: Confluence cloud
   - `mcp__mcp-atlassian-local__*`: Confluence self-hosted
   - Any other documentation MCP server that the user configured
3. **Inspect the tool schema of the chosen server** before the call. Parameter names differ between servers, so do not assume them. For Confluence cloud, the create-page tool typically expects `cloudId`, `spaceId`, `title`, `parentId`, `status`, `contentFormat`, and `content`. The local server uses `spaceKey` and `parentPageId`. Treat an ID that the user mentioned as a value from the user. This also holds for an example ID in a configuration, such as a `cloudId` or a `spaceId`. Do not hardcode it.
4. Call the selected MCP tool.
5. Report the published URL or ID to the user.

### Compose-Only Fallback

If no suitable MCP server is available in the session, for example in a restricted environment:

1. Finalize the Markdown draft in the drafts folder.
2. Report the file path, and say that the guide is not published. In a subagent, put both in your final reply, so that the caller can publish the draft.

Never claim a publish that did not happen. If the tool call cannot happen, say so plainly.

## Critical Rules

1. **Never publish without an explicit "publish".**
2. **Use Markdown format** for both the local and the published versions, unless the tool schema of the chosen server asks for another format.
3. **Never hardcode platform-specific IDs** (cloudId, spaceId, parentId). Get them from the user or from the tool schema of the MCP server at call time.

## Example Documentation Structure

````markdown
# [Topic Title]

Brief introduction explaining what this is and why it matters.

## Overview

High-level explanation of the concept or process.

## [Main Section 1]

Detailed information with context.

### [Subsection 1.1]

Specific details or steps.

```language
code example
```

## [Main Section 2]

Next major topic with examples.

| Column 1 | Column 2 |
|----------|----------|
| Data     | Data     |

## Best Practices

- Key recommendation 1
- Key recommendation 2
- Key recommendation 3
````

## Response Style

- Report each action, for example "Created [filename]", "Updated [section]", or "Published to Confluence (page ID 12345)".
- Do not ask for clarification unless you cannot continue without it.
- Show a brief preview of the structure after creating content.
