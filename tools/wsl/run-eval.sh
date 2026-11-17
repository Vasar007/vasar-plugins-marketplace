#!/usr/bin/env bash
# Run in Git Bash on Windows. Run one tests/evals/compare_versions.py command in WSL2, and copy its result folder back.
# The refs go to WSL2 as a git bundle, and the result comes back by a copy from Git Bash. See docs/tools.md.
# Usage: run-eval.sh [--no-wait] [--clone PATH] <repository> <ref> <result folder> <compare_versions arguments>...
#   --no-wait      do not wait for a quiet machine. The run still waits for the lock of the eval clone
#   --clone PATH   the Linux path of the eval clone (default: <tools folder>/eval-clone)
# Give the compare_versions arguments without --out and --claude, for example:
#   run-eval.sh /c/src/repo my-branch results/head baseline --plugin essentials/dev-essentials --commit HEAD \
#       --model <model id> --judge-model <model id> --case <case> --scaffold --runs 3 --keep-temp
# The result folder is a folder on Windows. It must be empty or new.
# The exit code is the exit code of compare_versions.py.
# The script itself ends with exit code 2 for a usage error, and for --out or --claude in the arguments.
# It ends with exit code 3 and a STOP line if ANTHROPIC_API_KEY is set, or if the sign-in is not claude.ai.
# It also does so if the repository does not have the ref, or if the result folder is not empty.
# If this script stops before the run ends, the run goes on in WSL2. Its result stays in the LINUX RESULT FOLDER.
# wsl.exe makes one backslash from two in a row, so give no argument with two backslashes in a row.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

usage() { echo "Usage: run-eval.sh [--no-wait] [--clone PATH] <repository> <ref> <result folder> <arguments>..." >&2; exit 2; }
wait=yes clone=
while [ $# -gt 0 ]; do
    case "$1" in
        -h | --help) sed -n '2,/^set -euo pipefail$/s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; exit 0 ;;
        --no-wait) wait=no; shift ;;
        --clone) [ $# -ge 2 ] || usage; clone=$2; shift 2 ;;
        -*) usage ;;
        *) break ;;
    esac
done
[ $# -ge 4 ] || usage
repo=$1 ref=$2 result=$3
shift 3
mkdir -p "$result" || { echo "STOP: cannot make the result folder $result" >&2; exit 3; }
[ -z "$(ls -A "$result")" ] || { echo "STOP: the result folder is not empty: $result" >&2; exit 3; }
tools=$(linux_tools)
clone=${clone:-$tools/eval-clone}
# The process id keeps the names of two runs apart, also when they start in the same second.
linux_out=$tools/out/$(date -u +%Y%m%d-%H%M%S)-$$-$(slug "$ref")
bundle=$(bash "$TOOLS_HERE/bundle.sh" "$repo" "eval-$ref.$$" main "$ref")
trap 'in_wsl rm -f -- "$bundle" || true' EXIT
part=$(put_linux_part "$tools" eval-run.sh)
echo "LINUX RESULT FOLDER: $linux_out"
status=0
run_linux_part "$part" "$bundle" "$ref" "$linux_out" "$clone" "$wait" "$@" || status=$?
if [ -d "$(unc "$linux_out")" ]; then
    cp -r "$(unc "$linux_out")/." "$result/"
    echo "COPIED TO: $result"
else
    echo "NO RESULT FOLDER: $linux_out"
fi
exit "$status"
