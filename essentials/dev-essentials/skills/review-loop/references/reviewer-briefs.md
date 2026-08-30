# Reviewer Briefs

Templates for the reviewer subagent dispatched in Phase 3 of `review-loop`. Each section is
one brief keyed by `target=` value. Phase 3 reads this file and pastes the matching brief (with
`<PLACEHOLDERS>` filled in) directly into the reviewer Agent prompt. Use the block verbatim.

---

## Common Rules

Every reviewer report MUST follow these rules. Individual briefs say "apply common rules" rather
than restating them.

**Output format:** use the Full format from `SKILL.md` §"Output formats → Full format" (reproduced
inline in SKILL.md). Do not improvise a near-but-not-quite version.

**Severity scale** — use these exact tokens, no abbreviations:

| Token | When to use |
|---|---|
| `Blocker` | Will not merge / will not ship — data loss, security holes, broken contracts, crashes. |
| `Critical` | Must fix before merge — logic errors with significant impact, missing critical error handling. |
| `High` | Should fix before merge — N+1 patterns, unsound assumptions, weak coverage of critical paths. |
| `Medium` | Quality issue — pattern violations, minor coverage gaps, cleanup opportunities. |
| `Low` | Nice-to-have — minor improvements, refactoring opportunities. |
| `Nit` | Style only — naming, formatting, conventions. |

**Type categories** — one per finding: `Bug`, `Reliability`, `Security`, `Performance`,
`Maintainability`, `Test`, `Style`, `Architecture`, `Spec`, `Docs`. Use `Spec`/`Docs` for
non-code targets.

**Verdict emojis:** ✅ Approve / ✅➕ Approve with suggestions / 🕒 Wait for author / ❌ Reject.

**Verify before confident fixes:** when proposing a concrete fix, verify against a primary source
(official docs, known-working example, repo's own working code, or a throwaway test) per
`dev-essentials:engineering-discipline` Rule 2. Frame unverified theories as theories
("this might be …"), not fixes.

**Ask, don't guess:** if the material is insufficient, file an explicit question-finding (type
`Docs` or `Spec`, severity `Low` unless blocking) rather than guessing.

**Missing tests:** call out missing tests or inadequate coverage explicitly; use type `Test`.

**Skip trivial commentary:** only report findings with actionable signal.

**Reviewer model footer:** end every report with exactly: `Review made by \`<MODEL>\``

---

## `branch` — Full branch diff against base

**Scope:** `git diff origin/<BASE>...HEAD`. Diff provided below.
**Round:** Round `<N>` — use this value; do not infer from conversation.

You are a code reviewer. Find real problems, not a list of everything you noticed.

**Focus areas (priority order):**
1. **Bugs and logic errors** — read the actual changed files in context, not just diff hunks.
   Cross-file consequences are invisible from the diff alone; load files the changed code calls.
2. **Security** — injection, credential exposure, broken auth, unsafe deserialization, CORS bypass.
3. **Data integrity** — broken FK relationships, silent truncation, lost updates, non-atomic ops.
4. **Performance** — N+1 queries, unbounded collection loads, synchronous I/O blocking the pool.
5. **DI lifetime** — scoped service captured in singleton, transient EF context in wrong lifetime.
6. **Contract breaks** — REST API shape changes, interface violations, event schema changes.
7. **Test coverage** — untested critical paths, assertions that don't verify anything meaningful.

**Coherence check (mandatory):** verify changes are coherent across commits. A later commit may
mask a regression introduced earlier — read `git log origin/<BASE>..HEAD` to check the commit sequence.

**Scope hint:** `<SCOPE_HINT>` (treat as focus annotation, not a hard boundary; omit if empty).

Apply common rules.

---

## `pr <id>` — Pull request diff

**PR:** `<PR_ID>` — `<PR_TITLE>`
**Source → target:** `<SOURCE_REF>` → `<TARGET_REF>`
**Round:** Round `<N>`.

You are a code reviewer. Find real problems, not a list of everything you noticed.

The diff below was fetched from PR `<PR_ID>`. The remote-tracking refs
`origin/<TARGET_BRANCH>` and `origin/<SOURCE_BRANCH>` are available locally; **do not rely on
`HEAD`** — it may point to an unrelated local branch that has nothing to do with this PR.

**Focus areas (priority order):**
1. **Bugs and logic errors** — read the actual changed files in context, not just diff hunks.
   Cross-file consequences are invisible from the diff alone; load files the changed code calls.
2. **Security** — injection, credential exposure, broken auth, unsafe deserialization, CORS bypass.
3. **Data integrity** — broken FK relationships, silent truncation, lost updates, non-atomic ops.
4. **Performance** — N+1 queries, unbounded collection loads, synchronous I/O blocking the pool.
5. **DI lifetime** — scoped service captured in singleton, transient EF context in wrong lifetime.
6. **Contract breaks** — REST API shape changes, interface violations, event schema changes.
7. **Test coverage** — untested critical paths, assertions that don't verify anything meaningful.

**Coherence check (mandatory):** verify changes are coherent across commits. A later commit may
mask a regression introduced earlier — run
`git log origin/<TARGET_BRANCH>..origin/<SOURCE_BRANCH>` to check the commit sequence. Do NOT
use `git log <BASE>..HEAD` — `HEAD` is not the PR source branch in this context.

**Scope hint:** `<SCOPE_HINT>` (treat as focus annotation, not a hard boundary; omit if empty).

**Open reviewer threads** (existing threads — active or pending at time of fetch; for context
only):

```
### Open reviewer threads
(Existing questions or issues raised by reviewers — not findings you wrote. They may indicate hot
spots worth looking at more closely, or findings you can independently endorse or refute. Do NOT
re-attribute these as your own findings.)

- [T#<threadId>] <Severity> <Type> on <file>:<firstLine> — <one-line summary> — status <Active|Pending>
- ...
```

If there are no active/pending threads, omit this section entirely.

**When `--include-resolved` is set**, append the following section **after** the open-thread
section above (or after the scope hint, if there are no open threads).
Populate it from the resolved/closed threads fetched in Phase 1:

```
### Previously addressed in this PR
(For context only — do not re-raise these unless the surrounding code regressed.)

- [T#<threadId>] <Severity> <Type> on <file>:<firstLine> — <one-line summary> — resolved as <statusLabel>
- ...
```

If there are no resolved/closed threads, omit this section entirely.

Apply common rules.

---

## `commits <N>` / `last-N` — Last N commits only

**Scope:** `git diff HEAD~<N>..HEAD`. Diff provided below.
**Round:** Round `<N_ROUND>` — use this value.

You are a code reviewer. Scope is narrower than a full branch review — only the last `<N>`
commits.

**Focus areas:** same list as the `branch` brief (bugs, security, data integrity, performance, DI
lifetime, contract breaks, test coverage), applied to the narrowed diff only.

**Coherence check:** verify the `<N>` commits are internally consistent — a commit midway through
the set should not leave the code in a state that a later commit silently patches.

Apply common rules.

---

## `diff <range>` — Arbitrary git diff range

**Scope:** `git diff <RANGE>`. Diff provided below.
**Round:** Round `<N>` — use this value.

You are a code reviewer. Apply the `branch` brief focus list (bugs, security, data integrity,
performance, DI lifetime, contract breaks, test coverage) to the provided diff range.

No implicit coherence check beyond the supplied range. If `<RANGE>` is a subset of a larger
branch, you are not expected to check commits outside it.

---

## `file <path>` — Full file review (not a diff)

**Scope:** full contents of `<PATH>`. File contents provided below.
**Round:** Round `<N>` — use this value.

You are doing a **complete-file review**, not a diff review. There is no "before" state — evaluate
the file as it exists now. Issues that were always present (not introduced recently) are valid
findings here.

**Focus areas:**
1. **Correctness** — logic, algorithms, and data flows correct end-to-end.
2. **Security** — any unsafe surface in the full file.
3. **Missing error handling** — unhandled exceptions, unchecked returns, partial-failure paths
   that leave state corrupted.
4. **Test coverage** — if this is a source file, are its public/internal contracts covered?
5. **Architecture** — layer violations, circular dependencies, misplaced responsibilities.
6. **Docs** — misleading or absent XML docs, comments that contradict the code.

Apply common rules.

---

## `class <FQN>` — Named class review

**Class:** `<FQN>` (`<FILE>` lines `<START>`–`<END>`)
**Callers:** `<CALLER_FILES>`
**Tests:** `<TEST_FILES>`
**Round:** Round `<N>` — use this value.

Phase 1 already resolved the FQN to file + line range; ambiguity was resolved before dispatch. Phase 3
populates `<CALLER_FILES>` by running `grep -rn '<SimpleName>'` (or language-equivalent)
and listing the matching files; populates `<TEST_FILES>` by grepping the test project root for the same
name. If either yields zero results, substitute "none found".

**Focus areas:**
1. **The class** — bugs, missing null checks, incorrect logic, state mutation hazards.
2. **Caller surface** — do callers consume the API correctly? Is the API contract clear enough
   to prevent misuse?
3. **Test coverage** — constructor variations, error paths, and edge cases covered?
4. **DI lifetime** — correct lifetime relative to the class's dependencies.
5. **Architecture** — does this class belong in this layer?

Under proposed changes: report what's wrong at the symbol AND identify caller/test surface that
breaks under a fix to the reported issue.

Apply common rules.

---

## `method <FQN>` — Named method review

**Method:** `<FQN>` (`<FILE>` lines `<START>`–`<END>`)
**Callers:** `<CALLER_FILES>`
**Tests:** `<TEST_FILES>`
**Round:** Round `<N>` — use this value.

Phase 1 already resolved the FQN to file + line range; ambiguity was resolved before dispatch. Phase 3
populates `<CALLER_FILES>` by running `grep -rn '<SimpleName>'` (or language-equivalent)
and listing the matching files; populates `<TEST_FILES>` by grepping the test project root for the same
name. If either yields zero results, substitute "none found".

**Focus areas:**
1. **Method body** — correctness, edge cases, off-by-one errors, error handling gaps.
2. **Pre/postconditions** — inputs validated? Return value contract matches the method's documented contract? Exceptions declared in the contract and no undeclared throws?
3. **Caller correctness** — correct arguments passed? All return values and exceptions handled?
4. **Test coverage** — boundary conditions, error paths, and happy path all tested?
5. **Performance** — cost justified given measured or expected call frequency?

Under proposed changes: report the issue at the method AND any caller or test that breaks under a
fix.

Apply common rules.

---

## `spec <path>` — Specification / design document review

**Scope:** full contents of `<PATH>`. File contents provided below.
**Round:** Round `<N>` — use this value.

You are reviewing a **specification or design document**, not code. Read it as a skeptical
implementer who must build exactly what is written — nothing more, nothing less. Your job is to
find gaps, ambiguities, and contradictions before any implementation is written.

**Focus areas (priority order):**
1. **Ambiguity** — any statement an implementer could reasonably read two or more ways. Flag every
   instance; even "reasonable" ambiguity causes divergent implementations. Type `Spec`.
2. **Undefined behavior** — what happens when inputs are malformed, external deps fail, or
   concurrent operations race? If the spec is silent, flag it. Type `Spec`.
3. **Missing error paths** — does the spec describe every observable error response, status code,
   log line, and event emission? Type `Spec`.
4. **Contradictions** — two sections that mandate incompatible behavior. Include section refs.
   Type `Spec`.
5. **Coverage gaps** — requirements implied but never stated, or stated in one place and omitted
   from the summary/contract table. Type `Spec`.
6. **Deferred decisions** — language matching "we'll figure it out later": "TBD", "to be decided",
   "implementation detail", "as appropriate", "depending on context". Flag with exact location.
   Type `Spec`.
7. **Docs quality** — missing sections, broken references, wrong examples. Type `Docs`.

**Not in scope:** code quality; checking whether an implementation matches this spec; rating
whether this is the right design choice.

**Severity for spec targets:** Same token names as the common-rules severity scale; the
definitions below apply only to `spec` targets. `Blocker` = will not merge / will not ship —
contradiction or undefined behavior making correct implementation impossible. `Critical` =
ambiguity that will definitely produce divergent implementations. `High` = missing error path or
coverage gap affecting observable behavior. `Medium` = deferred decision needing resolution
before implementation. `Low` = minor wording with low divergence risk. `Nit` = grammar,
formatting, style.

Apply common rules. The "missing tests" rule does not apply here — use "missing error paths"
(focus area 3) instead.

---

## Customization points

### `--reviewer-focus <areas>`

When the user passes `--reviewer-focus`, replace the default focus list in the dispatched brief
with the user-supplied comma-separated tokens. Available tokens:

| Token | Meaning |
|---|---|
| `bugs` | Logic errors, incorrect mappings, wrong conditions, missing null checks. |
| `security` | Injection, credential exposure, broken auth, unsafe deserialization. |
| `data-integrity` | FK breaks, silent truncation, lost updates, non-atomic operations. |
| `performance` | N+1 queries, unbounded collections, synchronous I/O. |
| `di-lifetime` | Scoped/singleton mismatches, captive dependencies. |
| `contracts` | REST API shape changes, interface violations, event schema changes. |
| `test-coverage` | Untested paths, weak assertions, missing edge-case tests. |
| `architecture` | Layer violations, circular deps, misplaced responsibilities. |
| `docs` | Misleading XML docs, comments that contradict code, missing docs. |

If every token in the list is unrecognized (none matches the table above), fall back to the
default focus list and print a warning to the user in chat at the start of Phase 3, before
dispatching the reviewer. If only some tokens are unrecognized, use the recognized tokens only
and print a warning naming the unrecognized ones.

### `--audit-team-args <...>`

When `--reviewer audit-team`, append `<...>` verbatim to the `/audit-team` invocation, after the
`<path>` positional Phase 2 supplies. When `--reviewer` is not `audit-team`, this arg is ignored
(Phase 2 prints a warning). `audit-team` itself is valid only on documentation-path targets — see
SKILL.md Phase 2 for the full adapter: target restriction, positional/argument mapping (where a
user-supplied `[agent-count]` or `[model]` always wins), and the 3-bucket → 6-severity output
mapping.
