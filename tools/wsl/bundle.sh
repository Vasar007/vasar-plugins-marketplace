#!/usr/bin/env bash
# Run in Git Bash on Windows. Write refs of a Windows clone as one git bundle into the Linux file system of WSL2.
# WSL2 then clones or fetches from that file, so no Linux command reads a Windows drive. See docs/tools.md.
# Usage: bundle.sh <repository> <name> <ref>...
# A ref that the repository does not have is left out, for example a local main in a new clone.
# The script prints the Linux path of the bundle: <tools folder>/bundles/<name>.bundle.
# The script ends with exit code 2 for a usage error.
# It ends with exit code 3 and a STOP line if the repository has no ref of the list, or if WSL2 gives no home folder.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

case "${1:-}" in -h | --help) sed -n '2,/^set -euo pipefail$/s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; exit 0 ;; esac
[ $# -ge 3 ] || { echo "Usage: bundle.sh <repository> <name> <ref>..." >&2; exit 2; }
repo=$1
name=$(slug "$2")
shift 2
refs=()
for ref in "$@"; do
    if git -C "$repo" rev-parse -q --verify "$ref^{commit}" > /dev/null; then refs+=("$ref"); fi
done
[ ${#refs[@]} -ge 1 ] || { echo "STOP: no ref of the list exists in $repo" >&2; exit 3; }
tools=$(linux_tools)
in_wsl mkdir -p "$tools/bundles"
git -C "$repo" bundle create -q "$(unc "$tools/bundles/$name.bundle")" "${refs[@]}"
printf '%s\n' "$tools/bundles/$name.bundle"
