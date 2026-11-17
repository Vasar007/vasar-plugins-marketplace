#!/usr/bin/env bash
# Run in Git Bash on Windows. Run one tests/evals/compare_versions.py command in WSL2, and copy its result folder back.
# The refs go to WSL2 as a git bundle, and the result comes back by a copy from Git Bash. See docs/tools.md.
# Usage: run-eval.sh [--no-wait] [--clone PATH] <repository> <ref> <result folder> <compare_versions arguments>...
#   --no-wait      start at once, also when a unit suite, a dotnet command, or another compare run is active
#   --clone PATH   the Linux path of the eval clone (default: <tools folder>/eval-clone)
# Give the compare_versions arguments without --out and --claude, for example:
#   run-eval.sh /c/src/repo my-branch results/head baseline --plugin essentials/dev-essentials --commit HEAD \
#       --model <model id> --judge-model <model id> --case <case> --scaffold --runs 3 --keep-temp
# The result folder is a folder on Windows. The exit code is the exit code of compare_versions.py.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

usage() { echo "Usage: run-eval.sh [--no-wait] [--clone PATH] <repository> <ref> <result folder> <arguments>..." >&2; exit 2; }
wait=yes clone=
while [ $# -gt 0 ]; do
    case "$1" in
        --no-wait) wait=no; shift ;;
        --clone) [ $# -ge 2 ] || usage; clone=$2; shift 2 ;;
        -*) usage ;;
        *) break ;;
    esac
done
[ $# -ge 4 ] || usage
repo=$1 ref=$2 result=$3
shift 3
tools=$(linux_tools)
clone=${clone:-$tools/eval-clone}
linux_out=$tools/out/$(date -u +%Y%m%d-%H%M%S)-$(slug "$ref")
bundle=$(bash "$TOOLS_HERE/bundle.sh" "$repo" "eval-$ref" main "$ref")
part=$(put_linux_part "$tools" eval-run.sh)
echo "LINUX RESULT FOLDER: $linux_out"
status=0
run_linux_part "$part" "$bundle" "$ref" "$linux_out" "$clone" "$wait" "$@" || status=$?
mkdir -p "$result"
if [ -d "$(unc "$linux_out")" ]; then
    cp -r "$(unc "$linux_out")/." "$result/"
    echo "COPIED TO: $result"
else
    echo "NO RESULT FOLDER: $linux_out"
fi
exit "$status"
