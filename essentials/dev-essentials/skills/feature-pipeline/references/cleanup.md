# Cleanup (Step 10)

The master agent reads this file at Step 10 of `SKILL.md`, after the result of Step 9 is final. Do the steps in order. By default, the task artifacts and the worktree stay on disk until the PR is merged.

## 1. Find the PR status

Steps 2 and 4 both use this status, so look it up only once.

- No PR: `pr` in `pipeline-state.json` is `null` (a branch-only flow, or the run created no PR). Skip the lookup. No PR exists to wait for.
- A PR exists: fetch the PR status from GitHub again, with the `pr` fields of `pipeline-state.json`. Follow `dev-essentials:github-mcp-conventions` Rules 1 and 2.

  ```text
  mcp__plugin_github_github__pull_request_read(
      method="get",
      owner=<pr.owner>,
      repo=<pr.repo>,
      pullNumber=<pr.number>
  )
  ```

  If the GitHub MCP call fails (MCP not loaded, a network error, or an authentication timeout), stop and ask the user: `GitHub PR lookup failed; should I proceed with cleanup based on the cached state, or wait?` Do not skip the lookup silently and continue to the archive or the worktree removal. With `--autonomous`, do not stop. Skip the archive and the worktree removal, and report the failed lookup.

If a PR exists, step 2 (archive) and step 4 (worktree removal) use the PR eligibility test. The action of a step can run in one of two cases:

- The PR `state` is `closed`, and `merged` is `true`.
- The user explicitly asks for that action now. Examples for step 2: "archive the task logs now", "go ahead and archive", "archive it anyway". Examples for step 4: "clean up the worktree", "remove the worktree", "you can drop the worktree now". An equivalent explicit instruction also counts.

The test does not cover the case without a PR. Steps 2 and 4 handle that case in different ways. Without a PR, the archive can run, but the worktree removal never runs on its own.

## 2. Archive the task logs (gated)

Do not archive by default right after the PR opens. While the PR is in review, the task artifacts are live documents. Examples: `spec.md`, `review.md`, the HTML artifact, and `pipeline-state.json`. The review rounds use the copy in the worktree.

Archive `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/` to `~/.claude/task-logs/{TASK_ID}/` in two cases only: the run has no PR, or the PR passes the eligibility test for the archive. If `~/.claude/task-logs/` does not exist, create it. If the target folder exists, overwrite its contents.

Else leave the artifacts in `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/`, skip the archive, and report that the archive waits for the PR review.

## 3. Without a worktree

With `--no-worktree`, skip the worktree removal, because no worktree exists. Announce the end of the run with the branch name. As step 2 says, also give the path of the archived logs, or a note that the archive waits for the PR review.

## 4. Remove the worktree (gated)

Do not remove the worktree by default. The worktree stays on disk until the PR is merged. PR review feedback, follow-ups of automated reviews, and build or test reproduction all need the working tree of the branch. An early removal leaves that work with no build.

- No PR: keep the worktree, unless the user explicitly asks to remove it. For that request, use the user-directed override of `dev-essentials:git-worktree-management` Workflow C. Do not remove a worktree without a PR on your own.
- A PR exists: use the PR status from step 1. Do not look it up again. The eligibility test for the removal decides.

If the archive of step 2 did not run yet, run it before each worktree removal. This holds for both triggers: a merged PR and an explicit request of the user. The removal deletes `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/` with the worktree. So copy anything that you want to keep to `~/.claude/task-logs/{TASK_ID}/` first. Workflow C of `dev-essentials:git-worktree-management` has the same rule ("archive anything worth keeping before removal").

> **Bulk cleanup is out of scope for this skill.** The user can ask to remove worktrees broadly. Examples: "remove all worktrees" or "clean up all merged worktrees". Do not try a bulk cleanup here. This skill manages exactly one worktree, for the current task, and `pipeline-state.json` has a `pr` object for that task only. Hand the request to Workflow D of `dev-essentials:git-worktree-management` at once, and stop the pipeline. Do not list or touch any other worktree.

If the eligibility test fails, leave the worktree on disk, and skip the removal.

If the removal can run, remove the worktree by `{WORKTREE_PATH}` (the absolute path from Step 0, sub-step 6), not by a hardcoded relative path. Run `git worktree remove {WORKTREE_PATH}`, then make sure with `git worktree list` that it is gone. If the removal fails with "Permission denied", do not assume an IDE file lock. Go through the ordered diagnosis of Workflow C of `dev-essentials:git-worktree-management` before you report to the user: a shell CWD parked in the worktree, then Windows long paths, then the leaf-first walkup. **Never run `git worktree remove --force`, and never force past a refusal for uncommitted changes.** The folder deletions of the diagnosis are allowed. Never use them to get past a refusal for uncommitted changes.

The keep-until-merged rule has its main text in the "Lifecycle Rule" section of `dev-essentials:git-worktree-management`.

## 5. Announce the end of the run

Report the final branch or PR outcome. Say whether the run removed the worktree or kept it on purpose, and why. Say whether the run archived the task logs or left them in place until the PR review ends.
