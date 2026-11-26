# The Fields of a New Pull Request

Do these steps right after a workflow opens a pull request on GitHub. They set three fields of the pull request: the assignee, the labels, and the Project. Follow `dev-essentials:github-mcp-conventions` in each call.

Take `owner`, `repo`, and the number of the pull request from its URL, for example `https://github.com/<owner>/<repo>/pull/<number>`. The create tool gives this URL as `url`, and `gh pr create` prints it. The `id` of the create result is not the number.

A field that the steps cannot set does not stop the run, because the pull request exists. Go on with the next step of the workflow. The report of the workflow names each field that the run did not set, with the reason.

A tool that the session lists with only its name counts. Load it with `ToolSearch`. If the session has no GitHub MCP tools, skip each MCP call of these steps, and use the `gh` commands of this file. Name each field that they cannot set. Do not ask the user to reconnect.

## The assignee

The assignee is the user that opened the pull request. The read of step 1 of the section "Set the assignee and the labels" gives this user as `user.login`. For `gh`, the assignee is `@me`.

## The labels

The labels come from the GitHub issue of the task. If the task is not a GitHub issue, the pull request gets no labels. Never create a label, and never add a label that the issue does not have.

1. Read the labels of the issue: call `mcp__plugin_github_github__issue_read` with `method: "get_labels"`. Pass the `owner`, the `repo`, and the `issue_number` of the issue, as the task names them (Rule 1). One call gives up to 100 labels. If the run already read the issue, use the labels of that read.
2. If the issue is in the repository of the pull request, keep each label.
3. If the issue is in another repository, keep only the labels that the repository of the pull request has. If you have `mcp__plugin_github_github__list_label`, list the labels of that repository (Rule 3). Else, call `mcp__plugin_github_github__get_label` for each label. The match of a name ignores case. Pass the spelling of that repository.
4. Name each label that you did not keep in the report.
5. If a read of this section fails, fix the call, and make it one more time. If it fails again, name each label that the read did not give as not set, with the error. Then go on with the next section.

## Set the assignee and the labels

1. Call `mcp__plugin_github_github__pull_request_read` with `method: "get"`, `owner`, `repo`, and `pullNumber` set to the number of the pull request. Take its `labels`, its `assignees`, and its `user.login`.
2. Call `mcp__plugin_github_github__issue_write` with `method: "update"`, `issue_number` set to the number of the pull request, `owner`, and `repo`. For the issues API, a pull request is an issue. The update replaces the old lists. So pass `assignees` set to the assignees of step 1 and the `user.login` of step 1. Pass `labels` set to the labels of step 1 and the kept labels. Pass no repeated name. Leave out a list with no name. Do not skip this call. A read of step 1 that already shows each name is no reason to skip it.
3. If the call of step 1 or step 2 fails, fix the call, and make it one more time. If it fails again, or if the session has no such tool, use `gh`. This step names its own `gh` command, and Rule 5 lets such a step win: `gh pr edit <number> --repo <owner>/<repo> --add-assignee @me --add-label "<label>,<label>"`. Leave out an option with no value.
4. If `gh` fails too, try no other command. Name the assignee and the labels as not set, with the error. Skip step 5.
5. Read the pull request one more time, as in step 1. If the read fails, name the assignee and the labels as unknown, with the error. Else, name each assignee and each label that the read does not show as not set. Without push access to the repository, GitHub drops these changes and gives no error.

## The Project

No GitHub MCP tool lists the Projects that a repository links. So step 1 uses `gh`, as Rule 5 allows.

1. List the Projects of the repository: `gh repo view <owner>/<repo> --json projectsV2 --jq '.projectsV2.Nodes[] | [.number, .title] | @tsv'`.
2. If the list is empty, the repository has no Project. Say so in the report. This is not a field that the run failed to set.
3. If the list has more than one Project, do not choose one. Name the Project as not set, and list the titles.
4. If the list has one Project and the session has `mcp__plugin_github_github__projects_write`, call it with `method: "add_project_item"`. Pass `owner` and `item_owner` set to the owner of the repository, and `item_repo` set to its name. Pass `project_number` set to the number of the Project, `item_type` set to `pull_request`, and `pull_request_number` set to the number of the pull request. If the call fails, fix it, and make it one more time. If it fails again, do step 5.
5. If the list has one Project, and the session has no such tool or the call of step 4 failed twice, run `gh pr edit <number> --repo <owner>/<repo> --add-project "<title>"`.
6. If the list fails because the token lacks a scope, name the Project as unknown, with the error. The repository can have a Project that the run cannot read.
7. If another call or command fails, try no other command, and do not run `gh auth refresh`. Name the Project as not set, with the error. For example, `gh` needs the `project` scope of the token to add a pull request to a Project.

Name each `gh` command of these steps and its reason in the report, as Rule 5 says.
