# Tag Action Matrix

Stage 2 reads this file before it acts on a tagged comment. It has the action, the reply, and the examples for each tag.

## Contents

- Size thresholds for autonomy
- Tags
- When multiple tags combine
- Fall-back rules

The gates in this file are the defaults. Where `SKILL.md` § "Autonomy" differs, `SKILL.md` wins: `interactive` and `autonomous` change these gates as Bucket A1 and Bucket A2 say. Where this file says to ask the human or to wait, Stage 2 records the open item and goes on with the other threads. The orchestrating session asks the human (see "Who talks to the user" in `SKILL.md`).

The replies in this file show the marker and the text. Post each reply in the full form of `commit-push-resolve.md` § "Reply templates": the marker and the T# link tag on the first line, then a blank line, then the text. Every reply in this file is a pending reply, in every mode. Stage 2 writes it at once. It posts in the one batch of the cycle (`commit-push-resolve.md` § "When replies post"). In this file, "post" means "add to the batch".

Tag parsing: the tags are the bracketed tokens at the very start of the comment, for example `[ToFix]` or `[P1][Performance]`. Several tags combine. Pick one action with the rules of "When multiple tags combine". A comment with an automated-review header goes to `automated-review-verification.md`, whatever its tags and whatever its author. That file defines the header (§ "What counts as an automated review comment").

## Size thresholds for autonomy

These thresholds apply to `[ToFix]`, `[Performance]`, `[PX]`, and a trivial `[Suggestion]` or `[Optional]`.

- **Small**: at most 20 changed lines of code, one file, and no public API change (signatures, DTOs, exposed types). It adds no dependency and no test refactor. It is safe to implement.
- **Medium / Large**: anything larger, or a change that touches public APIs, DI wiring, database migrations, string resources, or API specs. An example of a migration is an EF Core migration. An example of an API spec is an OpenAPI spec. If the comment or the existing code settles the approach, implement it (Bucket A1). Else draft and wait, unless `autonomous` is set (Bucket A2). With `interactive`, always draft and wait. If `deep-fix` names the thread, send it through `/research-implement-review-report` instead, in every mode (see `deep-fix.md` § "`deep-fix` override").
- **Architectural**: only for a change at **rewrite-from-scratch size**. The bar is the exception of `automated-review-verification.md` § "Obviousness test (Phase 3b step 5)". The reviewer asks for a basically different mechanism with no precedent in this codebase. Several materially different ways to build it exist, and nothing in the existing code chooses between them. Draft and wait, unless `autonomous` is set (Bucket A2). You can suggest a design review. If `deep-fix` names the thread, send it through `/research-implement-review-report`, as in the Medium / Large row. To add, move, or rename a type across projects is **not** this level on its own. That is a Medium / Large fix, and the row above applies.

`strict` treats every category as "draft and wait". `interactive` brings back "draft and wait" for Medium / Large. `deep-fix` is an override for one thread, which the human gives at invocation. `strict` and the size thresholds never pick it on their own. For the full rule, see `deep-fix.md` § "`deep-fix` override".

## Tags

### `[ToFix]`

The reviewer requires a change. The PR does not get approval without it.

- Small: implement the edit. Then run Phase 4 steps 1 to 4 (`commit-push-resolve.md`). Build and test, then commit at once, with no approval first. Write the reply with the local commit SHA as a pending reply: `**[AI]** Fixed: <one-line summary>. Committed as <short-sha>; will be included in the next push.` The push needs the explicit go-ahead of the user, unless `autonomous` is set (Phase 4). To stage only, pass `no-commit`.
- Medium / Large: if the comment or the existing code settles the approach, implement it (Bucket A1). Else prepare the diff in chat, explain the approach, and wait for the explicit go-ahead of the human. With `autonomous`, implement it instead, and name the approach in the reply (Bucket A2). With `interactive`, always draft and wait. If `deep-fix` names this thread, send it through `/research-implement-review-report` instead, in every mode (see `deep-fix.md`). On the draft path, do not edit files.
- After the fix, the thread stays open until the push of its commit lands. Then the skill resolves the thread itself (`commit-push-resolve.md` § "Resolve threads and report"). A fix of this skill needs no manual step in the GitHub UI.

Example (small):

> Reviewer: `[ToFix] Rename FooID to FooId — matches the rest of this file.`
>
> Action: edit the file, build and test, commit, and reply: `**[AI]** Fixed: renamed FooID → FooId. Committed as a1b2c3d; will be included in the next push.`

### `[Performance]`

The workflow is the same as for `[ToFix]`, with two additions:

1. In the reply, name each effect that you can observe, for example `inner loop tightened, removes N allocations per request`.
2. If tests or benchmarks exist near the change, run them locally, and put the result in the chat log. If none exist, say so: `No benchmark covers this path — consider adding one if this is hot code.`

Never mark a `[Performance]` thread as done silently. Always state what you changed and what you did not measure.

### `[PX]` (`[P1]`, `[P2]`, `[P3]`, …)

A priority marker, not an action class. The action comes from the other tag, for example `[P1][ToFix]`. A `[PX]` tag alone counts as `[ToFix]` at the stated priority.

Priority order:

- `P1` and `P2`: process them first in each cycle. Never defer them.
- `P3` and lower priorities (`P4` and up): process them after the `P1` and `P2` threads. Never skip them.

### `[Suggestion]`

A concrete improvement. It does not block the approval of the PR.

- Trivial and small: implement it like `[ToFix]`. Reply `**[AI]** Applied suggestion: <summary>. Committed as <short-sha>; will be included in the next push.`
- Non-trivial, and the comment or the existing code settles the direction: implement it. State the direction and a one-line reason in the reply (Bucket A1).
- Non-trivial, and nothing settles the direction: draft the trade-off in chat. Then write a pending `**[AI][Draft]**` reply that sums up the pros and the cons (Bucket A2). With `autonomous`, implement it instead, and name the direction and the reason in the reply. Example reply: `**[AI][Draft]** Option A keeps the current shape; option B inlines the helper. Current preference: A because <one-line reason>. Happy to switch — your call.`
- With `interactive`, draft in both non-trivial cases.

### `[Optional]`

Close to `[Suggestion]`, but weaker. The reviewer means: if it is easy, do it. Else skip it.

- Trivial and small: implement it. Reply with explicit "optional accepted" words: `**[AI]** Applied optional suggestion: <summary>. Committed as <short-sha>; will be included in the next push.`
- Non-trivial, and the comment or the existing code settles the direction: implement it (Bucket A1). Use the same reply, and add the direction and a one-line reason.
- Non-trivial, and nothing settles the direction: reply `**[AI][Draft]** Optional — keeping current shape; happy to change if preferred. Reason: <one-line>.` Make no code edit. With `autonomous`, implement it instead, and name the direction and the reason in the reply (Bucket A2).
- With `interactive`, use the draft reply in both non-trivial cases.

Never block on `[Optional]`. Never push back hard. Principle 5 of `review-principles.md` applies here in both directions.

### `[Question]`

The reviewer wants an explanation. A wrong public answer under the identity of the author can mislead reviewers. So without `autonomous`, never post a `[Question]` reply without an explicit go-ahead of a human. With `autonomous`, post the answer directly as an `**[AI]**` reply (Bucket A2). Give it the same content as the draft format: a claim, the reasoning, and a citation. Leave out the draft-pending line.

- Read the related code before you answer. Do not build the answer from the comment alone.
- Draft format: a claim, the reasoning, and a citation (file and line range, an existing test, or linked documentation).
- Show the draft to the human in chat first. Ask: `Post this [Question] reply to T#<thread-id>? (yes / edit / skip)`.
- Only after `yes`, post `**[AI][Draft]** <answer in 1–3 short sentences>. See <file:line> / <test> / <doc link>.\n\n*Draft pending author confirmation.*` The reply joins the batch, and it posts with the other replies of the cycle.
- On `edit`, use the revision of the human, and ask again. If the `yes` comes after the batch posted, the reply follows the rule for a reply that misses its batch (Rules in `SKILL.md`).
- On `skip`, add the comment to `processedCommentIds` with `action: "skipped"` and `replyPosted: false`. Do not post.
- If you do not know the answer, say so. Show the uncertainty in chat, and ask the human. Never post a guess.

### `[ToDiscuss]`

The reviewer wants a conversation, not a fix. Never edit code.

- Sum up the positions in chat: the concern of the reviewer, your reading of the trade-off, and a proposed direction.
- Without `autonomous`, do not post a thread reply on your own. Ask the human: `This thread is tagged [ToDiscuss] — want me to draft a reply or wait for you to respond?`
- If the user asks for a reply, or with `autonomous` (Bucket A2), post a measured reply that frames the options and marks the uncertainty.

### `[OutOfScope]`

Never implement it in the current PR. The comment records a concern, or asks for tracking in a follow-up.

Decision tree:

1. The reviewer only notes it: reply `**[AI]** Noted, out of scope for this PR.` Do nothing more.
2. The reviewer asks for separate tracking, with words like `track it`, `open a ticket`, `file an issue`, `separate PR`, or `TODO`: hand it to Task Composer.

Issue flow:

1. Load Task Composer (the skill `dev-essentials:compose-task`) with the Skill tool, and draft the issue in its `mode: response`. The draft uses the comment text, the file, and the line. It also uses the reason that it is out of scope, and each priority hint from other tags. End the description with the line `Source: <htmlUrl>`, with the `htmlUrl` of the thread. This line is a required part of the issue body, so that the issue names the comment that it came from. The draft holds the title and the description. This step writes no file and makes no GitHub call.
2. Search for an existing issue of this thread. This search is a best effort. The issue search tool of the GitHub server matches by meaning, not by exact text. So it can miss an issue that has the URL in its body. Call `mcp__plugin_github_github__search_issues`. Pass the words of the draft title as `query`, and pass `owner` and `repo`. If the call fails, go to step 3 and tell the user that the search failed. Use no `is:open` or `is:closed` filter, so that the search finds open and closed issues. If the body of a result has the line `Source: <htmlUrl>`, use the number and the title of that issue. Ask no question, create no issue, and go to step 5.
3. Else, tell the user that the search found no issue for this thread, and ask before you create one: `No issue found for T#<commentId>. Create issue "<title>"? (yes / edit / skip)`. Without `autonomous`, this question also asks the user to approve the title and the type. If the reviewer or the user named a type, show it. With `autonomous`, take the title from the draft, and still ask this question (Bucket A2 in `SKILL.md`). Stage 2 records the question as an open item, and the orchestrating session asks it (see "Who talks to the user" in `SKILL.md`). On `edit`, use the changes of the user, keep the `Source` line, and ask again. If the user names an existing issue in the answer, use its number and its title, create no issue, and go to step 5. If the answer gives only the number, read the issue with `mcp__plugin_github_github__issue_read` for its title. On `skip`, follow the decline rule at the end of this section.
4. After `yes`, keep the approved fields, with the `Source` line in the description. Then wait for the batch of the cycle (`commit-push-resolve.md` § "When replies post"). Right before it posts, run the `mode: create` steps of Task Composer with the approved fields, `owner`, and `repo`. The `yes` of the user is the approval of `mode: create`. Pass `owner` and `repo` word for word, and never infer them (`dev-essentials:github-mcp-conventions` Rule 1). The steps create the issue. If the user named a parent, they link the issue to it. Then they read the issue back, and give its ID and its URL. Never call `mcp__plugin_github_github__issue_write` outside these steps.
5. Reply `**[AI]** Tracked as issue #<id>: <title>.` For a new issue, use only the ID and the title that Task Composer returns after its read-back. For an issue that step 2 or step 3 found, use its number and its title. The reply posts in the same batch.

The `Tracked as issue` reply is the record that stops a second issue for the same thread. A later run sees the reply and leaves the thread alone (`committed-fix-state.md`, `already-assessed`). The search of step 2 can miss an issue, so it does not stop a duplicate on its own. The issue and its reply come at the same point. If the batch does not post, Task Composer creates no issue. A later run then finds no reply and no issue, and runs this flow again. If the `mode: create` call fails, the reply of this thread does not post, and the other replies of the batch still post.

An issue can exist while its reply did not post. Then the entry of the thread keeps the issue number in `issueNumber` (`thread-state-schema.md`). The reply misses its batch (Rules in `SKILL.md`). The next try in the session uses that number, and Task Composer creates no second issue. A later run in a new session has only the search of step 2, which can miss the issue. Then the question of step 3 comes, and the user can name the existing issue.

With `no-reply`, no batch posts, so Task Composer creates no issue, also after an approval. The cycle log shows the thread as `issue pending` with the approved title, and says that `no-reply` held it.

If the user answers `skip`, declines, or wants to defer: reply `**[AI]** Noted — will not track separately yet.` Create no issue.

### `[Note]` and untagged comments

Information only. No code edit and no thread reply.

- Sum up the note in chat, so that the human sees it.
- If the `tags` parameter excludes `Note`, do not add the comment to `processedCommentIds`. Else add it with `action: "noted"`, so that the next cycle does not show it again.
- A note can hide an action, for example `btw, should we refactor X?`. Then show the ambiguity, and ask the human whether to classify the note again as `[Suggestion]` or `[Question]`.

### `[Repetition]`

The reviewer marks a pattern that occurs several times. The tag means: fix the whole pattern, not only this instance.

1. Find the underlying tag, usually `[ToFix]` or `[Suggestion]`.
2. Find every occurrence of the pattern in the diff of the PR, and not outside it. Keep to the scope of the PR.
3. Without `interactive`, apply the pattern fix at every occurrence (Bucket A1), and go to step 4. With `interactive`, show the pattern and the list of occurrences in chat, and ask: `Found N occurrences. Apply the pattern fix across all?`
4. After the fix at every occurrence, commit at once (Phase 4), and reply `**[AI]** Fixed pattern across N occurrences: <summary>. Committed as <short-sha>; will be included in the next push.`
5. With `interactive` and no approval: fix only the flagged instance, and reply `**[AI]** Fixed this instance. Waiting on your call for the remaining N−1.`

### Automated review comments (special case)

They take precedence over tags. Follow [`automated-review-verification.md`](automated-review-verification.md). In short:

- Always test the finding on your own. Do not trust the framing of the bot.
- Set one verdict: `valid`, `valid-but-narrow`, `needs-clarification`, `false-positive`, or `not-applicable`.
- For `valid` and `valid-but-narrow`, the obviousness test of that file decides the path: a direct implementation, a draft, or Stage 3 for `deep-fix` (§ "Obviousness test (Phase 3b step 5)"). **The size thresholds of this file do not apply to this path.**
- `needs-clarification`, `false-positive`, and `not-applicable` never get a code change, and never go to `deep-fix`.

## When multiple tags combine

Pick one action with these rules, in this order:

1. A `[PX]` tag sets only the priority. Leave it out of the next steps.
2. `[Note]` adds no action. If another tag is present, leave `[Note]` out.
3. A workflow tag decides the workflow: `[OutOfScope]` first, then `[Repetition]`. Use the other tags as the underlying tag, with steps 4 and 5.
4. Of the other tags, the tag that asks for the smaller code change wins. The order, from the smallest change: `[ToDiscuss]`, `[Question]`, `[Optional]`, `[Suggestion]`, then `[ToFix]` and `[Performance]`. The reviewer marked the change with the weaker tag, so do not do more than that tag asks.
5. If `[Performance]` is present, also apply its two additions (the effect in the reply, and the local benchmark run).

Examples:

- `[P1][ToFix]`: treat it as `[ToFix]` with priority P1 (process it first).
- `[Optional][Suggestion]`: treat it as `[Optional]`. The reply says clearly that the change is optional.
- `[ToFix][Optional]`: treat it as `[Optional]`, by step 4.
- `[Repetition][ToFix]`: the `[Repetition]` workflow, with `[ToFix]` as the underlying tag.
- `[OutOfScope][Suggestion]`: the `[OutOfScope]` workflow (never implement it in the current PR). Use the text of the suggestion in the brief for the follow-up issue.
- `[Performance][ToFix]`: the `[Performance]` workflow, with the explicit note on the effect in the reply.

## Fall-back rules

- No tag parses: `[Note]`.
- The size category is not clear: treat the change as Medium / Large, and follow that row of "Size thresholds for autonomy".
- The file of the thread (`filePath`) cannot be read, for example because it was renamed or moved: do not guess. Show the thread to the human in chat, and leave the comment unprocessed for the next cycle.
