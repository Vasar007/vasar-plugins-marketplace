---
name: create-documentation
description: Create or update project documentation Markdown files following established conventions. Use when documenting features, configuration options, REST APIs, migrations, or architectural decisions in any project. Triggers on requests like "create documentation", "document feature", "write docs", "update documentation".
---

# Create Documentation

Create and maintain project documentation in the `Docs/` folder with the layout, names, and templates below. If the repository already has a documentation folder with another layout, use that layout and its names.

## Documentation Structure

```txt
Docs/
├── {ProjectName} - {Topic}.md           # Top-level documentation
├── Features/                             # Feature documentation
│   ├── {ProjectName} - Features-Overview.md
│   └── {ProjectName} - {Feature}.md
├── Migrations/                           # Database migration docs
│   └── {Version}/
│       └── {ProjectName} - {Migration}.md
└── REST API/                             # API documentation
    ├── {ProjectName} - REST-API-Overview.md
    └── {ProjectName} - REST-API-{Resource}.md
```

## File Naming Convention

**Pattern**: `{ProjectName} - {Topic}.md`

- Use title case for topic names.
- Separate the words of a topic with spaces. Only the fixed names `Features-Overview` and `REST-API-Overview` and the prefix `REST-API-` use hyphens.
- `{ServiceName}` in the templates means the same as `{ProjectName}`.

**Examples**:

- `{ProjectName} - Configuration.md`
- `{ProjectName} - {FeatureName}.md`
- `{ProjectName} - REST-API-{Resource}.md`

## Markdown Guidelines

**CRITICAL**: Follow the [write-markdown](../write-markdown/SKILL.md) skill for lint-free Markdown. Before you finish, go through the "Documentation Checklist" below.

## Content Conventions

### Rule 1: Describe current state, not a changelog

**Why**: A reader of a doc, a spec, or a code comment never saw its earlier revisions. Change narration is noise to that reader, and it goes stale. It belongs in the commit message or the PR.

**How to apply**:

- Write every revision of a doc, plan, spec, or code comment as the single current state of the thing that it describes.
- Remove meta-commentary about what changed: "corrected", "WITHDRAWN", `CONFIRMED (owner ...)`, "previously/formerly", "round N", "misremembered", and "OPEN QUESTION -> CLOSED" postmortems. Delete a resolved open question and state the answer. Do not mark the question as resolved.
- Code comments describe the code **as it is now**. Never write "was X, now Y" (for example `// was synchronous before v3, now async`), and never write an inline incident or change history. That history belongs in the commit message or the PR.
- Keep comments short, and do not repeat what the code already says. Put the high-level "what/why" of a type or method in its XML doc summary, not in scattered inline comments.
- Factual provenance can stay. Code, PR, and commit references and file:line anchors are references, not changelog entries.

### Rule 2: Treat docs as living, update them in the same change

**Why**: A doc that changes only in a later "docs cleanup" pass drifts from the code. If you do not write down a gotcha at once, it gets lost.

**How to apply**:

- If you change behavior that a doc describes (schedules, cleanup targets, category mappings, stages, regions, naming, architecture, workflow), update that doc in the **same** change. Never move the doc update to a separate follow-up task or backlog item.
- If you find a new gotcha during the work, add it to the related doc at once, not in a later cleanup batch. This also holds after you fix its cause.
- Update every doc that describes the change. This includes the deeper `docs/` files (architecture, dev workflow, SDK patterns), not only the top-level doc.
- Treat every maintained doc as a living starting point, not a write-once artifact.

## Document Templates by Type

Each template is in its own file. Before you write a document of one of these types, read its template file and follow its structure. Do not read the other template files.

| Document type | Template file | Related skill |
| --- | --- | --- |
| Configuration options classes of a .NET service | [templates/configuration.md](templates/configuration.md) | `dotnet-backend-dev:add-configuration-option` |
| Service features and workflows | [templates/feature.md](templates/feature.md) | None |
| REST API endpoints | [templates/rest-api.md](templates/rest-api.md) | `dotnet-backend-dev:update-swagger-spec` |
| Database migrations | [templates/migration.md](templates/migration.md) | `dotnet-backend-dev:add-migration` |

## Documentation Checklist

Before you submit documentation:

- [ ] File follows naming convention: `{ProjectName} - {Topic}.md`
- [ ] Single H1 heading as document title
- [ ] Table of Contents with working anchor links
- [ ] All code blocks have language specifiers
- [ ] Headings, code blocks, lists, and tables have blank lines before and after
- [ ] No bare URLs (use `<url>` or `[text](url)`)
- [ ] No trailing whitespace
- [ ] File ends with single newline
- [ ] Internal links use relative paths with URL encoding for spaces
- [ ] `markdownlint` reports no warnings for the documentation folder, for example `markdownlint "Docs/**/*.md"`

## Cross-References

When you document a new feature, also update the related documents:

| Document Type     | Update When                                  |
|-------------------|----------------------------------------------|
| Features-Overview | Adding new feature                           |
| REST-API-Overview | Adding new API controller                    |
| Configuration     | Adding new configuration options             |
| Migration folders | Adding database migrations                   |

## Related Skills

- [write-markdown](../write-markdown/SKILL.md): Markdown conventions and linting
- `dotnet-backend-dev:add-configuration-option`: configuration options classes
- `dotnet-backend-dev:add-migration`: database migration implementation
- `dotnet-backend-dev:update-swagger-spec`: OpenAPI specification updates
