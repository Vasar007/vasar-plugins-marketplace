#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
printf 'notes/\n' >> .gitignore
fixture_commit "ignore the notes folder"
fixture_publish main

# The state after Step 5 of an earlier run of implement-batch: two task commits on a branch that no remote holds.
# A run makes a commit with another SHA each time. So the scaffold makes these commits, and a test pins the head SHA in the mock.
git checkout -q -b work/retry-batch
sed -i 's/^HTTP_RETRY_LIMIT = 5$/HTTP_RETRY_LIMIT = 3/' config/settings.py
sed -i 's/(retries=5)/(retries=3)/' tests/test_http_client.py
fixture_commit "lower the HTTP retry limit to 3"
sed -i 's/^TIMEOUT_SECONDS = 30$/TIMEOUT_SECONDS = 10/' config/settings.py
fixture_commit "lower the HTTP timeout to 10 seconds"

# The plans and the report of the earlier run, in the ignored notes folder.
fixture_write notes/Plans/retry-batch-task-1-plan.md <<'PLAN_EOF'
# Plan of task 1: lower the HTTP retry limit of the users app

- [x] In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit. Run `python3 -m unittest discover -s tests`.
PLAN_EOF
fixture_write notes/Plans/retry-batch-task-2-plan.md <<'PLAN_EOF'
# Plan of task 2: lower the HTTP timeout of the users app

- [x] In `config/settings.py`, set `TIMEOUT_SECONDS` to 10. Run `python3 -m unittest discover -s tests`.
PLAN_EOF
fixture_write notes/Results/retry-batch-report.md <<'REPORT_EOF'
# Report: two HTTP settings of the users app

## Overview

- **Branch**: work/retry-batch
- **Base branch**: main
- **Head commit**: HEAD_SHA
- **Worktree**: none, the main work tree
- **Plans**: notes/Plans/retry-batch-task-1-plan.md, notes/Plans/retry-batch-task-2-plan.md

## Tasks

- Task 1: `HTTP_RETRY_LIMIT` is 3, and `tests/test_http_client.py` expects 3. Review loop: one round. Verdict `stop-clean`. No finding. Commit: "lower the HTTP retry limit to 3".
- Task 2: `TIMEOUT_SECONDS` is 10. Review loop: one round. Verdict `stop-clean`. No finding. Commit: "lower the HTTP timeout to 10 seconds".

## Batch

- Final review across the 2 tasks: one round. Verdict `stop-clean`. No finding, so no final-review commit.
- Commit topology: 2 task commits on top of main.
- Build and tests at the head commit: `python3 -m unittest discover -s tests` passes.

## What's Next

The branch is not pushed. The final gate asked about the push, the pull request, and the merge, and the answer was no.
REPORT_EOF
# The head commit is the head of the branch at the end of the earlier run. It has the SHA that the mock gives as the head of the pull request.
sed -i "s/HEAD_SHA/$(git rev-parse HEAD)/" notes/Results/retry-batch-report.md
