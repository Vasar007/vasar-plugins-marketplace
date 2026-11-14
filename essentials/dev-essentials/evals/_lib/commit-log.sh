#!/usr/bin/env bash
# Commit log for eval fixtures. A scaffold sources this file after git-fixture.sh. It is not meant to run alone.
#
# fixture_log_commits: log each later commit to .git/run-commits.log, also a commit in a linked worktree.
# Git writes the HEAD reflog of a linked worktree to .git/worktrees/<name>/logs/HEAD, so .git/logs/HEAD misses it.
# Call the function after the last fixture commit, so that the log holds only the commits of the run.
set -euo pipefail

fixture_log_commits() {
    : > .git/run-commits.log
    local hook=.git/hooks/post-commit
    mkdir -p "$(dirname "$hook")"
    printf '%s\n' '#!/bin/sh' \
        'tail -n 1 "$(git rev-parse --git-path logs/HEAD)" >> "$(git rev-parse --git-common-dir)/run-commits.log"' \
        > "$hook"
    chmod +x "$hook"
}
