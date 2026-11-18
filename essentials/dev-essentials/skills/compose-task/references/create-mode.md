# Creating in GitHub (`mode: create`): Verified Create, Then Confirm Relationships

Step 3 of `SKILL.md` points here.

**Mandatory verification:** `create` mode always creates, then reads back. Never report a result that did not come from the API.

**Pre-flight conditions.** Both must be true. If one is false, stop.

- The user explicitly asked for or approved `mode: create`, or used equivalent words ("publish", "create issue", "add to GitHub"). A calling skill can give this approval for the user: the user ran that skill in the full mode of `dev-essentials:work-modes`, and the brief says so.
- The user gave the explicit GitHub **`owner/repo`** pair. Never infer it from context, from the git remote, or from the session state (see `dev-essentials:github-mcp-conventions` Rule 1). If `owner/repo` is missing, stop and ask for it. Do not guess.

**Step 1: Create the issue. If the user asked for a parent, attach it in the same call.**

Call `mcp__plugin_github_github__issue_write` with `method: "create"` and:

- `owner`: user-supplied owner, verbatim
- `repo`: user-supplied repo, verbatim
- `title`: from user or draft H1
- `body`: full content in Markdown (H2 sections, bullets) **without** the H1 title (GitHub renders its own title field)
- `labels`: the labels that the user gave, and each other label that fits the issue. Do this for every issue, with a type or without one. Pass only labels that exist in the repository (see the label steps below). Without labels, leave it out.
- `type`: the issue type that the user gave or approved, for example `Bug` or `Task`. Without a type, leave it out. Before the create call, call `mcp__plugin_github_github__list_issue_types` with the `owner` and the `repo`. If the list has the type, pass it with the spelling of the list. If the call fails, or the list does not have the type, leave `type` out. Say so in the report of Step 3. Then the labels also get the label with the name of the type (see the label steps below).

  Never create a label. Before the create call, choose the labels:

  1. Start with the labels that the user gave, and add each label that fits the issue. If the call failed or the list lacks the type, also add the label with the name of the type. Example: `bug` for the type `Bug`. The match of the name ignores case.
  2. If you have `mcp__plugin_github_github__list_label`, list the labels of the repository with the `owner` and the `repo`. Follow the pagination rule (`dev-essentials:github-mcp-conventions` Rule 3). Add each listed label that fits the issue. Keep only the labels that the list has.
  3. Else, call `mcp__plugin_github_github__get_label` with the `owner`, the `repo`, and the `name` of each label from step 1. Keep only the labels that it finds.
  4. In the report of Step 3, name each label that you did not keep.
- `parent_issue_number`: the number of the parent issue. Pass it only for a task that the user asked for as a sub-issue of an existing issue. The create call attaches the new issue to this parent in the same operation, so the normal case needs no separate link call. If the parent issue is in another repository, also pass `parent_owner` and `parent_repo`. Else leave both out, and `owner`/`repo` apply.

If the call returns an error, report it honestly. Do not go on to Step 2.

**Step 2: Read the issue back, and confirm each requested relationship.**

Call `mcp__plugin_github_github__issue_read` with `method: "get"`. Pass the `owner`, the `repo`, and the `issue_number` from Step 1.

Find out whether the response matches:

- Title matches what was submitted
- Body matches (sample the first 200 characters)
- Labels are set (if passed)
- Type is set (if passed)

If Step 1 passed `parent_issue_number`, do not trust the `parent` and `sub_issues_summary` fields of this `get` response. The tool description calls them best-effort and optional. Call `mcp__plugin_github_github__issue_read` again with `method: "get_parent"` on the new issue:

- If `get_parent` returns the expected parent issue, the relationship is confirmed.
- If it returns no parent or a different one, the attach did not take effect. Do not report the link as set up. Either set it up yourself, or report the discrepancy to the user. To set it up, call `mcp__plugin_github_github__sub_issue_write` with `method: "add"`. Pass `issue_number` (the number of the parent) and `sub_issue_id` (the `id` of the new issue from the Step 1 response, not its issue number). Then read it again with `get_parent`.

If any call above fails or the item does not match, report the discrepancy honestly. Never cover it with a fabricated success.

**Step 3: Report.**

Report the real issue number and the real `html_url` from the read-back response. If the user asked for a parent link, state plainly whether `get_parent` confirmed it. The echoed `parent_issue_number` of the create call is not proof of a link. Never construct or invent a URL. The URL comes from the API response only.
