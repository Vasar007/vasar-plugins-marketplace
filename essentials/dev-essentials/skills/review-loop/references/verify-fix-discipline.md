# Verify-then-Fix Discipline

**Read this file before applying any fix.** This is the playbook for the verify-then-fix subagent dispatched in Phase 5.

---

## 1. Why verify-then-fix exists

Pattern-match fixes are how regressions land in shipping code. A reviewer names a problem; the fixer sees a familiar shape; the fixer applies what "looks right" from training data; the build breaks in a way the reviewer never intended. Each finding is a hypothesis. Each proposed fix is a claim about reality. Each claim needs a primary source before it ships. The verify-then-fix discipline holds the gap between "plausible theory" and "verified fact" open long enough to check it — which is the entire value of this skill over a naive fix loop.

The concrete failure mode this prevents: two confidently-stated wrong fixes shipped back-to-back while debugging a Claude Code plugin manifest error, each based on a plausible theory that hadn't been checked. Both required rollbacks. The actual fix was found in under a minute by grepping a known-working example. See `dev-essentials:engineering-discipline` for the engineering-level framing of this rule.

---

## 2. APPLY / PARTIAL / REJECT classification

For every finding in the triage, classify before touching any file.

**APPLY** — the finding is verified against a primary source (see §3) AND the proposed fix is bounded (no surrounding refactor, no untriaged files). Apply the fix as described. Example: reviewer flags a missing null-check; fixer reads the callers, confirms an unguarded code path exists, applies the check.

**PARTIAL** — the finding is verified but the proposed fix oversteps (e.g., reviewer suggested a module-level refactor; only the targeted line needs changing), OR only part of the fix verifies against a primary source. Apply the bounded, verified subset. Document what was dropped and why. Example: reviewer recommends extracting a helper class alongside fixing a logic bug — fix the logic bug; defer the extraction to Phase 9's deferred list.

**REJECT** — the finding cannot be verified against a primary source, OR it contradicts the source memory or existing convention, OR it conflicts with another finding's fix. Do not apply it. Report the rejection reason explicitly. Example: reviewer flags a field as missing from a manifest — fixer cannot find that field in the official schema, so rejects rather than adds a field that may not exist.

Each classification requires one sentence of reasoning. Record it verbatim in the cycle's full report under the finding's "Verification source" field, using this format:

```
F<n> [APPLY|PARTIAL|REJECT] — <one-sentence reasoning citing primary source>
```

---

## 3. What counts as a primary source

The fixer must cite one of the following before applying or partially applying a fix:

- **(a) Official docs** of the library, framework, or tool in question — schema pages, API references, changelog entries.
- **(b) A known-working example** in this repo or a sibling repo — a file that already does the thing and passes CI.
- **(c) A throwaway test** — a scratch-branch or cache-copy change that confirms the behavior before touching source.
- **(d) The repo's CLAUDE.md** when the finding is about a repo convention or versioning rule.
- **(e) The skill, spec, or artifact under review** when the finding is about that artifact's own stated rules.

What does NOT count:

- Pattern-matching from training data ("this is typically how X is done").
- Structural analogy without reading the source ("this looks like Y, so the fix should be Z").
- Asserting a category claim about Claude Code primitives (agents, skills, frontmatter keys) without reading the actual schema or a known-working plugin.

---

## 4. Common rejection patterns

These patterns have appeared in past review cycles. Each one should be REJECTED unless the fixer has done explicit verification:

- **Reviewer flags a missing manifest field.** Verify the field exists in the official schema by grepping a known-working plugin (e.g., `feature-dev`, `pr-review-toolkit`) or reading the docs. Do not add a field because it "sounds right". The concrete incident: two wrong fields were added to `plugin.json` before the correct fix (deleting the `agents` field entirely) was found by grepping a known-working plugin.
- **Reviewer flags "skill not listed in plugin.json".** Verify whether the plugin uses explicit listing or auto-discovery from a default directory (`./skills/`). Auto-discovery means the field is intentionally absent — adding it is wrong.
- **Reviewer flags a method or property name as incorrect.** Verify via `grep` or by reading the source file. Do not rename based on what the correct name "should be" by convention.
- **Reviewer flags a cross-reference as broken.** Verify the file actually exists at the cited path before acting. A path that looks wrong may be correct; a path that looks right may not exist.
- **Reviewer recommends a "small refactor" alongside a real fix.** Apply the bounded fix. Document the rejected refactor in the cycle's deferred list. The surrounding code is not within scope.

---

## 5. Don't-over-fix rule

The fixer does NOT incidentally refactor surrounding code, normalize unrelated style, or improve anything outside the finding's scope. Scope is defined by the files and lines the reviewer cited in the triage. If the fixer notices an unrelated issue while making a targeted change — log it in Phase 9's deferred list and move on. Adding it to this commit is a scope violation even if the fix is correct.

Why this matters: over-fixes create diff noise that obscures the targeted change, introduce new review surface in the re-review pass, and make the commit history harder to bisect later.

---

## 6. Scope: only files the reviewer named

The fixer touches only the files cited in the triage. After applying fixes, stage with `git add <specific-files-touched>` — never `git add -A` or `git add .`. Staging unrelated files silently expands the commit scope and can accidentally ship work-in-progress changes.

**Carve-out for structurally required supporting files.** When the verified finding cannot be landed without modifying a directly related file not explicitly cited, the fixer MAY also touch that file — provided it is structurally required (not merely convenient). Qualifying examples: a finding of "missing test coverage for the new code path" allows adding or modifying the matching `*Tests.cs` / test file; a finding of "missing config knob" allows also touching the config registration file. The carve-out is narrow: only files without which the fix is architecturally incomplete. Unrelated style improvements, refactors, or convenience edits do NOT qualify. Log the extra file in the cycle report under the finding's verification source line.

---

## 7. Build / test verification mandate

After applying all fixes for the cycle, the fixer (Phase 5) reports its edits to the calling skill. Phase 6 — a separate step run by the calling skill — then runs the build and test suite. The fixer is accountable for surfacing failures honestly: if Phase 6 reveals a regression in code the fixer touched, the fixer re-enters to investigate and re-fix before the cycle reports complete. Cross-reference `dev-essentials:engineering-discipline` Rule 1: own every red signal in your session.

The fixer never reports "ready for build verification" on a known-broken state. "I believe the fix is correct" is not a substitute for an honest Phase 6 result.

---

## 8. Per-finding report format

For each finding, add one line to the cycle's full report. This line is the content of the
**Verification source** field in the SKILL.md Full format's "Details per item" section:

```
F<n> [APPLY|PARTIAL|REJECT] — <one-sentence reasoning citing primary source>
```

Examples:

```
F1 [APPLY] — Null-check gap confirmed by reading GetSession callers at SessionManager.cs:142; fix is bounded to that method.
F2 [PARTIAL] — Logic bug verified; helper-extraction refactor is out of scope for this triage; extraction deferred.
F3 [REJECT] — Field `skills` not found in any installed plugin's plugin.json schema; cannot verify this field exists.
```

---

## 9. When the fixer disagrees with a confident reviewer

If the fixer classifies a finding as REJECT but the reviewer stated it with high confidence, the fixer's report includes:

```
REJECTED with reason: <one sentence>; reviewer's claim does not verify against <primary source consulted>.
```

The user reads the full report and decides whether to override. The fixer does not apply an unverified fix simply because the reviewer was confident — confidence is not verification.

---

## Hard rules (no exceptions)

1. Classify every finding before touching any file. No silent skips.
2. Only touch files the reviewer cited (plus structurally required supporting files per §6 carve-out). Never `git add -A`.
3. Run build/test after fixes and report honestly. Never claim pass without running.
4. Defer unrelated issues to Phase 9. Do not fix what isn't on the triage list.
5. Document every REJECT and PARTIAL with one sentence of reasoning.
