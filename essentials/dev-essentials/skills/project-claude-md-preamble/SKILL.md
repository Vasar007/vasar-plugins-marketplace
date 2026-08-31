---
name: project-claude-md-preamble
description: Prevents preamble drift between a repo's root instructions file (CLAUDE.md / AGENTS.md) and any nested per-directory instructions files. Provides a generic, stack-neutral checklist of section types a root preamble commonly needs (scope statement, response conventions, ask-vs-proceed boundary, tooling pointer, verification expectation, commit/PR pointer, decision-authority boundary) without prescribing their actual content, and enforces the rule that a repo holds exactly one copy of its preamble — a nested instructions file must point at the root's preamble instead of re-copying its text, because verbatim duplicates provably drift out of sync. Use when authoring a brand-new root CLAUDE.md/AGENTS.md, adding a nested instructions file under a subfolder or subproject, or auditing an existing repo for preamble drift or duplication. Triggers on requests like "create a CLAUDE.md for this repo", "add a nested instructions file for this subfolder", "audit our CLAUDE.md files for drift", "why do our instructions files disagree", "does this subproject need its own copy of the preamble", or "reconcile CLAUDE.md across this repo".
---

# Project CLAUDE.md Preamble

Root instructions files (`CLAUDE.md`, `AGENTS.md`) usually open with a short
**preamble**: a handful of general, behavioral bullets that apply everywhere in
the repo — how to respond, when to ask versus proceed, where the real
conventions live. When a repo also has nested instructions files (a
`.claude/CLAUDE.md`, a subproject's own `AGENTS.md`, a monorepo package's
local file), the easiest way to give that nested file the same general rules
is to copy-paste the preamble into it.

That copy is the bug. The root file gets edited later — a bullet reworded, a
new one added, one dropped — and the nested copy does not get touched in the
same pass, because nothing forces it to. Nobody notices until someone reads
both files side by side and finds them disagreeing. This skill exists to stop
that copy from ever being made, and to catch it when it already has been.

## When to use

- **Authoring**: a repo needs a root `CLAUDE.md`/`AGENTS.md` and doesn't yet
  have a preamble section.
- **Adding a nested file**: a subfolder or subproject needs its own
  instructions file in addition to the repo's root one.
- **Auditing**: an existing repo's instructions files (root and/or nested)
  need checking for drift — a bullet that quietly diverged, or a nested copy
  that duplicates the root instead of pointing at it.

## The one-copy rule

**A repo holds exactly one copy of its preamble, at the root.** Any nested
instructions file must **point at** the root file's preamble instead of
re-copying its text — a one-line reference such as "see the root
`CLAUDE.md`'s preamble for general conventions; this file adds only what's
specific to `<subfolder>`."

This is not a hypothetical risk, it is the default outcome of copy-pasting.
Two verbatim copies of the same bullets in one repo do not stay identical:
one location gets edited when the rules change, the other doesn't, and
nothing short of a manual side-by-side read ever surfaces the gap. Treat a
second full copy of the preamble anywhere in the repo as the finding itself —
regardless of whether the two copies still happen to match today.

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

Nested `backend/CLAUDE.md` — correct, points instead of copying:

```markdown
# backend/CLAUDE.md

See the root `CLAUDE.md`'s **General conventions** section for how to
respond, when to ask versus proceed, tooling preference, and verification —
this file only adds what's specific to `backend/`.

## Backend-specific notes

- ...
```

Nested `backend/CLAUDE.md` — the failure mode this skill exists to prevent:

```markdown
# backend/CLAUDE.md

## General conventions

- Match the user's language when responding; keep code, comments, and
  commits in English regardless of chat language.
- If a request is ambiguous, ask before proceeding — do not guess.
- Prefer this repo's own skills/commands for recurring tasks (tests,
  docs, PR descriptions) over ad hoc one-off approaches.
- Verify generated output (build, tests, lint) before reporting a task done.
- Commit and branch-naming conventions: see `docs/contributing.md`.

## Backend-specific notes

- ...
```

The second version is a verbatim fork. The moment the root's "ask before
proceeding" bullet is reworded, or a new bullet is added, this copy silently
falls behind — and nothing in the repo flags it.

## What a root preamble commonly covers

This is a **menu of section types**, not prescriptive content — what each
bullet actually says is project-specific and belongs to the project's own
conventions, not to this skill. Use it as a checklist when authoring a new
preamble or when checking whether an existing one is missing something it
probably needs:

1. **Scope statement** — what this file governs (the whole repo? a
   subfolder?), and, for a nested file, an explicit pointer to the root file
   it extends rather than replaces.
2. **Response / communication conventions** — how the assistant should talk
   back: language, tone, verbosity, formatting expectations.
3. **Ask-vs-proceed boundary** — when the assistant should stop and ask
   versus when it's expected to proceed independently. This is usually the
   single highest-value bullet in the whole preamble.
4. **Tooling / skill-usage pointer** — where the repo's own skills, agents,
   or commands live and that they should be preferred over improvising the
   same task from scratch each time.
5. **Verification-before-done expectation** — a rule that generated code or
   responses get checked (build, tests, lint, a manual read) before being
   reported as complete.
6. **Commit / PR / branch convention pointer** — not the conventions
   themselves, just where they live (a doc, a linked skill, a section further
   down the same file).
7. **Decision-authority boundary** *(optional)* — what the assistant may
   decide unilaterally versus what requires the user's sign-off (a public API
   shape, a new dependency, a schema change, etc.).

Not every repo needs all seven. A single-contributor personal repo might skip
the decision-authority boundary entirely; a repo with no dedicated tooling
might skip the skill-usage pointer. Include a section because the repo
actually needs it, not because the checklist lists it.

## Authoring a new root preamble

1. Walk the checklist above and decide which sections apply to this repo.
2. Write each as a short, direct bullet — a sentence or two, not a paragraph.
   A preamble that reads like documentation stops getting read.
3. Place it near the top of the root file, before repo-specific sections
   (architecture, build commands, domain conventions) — it's the part every
   later section implicitly assumes the reader already saw.
4. Do not embed project-specific technical conventions here (naming schemes,
   test frameworks, layering rules) — those belong in their own section or
   their own file; the preamble stays general-purpose.

## Adding a nested instructions file without duplicating

1. Confirm the root preamble already exists. If it doesn't, that's an
   authoring task (previous section), not a nested-file task.
2. Open the nested file with a one-line pointer at the root's preamble
   section by name (see the worked example above) — never restate its
   bullets.
3. Add only what's genuinely specific to the nested scope: a subfolder's
   build quirks, a subproject's own stack, exceptions that don't apply
   repo-wide.
4. If a bullet feels like it belongs in both places, it belongs in the root
   only — move it there and delete it from the nested file, don't keep it in
   both.

## Auditing an existing repo for drift

1. Locate every instructions file in the repo — root and nested
   (`.claude/CLAUDE.md`, subproject `AGENTS.md` files, etc.).
2. For each nested file, check whether it duplicates the root preamble
   (largely-matching bullets present in both) instead of pointing at it. Flag
   this as a finding on its own, independent of whether the two copies
   currently agree — duplication is the bug, not just the disagreement it
   eventually produces.
3. For each nested file that correctly points at the root, confirm the
   pointer still names real root section headings — a root file that renamed
   or restructured its preamble section leaves a stale pointer behind just as
   silently as a stale duplicate.
4. Report drift per file rather than as one pass/fail: a nested file that's
   missing a bullet because it genuinely doesn't apply to that subfolder is
   not drift; two files carrying the same bullet with different wording is.

## Anti-patterns

- Copy-pasting the whole preamble into a nested file "just this once, for
  convenience" — this is exactly the failure mode the one-copy rule exists to
  prevent, and it starts identically every time.
- A nested file's pointer naming a root section that no longer exists after
  the root was restructured.
- Treating the checklist above as literal text to paste — it names section
  *types*; the actual bullets are the project's own conventions.
- Adding a whole new preamble section to a nested file instead of adding it
  to the root and pointing at it — general rules belong at the root even when
  the need for one was first noticed while working in a subfolder.
