#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"

fixture_init
fixture_write .gitignore <<'FIX_EOF'
__pycache__/
*.pyc
FIX_EOF
fixture_write README.md <<'FIX_EOF'
# orders app

A small Python app with billing helpers.

Run the tests with `python3 -m unittest discover -s tests`.
FIX_EOF
fixture_write CLAUDE.md <<'FIX_EOF'
# orders app

- Test command: `python3 -m unittest discover -s tests`
- The repo has no build step.
FIX_EOF
fixture_write app/__init__.py < /dev/null
fixture_write app/billing.py <<'FIX_EOF'
"""Billing helpers."""


def apply_discount(total, percent):
    """Return the total after a discount of percent percent. For 10 percent of 200 the result is 180."""
    return total - percent
FIX_EOF
fixture_write tests/test_billing.py <<'FIX_EOF'
import unittest

from app.billing import apply_discount


class BillingTests(unittest.TestCase):
    def test_discount_is_a_percentage_of_the_total(self):
        self.assertEqual(apply_discount(200, 10), 180)

    def test_no_discount_keeps_the_total(self):
        self.assertEqual(apply_discount(200, 0), 200)


if __name__ == "__main__":
    unittest.main()
FIX_EOF
fixture_commit "add the orders app with a failing test"
