#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
sed -i 's/^- The repo has no build step\. Do not look for one\.$/- Build command: `python3 tools\/build_docs.py`. It builds the HTML docs with the shared theme./' CLAUDE.md
grep -q 'Build command: `python3 tools/build_docs.py`' CLAUDE.md
fixture_write tools/build_docs.py <<'PAGER_EOF'
"""Build the HTML docs of the pager package with the shared docs theme."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT.parent / "pager-docs-theme"


def main():
    """Write one HTML page for each Markdown file. Return the exit code."""
    layout = THEME / "layout.html"
    if not layout.is_file():
        print("error: the docs theme is missing. Clone the pager-docs-theme repository next to this repository.", file=sys.stderr)
        return 1
    out = ROOT / "build" / "docs"
    out.mkdir(parents=True, exist_ok=True)
    page = layout.read_text(encoding="utf-8")
    for source in sorted(ROOT.glob("*.md")):
        (out / (source.stem + ".html")).write_text(page.replace("{body}", source.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"built {len(list(out.glob('*.html')))} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
PAGER_EOF
printf 'build/\n' >> .gitignore
fixture_commit "add the docs build"
add_paging_branch
fixture_publish feature/paging
