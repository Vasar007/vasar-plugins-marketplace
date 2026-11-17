# Verify-then-Fix Discipline

**Read this file before you apply any fix**. This is the playbook of the fixer of Phase 5: the orchestrator, or the fixer subagent that Phase 5, step 5b chooses.

## Contents

- 1. Why verify-then-fix exists
- 2. APPLY / PARTIAL / REJECT classification
- 3. What counts as a primary source
- 4. Common rejection patterns
- 5. Don't-over-fix rule
- 6. Scope: only files the reviewer named
- 7. Build / test verification mandate
- 8. Per-finding report format
- 9. When the fixer disagrees with a confident reviewer
- Hard rules (no exceptions)

---

## 1. Why verify-then-fix exists

Fixes by pattern matching put regressions into shipping code. A reviewer names a problem, and the fixer sees a familiar shape and applies what "looks right". Then the build breaks in a way that the reviewer never meant. So treat each finding as a hypothesis, and each proposed fix as a claim about reality. Each claim needs a primary source before it ships. `dev-essentials:engineering-discipline` Rule 5 has the general form of this rule.

---

## 2. APPLY / PARTIAL / REJECT classification

Classify every finding of the triage before you touch any file.

**APPLY**: a primary source (see section 3) proves the finding, and the proposed fix is bounded (no refactor around it, no file outside the triage). Apply the fix as described. Example: the reviewer flags a missing null check. The fixer reads the callers, finds a code path with no guard, and adds the check.

**PARTIAL**: a primary source proves the finding, but the proposed fix goes too far, or only a part of the fix has a primary source. An example of too far: the reviewer suggests a refactor of the module, but only the target line needs a change. Apply the bounded, proven part. Write down what you left out, and why. Example: the reviewer recommends a new helper class together with the fix of a logic bug. Fix the logic bug, and put the helper class in the deferred list of Phase 9.

**REJECT**: no primary source proves the finding. Or the finding contradicts the source, a memory note, or an existing convention. Or it conflicts with the fix of another finding. Do not apply it. Report the reason for the rejection explicitly. Example: the reviewer says that a field is missing from a manifest. The fixer does not find that field in the official schema. So it rejects the finding, and does not add a field that perhaps does not exist.

Each verdict needs one sentence of reasoning. Write it into the field "Verification source" of the finding in the full report of the cycle, in the format of section 8.

---

## 3. What counts as a primary source

Before you apply a fix, or a part of a fix, cite one of these sources:

- **(a) Official docs** of the library, framework, or tool: schema pages, API references, changelog entries.
- **(b) A known working example** in this repository or a sibling repository: a file that already does the thing and passes CI.
- **(c) A throwaway test**: a change on a scratch branch or in a copy of the cache that shows the behavior before you touch the source.
- **(d) The CLAUDE.md of the repository**, for a finding about a convention or a versioning rule of the repository.
- **(e) The skill, spec, or artifact under review**, for a finding about the stated rules of that artifact.

These do not count:

- Pattern matching from training data ("this is typically how X is done").
- An analogy of structure with no reading of the source ("this looks like Y, so the fix is Z").
- A claim about a category of Claude Code primitives, such as agents, skills, or frontmatter keys. Without a reading of the real schema or of a known working plugin, it does not count.

---

## 4. Common rejection patterns

These patterns came up in past review cycles. REJECT each one unless you proved it explicitly:

- **The reviewer flags a missing manifest field**. Find out whether the field exists in the official schema. Grep a known working plugin (for example `feature-dev` or `pr-review-toolkit`), or read the docs. Do not add a field because it "sounds right".
- **The reviewer flags "skill not listed in plugin.json"**. Find out how the plugin finds its skills: an explicit list, or auto-discovery from a default folder (`./skills/`). With auto-discovery, the field is absent on purpose, and an added field is wrong.
- **The reviewer flags a method or property name as wrong**. Read the source file, or run `grep`. Do not rename by the name that a convention seems to ask for.
- **The reviewer flags a cross-reference as broken**. Before you act, find out whether the file exists at the cited path. A path that looks wrong can be correct, and a path that looks right can be missing.
- **The reviewer recommends a "small refactor" next to a real fix**. Apply the bounded fix. Put the rejected refactor in the deferred list of the cycle. The code around the fix is out of scope.

---

## 5. Don't-over-fix rule

The fixer does not refactor code around the fix, normalize unrelated style, or improve anything outside the scope of the finding. The files and lines that the reviewer cited in the triage set the scope. If you notice an unrelated issue during a targeted change, log it in the deferred list of Phase 9 and move on. An addition to this commit breaks the scope. This holds for a correct fix too.

The reason: an over-fix adds diff noise that hides the targeted change. It adds new review surface for the re-review pass, and it makes the commit history harder to bisect later.

---

## 6. Scope: only files the reviewer named

The fixer touches only the files that the triage cites. After the fixes, stage with `git add <specific-files-touched>`. Never use `git add -A` or `git add .`. Unrelated staged files silently widen the commit, and they can ship work-in-progress changes by accident.

**An exception for supporting files that the fix structurally needs**. Sometimes a proven finding cannot land without a change to a directly related file that the triage does not cite. Then the fixer can also touch that file. The fix must need the file in its structure. Convenience is not enough. Examples: for "missing test coverage for the new code path", the fixer can add or change the matching `*Tests.cs` or test file. For "missing configuration option", it can also touch the file that registers the configuration. The exception is narrow: only a file without which the fix is incomplete in its architecture. Unrelated style changes, refactors, and edits for convenience do not qualify. Log the extra file in the cycle report, on the verification source line of the finding.

---

## 7. Build / test verification mandate

After all fixes of the cycle, the fixer (Phase 5) reports its edits to the calling skill. Then Phase 6, a separate step of the calling skill, runs the build and the tests. The fixer must report failures honestly. Phase 6 can find a regression in code that the fixer touched. Then the fixer comes back to investigate and fix it again, before the cycle reports complete. See `dev-essentials:engineering-discipline` Rule 1: own every red signal in your session.

The fixer never reports "ready for build verification" on a state that it knows is broken. "I believe that the fix is correct" does not replace an honest Phase 6 result.

---

## 8. Per-finding report format

For each finding, add one line to the full report of the cycle. This line is the content of the field "Verification source" in the section "Details per item" of the Full format:

```text
F<n> [APPLY|PARTIAL|REJECT] — <one-sentence reasoning citing primary source>
```

Examples:

```text
F1 [APPLY] — Null-check gap confirmed by reading GetSession callers at SessionManager.cs:142; fix is bounded to that method.
F2 [PARTIAL] — Logic bug verified; helper-extraction refactor is out of scope for this triage; extraction deferred.
F3 [REJECT] — Field `skills` not found in any installed plugin's plugin.json schema; cannot verify this field exists.
```

---

## 9. When the fixer disagrees with a confident reviewer

Sometimes the fixer classifies a finding as REJECT, but the reviewer stated it with high confidence. Then the report of the fixer includes this line:

```text
REJECTED with reason: <one sentence>; reviewer's claim does not verify against <primary source consulted>.
```

The user reads the full report and decides whether to override the verdict. The fixer does not apply a fix without proof only because the reviewer was confident. Confidence is not proof.

---

## Hard rules (no exceptions)

1. Classify every finding before you touch any file. Skip nothing in silence.
2. Touch only the files that the reviewer cited, plus a supporting file that the fix structurally needs (the exception of section 6). Never use `git add -A`.
3. Never claim that the build or the tests pass without a real run. Phase 6 of the calling skill runs them. Report every result honestly.
4. Defer unrelated issues to Phase 9. Do not fix what is not on the triage list.
5. Document every REJECT and PARTIAL with one sentence of reasoning.
