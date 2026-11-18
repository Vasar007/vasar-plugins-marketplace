# Finish: Push, Pull Request, Merge

These are the finish steps of three workflows: `research-implement-review-report`, `implement-task`, and `implement-batch`. The steps push the branch, open a pull request, and merge it after the gate of `dev-essentials:merge-pr`. Each workflow names the step where they run. `feature-pipeline` keeps its own Step 9 and Step 9b, and `process-pr-comments` keeps its own push.

Read this file at the finish step of each run. Read it again in a later run of the same session.

## Who does the steps

A workflow does the finish steps one time, at its own end. When a workflow runs another workflow as one of its steps, only the caller does them. `implement-task` runs `research-implement-review-report`, and so does the `deep-fix` of `process-pr-comments`. In both cases, `research-implement-review-report` skips its finish step.

## When the steps run

- In the full mode, do the steps with no question.
- In the partial mode and in the interactive mode, the final gate comes after the final report. Show the verdict of each review loop of the run. Then ask one question: "Push the branch, open a pull request, and merge it after the gate of merge-pr? (yes / push and pull request only / no)". Do no step before the answer. With "push and pull request only", skip step 5. With "no", do no step.
- If the end of the run has another question, for example the cleanup question of `save-context`, ask both questions in one message.
- An old spelling can approve less. `dev-essentials:work-modes` says how to read it. For the old flag `--push`, do steps 1 to 3 with no question, and skip the question, step 4, and step 5.
- An instruction of the user outranks the mode (hard stop 7 of `dev-essentials:work-modes`). If the request forbids the push, do no step, and do not look for the repository. If the request forbids only the merge, skip step 5.

## The repository

`owner` and `repo` name the GitHub repository that gets the pull request. Take them from the first source that names them:

1. The request of the user: `owner/repo` in words, or a GitHub URL of the repository, of an issue, or of a pull request. Parse a URL as Rule 1 of `dev-essentials:github-mcp-conventions` says.
2. Outside the interactive mode: the `origin` remote, by the exception in Rule 1 of `dev-essentials:github-mcp-conventions`. If `git remote get-url origin` prints no URL of `github.com`, do not use it. Report the value as taken from the remote.

Step 3 pushes to `origin`, so only the repository of `origin` holds the branch of the pull request. So the remote is a safe source here. `feature-pipeline` does not use it, because its project context names the repository.

These cases are hard stop 6 of `dev-essentials:work-modes`. Ask the user, and do no step before the answer:

- No source names a repository.
- Another remote of the clone names a repository on `github.com`, for example the `upstream` remote of a fork. Then the target of the pull request is not clear.
- The request names a repository, and `origin` names another repository on `github.com`.

In the full mode, find the repository before the first step of the workflow. Then a question comes while the user is still there. In the other modes, find it after the answer of the final gate. If the request names no repository in the interactive mode, ask for it in the question of the final gate.

## Steps

1. Make sure that each start condition holds. If one fails, do no later step, and report it (hard stop 5):
   - Each review loop of the run ended `stop-clean`, or `stop-max-rounds` with no open blocking finding.
   - The branch is not the default branch of `origin`, and it is not the base branch of the run.
   - No tracked file has an uncommitted change.
2. Run the build and the tests one time, as item 1 of the section `Trust but verify` in `dev-essentials:subagent-orchestration` says. If the build or a test fails, do no later step, and report it (hard stop 5).
3. Push with `git -C "<work tree>" push -u origin <branch>`. Never force the push, and never pass `--no-verify`. If the push fails, do not push again with other options. Report the error and the local state, and end the run. A push protection block is hard stop 4.
4. Open the pull request:
   1. Dispatch the agent `dev-essentials:pr-composer`. Give it the absolute path of the work tree, the base branch, the branch, and the task text. Also give the paths of the plan files and of the report of the run. If the task is a GitHub issue of this repository, also give its closing line, for example `Closes #42.`. The agent returns the body. If it returns a question or no body, ask the user (hard stop 6).
   2. Write a title of at most 72 characters from the section `## What` of the body.
   3. Call `mcp__plugin_github_github__create_pull_request` with `owner`, `repo`, `base` (the base branch of the run), `head` (the branch), `title`, and `body`. If the tool is not loaded, load it with `ToolSearch` first. Follow `dev-essentials:github-mcp-conventions`.
   4. If the call fails, do not call it again. Report the error and the pushed branch, and end the run.
5. Load `dev-essentials:merge-pr` with the `Skill` tool, and do its steps for the new pull request. The full mode of the run, or the yes of the final gate, is the approval that its section "Approval" asks for. Its Step 2 waits for the checks that still run, up to its time limit. If its gate fails, it does not merge, and the pull request stays open. Its Step 4 does the steps after the merge. Before it removes a worktree, Workflow C of `dev-essentials:git-worktree-management` archives the files of the run.

## A failed step in the full mode

A failed step is hard stop 5 of `dev-essentials:work-modes`. Ask no question. Report the state, and end the run:

- A failed push: the branch and its commits stay local.
- A failed call for the pull request: the branch is pushed, and no pull request exists.
- A failed merge gate: red checks, a change request, a merge state that is not clean, or checks that still run at the end of the wait. The pull request stays open. Name the failed item from the report of `merge-pr`.

Do not repair the cause, and do not do a step again.

## Resume

The user can ask a workflow to finish an earlier run. Examples are a run with the answer "no" at the final gate, and a run with a failed step. The request names the report of that run, or its branch. Then skip the other steps of the workflow. Check out that branch, or work in the worktree that holds it (`git worktree list`). Do the steps of this file from step 1. The report of the earlier run gives the verdict of each review loop. If no report gives a verdict, ask the user (hard stop 6). If the request or the report names an open pull request of the branch, skip step 4, and use that pull request.

## The finish report

Print the finish report after the final report of the workflow. It lists:

- The repository, and its source: the request or the `origin` remote.
- The result of each step: the build and the tests, the push, the pull request with its number and its URL, and the report of `merge-pr`.
- Each step that did not run, with the reason.
- When a worktree was removed: the archive folder of the files of the run.
