---
name: engineering-discipline
description: "Engineering discipline rules that override the natural temptation to defer, dismiss, or unilaterally decide. Covers: (a) owning every red signal (tests, lint, compile) in the session without declaring it pre-existing; (b) never making unilateral critical decisions (DI dependency, public signature, contract weakening, test assertion relaxation) not covered by the current spec/plan; (c) never referencing pipeline-internal artifacts (Notes/Tasks/..., §7d, scenario-coverage-gap.md) from shipped code, docs, or commit messages; (d) never using try/catch to silence a red signal in tests or production code; (e) never claiming 'verified'/'confirmed' without solid proof and never padding a report with fake blockers; (f) surfacing overblown or analyzer-dodging code instead of burying it after a green-build summary; (g) completing the user's in-progress refactor direction and honoring 'refactor only' scope instead of reverting to the easier shape. Apply continuously during implementation, code review, PR-comment processing, and feature-pipeline runs. Triggers on requests like 'implement this spec', 'apply plan', 'fix tests', 'process PR comments', 'write feature code', 'run feature pipeline', or any session where code is being written, reviewed, or committed."
---

# Engineering Discipline

This skill captures seven discipline rules that surface repeatedly in code reviews and post-mortems. They aren't a checklist run once at the end — they're judgment calls you make continuously while writing or reviewing code.

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
- A workflow that approves its own plan by default does not change this rule. If the auto-approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Else the decision stays a question for the user.
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

## Rule 4 — Never use try/catch to silence a red signal

Never use `try`/`catch` (including a conditional exception filter) to make a red signal disappear — not in tests, not in production code. This includes narrowing or widening an existing catch filter as a "fix"; the correct fix is removing the catch and making the code run cleanly.

If a test needs a mock to behave a certain way so the system under test can run to completion, extend the mock (add the missing behavior to the shared builder/fixture) and assert the real outcome — don't wrap the call in a try/catch that swallows the failure and returns early. When a throw is genuinely the expected outcome, use the test framework's dedicated assertion for it (e.g. a `Throws`/`ThrowsAsync`-style helper) — never a manual try/catch.

Why this is the rule: a swallowed exception makes a test vacuous — it goes green whether or not the code actually works, and an early return inside a catch hides the very regression the test exists to catch. Restricting the catch to "known" exception types doesn't fix this; it just dresses corner-cutting up as rigor, and any later tweak to the filter can silently flip test outcomes in either direction without anyone noticing. This intersects with Rule 1: a run that reports green while a catch is masking a failure is not an owned signal, it's a hidden one.

How to apply:

- If the SUT can't run to the point a test needs, the only fix is extending the mock/fixture — never catching the failure.
- Expected-exception scenarios use the framework's assertion helper, never a manual try/catch.
- Never "tune" (narrow or widen) an existing catch filter as a review fix — delete the catch and make the SUT run cleanly instead.
- Self-audit before claiming a test file done: grep the file for `try`/`catch` — it should come back empty inside every test method body, unless that test is asserting an exception via the framework's own mechanism.
- The same ban applies to production code: never add or broaden a try/catch merely to make a failing path stop failing.
- Generalize: any shortcut that makes a red signal disappear without making the code actually work is this crutch — stop and do it properly, or stop and ask (Rule 2).

## Rule 5 — No "verified"/"confirmed" claims without solid proof; no fake blockers

Never state "verified", "confirmed", or "broken"/"breaks" as fact unless it is backed by solid, representative proof: passing tests with verbatim output (a real `Failed: X, Passed: Y, Total: Z` line), or an actual run of the real system. An isolated repro, static reasoning, or a subagent's tracing narrative is not proof. Label a repro-only or reasoning-only conclusion explicitly as a THEORY, not a verified fact, and defer to the user's own observation of the live system when they report one — it is ground truth, not a repro to re-argue against.

Before asserting a load-bearing mechanism claim — something a decision, fix, or bug report depends on (persistence timing, key semantics, call order, reachability) — read the actual two or three key methods yourself; don't relay a research subagent's summary of a load-bearing point verbatim as established fact. Subagent research is fine for breadth and first-pass location, not for the final claim a decision hinges on.

Symmetrically, never manufacture blockers or open questions to pad a report. Check the authoritative design doc or spec first — many "open questions" are already answered there. Classify every candidate item: if it has a sensible default, state the default, take it, and move on; only surface an item as blocking if work genuinely cannot proceed without the user's answer. If nothing blocks, say so in one line.

Why this is the rule: overclaiming (asserting a fix "verified" or a change "confirmed broken") on evidence that never actually exercised the real system burns trust and can talk the user out of a correct change — the user's own live observation is ground truth, not a repro to re-argue against. Underclaiming — padding a report with pseudo-blockers the design doc already settled — wastes the user's review time and buries the one or two items that actually need a decision. Both failures share the same root: asserting a certainty level the underlying evidence doesn't support, in either direction.

How to apply:

- "Verified"/"confirmed"/"broken"/"breaks" require passing-test verbatim output or a real-system run. Anything less gets labeled THEORY.
- When the user reports a live-system result that contradicts your repro or reasoning, believe them and apply the change — don't re-argue from the repro.
- Before stating a load-bearing mechanism claim to the user, read the actual methods involved yourself.
- Before listing any item as an open question or blocker, check the authoritative spec/design doc for an existing answer.
- Classify each candidate item as "has a sensible default — take it and move on" vs. "genuinely blocks progress"; only the latter goes in the blockers list.
- Answer the question actually asked; don't expand a narrow question into a survey of the surrounding subsystem.

## Rule 6 — Surface overblown or analyzer-dodging code, don't bury it

When you (or a subagent you dispatched) produce code that grew more complex or larger than the task actually needed — long branching if/else ladders, many optional parameters with inline-branched setup, intermediate variables that exist only to thread state, deeply nested conditions, repeated lines that could collapse into a builder chain — surface that fact to the user in the same response that reports the change, before they discover it themselves. Lead with it; don't bury it after a "tests green" summary.

The same applies when a static-analyzer or linter warning fires mid-implementation (e.g. a method-too-long or cyclomatic-complexity rule) and you make a decision about how to resolve it. Evaluate whether extraction is reasonable: does it map onto a natural sub-unit the plan already implies, without deviating from the chosen design shape? If yes, extract, but still report the extraction. If extraction would deviate from the approved design, don't extract just to dodge the warning — suppress it explicitly (with an inline suppression directive and a comment pointing to a follow-up) and report the suppression as a decision the user needs to see.

Why this is the rule: both silent cosmetic choices — accepting an overblown refactor, and quietly extracting a method just to avoid a diagnostic — are design decisions in disguise. A user who only sees "tests green" has no way to know the shape of the code that shipped, or that a decision about it was ever made. This is the same class of problem as Rule 2 (unilateral critical decisions) applied to something that looks purely cosmetic but isn't.

How to apply:

- After every implementation or refactor turn, scan the diff for hot-spots before responding: methods with many optional params plus branching setup, if/else chains several levels deep, long conditional builder chains, repeated boilerplate, intermediate variables that only thread state. In a multi-stage orchestration, delegate this scan to a subagent; in a single-shot session, scan inline.
- If you find one, lead the response with it: what grew overblown, why, and at least one simpler shape — don't append it as a footnote after the green-build report.
- When an analyzer diagnostic fires, cite its rule ID and explicitly decide extract-vs-suppress against the approved design shape, then report that decision to the user in the same turn — never resolve it silently either way.
- This applies equally to your own inline edits and to a subagent's edits; you own the final shape of the diff regardless of who drafted it.

## Rule 7 — Complete the user's stated direction, don't revert to the easier shape

When the user hands off an in-progress refactor (uncommitted or WIP) and asks you to fix errors or make it compile, complete the direction they started — never make it compile by reverting their in-progress change to the prior, easier-to-compile shape (e.g. reintroducing a singleton they were deliberately removing). If a subagent's edit overwrote the user's uncommitted work, recover it from git's index/stash (e.g. `git show :<path>`, `git restore --worktree <path>`) rather than reconstructing or discarding it from memory.

When the user states that the constraint behind an existing workaround no longer holds ("we did X because Y, and Y is no longer true"), treat the workaround as obsolete and lean toward removing it rather than patching around it further — but removal is still a decision, same class as Rule 2: clarify intent and get the user's explicit go-ahead before deleting the construct and its tests/helpers. Don't keep silently patching a workaround whose premise is gone, and don't silently rip it out either.

When a task is scoped as "refactor only" / "no behavior change," apply the strictest reading: zero observable behavior change, even in cases where a spec or plan elsewhere calls for a broadening or uniformization that would touch behavior. This includes preserving pre-existing asymmetries or awkward behavior that looks "wrong" — fixing it belongs to a different, explicitly-scoped task. If a spec's language conflicts with the refactor-only boundary, flag the tension to the user rather than silently picking one side.

Why this is the rule: the easy-compiling path and the "cleaner" broadened design are both plausible-looking outputs that quietly undo what the user actually asked for — reverting their refactor direction, deleting a workaround without consent, or changing behavior under a "refactor only" label. Each looks like progress (green build, tidier code, more uniform design) while actually discarding the user's stated intent.

How to apply:

- Before "fixing" a broken WIP build, read the user's diff to infer their target design; if genuinely ambiguous, treat the choice as a critical decision (Rule 2) and ask rather than picking the easy-compiling alternative.
- Recover overwritten uncommitted edits from git's index/stash before reconstructing them from memory.
- When a stated constraint is gone, propose removing the workaround, but wait for explicit approval before deleting it — removal is a consent checkpoint, not a unilateral move.
- Under a refactor-only scope, cross-session/behavioral scenarios are forbidden to touch; test changes are limited to mechanical swaps (e.g. mock-target changes when a call moved to a new collaborator) with identical assertions and counts; production-code semantic changes get rolled back even if a spec elsewhere prescribes them — surface the conflict instead of resolving it silently.
- Verify every "green" claim on WIP fixes with a real, fresh build/test run — a stale IDE diagnostic or a stale binary (`dev-essentials:dotnet-build-test` Rule 2's false-green trap) can mask exactly the regression this rule is trying to prevent.

## How these rules relate

Rule 1 is about not deferring problems. Rule 2 is about not deferring decisions to your own pattern-matching. Rule 3 is about not leaking the deferral structure (the pipeline's own scaffolding) into the output that ships. Rule 4 is the sharpest form of Rule 1's violation — not just deferring a red signal but actively hiding it. Rule 5 is about not overstating or understating certainty in either direction. Rule 6 is Rule 2 applied to decisions that look cosmetic but aren't. Rule 7 is about not letting the path of least resistance quietly override a direction the user already stated. They share a common spine: *the work is not done until what ships is consistent with what was promised*.

If you find yourself writing "I'll just" or "this is fine because", treat that as the trigger to re-read this skill.
