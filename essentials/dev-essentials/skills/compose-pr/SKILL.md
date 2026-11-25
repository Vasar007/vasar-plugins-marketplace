---
name: compose-pr
description: Create a concise architectural PR description from the git diff and from any spec or plan of the branch.
when_to_use: "Use it for 'compose a PR description' or 'write the PR summary'. Not for an issue or a task description. Use compose-task for that."
---

# Compose a PR Description

Write a concise pull request (PR) description about the architecture of a change. Focus on **what changed and why** at a high level, not on implementation details.

This skill reads the diff with git, so it needs the Bash tool and a git repository.

## Length Constraints

- **Small changes** (1-5 files, <200 lines): Max **1000 characters**
- **Larger changes**: Max **2000 characters**

## Input

The input comes from the request of the user, or from the brief of the agent that runs this skill. It can hold extra context or instructions. Follow them, but keep the format and the length limits of this file.

The input can also name a base branch, and a spec, a plan, or a design document of the branch, as a path. It can also hold the text of a linked issue or task. Step 2 uses these items first. Do not fetch an issue. If the input gives only an issue number or a link, treat it as a number with no text (step 2).

## Workflow

All paths below are relative to the root of the repository (`git rev-parse --show-toplevel`).

### 1. Analyze Git Changes

First, find the base branch. Use the first source that works:

1. If the input names the base branch, use it.
2. Run `git symbolic-ref refs/remotes/origin/HEAD`. The output is for example `refs/remotes/origin/main`. Then use `origin/main` as `<base>`.
3. If that command fails or prints nothing, run `git rev-parse --verify --quiet origin/main`, then `git rev-parse --verify --quiet origin/master`. Use the first one that succeeds.
4. If none works, stop. Do not guess. Ask for the base branch (see "When to Stop and Ask").

Then analyze changes against the base branch:

```bash
# Replace <base> with the detected branch (e.g., origin/main, origin/release/1.0/master)
git diff --stat <base>...HEAD
git diff --name-status <base>...HEAD
git log <base>...HEAD --oneline
```

Ignore ephemeral artifacts in the diff. Examples are the drafts of the spec framework, a notes folder inside the repository (`${CLAUDE_PLUGIN_ROOT}/references/notes-root.md`), and any other scratch folder. Describe only the changes to code and configuration, for example source folders, test folders, pipelines, Dockerfiles, and helm charts. Step 2 can read these artifacts for the reason of the change. They are still not components of the PR.

### 2. Find the Spec or Plan of the Branch

A spec or planning artifact tells the reason of the change and its intent.

First, get the keys of the branch:

- The branch name: `git rev-parse --abbrev-ref HEAD`.
- The slug: the last segment of the branch name without a leading number. For `user/tasks/123-add-retry`, the slug is `add-retry`.
- The issue numbers: the leading number of the last segment, for example `123`. Also each number after a closing keyword in the branch commits, for example `Fixes #123`. Run `git log <base>...HEAD --format=%B` to read the commit messages.

An artifact belongs to this branch in one of these cases:

- The input names it.
- The branch diff adds or changes it.
- Its file name or folder name holds the slug or an issue number of the branch as a whole part. A separator (`-`, `_`, `.`, `/`) or an end of the name comes before and after a whole part. For example, the number `123` matches `123-plan.md` and `plan-123.md`, but not `1234-plan.md`. The slug `ci` matches `ci-plan.md`, but not `decision-log.md`.

Look for artifacts in this order. Use each one that belongs to this branch:

1. **The input**: each path and each issue text that the input gives.
2. **The spec framework**: if the project uses a spec framework, read each of its active changes that belongs to this branch. Read all of its files, for example its proposal, its design, and its tasks. If exactly one active change exists, treat it as belonging to this branch, even if no rule above matches it. Without a matching rule, this is a guess. Name the change as a guess in your final reply. A guess ranks below each artifact that belongs to this branch by a rule. If such an artifact exists, do not use the guess in the PR description. Do not take the intent or the reason from it, and do not name it in the PR. If several exist, use only the ones that belong by the rules above. Ignore the archived changes.
3. **Plan and design files**: Markdown files in the plan folders and the notes folders of the repository. Examples are `Plans/` and `Tasks/<id>/` in the notes folder, `plans/`, `docs/plans/`, `.claude/plans/`, and `docs/design/`. These folders are often ignored by git, so list them with `find`, not only with `git diff`. If a file belongs to this branch, read it. Ignore the other files.
4. **Decision records**: architecture decision record (ADR) files that the branch diff adds or changes. Examples are `doc/adr/`, `docs/adr/`, and `docs/decisions/`. If the repository has an `.adr-dir` file, it names the folder.

Do not fetch an issue or a task from a remote system. If the input does not hold the text of an issue, the issue is not an artifact. If you found an issue number, but the input has no text for it, name the number in your final reply. If the input gives a closing line, keep it, and put it where step 5 says. Do not add another closing keyword, for example one from a commit message.

If you find several artifacts, use all of them. If they disagree about the intent, the first artifact in the order above wins. If you find no artifact, use the git diff only, and skip to step 3.

Use the artifacts together with the diff:

- The artifacts give the reason of the change and its intent.
- The diff gives what changed. Describe only the changes that the diff holds.
- If an artifact plans work that the diff does not hold, say so in the "Notes" section in one line. Do not do this for a change of the spec framework that belongs to this branch only by a guess.
- If a change of the spec framework belongs to this branch, name its ID or its name in the PR.
- Do not name the path of a plan file, a notes folder, or another scratch artifact in the PR description.

### 3. Categorize Changes

Group the files by purpose, with the folder layout of the project. Examples of groups are core logic, tests, configuration, infrastructure, and documentation.

### 4. Read Key Files

- For **new files**: Read to understand purpose.
- For **modified files**: Use `git diff` to see actual changes, not full content.
- Focus on **public APIs, interfaces, domain models**.
- Skip: test files, minor configuration changes, formatting.

### 5. Generate PR Description

Use this structure. Start with `## What`, `## Why`, and `## Changes`, in this order. Put no other section or title before them or between them:

```md
## What
[1-2 sentences: the task and the core of the change]

## Why
[1-2 sentences: the problem that the change solves, and what it makes better]

## Changes
- **[Component]**: [what changed - 1 line]
- **[Component]**: [what changed - 1 line]

## Testing
[Brief testing approach - 1 sentence]

## Notes
[Any breaking changes, migration steps, or risks - if applicable]
```

Writing rules:

- **Why** gives the reason of the change, not a list of files. Take it from the artifacts of step 2. If no artifact gives a reason, take it from the diff and the commit messages. If a source names a gain in time, resources, or cost, name it too. Do not invent a number.
- **Omit** obvious changes, for example "updated tests to match".
- **Combine** related changes, for example "Added discount validation to the pricing service and the order model".
- **Skip** implementation details (how it works). Do not describe every file change, and do not explain code line by line.
- **Focus** on architectural impact (what capabilities changed).
- In `## Changes`, use **bullet points**, not paragraphs.
- Use **technical terms**, not marketing language.
- Do not copy commit messages word for word.
- Stay within the character limits above. The limits count the whole description.
- If the input gives a closing line for an issue, put it on its own line after the last section. Examples are `Closes #42.` and `Part of #42.`. If the session adds an attribution line, it comes last.

For example outputs of a small and a larger change, read [references/examples.md](references/examples.md).

### 6. Save PR Description

The notes folder is the folder that `${CLAUDE_PLUGIN_ROOT}/references/notes-root.md` gives. Read that file before the first read or write in the notes folder.

- Save the description as `PRs/PR-<branch>.md` in the notes folder. `<branch>` is the branch name with each `/` replaced by `-`. In a detached HEAD, use a `yyyyMMdd-HHmmss` timestamp instead. If the folder `PRs/` does not exist, create it. If the repo already uses a different drafts folder, for example `docs/prs/`, use that folder instead.
- The file must be valid Markdown with the `.md` extension.
- This skill writes the text only. It does not open, push, or edit the PR.
- Tell the user the file path, and show the PR description for a quick review.
- Name each artifact that you used in your final reply, with its path. Also name each guess and each issue number that had no text in the input.

## When to Stop and Ask

Stop and ask in these cases. In the main session, ask the user. In a subagent, put the question in your final reply, so that the caller asks the user:

- You cannot find the base branch (step 1).
- The git diff shows **no changes** (stale branch).
- The changes span **multiple unrelated features**. Suggest that the user splits the PR.
- The changes hold **breaking changes**, but no migration is documented.
