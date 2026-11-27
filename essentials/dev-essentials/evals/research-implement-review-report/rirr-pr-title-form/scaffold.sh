#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
printf 'notes/\n' >> .gitignore
fixture_commit "ignore the notes folder"
# The PR template of the repository. Its rules are only in HTML comments. cmp-pr-repo-template plants the same file with one more check box line.
fixture_write .github/pull_request_template.md <<'TEMPLATE_EOF'
<!--
Title: write it as `type(scope): summary`. The type is one of feat, fix, refactor, docs, test, or chore. The scope is the area of the code, in lower case. Example: `fix(parser): keep the last line of a file`.
-->

## Problem

<!-- Say what was wrong or missing, and who met it. Use at most two sentences. -->

## Fix

<!-- List the main changes, one short bullet for each. -->

## Evidence

<!-- Name the tests that cover the change. Paste the test command that you ran and the last lines of its output. -->

<!-- If an AI agent wrote this pull request, end it with one line that names the agent tool and the model. -->
TEMPLATE_EOF
fixture_commit "add the pull request template"
fixture_publish main

# The state after Phase 4 of an earlier run: the change is committed on a branch that no remote holds.
# A run makes a commit with another SHA each time. So the scaffold makes this commit, and a test pins its SHA in the mock.
git checkout -q -b work/retry-title
sed -i 's/^HTTP_RETRY_LIMIT = 5$/HTTP_RETRY_LIMIT = 3/' config/settings.py
sed -i 's/(retries=5)/(retries=3)/' tests/test_http_client.py
fixture_commit "lower the HTTP retry limit to 3"

# The plan and the report of the earlier run, in the ignored notes folder.
fixture_write notes/Plans/retry-title-plan.md <<'PLAN_EOF'
# Plan: lower the HTTP retry limit of the users app

## Tasks

- [x] Task 1: In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit. Run `python3 -m unittest discover -s tests`, and commit the task.
PLAN_EOF
fixture_write notes/Results/retry-title-report.md <<'REPORT_EOF'
# Report: lower the HTTP retry limit of the users app

## Overview

- **Branch**: work/retry-title
- **Base branch**: main
- **Head commit**: HEAD_SHA
- **Worktree**: none, the main work tree
- **Plan**: notes/Plans/retry-title-plan.md
- **Task**: the request of the user, to lower the HTTP retry limit of the users app from 5 to 3

## What Was Done

- Task 1: `HTTP_RETRY_LIMIT` is 3, and `tests/test_http_client.py` expects 3. The tests pass.
- Review loop: one round. Verdict `stop-clean`. No finding.

## What's Next

The branch is not pushed. The final gate asked about the push, the pull request, and the merge, and the answer was no.
REPORT_EOF
# The head commit is the head of the branch at the end of the earlier run. It has the SHA that the mock gives as the head of the pull request.
sed -i "s/HEAD_SHA/$(git rev-parse HEAD)/" notes/Results/retry-title-report.md
