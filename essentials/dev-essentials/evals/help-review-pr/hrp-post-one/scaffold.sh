#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
cat >> CLAUDE.md <<'CASE_EOF'
- Convention skills: none. Review a pull request against the rules of this file.
- Style: build a string with an f-string, not with `%` or `str.format`. This rule is a style preference.
- New code gets its tests in a later pull request. A missing test is no finding.
CASE_EOF
fixture_commit "state the review rules"

# Pull request 7 has two defects: an off-by-one in page_slice, and a % format in page_label.
git checkout -q -b feature/page-tools
cat >> src/pager.py <<'CASE_EOF'


def page_slice(items, page, size=DEFAULT_PAGE_SIZE):
    """Return the items of a page (1-based). A page holds at most size items."""
    if size <= 0:
        raise ValueError("size must be positive")
    if page < 1:
        raise ValueError("page must be 1 or more")
    start = (page - 1) * size
    end = start + size - 1
    return items[start:end]
CASE_EOF
cat >> src/ranges.py <<'CASE_EOF'


def page_label(page, count):
    """Return the label of a page, for example "Page 2 of 5"."""
    return "Page %d of %d" % (page, count)
CASE_EOF
fixture_commit "add page_slice and page_label"
git checkout -q main
fixture_publish main 7:feature/page-tools
