#!/usr/bin/env bash
# The bug-hunt fixture. A scaffold sources this file after git-fixture.sh.
#
# make_shop_workspace builds ./project, a Python repo with three areas: billing/, inventory/, and notify/.
# The workspace root is not a repo. Each area holds one planted bug:
#   billing/invoice.py: invoice_total cuts the cents off a total with int().
#   inventory/cache.py: stock_level builds its cache key from the sku only, so two warehouses share one entry.
#   notify/retry.py: send_with_retry retries without end when max_retries is 0.
# NOTES.md lists one known bug, N-01 in notify/email.py. inventory/stock.py holds a decoy that looks wrong but is correct.
# The planted lines are SHOP_LINE_BILLING, SHOP_LINE_INVENTORY, and SHOP_LINE_NOTIFY. A test checks them.
set -euo pipefail

SHOP_LINE_BILLING=12
SHOP_LINE_INVENTORY=8
SHOP_LINE_NOTIFY=12

make_shop_workspace() {
    mkdir -p project
    cd project
    fixture_init
    fixture_write .gitignore <<'SHOP_EOF'
__pycache__/
*.pyc
SHOP_EOF
    fixture_write README.md <<'SHOP_EOF'
# shop

A small Python shop service with three areas: billing, inventory, and notify.

Run the tests with `python3 -m unittest discover -s tests`.
SHOP_EOF
    fixture_write NOTES.md <<'SHOP_EOF'
# Notes

Known bugs:

- N-01: `notify/email.py`: `build_subject` fails with a TypeError when the order id is an integer.
SHOP_EOF
    fixture_write billing/__init__.py < /dev/null
    fixture_write billing/invoice.py <<'SHOP_EOF'
"""Invoice totals."""


def line_total(price, quantity):
    """Return the total of one invoice line."""
    return price * quantity


def invoice_total(lines):
    """Return the total of all lines of an invoice, in currency units."""
    total = sum(line_total(line["price"], line["quantity"]) for line in lines)
    return int(total)
SHOP_EOF
    fixture_write inventory/__init__.py < /dev/null
    fixture_write inventory/cache.py <<'SHOP_EOF'
"""A cache for stock levels."""

_cache = {}


def stock_level(sku, warehouse, loader):
    """Return the stock level of a sku in one warehouse. The loader reads it from the database."""
    key = sku
    if key not in _cache:
        _cache[key] = loader(sku, warehouse)
    return _cache[key]


def clear():
    """Empty the cache."""
    _cache.clear()
SHOP_EOF
    fixture_write inventory/stock.py <<'SHOP_EOF'
"""Stock rules."""


def full_cases(units, case_size):
    """Return how many full cases a number of units fills."""
    # Floor division is correct here: a partial case is not shippable.
    return units // case_size


def free_units(on_hand, reserved):
    """Return the units that nobody reserved. The result is never below zero."""
    return max(on_hand - reserved, 0)
SHOP_EOF
    fixture_write notify/__init__.py < /dev/null
    fixture_write notify/email.py <<'SHOP_EOF'
"""Email texts."""


def build_subject(order_id):
    """Return the subject line of an order email."""
    return "Order " + order_id
SHOP_EOF
    fixture_write notify/retry.py <<'SHOP_EOF'
"""Send a message with retries."""


def send_with_retry(send, message, max_retries=3):
    """Call send(message). Retry after a ConnectionError, at most max_retries times."""
    attempt = 0
    while True:
        try:
            return send(message)
        except ConnectionError:
            attempt += 1
            if max_retries and attempt >= max_retries:
                raise
SHOP_EOF
    fixture_write tests/test_billing.py <<'SHOP_EOF'
import unittest

from billing.invoice import line_total


class BillingTests(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(5, 3), 15)


if __name__ == "__main__":
    unittest.main()
SHOP_EOF
    fixture_write tests/test_inventory.py <<'SHOP_EOF'
import unittest

from inventory.stock import free_units, full_cases


class InventoryTests(unittest.TestCase):
    def test_full_cases(self):
        self.assertEqual(full_cases(25, 10), 2)

    def test_free_units_are_never_negative(self):
        self.assertEqual(free_units(3, 5), 0)


if __name__ == "__main__":
    unittest.main()
SHOP_EOF
    fixture_write tests/test_notify.py <<'SHOP_EOF'
import unittest

from notify.retry import send_with_retry


class NotifyTests(unittest.TestCase):
    def test_send_returns_the_result(self):
        self.assertEqual(send_with_retry(lambda message: message.upper(), "hi"), "HI")


if __name__ == "__main__":
    unittest.main()
SHOP_EOF
    fixture_commit "add the shop project"
    cd ..
}
