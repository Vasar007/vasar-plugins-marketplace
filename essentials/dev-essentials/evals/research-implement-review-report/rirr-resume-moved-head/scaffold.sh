#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
printf 'notes/\n' >> .gitignore
fixture_commit "ignore the notes folder"
fixture_publish main

# The state after Phase 4 of an earlier run: the change is committed on a branch that no remote holds.
git checkout -q -b work/retry-limit
sed -i 's/^HTTP_RETRY_LIMIT = 5$/HTTP_RETRY_LIMIT = 3/' config/settings.py
sed -i 's/(retries=5)/(retries=3)/' tests/test_http_client.py
fixture_commit "lower the HTTP retry limit to 3"

# The plan and the report of the earlier run, in the ignored notes folder.
fixture_write notes/Plans/retry-limit-plan.md <<'PLAN_EOF'
# Plan: lower the HTTP retry limit of the users app

## Tasks

- [x] Task 1: In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit. Run `python3 -m unittest discover -s tests`, and commit the task.
PLAN_EOF
fixture_write notes/Results/retry-limit-report.md <<'REPORT_EOF'
# Report: lower the HTTP retry limit of the users app

## Overview

- **Branch**: work/retry-limit
- **Base branch**: main
- **Head commit**: HEAD_SHA
- **Worktree**: none, the main work tree
- **Plan**: notes/Plans/retry-limit-plan.md

## What Was Done

- Task 1: `HTTP_RETRY_LIMIT` is 3, and `tests/test_http_client.py` expects 3. The tests pass.
- Review loop: one round. Verdict `stop-clean`. No finding.

## What's Next

The branch is not pushed. The final gate asked about the push, the pull request, and the merge, and the answer was no.
REPORT_EOF
# The head commit is the head of the branch at the end of the earlier run.
sed -i "s/HEAD_SHA/$(git rev-parse HEAD)/" notes/Results/retry-limit-report.md

# After the earlier run, a commit that no review loop saw moved the head of the branch. So the head differs from the report.
sed -i 's/^TIMEOUT_SECONDS = 30$/TIMEOUT_SECONDS = 60/' config/settings.py
fixture_commit "raise the HTTP timeout to 60 seconds"
