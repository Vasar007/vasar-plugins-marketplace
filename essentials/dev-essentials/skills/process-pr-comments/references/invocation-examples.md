# Process PR Comments Invocation Examples

These examples show the parameters of `references/parameters.md` in use.

```text
# One-shot on a specific PR (owner and repo required)
/process-pr-comments pr=42 owner=my-org repo=my-repo

# Full GitHub URL — owner and repo parsed automatically
/process-pr-comments pr=https://github.com/my-org/my-repo/pull/42

# Opt in to polling monitor at default 15m cadence
/process-pr-comments pr=42 owner=my-org repo=my-repo loop

# Specific PR, 30-minute polling
/process-pr-comments pr=42 owner=my-org repo=my-repo loop interval=30m

# Dry-run classification only, focus on [ToFix] and [Question]
/process-pr-comments pr=42 owner=my-org repo=my-repo dry-run tags=ToFix,Question

# Strict mode — nothing is edited without approval
/process-pr-comments pr=42 owner=my-org repo=my-repo loop strict

# Edit + stage only, no commit, no push (human will commit)
/process-pr-comments pr=42 owner=my-org repo=my-repo no-commit

# Bundle all fixes from this cycle under a single commit; push still needs your explicit go-ahead
/process-pr-comments pr=42 owner=my-org repo=my-repo squash

# Full autonomy: implement, decide, reply, create issues, push, with no pauses (a human still reviews and approves the PR before merge)
/process-pr-comments pr=42 owner=my-org repo=my-repo autonomous

# Route one Medium/Large [ToFix] thread through research-implement-review-report instead of drafting it
/process-pr-comments pr=42 owner=my-org repo=my-repo deep-fix=T#2201458823

# Same, with a 3-round review loop instead of the default 2
/process-pr-comments pr=42 owner=my-org repo=my-repo deep-fix=2201458823 deep-fix-rounds=3

# Old default: draft and wait for larger fixes
/process-pr-comments pr=42 owner=my-org repo=my-repo interactive

# Already wrapped in /loop — outer harness controls cadence
/loop 15m /process-pr-comments pr=42 owner=my-org repo=my-repo
```
