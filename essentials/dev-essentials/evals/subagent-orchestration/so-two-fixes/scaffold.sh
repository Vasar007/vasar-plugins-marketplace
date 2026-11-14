#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/commit-log.sh"

fixture_init
fixture_write .gitignore <<'FIX_EOF'
__pycache__/
*.pyc
FIX_EOF
fixture_write README.md <<'FIX_EOF'
# orders app

A small Python app with billing and shipping helpers.

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
fixture_write app/shipping.py <<'FIX_EOF'
"""Shipping helpers."""

FREE_SHIPPING_THRESHOLD = 50
FLAT_RATE = 5


def shipping_cost(order_total):
    """Return the shipping cost of an order. Orders of 50 or more ship free."""
    if order_total > FREE_SHIPPING_THRESHOLD:
        return 0
    return FLAT_RATE
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
fixture_write tests/test_shipping.py <<'FIX_EOF'
import unittest

from app.shipping import shipping_cost


class ShippingTests(unittest.TestCase):
    def test_small_order_pays_the_flat_rate(self):
        self.assertEqual(shipping_cost(20), 5)

    def test_large_order_ships_free(self):
        self.assertEqual(shipping_cost(80), 0)

    def test_order_at_the_threshold_ships_free(self):
        self.assertEqual(shipping_cost(50), 0)


if __name__ == "__main__":
    unittest.main()
FIX_EOF
fixture_commit "add the orders app with two failing tests"
fixture_remote_init
fixture_publish main
fixture_log_commits
