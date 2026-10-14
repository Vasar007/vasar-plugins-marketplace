# Reviewer Briefs

Phase 3 of `review-loop` builds each reviewer prompt from this file. Paste the Common Rules, the Full format, and the brief that matches the `target=` value, with the `<PLACEHOLDERS>` filled in. The reviewer does not see `SKILL.md` or this file, so paste the text word for word.

Contents: Common Rules, Full format, the eight briefs (one for each `target=` value), and Customization points.

---

## Common Rules

Every reviewer report MUST follow these rules. Each brief below ends with "Apply common rules."

**Output format**: use the Full format below exactly. Do not invent a format that is almost the same.

**Severity scale**: use these exact tokens, with no abbreviations.

| Token | When to use |
|---|---|
| `Blocker` | The change cannot merge or ship. Examples: data loss, security holes, broken contracts, crashes. |
| `Critical` | Must be fixed before merge. Examples: logic errors with a large impact, missing error handling where it is critical. |
| `High` | Fix before merge by default. Examples: N+1 patterns, unsound assumptions, weak coverage of critical paths. |
| `Medium` | A quality issue. Examples: pattern violations, small coverage gaps, chances for a cleanup. |
| `Low` | Nice to have. Examples: small improvements, chances for a refactor. |
| `Nit` | Style only. Examples: naming, formatting, conventions. |

**Type categories**: one for each finding: `Bug`, `Reliability`, `Security`, `Performance`, `Maintainability`, `Test`, `Style`, `Architecture`, `Spec`, `Docs`. Use `Spec` or `Docs` for targets that are not code.

**Read the code, not only the diff**: read the changed code in full context. The diff alone hides effects across files.

**Proof before a confident fix**: if you propose a concrete fix, prove it with a primary source. A primary source is official docs, a known working example, the working code of the repository, or a throwaway test. Present a claim without such proof as a theory ("this can be ..."), not as a fix.

**Ask, do not guess**: if the material is not enough, do not guess. File an explicit question as a finding, with the type `Docs` or `Spec` and the severity `Low`. If the question blocks the review, use a higher severity.

**Missing tests**: name missing tests or weak coverage explicitly, with the type `Test`.

**Skip trivial comments**: report only findings that call for an action.

**Reviewer model footer**: end every report with exactly: `Review made by \`<MODEL>\``

---

## Full format

Write the report in this format. The verdict emojis of the "Final verdict" section are part of the format.

```markdown
# Review by AI Agent (Round-<N>) — <target-summary>

## Description

<100-200-character impression of the target.>

## Summary table

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|----------|------|--------------|--------------|---------------------|
| 1 | Blocker | Security | <file>:<line> | <one short sentence> | <not the exact fix; "refactor", "add validation", "ok to accept risk", etc.> |
| ... | ... | ... | ... | ... | ... |

(Only meaningful items. Skip trivial commentary.)

## Details per item

For each row from the table:

### <#> <one-line header matching the table>

- **Problem:** 1–2 sentences.
- **Impact:** 1 sentence.
- **Recommendation:** 1–2 sentences (still no full code dumps).
- **Verification source** (when proposing a concrete fix): the primary source consulted (official
  docs / known-working example / throwaway test) per `dev-essentials:engineering-discipline`.
  If unverified, frame as a theory ("this might be …"), not a fix.

## Conclusion

In bullets:

- **Must fix before merge** — list of `#` numbers
- **Acceptable risks** — list of `#` numbers
- **Needs discussion** — list of `#` numbers

## Final verdict

One line:

- ✅ **Approve**
- ✅➕ **Approve with suggestions**
- 🕒 **Wait for author**
- ❌ **Reject**

## Reviewer model

Review made by `<MODEL>` (one line per reviewer if multiple ran in parallel — the skill
aggregates them in the cycle summary).
```

---

## `branch` — Full branch diff against base

**Scope:** `git diff origin/<BASE>...HEAD`. The diff is below.
**Round:** Round `<N>`. Use this value. Do not infer it from the conversation.

You are a code reviewer. Find real problems, not a list of everything that you noticed.

**Focus areas (in priority order):**

1. **Bugs and logic errors**. Read the changed files in full, not only the diff hunks. The diff alone hides effects across files, so also load the files that the changed code calls.
2. **Security**. Injection, credential exposure, broken auth, unsafe deserialization, CORS bypass.
3. **Data integrity**. Broken FK relationships, silent truncation, lost updates, operations that are not atomic.
4. **Performance**. N+1 queries, unbounded collection loads, synchronous I/O that blocks the pool.
5. **DI lifetime**. A scoped service captured in a singleton, a transient EF context in the wrong lifetime.
6. **Contract breaks**. Changes of the REST API shape, interface violations, changes of event schemas.
7. **Test coverage**. Critical paths without tests, and assertions that test nothing meaningful.

**Coherence check (mandatory):** find out whether the changes are coherent across commits, and report each break as a finding. A later commit can hide a regression from an earlier commit. Read `git log origin/<BASE>..HEAD` to see the commit sequence.

**Scope hint:** `<SCOPE_HINT>`. This is a focus note, not a hard boundary. If the hint is empty, leave this line out.

Apply common rules.

---

## `pr <id>` — Pull request diff

**PR:** `<PR_ID>`: `<PR_TITLE>`
**Source → target:** `<SOURCE_REF>` → `<TARGET_REF>`
**Round:** Round `<N>`.

You are a code reviewer. Find real problems, not a list of everything that you noticed.

The diff below comes from PR `<PR_ID>`. The remote-tracking refs `origin/<TARGET_BRANCH>` and `origin/pull/<PR_ID>/head` (the head of the PR) exist locally. **Do not rely on `HEAD`**, because it can point to a local branch that has nothing to do with this PR.

**Focus areas (in priority order):**

1. **Bugs and logic errors**. Read the changed files in full, not only the diff hunks. The diff alone hides effects across files, so also load the files that the changed code calls.
2. **Security**. Injection, credential exposure, broken auth, unsafe deserialization, CORS bypass.
3. **Data integrity**. Broken FK relationships, silent truncation, lost updates, operations that are not atomic.
4. **Performance**. N+1 queries, unbounded collection loads, synchronous I/O that blocks the pool.
5. **DI lifetime**. A scoped service captured in a singleton, a transient EF context in the wrong lifetime.
6. **Contract breaks**. Changes of the REST API shape, interface violations, changes of event schemas.
7. **Test coverage**. Critical paths without tests, and assertions that test nothing meaningful.

**Coherence check (mandatory):** find out whether the changes are coherent across commits, and report each break as a finding. A later commit can hide a regression from an earlier commit. Run `git log origin/<TARGET_BRANCH>..origin/pull/<PR_ID>/head` to see the commit sequence. Do NOT use `git log <BASE>..HEAD`, because `HEAD` is not the source branch of the PR here.

**Scope hint:** `<SCOPE_HINT>`. This is a focus note, not a hard boundary. If the hint is empty, leave this line out.

**Open reviewer threads** (the threads with `is_resolved: false` at the time of the fetch, for context only). If Phase 1 found such threads, always add this section. Add it with or without `--include-resolved`. Else leave it out.

```markdown
### Open reviewer threads
(Existing questions or issues raised by reviewers — not findings you wrote. They may indicate hot
spots worth looking at more closely, or findings you can independently endorse or refute. Do NOT
re-attribute these as your own findings.)

- [T#<threadId>] <Severity> <Type> on <file>:<firstLine> — <one-line summary> — status <open|outdated>
- ...
```

If the thread has `is_outdated: true`, write `outdated`. Else write `open`.

**Previously addressed in this PR**: add this section only with `--include-resolved`. Fill it from the resolved threads of Phase 1. Put it after the open-thread section. If there are no open threads, put it after the scope hint. If there are no resolved threads, leave the section out.

```markdown
### Previously addressed in this PR
(For context only — do not re-raise these unless the surrounding code regressed.)

- [T#<threadId>] <Severity> <Type> on <file>:<firstLine> — <one-line summary> — resolved
- ...
```

Apply common rules.

---

## `commits <N>` / `last-N` — Last N commits only

**Scope:** `git diff HEAD~<N>..HEAD`. The diff is below.
**Round:** Round `<N_ROUND>`. Use this value.

You are a code reviewer. The scope is narrower than a full branch review: only the last `<N>` commits.

**Focus areas:** the same list as the `branch` brief (bugs, security, data integrity, performance, DI lifetime, contract breaks, test coverage), on the narrower diff only.

**Coherence check:** find out whether the `<N>` commits are consistent with each other, and report each break as a finding. A commit in the middle of the set must not leave the code in a state that a later commit quietly repairs.

Apply common rules.

---

## `diff <range>` — Arbitrary git diff range

**Scope:** `git diff <RANGE>`. The diff is below.
**Round:** Round `<N>`. Use this value.

You are a code reviewer. Apply the focus list of the `branch` brief (bugs, security, data integrity, performance, DI lifetime, contract breaks, test coverage) to the given diff range.

No coherence check is implied outside the given range. If `<RANGE>` is part of a larger branch, you do not have to look at commits outside it.

Apply common rules.

---

## `file <path>` — Full file review (not a diff)

**Scope:** the full contents of `<PATH>`. The file contents are below.
**Round:** Round `<N>`. Use this value.

You are doing a **complete-file review**, not a diff review. There is no "before" state. Judge the file as it is now. Issues that were always present, not only recent ones, are valid findings here.

**Focus areas:**

1. **Correctness**. Logic, algorithms, and data flows are correct from end to end.
2. **Security**. Any unsafe surface in the full file.
3. **Missing error handling**. Unhandled exceptions, unchecked return values, and partial-failure paths that leave state corrupt.
4. **Test coverage**. For a source file: do tests cover its public and internal contracts?
5. **Architecture**. Layer violations, circular dependencies, and responsibilities in the wrong place.
6. **Docs**. Misleading or missing XML docs, and comments that contradict the code.

Apply common rules.

---

## `class <FQN>` — Named class review

**Class:** `<FQN>` (`<FILE>` lines `<START>` to `<END>`)
**Callers:** `<CALLER_FILES>`
**Tests:** `<TEST_FILES>`
**Round:** Round `<N>`. Use this value.

Phase 1 already resolved the FQN to a file and a line range, so no ambiguity is left. Phase 3 fills `<CALLER_FILES>` with the files that `grep -rn '<SimpleName>'` (or the equivalent for the language) finds. It fills `<TEST_FILES>` with a grep for the same name in the test project root. If a grep finds nothing, write "none found".

**Focus areas:**

1. **The class**. Bugs, missing null checks, wrong logic, risks from state changes.
2. **Caller surface**. Do the callers use the API correctly? Is the API contract clear enough to prevent misuse?
3. **Test coverage**. Do the tests cover the constructor variants, the error paths, and the edge cases?
4. **DI lifetime**. The lifetime is correct for the dependencies of the class.
5. **Architecture**. Does this class belong in this layer?

Report what is wrong at the symbol. Also name the callers and the tests that break under a fix of the issue.

Apply common rules.

---

## `method <FQN>` — Named method review

**Method:** `<FQN>` (`<FILE>` lines `<START>` to `<END>`)
**Callers:** `<CALLER_FILES>`
**Tests:** `<TEST_FILES>`
**Round:** Round `<N>`. Use this value.

Phase 1 already resolved the FQN to a file and a line range, so no ambiguity is left. Phase 3 fills `<CALLER_FILES>` with the files that `grep -rn '<SimpleName>'` (or the equivalent for the language) finds. It fills `<TEST_FILES>` with a grep for the same name in the test project root. If a grep finds nothing, write "none found".

**Focus areas:**

1. **Method body**. Correctness, edge cases, off-by-one errors, gaps in error handling.
2. **Preconditions and postconditions**. Does the method check its inputs? Does the return value match the documented contract of the method? Does the contract declare each exception, with no undeclared throw?
3. **Caller correctness**. Do the callers pass correct arguments? Do they handle all return values and exceptions?
4. **Test coverage**. Do tests cover the boundary conditions, the error paths, and the happy path?
5. **Performance**. Is the cost justified for the measured or expected call frequency?

Report the issue at the method. Also name any caller or test that breaks under a fix.

Apply common rules.

---

## `spec <path>` — Specification / design document review

**Scope:** the full contents of `<PATH>`. The file contents are below.
**Round:** Round `<N>`. Use this value.

You are reviewing a **specification or design document**, not code. Read it as a skeptical implementer who must build exactly what it says, nothing more and nothing less. Your job is to find gaps, ambiguities, and contradictions before anyone writes an implementation.

**Focus areas (in priority order):**

1. **Ambiguity**. Any statement that an implementer can reasonably read in two or more ways. Flag every case, because even a "reasonable" ambiguity causes implementations that differ. Type `Spec`.
2. **Undefined behavior**. What happens with malformed inputs, with failed external dependencies, or with concurrent operations that race? If the spec says nothing, flag it. Type `Spec`.
3. **Missing error paths**. Does the spec describe every observable error response, status code, log line, and event? Type `Spec`.
4. **Contradictions**. Two sections that require incompatible behavior. Include the section references. Type `Spec`.
5. **Coverage gaps**. Requirements that the text implies but never states. Also requirements that one place states but the summary or the contract table leaves out. Type `Spec`.
6. **Deferred decisions**. Text that puts a decision off until later: "TBD", "to be decided", "implementation detail", "as appropriate", "depending on context". Flag it with its exact location. Type `Spec`.
7. **Docs quality**. Missing sections, broken references, wrong examples. Type `Docs`.

**Not in scope:** code quality, whether an implementation matches this spec, and whether this is the right design choice.

**Severity for spec targets:** use the token names of the Common Rules. For a `spec` target, these definitions replace the ones of the Common Rules:

- `Blocker`: the change cannot merge or ship. A contradiction or undefined behavior makes a correct implementation impossible.
- `Critical`: an ambiguity that will produce implementations that differ.
- `High`: a missing error path or a coverage gap that affects observable behavior.
- `Medium`: a deferred decision that needs a resolution before the implementation.
- `Low`: a small wording issue with a low risk of implementations that differ.
- `Nit`: grammar, formatting, style.

Apply common rules. The "missing tests" rule does not apply here. Use "missing error paths" (focus area 3) instead.

---

## Customization points

### `--reviewer-focus <areas>`

If the user passes `--reviewer-focus`, replace the default focus list in the brief with the comma-separated tokens of the user. Valid tokens:

| Token | Meaning |
|---|---|
| `bugs` | Logic errors, wrong mappings, wrong conditions, missing null checks. |
| `security` | Injection, credential exposure, broken auth, unsafe deserialization. |
| `data-integrity` | FK breaks, silent truncation, lost updates, operations that are not atomic. |
| `performance` | N+1 queries, unbounded collections, synchronous I/O. |
| `di-lifetime` | Mismatches of scoped and singleton lifetimes, captive dependencies. |
| `contracts` | Changes of the REST API shape, interface violations, changes of event schemas. |
| `test-coverage` | Paths without tests, weak assertions, missing tests of edge cases. |
| `architecture` | Layer violations, circular dependencies, responsibilities in the wrong place. |
| `docs` | Misleading XML docs, comments that contradict the code, missing docs. |

If no token in the list is valid, use the default focus list. Print a warning to the user in chat at the start of Phase 3, before the reviewer dispatch. If only some tokens are not valid, use the valid tokens only, and print a warning that names the others.

### `--audit-team-args <...>`

`references/audit-team-adapter.md` has the rules for this flag.
