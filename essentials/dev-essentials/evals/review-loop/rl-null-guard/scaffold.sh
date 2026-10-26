#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
git checkout -q -b feature/display-name
cat >> src/users.py <<'PAGER_EOF'


def display_name(user: User) -> str:
    """Return the name of a user without spaces at the start and the end."""
    return user.name.strip()
PAGER_EOF
sed -i 's/^from users import User, email_domain$/from users import User, display_name, email_domain/' src/report.py
grep -q 'import User, display_name, email_domain' src/report.py
cat >> src/report.py <<'PAGER_EOF'


def greeting_lines(users=EXAMPLE_USERS):
    """Return a greeting for each user."""
    return [f"Hello, {display_name(user)}!" for user in users]
PAGER_EOF
fixture_commit "add display_name and greeting_lines"
fixture_publish feature/display-name
