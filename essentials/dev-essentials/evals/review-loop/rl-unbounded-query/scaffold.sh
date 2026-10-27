#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
git checkout -q -b feature/recent-orders
cat >> src/store.py <<'PAGER_EOF'


def recent_orders(db):
    """Return the newest orders, at most 50 rows."""
    rows = db.execute("SELECT id, customer, total FROM orders ORDER BY id DESC")
    return rows.fetchall()
PAGER_EOF
fixture_commit "add recent_orders"
fixture_publish feature/recent-orders
