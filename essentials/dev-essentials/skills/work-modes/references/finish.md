# Finish: Push, Pull Request, Merge

These are the finish steps of the workflows `research-implement-review-report`, `implement-task`, and `implement-batch`.

Read this file at the finish step of each run.

## When the steps run

- In the full mode, do the steps with no question.
- In the partial mode and in the interactive mode, the final gate comes after the final report. Show the verdict of each review loop of the run. Then ask one question: "Push the branch, open a pull request, and merge it after the gate of merge-pr? (yes / push and pull request only / no)". Do no step before the answer. With "push and pull request only", skip step 5. With "no", do no step.

If the end of the run has another question, for example the cleanup question of `save-context`, ask both questions in one message.

An instruction of the user outranks the mode (hard stop 7 of `dev-essentials:work-modes`). If the request forbids the push, do no step, and do not look for the repository. If the request forbids only the merge, skip step 5.

## The repository

`owner` and `repo` name the GitHub repository that gets the pull request. Take them from the first source that names them:

1. The request of the user: `owner/repo` in words, or a GitHub URL of the repository, of an issue, or of a pull request. Parse a URL as Rule 1 of `dev-essentials:github-mcp-conventions` says.
2. Outside the interactive mode: the `origin` remote, by the exception in Rule 1 of `dev-essentials:github-mcp-conventions`. If `git remote get-url origin` prints no URL of `github.com`, do not use it.

Step 3 pushes to `origin`, so only the repository of `origin` holds the branch of the pull request. In a fork clone with no other remote, the pull request goes to the fork.

If the request names no repository, and no remote of the clone is on `github.com`, ask no question, and do no step. The finish report says which steps did not run, and why. This holds in every mode.

These cases are hard stop 6 of `dev-essentials:work-modes`. Ask the user, and do no step before the answer:

- Another remote of the clone names a repository on `github.com`, for example the `upstream` remote of a fork.
- The request names a repository, and `origin` names another repository on `github.com`.

Where this file says not to look for the repository, skip this section. In the full mode, find the repository before the first step of the workflow. In the other modes, find it at the final gate, before its question. The interactive mode asks for a missing repository in the question of the final gate.

## Steps

1. Make sure that each start condition holds. If one fails, do no later step, and report it (hard stop 5):
   - Each review loop of the run ended `stop-clean`, or `stop-max-rounds` with no open blocking finding.
   - The branch is not the default branch of `origin`, and it is not the base branch of the run.
   - No tracked file has an uncommitted change.
2. Run the build and the tests one time, as item 1 of the section `Trust but verify` in `dev-essentials:subagent-orchestration` says. If the build or a test fails, do no later step, and report it (hard stop 5). The full mode gives a fix round before the report to a failure of this run that the change of the branch causes. An example is a test that still expects the old behavior of changed code. A missing tool, a network error, or a time-out is not such a failure. A failure of another command, such as a lint script that no instructions file names, gets no fix round. Fix the cause in a new commit, and review it as step 3 of the section "A failed merge gate" says. Then do steps 1 and 2 again. Do at most 2 such rounds. Make no other commit before the push. A failed merge gate gets its fix in the section "A failed merge gate".
3. Push with `git -C "<work tree>" push -u origin <branch>`. Never force the push, and never pass `--no-verify`. If the push fails, do not push again with other options. Report the error and the local state, and end the run. A push protection block is hard stop 4.
4. Open the pull request:
   1. Look for an open pull request of the branch. Call `mcp__plugin_github_github__list_pull_requests` with `owner`, `repo`, `head` set to `<owner>:<branch>`, `state` set to `open`, and `perPage` set to `30`. Follow `dev-essentials:github-mcp-conventions` in each call of this step. If a found pull request has the base branch of the run as its base, use it. Skip the rest of step 4, and say so in the finish report. If each found pull request has another base, do no later step. Outside the full mode, ask the user (hard stop 6). In the full mode, report it, and end the run (hard stop 5).
   2. Dispatch the agent `dev-essentials:pr-composer`. Give it the absolute path of the work tree, the base branch, the branch, and the task text. Also give the paths of the plan files and of the report of the run. Also give the test command of step 2 and its result line. If the task is a GitHub issue of this repository, also give its closing line, for example `Closes #42.`. The agent returns the body.
   3. If the agent returns a question or no body, and the mode is not full, ask the user (hard stop 6). In the full mode, dispatch the agent one more time, and tell it to write the body from the facts that it has. Tell it to mark each open point with `Not confirmed:`. If it still returns no body, report the pushed branch, and end the run (hard stop 5).
   4. Write a title of at most 72 characters. A form for titles can come from the instructions file of the repository, or from the PR template that the agent names in its reply. If the reply names a template but quotes no rule for titles, read the template. If one of these sources gives a form, write the title in that form. Else write the title from the summary of the change in the body. For a body with no template, this is the section `## What`.
   5. Call `mcp__plugin_github_github__create_pull_request` with `owner`, `repo`, `base` (the base branch of the run), `head` (the branch), `title`, and `body`.
   6. If the call fails, report the error and the pushed branch, and end the run.
   7. Set the fields of the new pull request: do the steps of `skills/github-mcp-conventions/references/pull-request-fields.md` of this plugin. From the base folder of this skill, its path is `../github-mcp-conventions/references/pull-request-fields.md`. If the task is a GitHub issue, it is the issue of these steps. A field that these steps cannot set is no failed step. Then do step 5, unless this file says to skip step 5.
5. Load `dev-essentials:merge-pr` with the `Skill` tool, and do its steps for the pull request. The full mode of the run, or the yes of the final gate, is the approval that its section "Approval" asks for. If its gate fails, it does not merge, and the pull request stays open. Then do the section "A failed merge gate".

## A failed merge gate

Sort each failed item of the report of `merge-pr`. These items are fixable:

- A red check that fails in a local run of its command too. Take the command from the CI configuration of the repository or from the log of the failed job. Its output names at least one file or test, and each of them is one that the branch changed (`git diff --name-only origin/<base branch>...HEAD`).
- The merge state `behind` or `dirty`.

If a fixable red check fails, the merge state `unstable` or `blocked` of the same read is part of that item.

Each other item is a stop, for example a change request, a missing approval, or open review threads. A check with no command in these sources and local commits that the head lacks are stops too. A check that reports a secret or a security alert is hard stop 4. A local run of it does not change this. If one failed item is a stop, report each item, and end the run (hard stop 5).

If each failed item is fixable, do a fix round:

1. In the interactive mode, report each item with its evidence, and ask "Fix the cause in this run? (yes / no)". With "no", end the run.
2. Fix the cause in new commits, as the workflow does a task of its plan. For `behind` or `dirty`, run `git fetch origin <base branch>`, merge `origin/<base branch>` into the branch, and resolve each conflict. Never rebase.
3. Review the new commits with `dev-essentials:review-loop target=diff <head before the round>..HEAD --rounds=1`. After a merge with a conflict, use `target=branch`. A merge with no conflict needs no review. Then do steps 1 and 2 of the section "Steps" again, and run the command of each fixed check again. If it fails, report it, and end the run (hard stop 5).
4. Outside the full mode, report the fix, and ask "Push the fix, and merge after the gate of merge-pr? (yes / no)". With "no", end the run.
5. Push as step 3 of the section "Steps" says, and do step 5 of that section again.

Do at most 2 fix rounds. If the gate still fails, report it, and end the run (hard stop 5).

## A failed step in the full mode

A failed step is hard stop 5 of `dev-essentials:work-modes`. Ask no question. Report the state, and end the run. For a failed merge gate, first do the section "A failed merge gate". Do no other step again.

## Resume

The user can ask a workflow to finish an earlier run. The request names the report of that run, or its branch. Then skip the other steps of the workflow. Check out that branch, or work in the worktree that holds it (`git worktree list`). Do the steps of this file from step 1. Take the report of the earlier run from a file or from this conversation. It must give the verdict of each review loop and the head commit at the end of that run. The head of the branch must be that commit. If a fact is missing, or no report exists, or the head differs, do no step. Outside the full mode, ask the user (hard stop 6). In the full mode, report the state, and end the run (hard stop 5).

## The finish report

Print the finish report after the final report of the workflow. It lists:

- The repository, and its source: the request or the `origin` remote.
- The result of each step: the build and the tests, the push, the pull request with its number and its URL, and the report of `merge-pr`.
- Each field of the pull request that the run did not set, with the reason.
- Each step that did not run, with the reason.
- Each fix round: the failed items, the fix commits, the verdict of its review, and the push or the answer to the push question.
- When a worktree was removed: the archive folder of the files of the run.
