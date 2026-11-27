# Working across sessions

This page is for a user of the workflows of `dev-essentials`. It covers the work modes, and the choice between one Claude Code session and a new one.

## Work modes

Each gated workflow of `dev-essentials` takes the option `--mode`. It has the values below.

- `--mode interactive`: the workflow stops at each of its gates, and you approve each step.
- `--mode partial`: the default. The workflow reports its plan and goes on. It stops at the plan only for open decisions. It does not push or open a pull request without your answer or a push flag such as `--commit-push`. `research-implement-review-report`, `implement-task`, and `implement-batch` ask one question about these steps at their end.
- `--mode full`: the workflow asks no question, except at a hard stop or at a stop that the workflow keeps. It ends at its last outward step. In `feature-pipeline`, `research-implement-review-report`, `implement-task`, and `implement-batch`, that is the merge of the pull request. In `process-pr-comments`, that is the push of the fixes and the posted replies.

The hard stops hold in every mode. They are data loss, a change of pushed history, a red default branch, and a security risk. A failed gate, a blocking question, and your own instruction also stop the run. In every mode, a run removes the temporary files that it made itself, and asks no question. Only you pick the full mode, in your request. A rule in a project file or in a memory file cannot pick it. The skill `dev-essentials:work-modes` holds the rules.

A merge gate can fail on a cause of the branch. Examples are a red check that a local run shows, and a merge state `behind` or `dirty`. Then `research-implement-review-report`, `implement-task`, and `implement-batch` fix it, at most 2 times. The full mode pushes the fix. The other modes ask before the push, and the interactive mode also asks before the fix. Each other failed item stops the run. A call of `merge-pr` alone never fixes a cause.

Your request can name an unknown mode, or a flag that the workflow does not define. Then the workflow asks you which mode to use before it starts.

Some runs have no GitHub repository: the request names none, and no remote of the clone is on `github.com`. Then `research-implement-review-report`, `implement-task`, and `implement-batch` open no pull request and merge nothing, in every mode. They also ask no question about these steps.

## Work with no worktree

`feature-pipeline`, `implement-task`, and `implement-batch` make a git worktree for each run. With `--no-worktree`, they work in the current folder instead. This option is for a user who already works in a worktree or wants none. Then these rules hold:

- On the default branch or the base branch, the full mode creates a branch first, and the other modes ask.
- If a tracked file has a change, `implement-task` and `implement-batch` stop.
- They ask before a task writes an untracked file of the user.
- If the branch holds commits that are not on the remote base branch, they ask outside the full mode. If they cannot count these commits, they also ask. In the full mode, they do no push.
- After a merge, they remove no worktree.

## Where the notes go

The workflows of `dev-essentials` write plans, research files, reports, reviews, and drafts into a notes folder. The file [`notes-root.md`](../essentials/dev-essentials/references/notes-root.md) gives the rule. The first item that gives a folder wins:

1. A folder that you name in your request, for example with the option `--notes-dir` of `implement-task`.
2. A folder that the `CLAUDE.md` file of the repository names for notes. A folder that it names for one kind of file only, for example plans or reports, holds that kind only. The other files take the next items.
3. The task folder of a knowledge base (KB) clone. The variable `KB_DIR` names the clone, and the clone holds `_claude/RULES.md`. The `kb` plugin uses the same test.
4. Else the folder `~/claude-notes/<repo>/<branch>/` in your home folder.

The folders of items 3 and 4 are outside the repository. So no commit takes the notes, and the removal of a worktree keeps them. Claude Code asks before each write outside the working folders of a session. To allow these writes, add the folder with `/add-dir`, or add it to `permissions.additionalDirectories` in your configuration file.

`feature-pipeline` keeps the files of a run in its artifacts folder in the worktree. Its archive step, for example after the merge, copies them to `Pipeline/<task ID>/` in the notes folder.

## One session or a new one

The usual chain has these steps. You build a task, for example with `/dev-essentials:research-implement-review-report`. Then you open a pull request, or the workflow opens it at its end. Then you run `/dev-essentials:process-pr-comments` for the review comments.

If the review comes within the cache lifetime after the build, stay in the build session. Its prompt cache is still warm. The prompt cache is a saved copy of the history on the server. A call that hits it pays only the low cached rate for that history. A cached prefix expires after a period of inactivity. By default, the main conversation gets a one-hour cache on a Claude subscription, within the usage of the plan. With an API key, or with usage credits after the plan limit, it gets five minutes. The setting `promptCacheTtl` can change this. The page [How Claude Code uses prompt caching](https://code.claude.com/docs/en/prompt-caching#cache-lifetime) has the details.

After a pause longer than the cache lifetime, the cache is cold. The first call then processes the whole history again and writes it into the cache. A long session pays the most for that call. So write the hand-off file while the cache is still warm:

1. When the build ends, run `/dev-essentials:save-context` in the build session. The skill `research-implement-review-report` and the command `implement-task` already do this as their last local step.
2. If the review comes after the cache lifetime, start a new session in the same folder, on the branch of the pull request.
3. Run `/dev-essentials:process-pr-comments` in the new session.

The skill reads the hand-off file in Phase 1, so the decisions of the build session stay known. It reads each file in `Results/` of the [notes folder](#where-the-notes-go) whose `Branch:` line names the branch of the pull request. If you want another file, name it when you start the skill.

Claude Code can also compact a long session that stays idle on the one-hour cache. The hand-off file keeps the decisions in that case too.

To see the cache state, run `/usage`. After the first response, it shows a `Prompt cache (main)` line that says whether the cache is warm right now. This needs Claude Code 2.1.251 or later. The section [on cache performance](https://code.claude.com/docs/en/prompt-caching#check-cache-performance) has the details.

## What the runs showed

Eval runs of this marketplace on 2026-11-16 compared a long session of about 310000 tokens with a new session. The case of `process-pr-comments` needs a decision that only the build session knows. Each row is 3 runs:

| Session | Cost | Score |
| --- | ---: | ---: |
| Long session, cold cache | 3.04 USD | 1.00 |
| Long session, warm cache | 0.82 USD | 1.00 |
| New session with the hand-off file | 0.51 USD | 1.00 |
| New session with no hand-off file | no record | 0.50 |

The run with no hand-off file applied a change that the user had ruled out. The costs come from the list prices of one model at one time, so read them as a ratio and not as a price list. The cold and the warm cost come from the same runs. A comment that needs no fact of the build session works in a new session with no hand-off file.

## A new session for a long workflow

Start `/dev-essentials:feature-pipeline` in a new session. The pipeline reads its issue itself, so it needs no history. In a long session, each of its main calls reads the whole history. In the same runs, one run in a long session cost 7.60 USD with a cold cache and 5.42 USD with a warm cache. A run in a new session cost 3.21 USD (the mean of 3 runs), with the same score.

## After a plugin update

A running session keeps the plugin text that it loaded. After an update, start a new session for the next workflow skill. `/reload-plugins` loads the new text into the running session, but that session keeps a history from the old version. In the same runs, such a session did not start the skill in 10 of 12 runs. The cause is not known.

The page [Keep plugins updated](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated) says how updates work. The section [Update the plugins](./installing.md#update-the-plugins) says how to get the update.
