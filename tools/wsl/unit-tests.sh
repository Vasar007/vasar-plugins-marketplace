#!/usr/bin/env bash
# Run in Git Bash on Windows. Run the whole unit suite of one committed branch in a fresh clone in WSL2.
# The branch goes to WSL2 as a git bundle, so no Linux command reads a Windows drive. See docs/tools.md.
# Usage: unit-tests.sh [--linter-tag TAG] [--tail N] [--no-private-mount] <repository> <branch>
#   --linter-tag TAG     the release of the simple-english linter (default: the newest release tag)
#   --tail N             the last lines of the log to print (default: 8)
#   --no-private-mount   run without the private /tmp/plugin-evals (use it only when no eval run is active)
# The exit code is the exit code of the unit suite.
# The script itself ends with exit code 2 for a usage error.
# It ends with exit code 3 and a STOP line if the repository does not have the branch, or if a copy into WSL2 fails.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

usage() { echo "Usage: unit-tests.sh [--linter-tag TAG] [--tail N] [--no-private-mount] <repository> <branch>" >&2; exit 2; }
tag=latest lines=8 private=yes
while [ $# -gt 0 ]; do
    case "$1" in
        -h | --help) sed -n '2,/^set -euo pipefail$/s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; exit 0 ;;
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
# The bundle has the process id in its name, so two runs of one branch do not write one file. The trap removes it.
bundle=$(bash "$TOOLS_HERE/bundle.sh" "$repo" "unit-$branch.$$" main "$branch")
trap 'in_wsl rm -f -- "$bundle" || true' EXIT
part=$(put_linux_part "$tools" unit-tests-clone.sh)
run_linux_part "$part" "$tools" "$bundle" "$branch" "$tag" "$lines" "$private"
