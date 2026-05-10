---
name: engineering-discipline
description: "Engineering discipline rules that override the natural temptation to defer, dismiss, or unilaterally decide. Covers: (a) owning every red signal (tests, lint, compile) in the session without declaring it pre-existing; (b) never making unilateral critical decisions (DI dependency, public signature, contract weakening, test assertion relaxation) not covered by the current spec/plan; (c) never referencing pipeline-internal artifacts (Notes/Tasks/..., §7d, scenario-coverage-gap.md) from shipped code, docs, or commit messages. Apply continuously during implementation, code review, PR-comment processing, and feature-pipeline runs. Triggers on requests like 'implement this spec', 'apply plan', 'fix tests', 'process PR comments', 'write feature code', 'run feature pipeline', or any session where code is being written, reviewed, or committed."
---

# Engineering Discipline

This skill captures three discipline rules that surface repeatedly in code reviews and post-mortems. They aren't a checklist run once at the end — they're judgment calls you make continuously while writing or reviewing code.

## Rule 1 — Own every red signal in your session

When any automated check goes red — failing tests, `openspec validate`, markdownlint, compile errors, warnings-as-errors — that signal is yours to fix the moment you see it.

Do not say "pre-existing failure", "not caused by my change", "already failing before I touched this", or any equivalent. Do not check whether `git log` shows the failure predates your work. The act of working in the area transfers ownership. This applies even when the failure is codebase-wide (e.g., many specs already have the same format issue) — "everyone has it" is not an excuse to skip it.

Why this is the rule: Reviewers expect agents to surface ambiguity rather than mask it. Deferring a known-broken signal makes the next person's session start broken too, and over time the codebase drifts into a "tests have always been red" state that everyone tolerates. Owning every red signal in the session is what keeps the build honest.

How to apply:

- When a check fails, investigate and fix. Don't audit blame first.
- If a fix is genuinely out of scope (touching unrelated code, requires a new design conversation, etc.), flag it explicitly to the user and ask before moving on. Never skip silently.
- "Tests fail against my new code" is almost never solved by relaxing the assertion. Investigate the design gap before touching the test (this also intersects with Rule 2 below).

## Rule 2 — No unilateral critical decisions in spec-first / plan-first work

When you operate inside a spec-first or plan-first workflow (OpenSpec, design docs, task plans, RFCs, ADRs, feature-pipeline), you may not make a critical decision the artifact does not already cover. Critical decisions include, at minimum:

- Public signature changes (method, interface, controller endpoint shape)
- Adding a new DI dependency or persistence concern
- Choosing among alternatives for layering, library, or option
- Moving a type across architectural layers
- Weakening a test assertion to make broken code pass

If the artifact does not authorize the decision: stop. Either cite where the decision lives, or pause and ask the user — and propose an artifact amendment in the same session if the choice is real.

Why this is the rule: AI-picked defaults are bad in most cases. The canonical worked example is a public-API refactor where one method must replace two existing endpoints — earlier sessions silently introduced a null default in one path and altered the paired tests to accept null, producing a production-breaking gap hidden under green tests. The cure is to never weaken a test or invent a default to make the green light light up; surface the gap instead.

How to apply:

- When you reach for an A-vs-B decision that nothing in front of you names, that's the trigger. Stop, write the question, ask.
- Reframing a test to pass is the most common form of this rule's violation — it looks like progress. It almost never is.
- "Implicit by convention" is not a citation. If the decision is convention-driven, point at the convention file or skill that documents it; if you can't, treat it as undocumented and ask.

## Rule 3 — No pipeline-internal artifacts in shipped code, docs, or commit messages

Production source files, shipped tests, shipped docs (`Docs/`, `openspec/specs/`), commit messages, PR titles, and PR descriptions must not reference any pipeline-internal artifact:

- `Notes/Tasks/<id>/...` paths (gitignored working dir)
- Spec / test-plan section anchors like `§7d`, `§3.5`, `Q5`, `Resolved Question #5`
- Filenames like `scenario-coverage-gap.md`, `requirements.md`, `spec.md`, `test-plan.md`, `review.md`, `pipeline-state.json`
- Pipeline stage names like `Step C`, `Stage 3`, `feature-pipeline §X`

Use only stable references: issue/task IDs (`#1234`, `#5678`), code-level concepts (predicate names, helper names, configuration option names), self-contained behavior descriptions.

Why this is the rule: pipeline artifacts live under `Notes/Tasks/` (gitignored) and inside the orchestration's own working memory. Anyone who reads the merged code six months later sees a dangling reference they can't resolve, because the artifact never shipped. The reference promises traceability and delivers confusion.

How to apply:

- When writing XML docs, inline comments, log messages, test names, or commit bodies, describe the *behavior* in self-contained terms. The reader should not need access to the pipeline's working dir to understand the comment.
- If the *why* is non-obvious, link to a stable issue/task ID, not to a pipeline section anchor.
- Before committing, grep the staged diff for `Notes/Tasks`, `§`, `scenario-coverage-gap`, `Stage <N>`, `pipeline-state.json`, `Resolved Q`. Strip every match unless it lives in `Notes/Tasks/<id>/` itself (gitignored, never shipped).
- When briefing a subagent that writes shipped artifacts (tests, docs, code), include this rule in the prompt so the subagent doesn't paste pipeline cross-references into the diff.

## How these three rules relate

Rule 1 is about not deferring problems. Rule 2 is about not deferring decisions to your own pattern-matching. Rule 3 is about not leaking the deferral structure (the pipeline's own scaffolding) into the output that ships. They share a common spine: *the work is not done until what ships is consistent with what was promised*.

If you find yourself writing "I'll just" or "this is fine because", treat that as the trigger to re-read this skill.
