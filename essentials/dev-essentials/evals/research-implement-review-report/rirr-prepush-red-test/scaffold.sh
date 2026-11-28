#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
# The commit of the earlier run lowers the limit but leaves the test at 5, so the tests fail at the finish step.
# The mock of pull_request_read gives that commit as the head. The main branch of the remote is the base of the branch.
printf 'notes/\n' >> .gitignore
fixture_commit "ignore the notes folder"
fixture_publish main

git checkout -q -b work/retry-red
sed -i 's/^HTTP_RETRY_LIMIT = 5$/HTTP_RETRY_LIMIT = 3/' config/settings.py
fixture_commit "lower the HTTP retry limit to 3"

fixture_write notes/Plans/retry-red-plan.md <<'USERS_EOF'
# Plan: lower the HTTP retry limit of the users app

## Tasks

- [x] Task 1: In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit. Run `python3 -m unittest discover -s tests`, and commit the task.
USERS_EOF
fixture_write notes/Results/retry-red-report.md <<'USERS_EOF'
# Report: lower the HTTP retry limit of the users app

## Overview

- **Branch**: work/retry-red
- **Base branch**: main
- **Head commit**: HEAD_SHA
- **Worktree**: none, the main work tree
- **Plan**: notes/Plans/retry-red-plan.md

## What Was Done

- Task 1: `HTTP_RETRY_LIMIT` is 3.
- Review loop: one round. Verdict `stop-clean`. No finding.

## What's Next

The branch is not pushed. The final gate asked about the push, the pull request, and the merge, and the answer was no.
USERS_EOF
sed -i "s/HEAD_SHA/$(git rev-parse HEAD)/" notes/Results/retry-red-report.md
