#!/usr/bin/env bash
# Run in Git Bash on Windows. Run the whole unit suite of one committed branch in a fresh clone in WSL2.
# The branch goes to WSL2 as a git bundle, so no Linux command reads a Windows drive. See docs/tools.md.
# Usage: unit-tests.sh [--linter-tag TAG] [--tail N] [--no-private-mount] <repository> <branch>
#   --linter-tag TAG     the release of the simple-english linter (default: the newest release tag)
#   --tail N             the last lines of the log to print (default: 8)
#   --no-private-mount   run without the private /tmp/plugin-evals (use it only when no eval run is active)
# The exit code is the exit code of the unit suite.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

usage() { echo "Usage: unit-tests.sh [--linter-tag TAG] [--tail N] [--no-private-mount] <repository> <branch>" >&2; exit 2; }
tag=latest lines=8 private=yes
while [ $# -gt 0 ]; do
    case "$1" in
        --linter-tag) [ $# -ge 2 ] || usage; tag=$2; shift 2 ;;
        --tail) [ $# -ge 2 ] || usage; lines=$2; shift 2 ;;
        --no-private-mount) private=no; shift ;;
        -*) usage ;;
        *) break ;;
    esac
done
[ $# -eq 2 ] || usage
case "$lines" in '' | *[!0-9]*) usage ;; esac
repo=$1 branch=$2
tools=$(linux_tools)
bundle=$(bash "$TOOLS_HERE/bundle.sh" "$repo" "unit-$branch" main "$branch")
part=$(put_linux_part "$tools" unit-tests-clone.sh)
run_linux_part "$part" "$tools" "$bundle" "$branch" "$tag" "$lines" "$private"
