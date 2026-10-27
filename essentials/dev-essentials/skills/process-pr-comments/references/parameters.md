# Process PR Comments Parameters

Phase 1 of `SKILL.md` reads this file. The orchestrating session names it in each Stage 1 and Stage 2 brief.

Pass the parameters as free-form `key=value` pairs and standalone flags in the skill arguments. `pr` is required. `owner` and `repo` are required for a PR number. All other parameters are optional.

| Param | Values | Default | Meaning |
| --- | --- | --- | --- |
| `pr` | `<id>` or full GitHub PR URL | Required | The target PR. A full URL gives `owner`, `repo`, and the PR number. These values override the other parameters. |
| `owner` | GitHub org or user name | From the URL, else required | The owner of the repository. Use the value of the user word for word. Never infer it. |
| `repo` | Repository name | From the URL, else required | The name of the repository. Use the value of the user word for word. Never infer it. |
| `interval` | `5m`, `15m`, `30m`, `1h`, `<N>m` | `15m` | The poll interval for `loop`. Without `loop`, the skill ignores it. |
| `loop` | flag | off | Turns on the monitor. After the first cycle, the skill starts `/loop` at `interval` (see Phase 6). Without this flag, the skill runs one cycle and stops. Not allowed together with `deep-fix` (see Rules). |
| `dry-run` | flag | off | Analysis and a report in chat only. No replies and no edits. |
| `tags` | Tag names, comma-separated, for example `ToFix,Question` | all | Process only these tags in this cycle. Write the tag names without brackets. |
| `bots` | Bot logins, comma-separated | `github-actions[bot]`, `copilot-pull-request-reviewer[bot]`, `coderabbitai[bot]` | Adds bot logins to the default bot list. Phase 2 step 1 keeps the comments of listed bots and skips the comments of other bots. It compares logins without the `[bot]` suffix. A comment with an automated-review header goes to Phase 3b, from any author. |
| `no-reply` | flag | off | Post no thread replies. Code edits are still allowed. |
| `no-edit` | flag | off | Drafts only. Never edit files, also not for a trivial fix. |
| `no-commit` | flag | off | Edit and stage locally only. Do not commit or push. For a review session where the human wants to inspect the change first. |
| `squash` | flag | off | One commit for all fixes of this cycle, instead of one commit for each thread. The push stays once per cycle, and it still needs the go-ahead unless `autonomous` is set. |
| `autonomous` | flag | off | No gate of this skill stops: Bucket A1, Bucket A2, and the push go-ahead (see "Autonomy"). The skill posts `[Question]` and `[ToDiscuss]` replies. It implements fixes where nothing settles the approach, and automated-review fixes that add a new architecture or a new public contract. It creates `[OutOfScope]` issues through Task Composer. It pushes once per cycle. The invariants of Bucket B and an active "pause for my review" instruction still hold. `--autonomous` also works. On a `deep-fix` run, pass `--autonomous` to `/research-implement-review-report`. |
| `interactive` | flag | off | Stop at the gates of Bucket A1 and Bucket A2 (see "Autonomy"). `--interactive` also works. On a `deep-fix` run, pass `--interactive` to `/research-implement-review-report`. |
| `strict` | flag | off | Pause before every file edit, whatever its size. |
| `include-resolved` | flag | off | Also process the threads that Phase 2 skips because `is_resolved` or `is_outdated` is true. Rarely useful. |
| `deep-fix` | `<commentId>` or `T#<commentId>` | off | The ID of the top comment of the thread (the `T#` number), not the `PRRT_` node ID. Send the fix of this ONE thread through `/research-implement-review-report` with `--commit-mode=single`, instead of the inline fix path of this skill. That skill runs research, a plan, a plan gate, the implementation, a review loop, and a report. A human named the thread, so no size or tag list limits it. Only the ineligible cases in `references/deep-fix.md` apply. One thread per invocation. Not allowed together with `loop` (see Rules). |
| `deep-fix-rounds` | `<N>` | `2` | The cycle count of the review loop, passed word for word as `--rounds` to `/research-implement-review-report`. Without `deep-fix`, the skill ignores it. |
