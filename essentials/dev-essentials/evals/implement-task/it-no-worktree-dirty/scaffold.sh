#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
printf 'notes/\n' >> .gitignore
fixture_commit "ignore the notes folder"
fixture_publish main

# A change of the user in the file of the task, with no commit. The run must stop before any work and keep it.
sed -i 's/^TIMEOUT_SECONDS = 30$/TIMEOUT_SECONDS = 45/' config/settings.py
