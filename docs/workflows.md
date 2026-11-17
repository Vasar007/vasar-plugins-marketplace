# Working across sessions

This page covers the choice between one Claude Code session and a new one, for the workflows of this marketplace.

## One session or a new one

The usual chain has three steps. You build a task, for example with `/dev-essentials:research-implement-review-report`. Then you open a pull request. Then you run `/dev-essentials:process-pr-comments` for the review comments.

If the review comes soon after the build, stay in the build session. Its prompt cache is still warm. The prompt cache is a saved copy of the history on the server. A call that hits it pays only the low cached rate for that history. A cached prefix expires after a period of inactivity. On a Claude subscription, the main conversation gets a one-hour cache. With an API key, it gets five minutes. The page [How Claude Code uses prompt caching](https://code.claude.com/docs/en/prompt-caching.md#cache-lifetime) has the details.

After a long pause, the cache is cold. The first call then reads the whole history again as new input. A long session pays the most for that call. In this case, follow these steps:

1. Run `/dev-essentials:save-context` in the build session.
2. Start a new session.
3. Run `process-pr-comments` in the new session.

The skill reads the hand-off file of the build session in Phase 1, so the decisions of the build session stay known.

To see the cache state, run `/usage`. After the first response, it shows a `Prompt cache (main)` line that says whether the cache is warm right now. This needs Claude Code 2.1.251 or later. See the section [on cache performance](https://code.claude.com/docs/en/prompt-caching.md#check-cache-performance).

## What the runs showed

The study of issue #184 ran on 2026-11-16. It measured a long session of about 310000 tokens against a new session. The case needs a decision that only the build session knows. These are the results of `process-pr-comments`:

- A long session with a cold cache cost 3.04 USD and scored 1.00 in 3 of 3 runs.
- A long session with a warm cache cost 0.82 USD and scored 1.00 in 3 of 3 runs.
- A new session with the hand-off file cost 0.51 USD and scored 1.00 in 3 of 3 runs.
- A new session with no hand-off file scored 0.50 in 3 of 3 runs. It applied a change that the user had ruled out.

The costs are the list prices of the eval tool, for one model, at one time. They show a ratio between the ways to work. They are not a price list. A comment that needs no fact of the build session works in a new session with no hand-off file.

## A fresh session for a long workflow

Start `/dev-essentials:feature-pipeline` in a fresh session. The pipeline reads its issue itself, so it needs no history. In a long session, each of its main calls reads the whole history. In the same study, one run in a long session cost 7.60 USD with a cold cache and 5.42 USD with a warm cache. A run in a fresh session cost 3.21 USD (the mean of 3 runs), with the same score.

## After a plugin update

A running session keeps the plugin text that it loaded. After an update, start a new session, or run `/reload-plugins` in the session. The page [Keep plugins updated](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated) says how this works. The section "Updating the plugins" of the [README](../README.md#updating-the-plugins) says how to get the update.

In the study, a session that went on with a history from another plugin version did not start the skill in 10 of 12 runs. The cause is not known.
