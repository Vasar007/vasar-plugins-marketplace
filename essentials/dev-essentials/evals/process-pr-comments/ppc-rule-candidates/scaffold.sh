#!/usr/bin/env bash
# The branch adds three functions with camelCase names in three files, and raises a default limit in a fourth file.
# Three review threads make the same naming point in other words. One thread is about the limit.
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
git checkout -q -b feature/page-helpers
cat >> src/pager.py <<'PAGER_EOF'


def pageCount(items, size=DEFAULT_PAGE_SIZE):
    """Return the number of pages for a list of items."""
    return total_pages(len(items), size)
PAGER_EOF
cat >> src/ranges.py <<'PAGER_EOF'


def lastPage(count):
    """Return the number of the last page of count pages, or 0 for no pages."""
    return count
PAGER_EOF
cat >> src/users.py <<'PAGER_EOF'


def displayName(user):
    """Return the name of the user, or the email address for a user with no name."""
    return user.name or user.email
PAGER_EOF
sed -i 's/def orders_for_customer(db, customer, limit=50):/def orders_for_customer(db, customer, limit=500):/' src/store.py
fixture_commit "add the page helpers"
fixture_publish feature/page-helpers 42:feature/page-helpers
