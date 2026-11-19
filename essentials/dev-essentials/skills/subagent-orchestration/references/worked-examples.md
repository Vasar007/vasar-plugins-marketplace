# Worked examples

Real failures and the correct pattern for each. `SKILL.md` has the rules. This file shows how each rule applies.

## Rule 1: a bundled review loop

An orchestrating session dispatched ONE subagent with a brief of seven steps:

1. Research the patterns behind a design decision.
2. Pick a design.
3. Implement it.
4. Build and test.
5. Commit as one commit.
6. Run `dev-essentials:review-loop` on everything since a given baseline, and amend its fixes into that commit.
7. Do not push.

The session then told the user that the implementation subagent had steps 1-5. It also said that the review loop (step 6) comes after the completion notification of that subagent.

This one dispatch had two defects:

- Step 6 is an orchestration phase, because it fans out to a reviewer and a fixer. So it was the next dispatch of the orchestrator, after the implementation report arrived. In the brief of the implementer, it became `main → implementer → reviewer + fixer`, with no checkpoint for the orchestrator between the implementation and the review.
- The summary claimed the scope of steps 1-5, but the prompt also held steps 6 and 7.

Correct pattern: dispatch steps 1-5, receive the report, and check the commit. Then dispatch the review loop as the next phase of the orchestrator. Report the scope as steps 1-5 only, because the brief said only that.

## Rule 4: a thread fetch in the main agent

The main agent dispatched a subagent that only checks the threads. This was correct. The user then said "post replies (DO IT by yourself) and push (1 command, do it by yourself)". So the exception for an explicit ask applied. The main agent ALSO fetched the full thread list inline (the full response, 5 threads) to get the timestamps for the reply anchors. This was the mistake. It filled the main context with data that the subagent can return.

Correct pattern: the subagent that checks the threads also returns the timestamps in its structured report. The main agent receives only the small summary. Then it posts the replies itself (the explicit ask), or it dispatches another subagent to post them.

## Rule 7: a worktree cleanup

An orchestrating session loaded `dev-essentials:git-worktree-management`. It then dispatched a subagent to remove a merged worktree and its branch for a completed task. This was correct. The whole brief of that subagent WAS the concrete work: find out whether the branch is merged, keep anything worth keeping, run `git worktree remove`, and delete the branch.

But the subagent dispatched another subagent for exactly that scope. It reported that a new subagent now ran the worktree and branch cleanup, and that it was to report back at the end.

The actual chain was `main → agent → agent`. The correct chain is `main → agent`, and that agent does the removal itself. The inner dispatch had no decomposition: the same scope, the same paths, one extra hop, and no work by the agent that owned the task.
