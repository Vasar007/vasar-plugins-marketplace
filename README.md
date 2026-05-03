# vasar-claude-marketplace

Personal [Claude Code](https://docs.claude.com/claude-code) marketplace — composer agents, workflow commands, generic developer skills, a .NET backend toolkit, and a full Git Operations Pipeline (GOP) workflow.

> **Private repo.** Generic / stack-neutral artifacts. No employer or product branding.

---

## Plugins

| Plugin | Group | Purpose |
|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | Composer agents (PR, Task, Test, Docs) + generic workflow commands + cross-stack skills (markdown, XML docs, worktrees, PR review, feature pipeline, general conventions) |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | .NET / Clean Arch / DDD / EF Core / OpenAPI skills + backend conventions hub (controllers, services, configuration, domain models, EF patterns, logging, mappers, security, testing) |
| [`gop-pipeline`](./workflows/gop-pipeline) | `workflows` | Plan → implement → build → test → validate (correctness/reuse/security/compliance/performance, in parallel) → commit pipeline with specialist validator subagents |

---

## Installing the marketplace

Gives access to all plugins at once.

**Via command:**

```text
/plugins marketplace add https://github.com/Vasar007/vasar-claude-marketplace
```

**Via `.claude/settings.local.json`:**

```json
{
  "plugins": {
    "marketplaces": [
      "https://github.com/Vasar007/vasar-claude-marketplace"
    ]
  }
}
```

> The repo is private. You'll need a GitHub credential helper (or SSH URL `git@github.com:vasar007/vasar-claude-marketplace.git`) configured locally before Claude Code can clone it.

---

## Installing a single plugin

**Via `.claude/settings.local.json`:**

```json
{
  "plugins": {
    "sources": [
      {
        "name": "my-plugin",
        "url": "https://github.com/Vasar007/vasar-claude-marketplace",
        "path": "<group>/<plugin>"
      }
    ]
  }
}
```

Replace `<group>/<plugin>` with one of:

- `essentials/dev-essentials`
- `dotnet/dotnet-backend-dev`
- `workflows/gop-pipeline`

---

## Authoring reference

Only needed if you are modifying this marketplace or adding new plugins.

### Folder structure

```text
vasar-claude-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Lists every plugin in this marketplace
├── essentials/
│   └── dev-essentials/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/
│       ├── commands/
│       └── skills/
├── dotnet/
│   └── dotnet-backend-dev/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
└── workflows/
    └── gop-pipeline/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── agents/
        └── skills/
```

### `marketplace.json` schema

```json
{
  "name": "vasar-claude-marketplace",
  "owner": { "name": "Vasily Vasilyev", "email": "vasar007@gmail.com" },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./<group>/<plugin>",
      "version": "1.0.0",
      "description": "One-line summary shown in /plugins UI"
    }
  ]
}
```

### `plugin.json` schema

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin covers",
  "author": { "name": "Vasily Vasilyev" },
  "skills": "./skills/",
  "agents": "./agents/",
  "commands": "./commands/"
}
```

`skills`, `agents`, and `commands` may be either a directory string (`"./skills/"`) or an explicit list of paths (`["./agents/foo.md", "./agents/bar.md"]`). Use lists when you want to load only a subset of files in the directory.

---

## Conventions

- Names: `lowercase-kebab-case`. No organization or product prefixes.
- Skill files: `SKILL.md` at the root of each `skills/<name>/` directory; supporting files (templates, reference docs, stage scripts) sit alongside it.
- Agent files: one `.md` per agent under `agents/`.
- Command files: one `.md` per command under `commands/`. Filename = slash-command name.
- Stack-specific assumptions (e.g. .NET, PowerShell) must be declared explicitly inside the skill, not implied across files.

See [`CHANGELOG.md`](./CHANGELOG.md) for what landed when.
