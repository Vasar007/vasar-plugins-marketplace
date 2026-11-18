#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
printf 'notes/\n' >> .gitignore
fixture_commit "ignore the notes folder"
fixture_publish main
# The plan file is in the ignored notes folder, so no commit holds it.
fixture_write notes/Plans/retry-limit-plan.md <<'PLAN_EOF'
# Plan: lower the HTTP retry limit of the users app

## Tasks

- [ ] Task 1: In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit. Run `python3 -m unittest discover -s tests`, and commit the task.
PLAN_EOF
