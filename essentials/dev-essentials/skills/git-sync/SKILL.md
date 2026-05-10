---
name: git-sync
description: Git sync mechanics — when to rebase, when to merge, and how to verify branch state before reviews/PRs. Covers the `git rebase --onto <new-base> <old-base-tip>` pattern with subject-corruption fix recipe, the `git merge --no-ff` rule for branches the user does not own, and the pre-review branch-state verification checklist. Triggers on requests like "rebase the branch", "sync with master", "the base was rewritten", "fix conflicts after merge", "review this branch", "compose PR", "bring branch up to date", or any time the agent is about to invoke `git rebase` / `git pull --rebase` / `git merge` on a long-lived branch.
---

# Git Sync Conventions

Three patterns the user has corrected the main agent on enough times that they belong in a skill, not just memory.

## Rule 1 — Use `git rebase --onto` when the upstream base has been rewritten

When the upstream base of a feature branch has been **rewritten behind it** — different SHAs for the same logical content (squashed PR merges, branch resets, force-pushes on release branches) — plain `git rebase <new-base>` will replay redundant intermediate "Merged PR" commits and produce conflicts you don't need.

Use the explicit form:

```bash
git rebase --onto <new-base> <old-base-tip-or-commit-just-before-feature-commits>
```

This replays only the commits between `<old-base-tip>..HEAD` (the feature commits), skipping the obsolete merges whose tree state is already in `<new-base>`.

### How to detect the rewrite

After `git fetch origin <base-branch>`, check whether the prior local-master tip is still in upstream history:

```bash
git log --oneline origin/<base-branch> | grep -E "^<old-base-tip-prefix>"
```

If empty, the upstream was rewritten — use `--onto`.

### Picking `<old-base-tip>`

The `<old-base-tip>` argument is the commit immediately below your first feature commit on the branch.

- One-commit feature branch: `git rebase --onto origin/<base> HEAD~1`
- Multi-commit: identify the parent of your earliest feature commit and use that.

After the rebase, sanity-check `git log --oneline origin/<base>..HEAD` — the count must equal the number of feature commits, no more.

### Watch out — silent subject-line corruption

`git rebase --onto` can mangle commit subjects when crossing many obsolete merges in the replay path. The body line gets promoted to the subject; the original subject line is silently dropped.

Detect immediately after rebase:

```bash
git log --format="%h %s" origin/<base>..HEAD
```

If a subject is just the body's opening sentence (no leading scope tag or issue reference), it's been mangled.

### Fix recipe — does NOT require interactive rebase or amend permission

```bash
# Save the top commit(s) above the broken one
git tag tmp/cherry-pick-restore HEAD              # for one-commit-above
# (for multiple, save patches: git format-patch -<n> HEAD --stdout > /tmp/keep.mbox)

git reset --hard <broken-commit>~1                # reset to parent of broken commit

# Re-apply the broken commit's tree, then commit with the correct message:
git cherry-pick --no-commit <broken-commit-sha>
git commit -F- <<'EOF'
<subject line>

<body restored from "git show <broken-commit> --format=%B">
EOF

# Re-apply the saved commit(s)
git cherry-pick tmp/cherry-pick-restore
git tag -d tmp/cherry-pick-restore
```

Cherry-pick preserves authorship and committer dates; `git commit -F-` creates a fresh commit with the correct message (tree from the cherry-pick, no rebuild needed).

### Safety net

ALWAYS create a backup tag before any rebase that crosses an upstream rewrite:

```bash
git tag backup/<task>-pre-rebase-<n> <current-head>
```

If conflicts during `--onto` rebase look unexpectedly broad (the same files modified by both sides for unrelated reasons), STOP and re-check the merge-base with `git merge-base HEAD <new-base>` and the diff between old/new bases — there may be a third commit you didn't expect.

### Anti-patterns

- `git pull --rebase` on a feature branch when upstream was rewritten — same problem as plain rebase, plus auto-applies before you can audit.
- Skipping the post-rebase subject-line check because "the rebase succeeded with no conflicts" — the corruption is silent.
- Using `git rebase -i --interactive` and a TUI editor in this harness — interactive editors are blocked. Use the tag + reset + amend + cherry-pick recipe above.

## Rule 2 — `git merge --no-ff`, never rebase, when working someone else's branch

When you are processing PR feedback on a branch authored by **someone else** (typical case: a collaborator whose code the user is covering), sync with the base via a no-fast-forward merge commit:

```bash
git fetch origin <base-ref>
git -C <worktree> merge --no-ff origin/<base-ref> -m "Merge branch '<base-ref>' into <feature-branch>"
```

Never `git rebase`, `git pull --rebase`, or `git rebase -i`. Never force-push.

### Why

Rebasing rewrites the original author's commit SHAs and authorship metadata, erasing their attribution from blame/log and breaking any local checkouts the original author has. A merge commit keeps the original author's commits intact and adds one new merge commit on top authored by the user covering them.

### Anti-patterns

- `git pull --rebase origin <base>` from inside someone else's worktree — rewrites their commits.
- `git rebase origin/<base>` — same problem.
- Auto-fast-forward (`git merge --ff-only`) — silently absorbs master commits without a merge commit; loses the audit trail of when the user synced.
- Force-pushing after any rebase — visible to the original author and breaks their local clones.
- "The merge commit clutters history, let me rebase instead" — preserve attribution over aesthetics whenever the branch isn't yours.

### How to detect "someone else's branch"

- The PR's `createdBy` is not the user, OR
- The branch name contains another `<username>` segment (e.g. `release/<other-user>/tasks/...`), OR
- The user has explicitly said they're not the author.

When the author is ambiguous, default to merge.

### Operational rules

- Always `--no-ff` so the merge commit is explicit even when fast-forward would be possible. The merge commit is the audit trail of when the user pulled master into the branch.
- Run from inside the branch's worktree using `git -C <worktree> ...`.
- Build-verify the full affected scope after the merge — a cross-area merge can pull in changes anywhere; build the solution rather than a single project unless you have specific scoping evidence.
- Do NOT push the merge as part of the sync. Push is a separate, user-gated step.
- If conflicts arise: report the file list, run `git merge --abort`, hand it back to the user. Do NOT auto-resolve — the original author may have context about the correct resolution.
- Do NOT change the worktree's upstream (see `dev-essentials:git-worktree-management` for the unset-upstream rule).

### Edge case

If the user IS the branch author and asks for a rebase, that's their call — Rule 1 applies. Rule 2 is specifically about assisting on another author's branch.

## Rule 3 — Verify branch state before reviews and PRs

Before composing PR descriptions, running code reviews, or generating change summaries, verify the branch is rebased on the target branch and only analyze the actual diff.

```bash
git diff origin/<base>...HEAD --stat
```

Exclude files/changes that are already in the base branch. Do not include already-merged changes in PR descriptions or review analysis.

### Why this matters

A branch that was rebased after the initial commit may have stranded changes already in master. Without the `origin/<base>...HEAD` filter, the PR description and review will treat already-merged changes as if they belonged to this branch.

The three-dot form (`origin/<base>...HEAD`) diffs from the merge base, showing only what the branch contributes regardless of whether the branch is behind `origin/<base>`. The two-dot form (`..`) is a plain tree diff that includes base-side changes when the branch is not up to date, reintroducing the misattribution problem this rule exists to prevent.

### Checklist

1. Run `git fetch origin <base>` so `origin/<base>` is current.
2. Run `git diff origin/<base>...HEAD --stat` to see the actual ahead-set.
3. If anything in the diff looks unrelated to the task, suspect a stale base — confirm with the user before publishing.
4. Hand the diff (or its summary) to the PR/review subagent. Do not paste raw `git log` output that may include rewritten commits.
