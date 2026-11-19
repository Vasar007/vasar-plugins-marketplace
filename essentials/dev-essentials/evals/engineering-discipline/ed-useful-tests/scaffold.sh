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
# shop app

A small Python app with the shipping fees of an order.

Run the tests with `python3 -m unittest discover -s tests`.
FIX_EOF
fixture_write CLAUDE.md <<'FIX_EOF'
# shop app

- Test command: `python3 -m unittest discover -s tests`
- The tests use `unittest`. The repo has no build step.
FIX_EOF
fixture_write app/__init__.py < /dev/null
fixture_write app/shipping.py <<'FIX_EOF'
"""Shipping fees of an order."""

FREE_SHIPPING_THRESHOLD = 50.0
"""The order total from which shipping is free."""

BASE_FEE = 4.90
"""The fee for a parcel of one kilogram."""

FEE_PER_KILOGRAM = 1.20
"""The fee for each kilogram after the first one."""

MAX_WEIGHT_KILOGRAMS = 30
"""The largest parcel weight in kilograms."""


def shipping_fee(order_total, weight_kilograms):
    """Return the shipping fee for an order total and a parcel weight in whole kilograms."""
    if order_total < 0:
        raise ValueError("The order total must not be negative.")
    if not 1 <= weight_kilograms <= MAX_WEIGHT_KILOGRAMS:
        raise ValueError("The weight must be from 1 to 30 kilograms.")
    if order_total >= FREE_SHIPPING_THRESHOLD:
        return 0.0
    return round(BASE_FEE + FEE_PER_KILOGRAM * (weight_kilograms - 1), 2)
FIX_EOF
fixture_commit "add the shipping fees"
