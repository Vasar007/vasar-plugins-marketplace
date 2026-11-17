# Working across sessions

This page covers the choice between one Claude Code session and a new one, for the workflows of this marketplace.

## One session or a new one

The usual chain has three steps. You build a task, for example with `/dev-essentials:research-implement-review-report`. Then you open a pull request. Then you run `/dev-essentials:process-pr-comments` for the review comments.

If the review comes within the cache lifetime after the build, stay in the build session. Its prompt cache is still warm. The prompt cache is a saved copy of the history on the server. A call that hits it pays only the low cached rate for that history. A cached prefix expires after a period of inactivity. By default, the main conversation gets a one-hour cache on a Claude subscription, within the usage of the plan. With an API key, or with usage credits after the plan limit, it gets five minutes. The setting `promptCacheTtl` can change this. The page [How Claude Code uses prompt caching](https://code.claude.com/docs/en/prompt-caching#cache-lifetime) has the details.

After a pause longer than the cache lifetime, the cache is cold. The first call then processes the whole history again and writes it into the cache. A long session pays the most for that call. So write the hand-off file while the cache is still warm:

1. When the build ends, run `/dev-essentials:save-context` in the build session. The skill `research-implement-review-report` and the command `implement-task` already do this as their last step.
2. If the review comes after the cache lifetime, start a new session in the same folder, on the branch of the pull request.
3. Run `/dev-essentials:process-pr-comments` in the new session.

The skill reads the hand-off file in Phase 1, so the decisions of the build session stay known. It reads each file in `Results/` of the notes folder whose `Branch:` line names the branch of the pull request. If you want another file, name it when you start the skill.

Claude Code can also compact a long session that stays idle on the one-hour cache. The hand-off file keeps the decisions in that case too.

To see the cache state, run `/usage`. After the first response, it shows a `Prompt cache (main)` line that says whether the cache is warm right now. This needs Claude Code 2.1.251 or later. See the section [on cache performance](https://code.claude.com/docs/en/prompt-caching#check-cache-performance).

## What the runs showed

Eval runs of this marketplace on 2026-11-16 measured the cost. They compared a long session of about 310000 tokens with a new session. The case needs a decision that only the build session knows. These are the results of `process-pr-comments`:

- A long session with a cold cache cost 3.04 USD and scored 1.00 in 3 of 3 runs.
- A long session with a warm cache cost 0.82 USD and scored 1.00 in 3 of 3 runs.
- A new session with the hand-off file cost 0.51 USD and scored 1.00 in 3 of 3 runs.
- A new session with no hand-off file scored 0.50 in 3 of 3 runs. It applied a change that the user had ruled out.

The costs come from the token counts of the runs and the list prices of one model at one time. The costs with a cold and a warm cache are computed from the same runs, not measured in separate runs. They show a ratio between the ways to work. They are not a price list. A comment that needs no fact of the build session works in a new session with no hand-off file.

## A new session for a long workflow

Start `/dev-essentials:feature-pipeline` in a new session. The pipeline reads its issue itself, so it needs no history. In a long session, each of its main calls reads the whole history. In the same runs, one run in a long session cost 7.60 USD with a cold cache and 5.42 USD with a warm cache. A run in a new session cost 3.21 USD (the mean of 3 runs), with the same score.

## After a plugin update

A running session keeps the plugin text that it loaded. After an update, start a new session for the next workflow skill. `/reload-plugins` loads the new text into the running session, but that session keeps a history from the old version. The page [Keep plugins updated](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated) says how updates work. The section "Updating the plugins" of the [README](../README.md#updating-the-plugins) says how to get the update.

In the same runs, a session went on with a history from another plugin version. It did not start the skill in 10 of 12 runs. The cause is not known.
