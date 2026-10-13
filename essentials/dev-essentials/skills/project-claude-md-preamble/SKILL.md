---
name: project-claude-md-preamble
description: Prevents preamble drift between the root instructions file of a repo (CLAUDE.md or AGENTS.md) and nested per-directory instructions files. Gives a generic, stack-neutral checklist of the section types that a root preamble commonly needs, without their content. Enforces the one-copy rule. A repo holds exactly one copy of its preamble. A nested instructions file points at the root preamble instead of a copy of its text. Use it to write a new root CLAUDE.md or AGENTS.md, or to add a nested instructions file under a subfolder or subproject. Also use it to audit a repo for preamble drift or duplication. Triggers on requests like "create a CLAUDE.md for this repo", "add a nested instructions file for this subfolder", or "audit our CLAUDE.md files for drift". Also on "why do our instructions files disagree", "does this subproject need its own copy of the preamble", or "reconcile CLAUDE.md across this repo".
---

# Project CLAUDE.md Preamble

Root instructions files (`CLAUDE.md`, `AGENTS.md`) usually open with a short
**preamble**: a few general rules on behavior that apply everywhere in the
repo. Examples: how to respond, the boundary between asking and proceeding,
and where the real conventions live. Nested instructions files often get a
pasted copy of that preamble. Examples of nested files: a `.claude/CLAUDE.md`,
the `AGENTS.md` of a subproject, or the local file of a monorepo package. That
copy is the bug. Later edits change the root file, and the nested copy falls
behind without a warning. This skill stops that copy, and finds it where it
already exists.

## The one-copy rule

**A repo holds exactly one copy of its preamble, at the root**. A nested
instructions file must **point at** the preamble of the root file instead of a
copy of its text. Use a one-line reference, for example: "See the preamble of
the root `CLAUDE.md` for general conventions. This file adds only what is
specific to `<subfolder>`".

A second full copy of the preamble anywhere in the repo is a finding on its
own. This holds also for two copies that still match today. Two verbatim
copies do not stay identical: if the rules change, one copy gets the edit, and
the other does not.

### Worked example

Root `CLAUDE.md`:

```markdown
## General conventions

- Match the user's language when responding; keep code, comments, and
  commits in English regardless of chat language.
- If a request is ambiguous, ask before proceeding — do not guess.
- Prefer this repo's own skills/commands for recurring tasks (tests,
  docs, PR descriptions) over ad hoc one-off approaches.
- Verify generated output (build, tests, lint) before reporting a task done.
- Commit and branch-naming conventions: see `docs/contributing.md`.
```

Correct nested `backend/CLAUDE.md`, with a pointer instead of a copy:

```markdown
# backend/CLAUDE.md

See the root `CLAUDE.md`'s **General conventions** section for how to
respond, when to ask versus proceed, tooling preference, and verification —
this file only adds what's specific to `backend/`.

## Backend-specific notes

- ...
```

The failure that this skill prevents is a nested `backend/CLAUDE.md` that
holds its own `## General conventions` section with the root bullets pasted
in. Such a file is a verbatim fork. After the next edit of a root bullet, the
copy falls behind, and nothing in the repo flags it.

## What a root preamble commonly covers

This is a **menu of section types**, not content to copy. What each bullet
says is specific to the project and belongs to its own conventions. Use the
menu as a checklist for a new preamble, or to find out whether an existing
one misses a section that it probably needs:

1. **Scope statement**: what the file governs (the whole repo or a
   subfolder). For a nested file, also an explicit pointer to the root file
   that it extends, not replaces.
2. **Response and communication conventions**: how the assistant answers
   (language, tone, length, formatting).
3. **Ask-vs-proceed boundary**: where the assistant stops and asks, and where
   it proceeds on its own. This is usually the bullet with the most value in
   the whole preamble.
4. **Tooling and skill-usage pointer**: where the skills, agents, or commands
   of the repo live, and that they come first, before an improvised approach
   to the same task.
5. **Verification-before-done expectation**: a rule that the assistant tests
   generated code or answers (build, tests, lint, a manual read) before it
   reports them as complete.
6. **Commit, PR, and branch convention pointer**: not the conventions
   themselves, only where they live (a doc, a linked skill, or a later
   section of the same file).
7. **Decision-authority boundary** *(optional)*: what the assistant can
   decide alone, and what needs the sign-off of the user (a public API shape,
   a new dependency, a schema change).

Not every repo needs all seven. A personal repo with one contributor can skip
the decision-authority boundary. A repo with no own tooling can skip the
skill-usage pointer. Add a section because the repo needs it, not because the
menu lists it.

## Authoring a new root preamble

1. Walk through the menu above, and decide which sections apply to this repo.
2. Write each one as a short, direct bullet of one or two sentences, not a
   paragraph. Nobody reads a preamble that reads like documentation.
3. Put it near the top of the root file, before the repo-specific sections
   (architecture, build commands, domain conventions). Every later section
   assumes that the reader saw it.
4. Do not put project-specific technical conventions here (naming schemes,
   test frameworks, layering rules). They belong in their own section or
   file. The preamble stays general.

## Adding a nested instructions file without duplicating

1. Find out whether the root preamble exists. If it does not, start with the
   authoring task of the previous section.
2. Open the nested file with a one-line pointer to the preamble section of
   the root, by name (see the worked example above). Never restate its
   bullets.
3. Add only what is truly specific to the nested scope: build quirks of a
   subfolder, the stack of a subproject, or exceptions that do not apply to
   the whole repo.
4. If a bullet seems to belong in both places, it belongs in the root only.
   Move it there and delete it from the nested file. Do not keep it in both.
   This also holds for a new general rule that you first noticed in a
   subfolder.

## Auditing an existing repo for drift

1. Find every instructions file in the repo, root and nested
   (`.claude/CLAUDE.md`, `AGENTS.md` files of subprojects, and others).
2. For each nested file, find out whether it duplicates the root preamble
   (mostly matching bullets in both files) instead of a pointer to it. Report
   a duplicate as a finding on its own, also where the two copies agree
   today. The duplication is the bug, not only the disagreement that it
   causes later.
3. For each nested file with a correct pointer, find out whether the pointer
   still names a real section heading of the root. If it does not, report it.
   After a rename or a restructure of the root preamble, a stale pointer is
   as silent as a stale copy.
4. Report drift for each file, not as one pass or fail. A nested file that
   lacks a bullet because the bullet does not apply to its subfolder is not
   drift. Two files with the same bullet in different words are drift.
