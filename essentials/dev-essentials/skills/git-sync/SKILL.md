---
name: git-sync
description: Git sync rules for rebase, merge, and staging. Use `git rebase --onto` after a base rewrite, and `git merge --no-ff` on the branch of another author. Check the branch state before a review or a PR, and stage explicit paths only.
when_to_use: Use it for "rebase the branch", "sync with master", "the base was rewritten", or "bring branch up to date". Use it also before any `git rebase`, `git pull --rebase`, or `git merge` on a long-lived branch.
---

# Git Sync Conventions

## Rule 1 — Use `git rebase --onto` when the upstream base has been rewritten

A rewrite gives the same logical content different SHAs. Examples: squashed PR merges, branch resets, and force-pushes on release branches. If the upstream base of a feature branch was **rewritten behind it**, a plain `git rebase <new-base>` replays redundant "Merged PR" commits. These commits produce conflicts that you do not need.

Use the explicit form:

```bash
git rebase --onto <new-base> <old-base-tip-or-commit-just-before-feature-commits>
```

This replays only the commits in `<old-base-tip>..HEAD` (the feature commits). It skips the obsolete merges whose tree state is already in `<new-base>`.

### How to detect the rewrite

`<old-base-tip>` is the commit right below your first feature commit (see "Picking `<old-base-tip>`" below). After `git fetch origin <base-branch>`, find out whether this commit is still in the upstream history:

```bash
git merge-base --is-ancestor <old-base-tip> origin/<base-branch>
```

If the exit code is 0, the commit is still upstream, and a plain rebase is enough. If the exit code is 1, the upstream was rewritten. Use `--onto`. Any other exit code is an error, for example an unknown commit. Then stop, and find the cause before you rebase.

### Picking `<old-base-tip>`

The `<old-base-tip>` argument is the commit right below your first feature commit on the branch.

- One-commit feature branch: `git rebase --onto origin/<base> HEAD~1`
- Multi-commit branch: find the parent of your earliest feature commit, and use it.

After the rebase, sanity-check with `git log --oneline origin/<base>..HEAD`. The count must equal the number of feature commits, no more.

### Watch out — silent subject-line corruption

In a replay across many obsolete merges, `git rebase --onto` can mangle commit subjects. The body line becomes the subject, and the original subject line is lost silently.

Look for it right after the rebase:

```bash
git log --format="%h %s" origin/<base>..HEAD
```

If a subject is only the opening sentence of the body (no leading scope tag or issue reference), the rebase mangled it.

### Fix recipe — does NOT require interactive rebase or amend permission

```bash
# Save the commit(s) above the broken one
git tag tmp/cherry-pick-restore HEAD

git reset --hard <broken-commit>~1                # reset to parent of broken commit

# Re-apply the broken commit's tree, then commit with the correct message.
# --author and --date keep the original author and author date.
git cherry-pick --no-commit <broken-commit-sha>
git commit --author="$(git log -1 --format='%an <%ae>' <broken-commit-sha>)" \
  --date="$(git log -1 --format=%aI <broken-commit-sha>)" -F- <<'EOF'
<subject line>

<body restored from "git show <broken-commit> --format=%B">
EOF

# Re-apply every saved commit above the broken one, in order
git cherry-pick <broken-commit-sha>..tmp/cherry-pick-restore
git tag -d tmp/cherry-pick-restore
```

If the broken commit is `HEAD`, skip the last `git cherry-pick`, because no commit sits above it. The cherry-pick of the saved commits keeps their author and author date. `git commit -F-` creates a fresh commit with the correct message, and `--author` and `--date` copy the author and the author date of the broken commit. Do not use `-C <sha>` for this, because git does not allow `-C` together with `-F`. The tree comes from the cherry-pick, so no rebuild is needed.

### Safety net

ALWAYS create a backup tag before any rebase that crosses an upstream rewrite:

```bash
git tag backup/<task>-pre-rebase-<n> <current-head>
```

If conflicts during an `--onto` rebase look unexpectedly broad (the same files changed on both sides for unrelated reasons), STOP. Look at the merge base again with `git merge-base HEAD <new-base>`, and at the diff between the old and the new base. A third commit that you did not expect can be the cause.

### Anti-patterns

- `git pull --rebase` on a feature branch after an upstream rewrite. It has the same problem as a plain rebase, and it applies before you can review the result.
- No subject-line check after the rebase, because "the rebase succeeded with no conflicts". The corruption is silent.
- `git rebase -i` with a TUI editor. Interactive editors are blocked in this environment. Use the tag, reset, and cherry-pick recipe above.

## Rule 2 — `git merge --no-ff`, never rebase, when working someone else's branch

This rule is for PR feedback on a branch that **someone else** wrote, typically a collaborator whose code the user covers. On such a branch, sync with the base through a no-fast-forward merge commit:

```bash
git fetch origin <base-ref>
git -C <worktree> merge --no-ff origin/<base-ref> -m "Merge branch '<base-ref>' into <feature-branch>"
```

Never run `git rebase`, `git pull --rebase`, or `git rebase -i` on it. Never force-push.

### Why

A rebase rewrites the commit SHAs and the authorship metadata of the original author. It removes their attribution from blame and log, and it breaks their local checkouts. A merge commit keeps the commits of the original author intact. It adds one new merge commit on top, authored by the user who covers them.

### Anti-patterns

- `git pull --rebase origin <base>` inside the worktree of someone else rewrites their commits.
- `git rebase origin/<base>` has the same problem.
- A fast-forward (`git merge --ff-only`) takes in base commits silently, without a merge commit. The audit trail of the sync is lost.
- A force-push after any rebase is visible to the original author and breaks their local clones.
- "The merge commit clutters history, so I rebase instead." On a branch that is not yours, attribution comes before a clean history.

### How to detect "someone else's branch"

Any one of these signs means that the branch belongs to someone else:

- The PR author is not the user.
- The branch name has the `<username>` segment of another user (for example `release/<other-user>/tasks/...`).
- The user said explicitly that they are not the author.

If the author is ambiguous, default to a merge.

### Operational rules

- Always use `--no-ff`, so that the merge commit is explicit even where a fast-forward is possible. The merge commit records the moment that the user pulled the base into the branch.
- Run from inside the worktree of the branch with `git -C <worktree> ...`.
- After the merge, build the full affected scope. A merge across areas can pull in changes anywhere. Build the solution, not a single project, unless you have specific evidence for a narrower scope.
- Do NOT push the merge as part of the sync. A push is a separate step, and the user decides on it.
- If conflicts arise, report the file list, run `git merge --abort`, and hand it back to the user. Do NOT resolve them automatically, because the original author can have context about the correct resolution.
- Do NOT change the upstream of the worktree. See `dev-essentials:git-worktree-management` for the rule to unset the upstream.

### Edge case

If the user IS the author of the branch and asks for a rebase, that is the choice of the user, and Rule 1 applies. Rule 2 is only for help on the branch of another author.

## Rule 3 — Verify branch state before reviews and PRs

Before you write a PR description, run a code review, or write a change summary, look only at the changes that the branch adds. Use the three-dot diff against the target branch:

```bash
git diff origin/<base>...HEAD --stat
```

Leave out files and changes that are already in the base branch. Do not put changes that are already merged into PR descriptions or review analysis.

### Why this matters

After a rebase, a branch can hold stranded changes that are already in the base. Without the `origin/<base>...HEAD` filter, the PR description and the review treat already-merged changes as part of this branch.

The three-dot form (`origin/<base>...HEAD`) diffs from the merge base. It shows only what the branch adds, even for a branch that is behind `origin/<base>`. The two-dot form (`..`) is a plain tree diff. If the branch is not up to date, the two-dot form includes changes from the base side and brings the misattribution back.

### Checklist

1. Run `git fetch origin <base>`, so that `origin/<base>` is current.
2. Run `git diff origin/<base>...HEAD --stat` to see what the branch adds.
3. If anything in the diff looks unrelated to the task, suspect a stale base. Ask the user before you publish.
4. Give the diff, or its summary, to the PR or review subagent. Do not paste raw `git log` output, which can include rewritten commits.

## Rule 4 — Stage explicit paths only, never `git add -A` or `git add .`

Always stage files by explicit path:

```bash
git add <path1> <path2> ...
```

Never run `git add -A` or `git add .`. A blanket add sweeps everything in the working tree into the commit, without a warning: stray local edits, formatter or build byproducts, and files that an earlier step forgot to roll back.

### Never auto-stage shared build-configuration files

Never stage these files unless the change of the task really modifies them:

- `Directory.Build.props`
- `Directory.Packages.props`
- `global.json`

A local build or format pass can regenerate or reformat these shared files as a side effect, even though the task never touched them. Examples: whitespace normalization, package-version drift, and SDK-pin churn. They sit at the root of the solution or the repo, so `-A` or `.` stages them without any visible diff review. These files affect every project in the solution, so an unrelated change to them is a risk, and it is easy to miss in review.

### How to apply

1. Before you stage, run `git status --short` and review every entry.
2. Stage only the files that the current task changes on purpose: `git add -- <path1> <path2>`.
3. If one of the three files above shows as modified, and the task did not intend to change it, roll it back first. Use `git checkout -- <path>`, and do not stage it.
4. If a change to one of those files IS an intended part of the task, you can stage it. The rule is about an accidental add through a blanket add, not a ban on these files.
