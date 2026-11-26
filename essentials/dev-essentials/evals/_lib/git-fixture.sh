#!/usr/bin/env bash
# Git setup for eval fixtures. A scaffold sources this file. It is not meant to run alone.
#
# fixture_init, fixture_commit, fixture_write: build a repo in the current folder.
# fixture_remote_init: add a bare remote at .remote/origin.git inside the workspace. The remote URL is an absolute path.
# fixture_publish: push every branch, then turn on the reflogs that the graders read.
# fixture_notes_folder: name notes/ as the notes folder in CLAUDE.md, and commit it.
# Every commit has the subject prefix "fixture:", so that a grader can tell it from a commit of the run.
#
# dotnet-backend-dev has a git symlink to this file. A test makes sure that the link is there.
set -euo pipefail

FIXTURE_CLOCK="${FIXTURE_CLOCK:-1767225600}"
FIXTURE_CLOCK_STEP=60

fixture_init() {
    git init -q -b main
    git config user.name "Eval User"
    git config user.email "eval@example.com"
    git config commit.gpgsign false
    git config core.autocrlf false
    git config core.logAllRefUpdates true
}

# Write standard input to a file, and make the folders of the path.
fixture_write() {
    mkdir -p "$(dirname "$1")"
    cat > "$1"
}

# Commit all changes with a fixed date. The subject gets the prefix "fixture: ".
fixture_commit() {
    local subject="$1"
    FIXTURE_CLOCK=$((FIXTURE_CLOCK + FIXTURE_CLOCK_STEP))
    git add -A
    GIT_AUTHOR_DATE="$FIXTURE_CLOCK +0000" GIT_COMMITTER_DATE="$FIXTURE_CLOCK +0000" \
        git commit -q --allow-empty -m "fixture: ${subject#fixture: }"
}

# Name the folder notes/ in CLAUDE.md as the notes folder, and commit the line.
fixture_notes_folder() {
    printf '%s
' '- Notes folder: `notes/`.' >> CLAUDE.md
    fixture_commit "name the notes folder"
}

# Add the bare remote origin inside the workspace. A sandboxed run can write only there.
# The URL is absolute, so that a push or a fetch from a linked worktree finds the remote. A relative URL starts at the
# top folder of the current worktree. The agent works in the folder of the scaffold, so the path stays right for the run.
fixture_remote_init() {
    git init -q --bare -b main .remote/origin.git
    git remote add origin "$PWD/.remote/origin.git"
    mkdir -p .git/info
    printf '.remote/\n' >> .git/info/exclude
}

# fixture_publish <work-branch> [<pull-id>:<branch> ...]
# Push every branch and each pull request ref, point origin/HEAD at main, and set the upstream of the work branch.
# Then log the ref updates of the remote, so that a later push of the run leaves a reflog file.
# As on GitHub, a hook of the remote moves each pull request ref to the new tip when a later push changes its branch.
fixture_publish() {
    local work_branch="$1"
    shift
    git push -q origin --all
    local pull
    for pull in "$@"; do
        git push -q origin "refs/heads/${pull#*:}:refs/pull/${pull%%:*}/head"
    done
    git remote set-head origin main > /dev/null
    git branch -q --set-upstream-to="origin/$work_branch" "$work_branch"
    git -C .remote/origin.git config core.logAllRefUpdates always
    git -C .remote/origin.git config core.hooksPath hooks
    [ $# -gt 0 ] || return 0
    local hook=.remote/origin.git/hooks/post-receive
    mkdir -p "$(dirname "$hook")"
    {
        printf '#!/bin/sh\nwhile read -r old new ref; do\n'
        printf '    case "$new" in *[!0]*) ;; *) continue ;; esac\n'
        for pull in "$@"; do
            printf '    if [ "$ref" = "refs/heads/%s" ]; then git update-ref "refs/pull/%s/head" "$new"; fi\n' \
                "${pull#*:}" "${pull%%:*}"
        done
        printf 'done\n'
    } > "$hook"
    chmod +x "$hook"
}
