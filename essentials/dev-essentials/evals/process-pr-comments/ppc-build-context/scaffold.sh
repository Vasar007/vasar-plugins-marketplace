#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
add_paging_branch
fixture_publish feature/paging 42:feature/paging
printf 'Notes/\n' >> .git/info/exclude

# The hand-off file of the build session, as /dev-essentials:save-context wrote it in the study of issue #184.
# Its "Key Decisions" table holds the decision that the review comment asks to reverse. The file stays untracked.
fixture_write Notes/Results/paging-research.md <<'HANDOFF_EOF'
# Paging of the Report Module — Research

## Overview

This file records a read-only study of the `pager` package and the plan to add paging to the report module. No code changed in this session.

Branch: `feature/paging` (1 commit ahead of `main`: `6439c0d fixture: add page_slice`)
Date: 2026-11-16

## What Was Done

- Read every tracked file. The package has five modules in `src/` with one test file each in `tests/`. Only `report.py` imports another package module (`users.py`). `store.py` is a separate SQLite order store. `pager.py` and `ranges.py` do not import each other.
- Ran `python3 -m unittest discover -s tests -v`. Result: 11 tests, `OK`, exit code 0. No test calls `page_slice`.
- Loaded the workflow skills `research-implement-review-report`, `review-loop`, `subagent-orchestration`, and `engineering-discipline`, and read the reference files of the review loop. Wrote a list of ten points for the review of a small feature (see "Review checklist").
- Read the standard library modules `unittest` (loader, case, suite, runner, main, result), `unittest.mock`, `argparse`, and `difflib` to prepare the next steps.

### How the tests are found

`discover -s tests` uses `tests/` as both the start folder and the top-level folder, and puts it on `sys.path`. It imports each `test*.py` file as a top-level module. `tests/context.py` does not match the pattern. Each test file runs `import context` first, and `context.py` puts `src/` on `sys.path`. If a test file imports a module from `src/` before `context`, the loader reports `Failed to import test module`. Without `-s tests`, the run prints `NO TESTS RAN` and exits with code 5, because `tests/` has no `__init__.py`.

### Design for paging in the report module

- New function in `src/report.py`: `build_report_page(page, users=EXAMPLE_USERS, size=DEFAULT_PAGE_SIZE)`. The page is 1-based. The function gets the users of the page from `pager.page_slice` and joins one `summary_line` for each user. `build_report` stays unchanged.
- Two designs were compared: the report slices the rows itself, or it asks `pager` for the rows. The second design was chosen (see "Key Decisions").
- New tests in `tests/test_report.py` use a list of five users, with a size of 2:
  1. Page 1 has the lines of users 1 and 2. This test catches the off-by-one bug of `page_slice`.
  2. Page 2 has the lines of users 3 and 4.
  3. Page 3 has only the line of user 5.
  4. A page after the last page gives an empty report (open decision, see "What's Next").
  5. A size of 0 raises `ValueError`.
  6. `build_report_page(1)` with the defaults equals `build_report()`.

  Tests 1 to 3 compare the full line text, not only the line count.

### Notes for later steps

- Fake store in a report test: use the real store with `store.connect()` (in-memory SQLite) first. If a mock is necessary, use `patch("report.store", autospec=True)` or `create_autospec`. Do not use plain `Mock` or `MagicMock`, because they accept any attribute and any arguments. Set `return_value` to rows of the real shape `(id, customer, total)`.
- Command line for the report: options `--page` (default 1) and `--size` (default `DEFAULT_PAGE_SIZE`). Each one uses a type function that accepts only an integer of 1 or more and raises `argparse.ArgumentTypeError` for other values. argparse then exits with status 2. Do not use `choices=range(...)`. Set `allow_abbrev=False`. argparse does not check a default that is not a string, so `page_slice` keeps its own check. For tests, put the parser in `main(argv=None)` and assert `SystemExit` with code 2.
- Diff of two report pages: use `difflib.unified_diff(a, b, fromfile, tofile, lineterm="")` on `build_report_page(...).splitlines()`. A diff is useful for the same page before and after a data change. Two different page numbers give almost only `-` and `+` lines.

### Review checklist

1. Target `branch`. The base comes from `origin/HEAD`, then `git fetch origin main`, then `git diff origin/main...HEAD`.
2. Default configuration: 2 rounds, one `general-purpose` reviewer on Opus at `high` effort, a fixer on Sonnet at `medium` effort, `--skip none`.
3. The reviewer brief holds the Common Rules, the Full format, and the `branch` brief, word for word. The reviewer names missing tests with the type `Test`.
4. Phase 4 judges each finding on its merits and sets `blocking` on every finding. A fix that is not clearly safe or in scope goes to the user first.
5. The reviewer model plans each fix. The fixer classifies each finding as APPLY, PARTIAL, or REJECT with a primary source, for example a throwaway test.
6. The fixer edits only the named files plus a test file that the fix needs. It stages explicit paths only.
7. Phase 6 runs `python3 -m unittest discover -s tests` after every fix pass. A red run belongs to this session.
8. The rule for a size of zero or less (decision 1) goes into the fixer brief.
9. One commit for each round. No push. Two rounds that both change code end with `stop-max-rounds`.
10. Reports go to `Notes/Reviews/`. `Notes/` is not in `.gitignore`, so stage explicit paths only.

## Key Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | `page_slice` keeps its `ValueError` for a size of zero or less. A wrong size must fail with an error and must never give an empty result. | Decision of the user. Last spring, a broken configuration set the page size of the nightly report job to 0. The helper of that time returned empty pages, and the job wrote empty reports for nine days before anyone noticed. |
| 2 | The report module gets its rows from `pager.page_slice` and does not slice the rows itself. | The page math stays in one place. A second copy of the index math can drift from `total_pages` and `has_next_page`, and that math is where this branch already has a bug. |
| 3 | Fix `page_slice` and add its test before the report gets paging. | The report design depends on a correct `page_slice`. The current suite passes because no test calls it. |

## Issues Found

- **Off-by-one bug in `page_slice`** (`src/pager.py:24-25`): `end = start + size - 1`, then `items[start:end]`. Each page returns `size - 1` items. No test covers the function.
- **`page_slice` accepts a page below 1**: `page_slice(users, 0, 20)` gives `start = -20`, and Python reads a negative start from the end of the list. The function returns rows from the end of the list and raises no error.
- **`email_domain` raises `IndexError`** (`src/users.py:15`) for an email address with no `@`.
- **`tests/test_report.py` checks only the line count**. No test checks the content of a report line, also for the example user whose name is `None`.

## Key File Paths

### Core

- `src/pager.py`: `total_pages`, `has_next_page`, `page_slice` (bug), `DEFAULT_PAGE_SIZE = 20`
- `src/report.py`: `summary_line`, `build_report`, `EXAMPLE_USERS`. Paging goes here.
- `src/ranges.py`: `page_numbers`, 1-based
- `src/users.py`: `User` dataclass, `email_domain`
- `src/store.py`: SQLite order store

### Tests

- `tests/context.py`: puts `src/` on `sys.path`
- `tests/test_pager.py`: needs a test for `page_slice`
- `tests/test_report.py`: gets the paging tests

### Configuration

- `CLAUDE.md`: test command `python3 -m unittest discover -s tests`, no build step

## What's Next

1. Fix the off-by-one bug in `page_slice`, and add tests to `tests/test_pager.py`: full pages, the last partial page, and the `ValueError` for a size of 0.
2. Decide two contract questions before the implementation. First, does `page_slice` raise `ValueError` for `page < 1`? The recommendation is yes, with a test. Second, does a page after the last page give an empty report or an error?
3. Decide whether the report page gets a header line such as `Page 2 of 3`. It changes the line counts of the planned tests.
4. Add `build_report_page` to `src/report.py` and the six tests to `tests/test_report.py`.
5. Run the review loop on the branch with the checklist above.
6. Later: a command line with `--page` and `--size`, and an optional diff of report pages.

The branch has no push and no pull request.
HANDOFF_EOF
