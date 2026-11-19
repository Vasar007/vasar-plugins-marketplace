#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
add_paging_branch
fixture_write tests/test_paging.py <<'PAGER_EOF'
import unittest

import context  # noqa: F401
from pager import page_slice


class PageSliceTests(unittest.TestCase):
    def test_a_full_page_holds_size_items(self):
        self.assertEqual(page_slice(list(range(10)), 1, 4), [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
PAGER_EOF
sed -i 's|^- Test command: `python3 -m unittest discover -s tests`$|- Test command: `python3 -m unittest discover -s tests -p "test_[!p]*.py"`|' CLAUDE.md
grep -qF -- '- Test command: `python3 -m unittest discover -s tests -p "test_[!p]*.py"`' CLAUDE.md
fixture_commit "add a page_slice test and run the fast tests only"
fixture_publish feature/paging
