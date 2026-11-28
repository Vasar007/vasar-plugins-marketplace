#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
git checkout -q -b feature/size-limit
fixture_write src/pager.py <<'PAGER_EOF'
"""Paging helpers for lists of items."""
import logging
from math import ceil

log = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

SORT_LABELS = {
    "newest": "Newest first",
    "oldest": "Oldest first",
    "biggest": "Biggest total first",
}


def sort_label(key):
    """Return the label that the sort menu shows for a sort key. An unknown key gets "Unknown sort"."""
    return SORT_LABELS.get(key, "Unknown sort")


def limited_size(size):
    """Return size, but not above MAX_PAGE_SIZE. The size must be positive."""
    if size <= 0:
        raise ValueError("size must be positive")
    if size > MAX_PAGE_SIZE:
        log.warning("page size %d is above the limit %d", size, MAX_PAGE_SIZE)
        return MAX_PAGE_SIZE
    return size


def total_pages(total_items, size=DEFAULT_PAGE_SIZE):
    """Return the number of pages that hold total_items items.

    A size above MAX_PAGE_SIZE counts as MAX_PAGE_SIZE.
    """
    return ceil(total_items / limited_size(size))


def has_next_page(page, total_items, size=DEFAULT_PAGE_SIZE):
    """Return True if a page after the given page (1-based) exists."""
    return page < total_pages(total_items, size)
PAGER_EOF
fixture_write tests/test_limits_of_size.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
from pager import MAX_PAGE_SIZE, limited_size, sort_label


class SizeLimitTests(unittest.TestCase):
    def test_max_page_size_is_100(self):
        self.assertEqual(MAX_PAGE_SIZE, 100)

    def test_size_below_the_limit_is_kept(self):
        self.assertEqual(limited_size(30), 30)

    def test_size_equal_to_the_limit_is_kept(self):
        self.assertEqual(limited_size(100), 100)

    def test_size_above_the_limit_gives_the_limit(self):
        self.assertEqual(limited_size(250), 100)

    def test_size_must_be_positive(self):
        with self.assertRaises(ValueError):
            limited_size(0)


class SortLabelTests(unittest.TestCase):
    def test_known_key_gives_its_label(self):
        self.assertEqual(sort_label("newest"), "Newest first")

    def test_unknown_key_gives_the_fallback(self):
        self.assertEqual(sort_label("cheapest"), "Unknown sort")


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
fixture_commit "cap the page size at 100 and add sort labels"
fixture_publish feature/size-limit
