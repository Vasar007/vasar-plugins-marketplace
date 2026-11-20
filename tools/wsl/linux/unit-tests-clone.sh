#!/usr/bin/env bash
# Runs in WSL2 or Linux. tools/wsl/unit-tests.sh copies it to <tools folder>/bin and starts it.
# Run the whole unit suite in a fresh clone of one branch, with a release of the simple-english linter.
# Usage: unit-tests-clone.sh <tools folder> <bundle> <branch> <linter tag or latest> <tail lines> <private mount: yes or no>
# The private mount gives the run its own /tmp/plugin-evals, so it does not touch the NuGet folder of an eval run.
set -euo pipefail
cd "$HOME"
[ $# -eq 6 ] || { echo "Usage: unit-tests-clone.sh <tools folder> <bundle> <branch> <tag> <lines> <yes|no>" >&2; exit 2; }
tools=$1 bundle=$2 branch=$3 tag=$4 lines=$5 private=$6
case "$bundle" in /mnt/*) echo "STOP: the bundle is on a Windows drive: $bundle" >&2; exit 3 ;; esac
[ -f "$bundle" ] || { echo "STOP: no bundle $bundle" >&2; exit 3; }
[ -n "$(git bundle list-heads "$bundle" "refs/heads/$branch")" ] || { echo "STOP: the bundle has no branch $branch" >&2; exit 3; }
linter_url=https://github.com/AminBlg/SimpleEnglish.git
if [ "$tag" = latest ]; then
    tag=$(git ls-remote --tags --refs "$linter_url" 'v*' | sed -n 's#.*refs/tags/\(v[0-9][0-9.]*\)$#\1#p' | sort -V | tail -n 1)
    [ -n "$tag" ] || { echo "STOP: cannot read the release tags of $linter_url" >&2; exit 3; }
fi
linter=$tools/simple-english-$tag
if [ ! -d "$linter/.git" ]; then
    # Clone into a folder of this run, then rename it. So another run never uses a clone that is not complete.
    git -c init.defaultBranch=main -c advice.detachedHead=false clone -q --depth 1 --branch "$tag" "$linter_url" "$linter.$$"
    mv -T "$linter.$$" "$linter" 2> /dev/null || rm -rf -- "$linter.$$"
fi
# Each run has its own clone folder, so two runs of one branch do not delete the clone of each other.
clone=$tools/test-clones/$(printf '%s' "$branch" | tr -c 'A-Za-z0-9._-' '_').$$
mkdir -p "$tools/test-clones"
git -c init.defaultBranch=main -c advice.detachedHead=false clone -q --no-checkout "$bundle" "$clone"
git -C "$clone" checkout -q "$branch"
echo "HEAD: $(git -C "$clone" log --oneline -1)"
echo "LINTER: $tag $(git -C "$linter" log --oneline -1)"
export TMPDIR=$HOME/.cache/plugin-evals/tmp SIMPLE_ENGLISH_DIR=$linter PATH=$HOME/.local/bin:$PATH
mkdir -p "$TMPDIR"
log=$clone.log
status=0
if [ "$private" = yes ]; then
    nuget=$tools/nuget-private
    mkdir -p "$nuget"
    unshare -r -m bash -c 'mkdir -p /tmp/plugin-evals && mount --bind "$1" /tmp/plugin-evals && cd "$2" &&
        python3 -m unittest discover -s tests -v' sh "$nuget" "$clone" < /dev/null > "$log" 2>&1 || status=$?
else
    (cd "$clone" && python3 -m unittest discover -s tests -v) < /dev/null > "$log" 2>&1 || status=$?
fi
echo "FULL LOG: $log"
grep -E '^(FAIL|ERROR):|\.\.\. skipped |Retry of [^:]*: dotnet crashed' "$log" || true
tail -n "$lines" "$log"
rm -rf -- "$clone"
exit "$status"
