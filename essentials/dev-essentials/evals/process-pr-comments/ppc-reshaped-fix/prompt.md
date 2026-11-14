---
description: "A reviewer marks one thread as ToFix, and the user changes the shape of the fix before the go-ahead of the push. The run must make the change as a new commit and post exactly one reply for the thread, in the batch right before the push. The reply must name the pushed commit and describe the new shape with itertools.islice, not the first fix."
tags: [process-pr-comments, mocks]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3000
---

Process the review comments of PR 42 in example-org/pager.

I am away during the run, so here are my answers to your questions in advance:

1. At your first go-ahead question for the push, my answer is: do not push yet. First change the fix of the `page_slice` thread. `page_slice` must also accept a generator, so return `list(itertools.islice(items, start, start + size))` instead of a list slice. Make the change as a new commit.
2. When you then show me the changed reply and the commit list, my answer is: push, and post the replies.
