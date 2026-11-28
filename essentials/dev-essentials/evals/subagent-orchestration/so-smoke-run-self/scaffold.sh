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
# receipts app

A small Python app that prints the receipt of an order.

Print the receipt of the sample order: `python3 -m app.cli samples/order.json`.

Run the tests with `python3 -m unittest discover -s tests`.
FIX_EOF
fixture_write CLAUDE.md <<'FIX_EOF'
# receipts app

- Test command: `python3 -m unittest discover -s tests`
- The repo has no build step.
FIX_EOF
fixture_write .github/workflows/ci.yml <<'FIX_EOF'
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Unit tests
        run: python3 -m unittest discover -s tests
FIX_EOF
fixture_write app/__init__.py < /dev/null
fixture_write app/pricing.py <<'FIX_EOF'
"""Pricing rules of the shop. All amounts are in cents."""

MEMBER_DISCOUNT_PERCENT = 10


def subtotal(lines):
    """Return the sum of price times quantity of each (price, quantity) line."""
    return sum(price * quantity for price, quantity in lines)


def member_discount(amount):
    """Return the discount of a member on an amount."""
    return amount * MEMBER_DISCOUNT_PERCENT // 100


def order_total(lines, member):
    """Return the total of an order. A member gets MEMBER_DISCOUNT_PERCENT percent off the subtotal."""
    amount = subtotal(lines)
    if member:
        return amount - member_discount(amount)
    return amount
FIX_EOF
fixture_write app/receipt.py <<'FIX_EOF'
"""The text receipt of an order."""

from app.pricing import MEMBER_DISCOUNT_PERCENT, member_discount, order_total, subtotal


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def render(order):
    """Return the receipt of an order as text."""
    lines = [(item["price"], item["quantity"]) for item in order["items"]]
    rows = [f"Order {order['id']}"]
    for item in order["items"]:
        rows.append(f"{item['quantity']} x {item['name']:<20}{money(item['price'] * item['quantity']):>8}")
    amount = subtotal(lines)
    rows.append(f"{'Subtotal':<24}{money(amount):>8}")
    if order["member"]:
        label = f"Member discount {MEMBER_DISCOUNT_PERCENT}%"
        rows.append(f"{label:<24}{'-' + money(member_discount(amount)):>8}")
    rows.append(f"{'Total':<24}{money(order_total(lines, order['member'])):>8}")
    return "\n".join(rows) + "\n"
FIX_EOF
fixture_write app/cli.py <<'FIX_EOF'
"""Print the receipt of an order file: python3 -m app.cli <order.json>."""

import json
import sys

from app.receipt import render


def main(argv):
    if len(argv) != 2:
        print("usage: python3 -m app.cli <order.json>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as stream:
        order = json.load(stream)
    sys.stdout.write(render(order))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
FIX_EOF
fixture_write samples/order.json <<'FIX_EOF'
{
  "id": "A-1001",
  "member": true,
  "items": [
    {"name": "Notebook", "price": 1250, "quantity": 2},
    {"name": "Pen set", "price": 1500, "quantity": 1}
  ]
}
FIX_EOF
fixture_write tests/test_pricing.py <<'FIX_EOF'
import unittest

from app.pricing import order_total, subtotal

LINES = [(1250, 2), (1500, 1)]


class PricingTests(unittest.TestCase):
    def test_the_subtotal_adds_each_line(self):
        self.assertEqual(subtotal(LINES), 4000)

    def test_a_guest_pays_the_subtotal(self):
        self.assertEqual(order_total(LINES, member=False), 4000)

    def test_a_member_gets_ten_percent_off(self):
        self.assertEqual(order_total(LINES, member=True), 3600)


if __name__ == "__main__":
    unittest.main()
FIX_EOF
fixture_commit "add the receipts app"
fixture_remote_init
fixture_publish main
