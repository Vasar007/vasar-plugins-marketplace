#!/usr/bin/env bash
# Runs in WSL2 or Linux. tools/wsl/run-eval.sh copies it to <tools folder>/bin and starts it.
# Run one tests/evals/compare_versions.py command in the eval clone, at a ref of a git bundle.
# Usage: eval-run.sh <bundle> <ref> <result folder> <eval clone> <wait: yes or no> <compare_versions arguments>...
# The script adds --out <result folder> and --claude <path>. Give the other arguments, also --model and --judge-model.
# A lock lets only one run use the eval clone at a time. With wait "yes", the run also waits for a quiet machine.
set -euo pipefail
cd "$HOME"
[ $# -ge 6 ] || { echo "Usage: eval-run.sh <bundle> <ref> <result folder> <eval clone> <yes|no> <arguments>..." >&2; exit 2; }
bundle=$1 ref=$2 out=$3 clone=$4 wait=$5
shift 5
case "$bundle" in /mnt/*) echo "STOP: the bundle is on a Windows drive: $bundle" >&2; exit 3 ;; esac
for arg in "$@"; do
    case "$arg" in --out | --out=* | --claude | --claude=*) echo "STOP: the script sets $arg itself" >&2; exit 2 ;; esac
done
claude=$HOME/.local/bin/claude
[ -x "$claude" ] || claude=$(command -v claude) || { echo "STOP: no claude command" >&2; exit 3; }
[ -z "${ANTHROPIC_API_KEY:-}" ] || { echo "STOP: ANTHROPIC_API_KEY is set, so the runs would use API billing" >&2; exit 3; }
auth=$("$claude" auth status 2>&1) || true
grep -Eq '"authMethod": *"claude\.ai"' <<< "$auth" || { echo "STOP: not signed in with claude.ai" >&2; exit 3; }
[ -n "$(git bundle list-heads "$bundle" "refs/heads/$ref")" ] || { echo "STOP: the bundle has no branch $ref" >&2; exit 3; }
export TMPDIR=$HOME/.cache/plugin-evals/tmp
mkdir -p "$TMPDIR" "$(dirname "$clone")" "$(dirname "$out")"
# The lock stays until the script ends. A second run waits here, so it cannot check out another ref under this run.
exec 9> "$clone.lock"
flock -n 9 || { echo "WAIT: another run holds $clone.lock"; flock 9; }
busy() { ps -eo args | grep -cE '[u]nittest discover|bin/[d]otnet (restore|build|test)|[c]ompare_versions\.py' || true; }
if [ "$wait" = yes ]; then
    [ "$(busy)" = 0 ] || echo "WAIT: a unit suite, a dotnet command, or a compare run is active"
    # Wait two times with a pause, because one run can end just before the next one starts.
    until [ "$(busy)" = 0 ]; do sleep 5; done
    sleep 6
    until [ "$(busy)" = 0 ]; do sleep 5; done
fi
[ -d "$clone/.git" ] || git -c init.defaultBranch=main -c advice.detachedHead=false clone -q --no-checkout "$bundle" "$clone"
git -C "$clone" fetch -q "$bundle" '+refs/heads/*:refs/remotes/win/*'
git -C "$clone" checkout -q --detach "win/$ref"
echo "HEAD: $(git -C "$clone" log --oneline -1)"
echo "START: $(date -u +%H:%M:%S)"
status=0
(cd "$clone" && python3 tests/evals/compare_versions.py "$@" --out "$out" --claude "$claude") < /dev/null || status=$?
echo "EXIT: $status at $(date -u +%H:%M:%S)"
exit "$status"
