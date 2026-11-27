#!/usr/bin/env bash
# Python fixtures for the dev-essentials eval cases. A scaffold sources this file after git-fixture.sh.
#
# make_pager_repo: the "pager" repo with CLAUDE.md, src/, and passing unittest tests. A case adds its own branch.
# make_users_repo <modules>: an app whose modules call fetch_user. The argument is 6 (small) or 40 (large).
# Both functions leave main checked out with one fixture commit and a bare remote. They do not publish it.
# add_paging_branch: on the pager repo, add the branch feature/paging with the planted off-by-one in page_slice.
# It leaves feature/paging checked out. It does not publish it.
# add_retry_lint_run: on the small users repo, the state of an earlier run whose commit fails only the lint check of CI.
# It publishes main, and it leaves work/retry-lint checked out with no remote copy.
set -euo pipefail

make_pager_repo() {
    fixture_init
    fixture_write .gitignore <<'PAGER_EOF'
__pycache__/
*.pyc
PAGER_EOF
    fixture_write README.md <<'PAGER_EOF'
# pager

A small Python package that pages lists of orders and users.

Run the tests with `python3 -m unittest discover -s tests`.
PAGER_EOF
    fixture_write CLAUDE.md <<'PAGER_EOF'
# pager

Small Python package. The code is in `src/`, and the tests are in `tests/`.

- Test command: `python3 -m unittest discover -s tests`
- The repo has no build step. Do not look for one.
PAGER_EOF
    fixture_write src/pager.py <<'PAGER_EOF'
"""Paging helpers for lists of items."""
from math import ceil

DEFAULT_PAGE_SIZE = 20


def total_pages(total_items, size=DEFAULT_PAGE_SIZE):
    """Return the number of pages that hold total_items items."""
    if size <= 0:
        raise ValueError("size must be positive")
    return ceil(total_items / size)


def has_next_page(page, total_items, size=DEFAULT_PAGE_SIZE):
    """Return True if a page after the given page (1-based) exists."""
    return page < total_pages(total_items, size)
PAGER_EOF
    fixture_write src/ranges.py <<'PAGER_EOF'
"""Page number ranges."""


def page_numbers(count):
    """Return the page numbers of count pages.

    The numbers are 1-based, inclusive: for 3 pages the result is [1, 2, 3].
    """
    return list(range(1, count + 1))
PAGER_EOF
    fixture_write src/store.py <<'PAGER_EOF'
"""A small order store on SQLite."""
import sqlite3


def connect(path=":memory:"):
    """Open the database and make the orders table."""
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, customer TEXT NOT NULL, total INTEGER NOT NULL)")
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


def biggest_orders(db, count):
    """Return the count biggest orders."""
    rows = db.execute("SELECT id, customer, total FROM orders ORDER BY total DESC LIMIT ?", (count,))
    return rows.fetchall()
PAGER_EOF
    fixture_write src/users.py <<'PAGER_EOF'
"""Users of the pager service."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    name: Optional[str]
    email: str


def email_domain(user):
    """Return the part of the email address after the @ sign."""
    return user.email.split("@", 1)[1]
PAGER_EOF
    fixture_write src/report.py <<'PAGER_EOF'
"""A plain text report of users."""
from users import User, email_domain

EXAMPLE_USERS = [
    User(1, "Ada", "ada@example.com"),
    User(2, None, "guest@example.com"),
]


def summary_line(user):
    """Return one report line for a user."""
    return f"{user.id}: {user.email} ({email_domain(user)})"


def build_report(users=EXAMPLE_USERS):
    """Return the report for the users, one line for each user."""
    return "\n".join(summary_line(user) for user in users)
PAGER_EOF
    fixture_write tests/context.py <<'PAGER_EOF'
"""Put src/ on the import path, so that the tests can import the modules."""
import sys
from pathlib import Path

SRC = str(Path(__file__).resolve().parents[1] / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
PAGER_EOF
    fixture_write tests/test_pager.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
from pager import has_next_page, total_pages


class PagerTests(unittest.TestCase):
    def test_total_pages_rounds_up(self):
        self.assertEqual(total_pages(41, 20), 3)

    def test_total_pages_of_no_items_is_zero(self):
        self.assertEqual(total_pages(0, 20), 0)

    def test_size_must_be_positive(self):
        with self.assertRaises(ValueError):
            total_pages(10, 0)

    def test_has_next_page(self):
        self.assertTrue(has_next_page(1, 41, 20))
        self.assertFalse(has_next_page(3, 41, 20))


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
    fixture_write tests/test_ranges.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
from ranges import page_numbers


class RangesTests(unittest.TestCase):
    def test_page_numbers_are_one_based(self):
        self.assertEqual(page_numbers(3), [1, 2, 3])

    def test_no_pages(self):
        self.assertEqual(page_numbers(0), [])


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
    fixture_write tests/test_store.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
import store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.db = store.connect()
        for customer, total in (("ada", 10), ("ada", 30), ("bob", 20)):
            store.add_order(self.db, customer, total)

    def test_orders_for_customer_are_newest_first(self):
        rows = store.orders_for_customer(self.db, "ada")
        self.assertEqual([row[2] for row in rows], [30, 10])

    def test_orders_for_customer_respect_the_limit(self):
        self.assertEqual(len(store.orders_for_customer(self.db, "ada", limit=1)), 1)

    def test_biggest_orders(self):
        rows = store.biggest_orders(self.db, 2)
        self.assertEqual([row[2] for row in rows], [30, 20])


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
    fixture_write tests/test_users.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
from users import User, email_domain


class UsersTests(unittest.TestCase):
    def test_email_domain(self):
        self.assertEqual(email_domain(User(1, "Ada", "ada@example.com")), "example.com")


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
    fixture_write tests/test_report.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
from report import build_report


class ReportTests(unittest.TestCase):
    def test_report_has_one_line_for_each_user(self):
        self.assertEqual(len(build_report().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
    fixture_commit "add the pager package"
    fixture_remote_init
}

# The planted defect is "end = start + size - 1" in src/pager.py, so a page holds one item too few.
add_paging_branch() {
    git checkout -q -b feature/paging
    cat >> src/pager.py <<'PAGER_EOF'


def page_slice(items, page, size=DEFAULT_PAGE_SIZE):
    """Return the items of a page (1-based, like page_numbers in ranges.py). A page holds at most size items."""
    if size <= 0:
        raise ValueError("size must be positive")
    start = (page - 1) * size
    end = start + size - 1
    return items[start:end]
PAGER_EOF
    fixture_commit "add page_slice"
}

make_users_repo() {
    local modules="${1:?make_users_repo needs the number of modules: 6 or 40}"
    local names=("app.users" "app.http_client")
    fixture_init
    fixture_write .gitignore <<'USERS_EOF'
__pycache__/
*.pyc
USERS_EOF
    fixture_write README.md <<'USERS_EOF'
# users app

A small Python app. Many modules load a user record with `fetch_user`.

Run the tests with `python3 -m unittest discover -s tests`.
USERS_EOF
    fixture_write CLAUDE.md <<'USERS_EOF'
# users app

- Test command: `python3 -m unittest discover -s tests`
- The repo has no build step.
USERS_EOF
    fixture_write app/__init__.py < /dev/null
    fixture_write config/__init__.py < /dev/null
    fixture_write config/settings.py <<'USERS_EOF'
"""Settings of the users app."""

HTTP_RETRY_LIMIT = 5
TIMEOUT_SECONDS = 30
USERS_EOF
    fixture_write app/users.py <<'USERS_EOF'
"""The user records of the app."""

USERS = {
    1: {"id": 1, "name": "Ada"},
    2: {"id": 2, "name": "Grace"},
}


def fetch_user(user_id):
    """Return a copy of the user record. Raise KeyError for an unknown id."""
    return dict(USERS[user_id])
USERS_EOF
    fixture_write app/http_client.py <<'USERS_EOF'
"""A stand-in HTTP client."""
from config.settings import HTTP_RETRY_LIMIT


def get(url, retries=HTTP_RETRY_LIMIT):
    """Return a text that shows the call. The client does not use the network."""
    return f"GET {url} (retries={retries})"
USERS_EOF
    case "$modules" in
        6)
            _users_caller app/orders.py orders
            _users_caller app/invoices.py invoices
            _users_caller app/notify.py notify
            _users_plain app/audit.py audit
            names+=("app.orders" "app.invoices" "app.notify" "app.audit")
            ;;
        40)
            local n group path module
            for n in $(seq 1 38); do
                group="app/pkg_$(((n - 1) / 10))"
                module="mod_$(printf '%02d' "$n")"
                path="$group/$module.py"
                fixture_write "$group/__init__.py" < /dev/null
                if [ "$n" -eq 25 ]; then
                    path="$group/inner/deep/$module.py"
                    fixture_write "$group/inner/__init__.py" < /dev/null
                    fixture_write "$group/inner/deep/__init__.py" < /dev/null
                fi
                if [ "$n" -le 25 ]; then
                    _users_caller "$path" "$module"
                else
                    _users_plain "$path" "$module"
                fi
                names+=("$(echo "${path%.py}" | tr / .)")
            done
            ;;
        *)
            echo "make_users_repo: the number of modules must be 6 or 40, not $modules" >&2
            return 1
            ;;
    esac
    _users_tests "${names[@]}"
    fixture_commit "add the users app with $modules modules"
    fixture_remote_init
}

# _users_caller <path> <label>: a module that calls fetch_user.
_users_caller() {
    local path="$1" label="$2"
    fixture_write "$path" <<USERS_EOF
"""The $label module."""
from app.users import fetch_user


def run(user_id):
    """Return a text with the name of the user."""
    user = fetch_user(user_id)
    return f"$label:{user['name']}"
USERS_EOF
}

# _users_plain <path> <label>: a module that does not call fetch_user.
_users_plain() {
    local path="$1" label="$2"
    fixture_write "$path" <<USERS_EOF
"""The $label module."""


def run(user_id):
    """Return a text with the id of the user."""
    return f"$label:{user_id}"
USERS_EOF
}

# _users_tests <module name>...: the test files. The module test imports each name that the fixture made.
_users_tests() {
    local name
    fixture_write tests/test_users.py <<'USERS_EOF'
import unittest

from app.users import fetch_user


class UsersTests(unittest.TestCase):
    def test_fetch_user_returns_the_record(self):
        self.assertEqual(fetch_user(1)["name"], "Ada")

    def test_fetch_user_of_an_unknown_id_fails(self):
        with self.assertRaises(KeyError):
            fetch_user(99)


if __name__ == "__main__":
    unittest.main()
USERS_EOF
    fixture_write tests/test_http_client.py <<'USERS_EOF'
import unittest

from app.http_client import get


class HttpClientTests(unittest.TestCase):
    def test_get_uses_the_retry_limit_of_the_settings(self):
        self.assertEqual(get("/users"), "GET /users (retries=5)")


if __name__ == "__main__":
    unittest.main()
USERS_EOF
    {
        printf 'import importlib\nimport unittest\n\nMODULES = [\n'
        for name in "$@"; do
            printf '    "%s",\n' "$name"
        done
        printf ']\n\n\nclass ModuleTests(unittest.TestCase):\n'
        printf '    def test_every_module_with_a_run_function_runs(self):\n'
        printf '        for name in MODULES:\n'
        printf '            module = importlib.import_module(name)\n'
        printf '            if hasattr(module, "run"):\n'
        printf '                with self.subTest(module=name):\n'
        printf '                    self.assertTrue(module.run(1).startswith(name.rsplit(".", 1)[1]))\n'
        printf '\n\nif __name__ == "__main__":\n    unittest.main()\n'
    } | fixture_write tests/test_modules.py
}

# The commit of the earlier run adds a comment line of more than 88 characters to config/settings.py.
# The local tests pass, and CLAUDE.md names no lint command. The repository holds no CI config: the lint job runs outside it.
# Only the mocked check run names its command, so no CI file shows a run the lint before the push.
add_retry_lint_run() {
    printf 'notes/\n' >> .gitignore
    fixture_write tools/lint.py <<'USERS_EOF'
"""Lint the Python files of the given folders: a line has at most 88 characters."""
import sys
from pathlib import Path

LIMIT = 88


def main(folders):
    problems = []
    for folder in folders:
        for path in sorted(Path(folder).glob("**/*.py")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, start=1):
                if len(line) > LIMIT:
                    problems.append(f"{path.as_posix()}:{number}: line too long ({len(line)} > {LIMIT})")
    print("\n".join(problems) if problems else "lint: no problem found")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
USERS_EOF
    fixture_commit "add the lint tool, and ignore the notes folder"
    fixture_publish main

    git checkout -q -b work/retry-lint
    fixture_write config/settings.py <<'USERS_EOF'
"""Settings of the users app."""

# Three retries keep a failed call short. With five retries, a user waited too long for an answer.
HTTP_RETRY_LIMIT = 3
TIMEOUT_SECONDS = 30
USERS_EOF
    sed -i 's/(retries=5)/(retries=3)/' tests/test_http_client.py
    fixture_commit "lower the HTTP retry limit to 3"

    fixture_write notes/Plans/retry-lint-plan.md <<'USERS_EOF'
# Plan: lower the HTTP retry limit of the users app

## Tasks

- [x] Task 1: In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3, with a comment that gives the reason. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit. Run `python3 -m unittest discover -s tests`, and commit the task.
USERS_EOF
    fixture_write notes/Results/retry-lint-report.md <<'USERS_EOF'
# Report: lower the HTTP retry limit of the users app

## Overview

- **Branch**: work/retry-lint
- **Base branch**: main
- **Head commit**: HEAD_SHA
- **Worktree**: none, the main work tree
- **Plan**: notes/Plans/retry-lint-plan.md

## What Was Done

- Task 1: `HTTP_RETRY_LIMIT` is 3, with a comment that gives the reason, and `tests/test_http_client.py` expects 3. The tests pass.
- Review loop: one round. Verdict `stop-clean`. No finding.

## What's Next

The branch is not pushed. The final gate asked about the push, the pull request, and the merge, and the answer was no.
USERS_EOF
    sed -i "s/HEAD_SHA/$(git rev-parse HEAD)/" notes/Results/retry-lint-report.md
}
