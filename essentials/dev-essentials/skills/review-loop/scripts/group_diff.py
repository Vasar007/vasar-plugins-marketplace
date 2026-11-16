#!/usr/bin/env python3
"""Group the changed files of a diff into review areas. Uses only the standard library and git.

The large-target mode of the review-loop skill gives one Area Explorer to each
area. The script reads `git diff --numstat` and `git diff --raw` of the range.
It changes nothing in the repository.

Rules, in this order:
  1. A lock file, a file that .gitattributes marks linguist-generated, and a
     file with an "auto-generated" or "do not edit" comment in its first 10
     lines go to the area "skipped". This area is never split.
  2. A file in the root folder goes to the area "root".
  3. Each other file goes to the area of its top-level folder.
  4. While an area has more than 10 files or more than 800 changed lines, it
     splits by the next folder level. The files that sit directly in the split
     folder stay in an area with the name of that folder.
  5. An area with no next folder level does not split. Only a file with more
     than 800 changed lines leaves it, as an area of its own.
Changed lines are added plus deleted lines. A binary file counts 0 lines.
In each area, production files come before test files.

Output: one TOTAL line, then for each area an AREA line and one line for each
file: the change kind, +added, -deleted, the path, and the old path of a
rename. A path with a control character prints as a JSON string.

Exit codes: 0 = the areas are printed, 2 = usage error or git error.

Example:
  python3 -I group_diff.py --repo /path/to/repo --range origin/main...HEAD
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import PurePosixPath

MAX_FILES = 10
MAX_LINES = 800
HEADER_LINES = 10
HEADER_BYTES = 64 * 1024
HEADER = re.compile(r"^\s*(#|//|/\*|\*|<!--|--|;|')(.*?)(auto-?generated|do not edit)", re.IGNORECASE | re.MULTILINE)
MARKDOWN_HEADER = re.compile(r"^\s*<!--(.*?)(auto-?generated|do not edit)", re.IGNORECASE | re.MULTILINE)
LOCK_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "poetry.lock",
    "Gemfile.lock", "composer.lock", "packages.lock.json", "go.sum",
}
TEST_DIRS = {"test", "tests", "__tests__"}
TEST_NAMES = ("test_*", "*_test.*", "*.test.*", "*.spec.*", "*Test.*", "*Tests.*")
KINDS = {"A": "added", "C": "copied", "D": "deleted", "M": "modified", "R": "renamed", "T": "type-changed"}
ZERO = re.compile(r"^0+$")
DIFF = ["diff", "--no-color", "--no-ext-diff", "--no-textconv", "--no-relative", "-M", "-z"]


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def git(repo, *args, data=None):
    result = subprocess.run(["git", "-C", repo, *args], input=data, capture_output=True)
    if result.returncode != 0:
        fail(f"git {args[0]} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def count(text):
    """The number of a numstat column. A binary file has "-" there."""
    return None if text == "-" else int(text)


def fields(data):
    return data.decode("utf-8", "surrogateescape").split("\0")


class Change:
    def __init__(self, path, old, added, deleted):
        self.path, self.old, self.added, self.deleted = path, old, added, deleted
        self.kind, self.blob, self.skip = "modified", None, None

    @property
    def lines(self):
        return (self.added or 0) + (self.deleted or 0)

    @property
    def parts(self):
        return PurePosixPath(self.path).parts

    @property
    def is_test(self):
        name = self.parts[-1]
        return bool(TEST_DIRS & {p.lower() for p in self.parts[:-1]}) or any(
            fnmatch.fnmatchcase(name, pattern) for pattern in TEST_NAMES)


def read_numstat(repo, rng):
    items = fields(git(repo, *DIFF, "--numstat", rng, "--"))
    changes, i = [], 0
    while i < len(items) and items[i]:
        added, deleted, path = items[i].split("\t", 2)
        old = None
        if path == "":
            old, path = items[i + 1], items[i + 2]
            i += 2
        i += 1
        changes.append(Change(path, old, count(added), count(deleted)))
    return changes


def read_raw(repo, rng, changes):
    """Set the change kind and the blob that holds the new content of each file."""
    by_path = {c.path: c for c in changes}
    items = fields(git(repo, *DIFF, "--raw", "--no-abbrev", rng, "--"))
    i = 0
    while i < len(items) and items[i].startswith(":"):
        meta = items[i].split()
        status = meta[4][0]
        if status in "RC":
            path = items[i + 2]
            i += 3
        else:
            path = items[i + 1]
            i += 2
        change = by_path.get(path)
        if change is None:
            continue
        change.kind = KINDS.get(status, "modified")
        blob = meta[2] if status == "D" else meta[3]
        change.blob = None if ZERO.match(blob) else blob


def mark_skipped(repo, changes):
    top = git(repo, "rev-parse", "--show-toplevel").decode("utf-8", "surrogateescape").strip()
    for c in changes:
        if c.parts[-1] in LOCK_FILES:
            c.skip = "lock file"
    paths = [c.path for c in changes if not c.skip]
    if paths:
        out = fields(git(top, "check-attr", "-z", "--stdin", "linguist-generated",
                         data="\0".join(paths).encode("utf-8", "surrogateescape") + b"\0"))
        generated = {out[i] for i in range(0, len(out) - 2, 3) if out[i + 2] in ("set", "true")}
        for c in changes:
            if c.path in generated:
                c.skip = "linguist-generated"
    text = [c for c in changes if not c.skip and c.added is not None]
    blobs = read_blobs(repo, sorted({c.blob for c in text if c.blob}))
    for c in text:
        if c.blob:
            data = blobs.get(c.blob, b"")
        else:
            try:
                with open(PurePosixPath(top, c.path), "rb") as handle:
                    data = handle.read(HEADER_BYTES)
            except OSError:
                data = b""
        head = "\n".join(data.decode("utf-8", "replace").splitlines()[:HEADER_LINES])
        rule = MARKDOWN_HEADER if c.path.lower().endswith((".md", ".markdown")) else HEADER
        if rule.search(head):
            c.skip = "generated header"


def read_blobs(repo, shas):
    """The content of each blob, from one `git cat-file --batch` process."""
    out = git(repo, "cat-file", "--batch", data="".join(s + "\n" for s in shas).encode("ascii"))
    blobs, pos = {}, 0
    for sha in shas:
        end = out.index(b"\n", pos)
        header = out[pos:end].split()
        pos = end + 1
        if len(header) == 3:
            size = int(header[2])
            blobs[sha] = out[pos:pos + size]
            pos += size + 1
    return blobs


def fits(files):
    return len(files) <= MAX_FILES and sum(f.lines for f in files) <= MAX_LINES


def leaf(name, files):
    """An area with no next folder level. Only a file over the line limit leaves it."""
    if fits(files):
        return [(name, files)]
    big = [f for f in files if f.lines > MAX_LINES]
    rest = [f for f in files if f.lines <= MAX_LINES]
    return ([(name, rest)] if rest else []) + [(f.path, [f]) for f in big]


def folder(name, files, depth):
    if fits(files):
        return [(name, files)]
    direct = [f for f in files if len(f.parts) == depth + 1]
    groups = {}
    for f in files:
        if len(f.parts) > depth + 1:
            groups.setdefault(f.parts[depth], []).append(f)
    if not groups:
        return leaf(name, files)
    areas = leaf(name, direct) if direct else []
    for key in sorted(groups):
        areas += folder(f"{name}{key}/", groups[key], depth + 1)
    return areas


def build_areas(changes):
    normal = [c for c in changes if not c.skip]
    root = [c for c in normal if len(c.parts) == 1]
    tops = {}
    for c in normal:
        if len(c.parts) > 1:
            tops.setdefault(c.parts[0], []).append(c)
    areas = leaf("root", root) if root else []
    for key in sorted(tops):
        areas += folder(f"{key}/", tops[key], 1)
    skipped = [c for c in changes if c.skip]
    if skipped:
        areas.append(("skipped", skipped))
    return areas


def show(path):
    return json.dumps(path) if any(ord(ch) < 32 or ord(ch) == 127 for ch in path) else path


def count_text(n):
    return "bin" if n is None else str(n)


def file_line(c):
    text = f"  {c.kind} +{count_text(c.added)} -{count_text(c.deleted)} {show(c.path)}"
    if c.old is not None:
        text += f" <- {show(c.old)}"
    if c.skip:
        text += f" [{c.skip}]"
    elif c.is_test:
        text += " [test]"
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--range", required=True, help="the diff range, for example origin/main...HEAD")
    parser.add_argument("--repo", default=".", help="a folder in the work tree (default: the current folder)")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    if args.range.startswith("-"):
        fail("the range must not start with '-'")
    changes = read_numstat(args.repo, args.range)
    read_raw(args.repo, args.range, changes)
    mark_skipped(args.repo, changes)
    areas = build_areas(changes)
    added = sum(c.added or 0 for c in changes)
    deleted = sum(c.deleted or 0 for c in changes)
    print(f"TOTAL files={len(changes)} added={added} deleted={deleted} areas={len(areas)}")
    for number, (name, files) in enumerate(areas, 1):
        files = sorted(files, key=lambda c: (c.is_test, c.path))
        print(f"AREA {number} {show(name)} files={len(files)} lines={sum(f.lines for f in files)}")
        for c in files:
            print(file_line(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
