#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
fixture_notes_folder
git checkout -q -b user/tasks/12-customer-index
fixture_write src/store.py <<'CASE_EOF'
"""A small order store on SQLite."""
import sqlite3


def connect(path=":memory:"):
    """Open the database, and make the orders table and its index on customer."""
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, customer TEXT NOT NULL, total INTEGER NOT NULL)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer)")
    return db


def add_order(db, customer, total):
    """Add an order and return its id."""
    cursor = db.execute("INSERT INTO orders (customer, total) VALUES (?, ?)", (customer, total))
    db.commit()
    return cursor.lastrowid


def orders_for_customer(db, customer, limit=50):
    """Return the newest orders of a customer, at most limit rows."""
    rows = db.execute(
        "SELECT id, customer, total FROM orders WHERE customer = ? ORDER BY id DESC LIMIT ?",
        (customer, limit),
    )
    return rows.fetchall()


def orders_count(db, customer):
    """Return the number of orders of a customer."""
    return db.execute("SELECT COUNT(*) FROM orders WHERE customer = ?", (customer,)).fetchone()[0]


def biggest_orders(db, count):
    """Return the count biggest orders."""
    rows = db.execute("SELECT id, customer, total FROM orders ORDER BY total DESC LIMIT ?", (count,))
    return rows.fetchall()
CASE_EOF
cat >> tests/test_store.py <<'CASE_EOF'


class OrdersCountTests(unittest.TestCase):
    def test_orders_count(self):
        db = store.connect()
        store.add_order(db, "ada", 10)
        store.add_order(db, "ada", 30)
        self.assertEqual(store.orders_count(db, "ada"), 2)
        self.assertEqual(store.orders_count(db, "bob"), 0)
CASE_EOF
fixture_commit "add the customer index and the order count"
fixture_write notes/scratch.md <<'CASE_EOF'
# Scratch

EXPLAIN QUERY PLAN shows a full scan of orders before the index.
CASE_EOF
fixture_commit "add a scratch note"
fixture_publish user/tasks/12-customer-index
fixture_write notes/Plans/12-customer-index-plan.md <<'CASE_EOF'
# Plan for issue 12: index on customer

Reason: the monthly invoice report reads the orders of each customer, and the report job times out for the biggest customers.

1. Add an index on the customer column of the orders table.
2. Add the order count of a customer, for the invoice header.
3. Cache the invoice header.
CASE_EOF
fixture_write notes/Plans/34-export-retry-plan.md <<'CASE_EOF'
# Plan for issue 34: retry for the export job

Reason: the nightly export fails on short network errors.

1. Add a retry with backoff to the export job.
CASE_EOF
