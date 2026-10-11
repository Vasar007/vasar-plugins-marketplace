#!/usr/bin/env python3
"""Compare a tree before and after a trim pass.

The script reports the size of each file, lost or new ids, changed protected
blocks, and references to deleted files. It uses only the standard library.
It converts CRLF to LF before it compares text. It matches the names of
deleted files without regard to case.

A regex that matches nothing in the before tree is a failure. Without this
test, a typo switches the protection off.

An allowed block is a protected block that the user approved for withdrawal.
The script tests the allow regex against the text PATH:FIRST_LINE. PATH is the
relative path with forward slashes. After the trim, the same file must still
hold one line that matches the regex. This line is the tombstone.

Exit codes: 0 = pass, 1 = an integrity check failed, 2 = usage error.

Example:
  python3 -I trim_report.py --before /path/to/backup --after /path/to/workspace \\
      --id-regex '\\bREQ-\\d+\\b' \\
      --protected-regex '(?m)^## Decision \\d+\\n\\nQuote: .*\\nDecision: .*$' \\
      --allow-changed '^notes/decisions\\.md:## Decision 3\\b' --target-percent 60

To allow the block in any file, write the regex without ^PATH, for example
':## Decision 3\\b'. Do not end the regex with $, so that it also matches the
tombstone heading.
"""
import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def usage_error(message):
    print(f"error: {message}\nRun with --help for the flags.", file=sys.stderr)
    sys.exit(2)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--before", required=True, help="backup tree (state before the trim)")
    parser.add_argument("--after", required=True, help="trimmed tree")
    parser.add_argument("--glob", default="**/*.md",
                        help="relative pattern for the files to compare (default: **/*.md)")
    parser.add_argument("--id-regex", action="append", default=[],
                        help="one id family per flag, for example '\\bREQ-\\d+\\b'")
    parser.add_argument("--protected-regex", action="append", default=[],
                        help="multiline regex. Each match must stay byte-identical.")
    parser.add_argument("--allow-changed", action="append", default=[], metavar="PATTERN",
                        help="regex for PATH:FIRST_LINE of a protected block. A matching block can "
                             "change or vanish. If it vanishes, the same file must "
                             "keep a line that matches (the tombstone).")
    parser.add_argument("--target-percent", type=float,
                        help="mark the files that keep more than this percent of their bytes")
    args = parser.parse_args()
    for name in ("before", "after"):
        if not Path(getattr(args, name)).is_dir():
            usage_error(f"--{name} is not a directory: {getattr(args, name)}")
    try:
        args.id_res = [re.compile(r) for r in args.id_regex]
        args.protected_res = [re.compile(r, re.MULTILINE) for r in args.protected_regex]
        args.allow_res = [re.compile(r) for r in args.allow_changed]
    except re.error as exc:
        usage_error(f"bad regex: {exc}")
    return args


def fail_unreadable(exc):
    usage_error(f"cannot read directory {exc.filename}: {exc.strerror}")


def load_tree(root, pattern):
    """Return the raw bytes of each file that matches the glob, by relative path."""
    root, tree = Path(root), {}
    for _ in os.walk(root, onerror=fail_unreadable):
        pass
    try:
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                tree[p.relative_to(root).as_posix()] = p.read_bytes()
    except (OSError, NotImplementedError, ValueError) as exc:
        usage_error(f"cannot read {root} with glob {pattern!r}: {exc}")
    return tree


def text(data):
    """Decode with LF endings. Invalid bytes stay distinct (surrogateescape)."""
    return data.decode("utf-8", errors="surrogateescape").replace("\r\n", "\n")


def line_count(data):
    return len(data.splitlines())


def line_of(content, offset):
    return content.count("\n", 0, offset) + 1


def head_of(block):
    lines = block.strip().splitlines()
    return lines[0].strip() if lines else "(blank)"


def size_table(before, after, target):
    print("## Sizes\n")
    print("| File | Bytes before | Bytes after | Kept % | Lines before | Lines after | Status |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    totals = [0, 0, 0, 0]
    for path in sorted(set(before) | set(after)):
        b, a = before.get(path), after.get(path)
        bb, ab = len(b or b""), len(a or b"")
        bl, al = line_count(b or b""), line_count(a or b"")
        if a is None:
            status = "deleted"
        elif b is None:
            status = "new"
        elif a == b:
            status = "kept"
        elif text(a) == text(b):
            status = "line endings only"
        elif ab == bb:
            status = "changed"
        else:
            status = "trimmed" if ab < bb else "grown"
        pct = f"{100 * ab / bb:.0f}" if b else "-"
        if target is not None and b and a is not None and 100 * ab / bb > target:
            status += f" (above {target:g}%)"
        totals = [totals[0] + bb, totals[1] + ab, totals[2] + bl, totals[3] + al]
        print(f"| {path} | {bb:,} | {ab:,} | {pct} | {bl:,} | {al:,} | {status} |")
    pct = f"{100 * totals[1] / totals[0]:.0f}" if totals[0] else "-"
    print(f"| **Total** | {totals[0]:,} | {totals[1]:,} | {pct} | {totals[2]:,} | {totals[3]:,} | |\n")


def id_check(before, after, id_res):
    failed = False
    for rx in id_res:
        ids_before = {m.group(0) for d in before.values() for m in rx.finditer(text(d))}
        ids_after = {m.group(0) for d in after.values() for m in rx.finditer(text(d))}
        missing, new = sorted(ids_before - ids_after), sorted(ids_after - ids_before)
        print(f"## Ids `{rx.pattern}`: {len(ids_before)} before, {len(ids_after)} after\n")
        if not ids_before:
            print("- FAIL: regex matched nothing in the before tree\n")
            failed = True
            continue
        print(f"- Missing: {', '.join(missing) or 'none'}")
        print(f"- New: {', '.join(new) or 'none'}\n")
        failed |= bool(missing)
    return failed


def has_tombstone(path, after_text, allow_res):
    lines = after_text.get(path, "").splitlines()
    return any(a.search(f"{path}:{line.strip()}") for a in allow_res for line in lines)


def protected_check(before, after, protected_res, allow_res):
    if not protected_res:
        return False
    print("## Protected blocks\n")
    before_text = {p: text(d) for p, d in before.items()}
    after_text = {p: text(d) for p, d in after.items()}
    problems = moved = allowed = total = 0
    for rx in protected_res:
        found = {p: [m for m in rx.finditer(t)] for p, t in before_text.items()}
        if not any(found.values()):
            print(f"- FAIL: regex matched nothing in the before tree: `{rx.pattern}`")
            problems += 1
            continue
        after_blocks = {p: [m.group(0) for m in rx.finditer(t)] for p, t in after_text.items()}
        files_with = defaultdict(set)
        for path, blocks in after_blocks.items():
            for block in blocks:
                files_with[block].add(path)
        for path in sorted(found):
            unmatched = Counter(after_blocks.get(path, []))
            for m in found[path]:
                total += 1
                block = m.group(0)
                if unmatched[block] > 0:
                    unmatched[block] -= 1
                    continue
                head = head_of(block)
                where = f"{path}:{line_of(before_text[path], m.start())}"
                key = f"{path}:{head}"
                matching = [a for a in allow_res if a.search(key)]
                if files_with[block] - {path}:
                    moved += 1
                    print(f"- IN OTHER FILE (intact, moved or deduplicated) {where}: {head[:80]}")
                elif matching and has_tombstone(path, after_text, matching):
                    allowed += 1
                    print(f"- ALLOWED {where}: {head[:80]}")
                elif matching:
                    problems += 1
                    print(f"- WITHDRAWN, NO TOMBSTONE {where}: {head[:80]}")
                else:
                    problems += 1
                    kind = "CHANGED" if head in after_text.get(path, "") else "MISSING"
                    print(f"- {kind} {where}: {head[:80]}")
    print(f"\n{total} blocks checked, {problems} missing or changed, "
          f"{allowed} allowed, {moved} in other files.\n")
    return problems > 0


def dangling_check(before, after):
    deleted = sorted(set(before) - set(after))
    if not deleted:
        return False
    print("## References to deleted files\n")
    surviving_names = {Path(p).name.lower() for p in after}
    lines = {p: text(d).splitlines() for p, d in sorted(after.items())}
    failed = False
    for path in deleted:
        name = Path(path).name
        cite = re.compile(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-]|\.\w)", re.IGNORECASE)
        hits = [f"{p}:{n}" for p, ls in lines.items()
                for n, line in enumerate(ls, 1) if cite.search(line)]
        if not hits:
            print(f"- {path}: no references")
        elif name.lower() in surviving_names:
            print(f"- {path}: AMBIGUOUS. Another `{name}` survives. Review these by hand: {', '.join(hits)}")
        else:
            failed = True
            print(f"- {path}: DANGLING in {', '.join(hits)}")
    print()
    return failed


def main():
    args = parse_args()
    sys.stdout.reconfigure(errors="backslashreplace")
    before, after = load_tree(args.before, args.glob), load_tree(args.after, args.glob)
    if not before:
        usage_error(f"no files match {args.glob!r} under {args.before}")
    size_table(before, after, args.target_percent)
    failed = id_check(before, after, args.id_res)
    failed |= protected_check(before, after, args.protected_res, args.allow_res)
    failed |= dangling_check(before, after)
    print("RESULT: FAIL" if failed else "RESULT: PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
