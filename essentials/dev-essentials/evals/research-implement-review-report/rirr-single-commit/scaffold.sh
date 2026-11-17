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
fixture_write notes/Plans/retry-and-timeout-plan.md <<'PLAN_EOF'
# Plan: lower the retry limit and the timeout of the users app

The plan has two independent tasks. Implement them in this order. Commit each task on its own, right after its tests pass.

## Tasks

- [ ] Task 1: In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit. Run `python3 -m unittest discover -s tests`, and commit the task.
- [ ] Task 2: In `config/settings.py`, set `TIMEOUT_SECONDS` to 10. No test reads it. Run `python3 -m unittest discover -s tests`, and commit the task.
PLAN_EOF
