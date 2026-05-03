---
description: Review the current PR across all commits against the target branch
---

Review this pull request **across all commits in the current branch** (not just the last commit).

Use `git` to inspect the full diff against the target branch (e.g., `main`/`master`) and include changes introduced by every new commit.

**Arguments**: $ARGUMENTS

- If the argument is a file path, read it as the PR description for additional context.
- If empty, proceed without a PR description.

---

Output format (keep it very compact, no essays):

# Review by AI Agent (Round-N)

Replace N with a valid review round number. If a previous review exists in the conversation, increment the round number.

## Description

Give a brief overall impression of the PR (100-200 characters).

## Summary table

Provide a table of findings (issues/notes) with:

- `#` (sequential number)
- `Severity` (Blocker / High / Medium / Low / Nit)
- `Type` (Bug / Reliability / Security / Performance / Maintainability / Test / Style / Architecture)
- `File:Line(s)`
- `What's wrong` (max 1 short sentence)
- `Suggested direction` (not the exact fix; e.g., "refactor", "add validation", "adjust API contract", "ok to accept risk")

Only include meaningful items; skip trivial commentary.

## Details per item

For each row from the table, add a short section:

- **Header**
- **Problem:** 1-2 sentences
- **Impact:** 1 sentence
- **Recommendation:** 1-2 sentences (still no full code dumps)

## Conclusion

In bullets:

- **Must fix before merge**
- **Acceptable risks**
- **Needs discussion**

## Final verdict

One line:

- ✅ **Approve**
- ✅➕ **Approve with suggestions**
- 🕒 **Wait for author**
- ❌ **Reject**

## Reviewer model

"Review made by `{MODEL}`" (replace {MODEL} with your actual model name, e.g. `claude-opus-4-6`)

---

## Review rules

- Focus on correctness, edge cases, consistency with existing patterns, logging/telemetry, error handling, tests, and architecture.
- Verify that changes are coherent across commits (no regressions introduced in earlier commits).
- Call out missing tests or inadequate coverage.
- If you can't determine something from the diff, explicitly ask a specific question instead of guessing.

---

Now review the PR accordingly.
