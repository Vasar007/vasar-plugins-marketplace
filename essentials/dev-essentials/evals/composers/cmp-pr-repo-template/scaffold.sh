#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"

# The prompt gives the diff, and the session has no shell. So the repository holds only the PR template on main.
# The rules of the template are only in HTML comments. rirr-pr-title-form plants the same file, and a test makes sure of it.
fixture_init
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

- [ ] The tests ran and passed.

<!-- If an AI agent wrote this pull request, end it with one line that names the agent tool and the model. -->
TEMPLATE_EOF
fixture_commit "add the pull request template"
git checkout -q -b user/tasks/12-customer-index
