#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
git checkout -q -b feature/clamp
fixture_write src/limits.py <<'PAGER_EOF'
"""Limits for numbers."""


def clamp(value, low, high):
    """Return value, but not below low and not above high. The value and the limits must be numbers, not NaN."""
    if low > high:
        raise ValueError("low must not be above high")
    return max(low, min(value, high))
PAGER_EOF
fixture_write tests/test_limits.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
from limits import clamp


class LimitsTests(unittest.TestCase):
    def test_value_inside_the_limits_is_kept(self):
        self.assertEqual(clamp(5, 1, 10), 5)

    def test_value_below_the_low_limit_gives_the_low_limit(self):
        self.assertEqual(clamp(-3, 1, 10), 1)

    def test_value_above_the_high_limit_gives_the_high_limit(self):
        self.assertEqual(clamp(30, 1, 10), 10)

    def test_value_equal_to_a_limit_is_kept(self):
        self.assertEqual(clamp(1, 1, 10), 1)
        self.assertEqual(clamp(10, 1, 10), 10)

    def test_equal_limits_give_that_limit(self):
        self.assertEqual(clamp(7, 3, 3), 3)

    def test_limits_in_the_wrong_order_are_refused(self):
        with self.assertRaises(ValueError):
            clamp(5, 10, 1)


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
fixture_commit "add clamp"
fixture_publish feature/clamp
