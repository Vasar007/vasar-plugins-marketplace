#!/usr/bin/env python3
"""Compare a tree before and after a trim pass, or apply a proven plan.

The script reports the size of each file, lost or new ids, changed protected
blocks, and references to deleted files. It uses only the standard library.
It converts CRLF to LF before it compares text. It matches the names of
deleted files without regard to case.

A regex that matches nothing in the before tree is a failure. Without this
test, a typo switches the protection off.

An allowed block is a protected block that the user approved for withdrawal.
The script tests the allow regex against the text PATH:FIRST_LINE. PATH is the
relative path with forward slashes. After the trim, the same file must still
hold at least one line that matches the regex. This line is the tombstone.

The script resolves both roots, including symbolic links. It refuses a before
tree and an after tree that are equal or that contain each other. A backup
inside the workspace can hide a loss.

Exit codes: 0 = pass, 1 = an integrity check failed, 2 = usage error.

Example:
  python3 -I trim_report.py --before /path/to/backup --after /path/to/workspace \\
      --id-regex '\\bREQ-\\d+\\b' \\
      --protected-regex '(?m)^## Decision \\d+\\n\\nQuote: .*\\nDecision: .*$' \\
      --allow-changed '^notes/decisions\\.md:## Decision 3\\b' --target-percent 60

To allow the block in any file, write the regex without ^PATH, for example
':## Decision 3\\b'. Do not end the regex with $, so that it also matches the
tombstone heading.

The subcommand apply copies the result of a proven plan into the workspace.
Run "trim_report.py apply --help" for its steps, its output, and its exit codes.
"""
import argparse
import contextlib
import io
import json
import os
import re
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

APPLY_HELP = """\
Apply the plan of one batch: copy the result of the dry run into the workspace.

The planner of the batch made two copies: --orig (the files before the plan)
and --target (the files after the plan). Both copies and the trees hold the
files that --glob matches, by the same relative paths. A file that differs
between the two copies is changed. A file only in --orig is deleted. A file
only in --target is new. The other files stay as they are. A --delete flag
for a file that the plan keeps does nothing, and the output has a KEPT line
for it.

Before it writes, the script tests the plan and the trees. If one test fails,
it changes no file:
  1. The checks pass on --orig against --target, with the same flags.
  2. Each changed or deleted file of --after equals its --orig copy, and so
     does its --before copy (the backup).
  3. No new file exists in --after.
  4. Each deleted file has a --delete flag: the user approved it at the gate.
  5. On the path of such a file in --after, no folder or file is a link, no
     file has the place of a folder, and no name differs only by case.
A file of --after that already equals --target, and a deleted file that is
gone, count as done. So a second run after a stop goes on where it stopped.

Then the script writes the changed and the new files, deletes the files, and
removes each folder that a deletion emptied. Last, it runs the checks on
--before against --after, as the report form does.

Output: one fact on each line, at most 100 lines of at most 250 characters,
then the RESULT line. The lines that need an action come first.

Exit codes: 0 = applied, and the checks pass. 1 = applied, and a check
failed. 2 = usage error, no file changed. 3 = refused, no file changed.
4 = a write failed, or a file changed after its test, and part of the plan
is applied. A Python error also exits with 1, but prints a traceback and no
RESULT line.

Example:
  python3 -I trim_report.py apply --orig /scratch/b1/orig \\
      --target /scratch/b1/target --before /path/to/backup \\
      --after /path/to/workspace --delete notes/old-log.md \\
      --id-regex '\\bREQ-\\d+\\b'
"""
MAX_LINES = 100
LINE_CHARS = 250
REFUSED = "RESULT: REFUSED. No file was changed."
WHOLE_REPORT = (" The report form with the same --before, --after, and check flags prints the whole "
                "integrity report and the whole size table.")
WHOLE_PLAN = (" The report form with --before set to the --orig folder, --after set to the --target folder, "
              "and the same check flags prints the whole report.")


def usage_error(message):
    print(f"error: {message}\nRun with --help for the flags.", file=sys.stderr)
    sys.exit(2)


def tree_flags():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--before", required=True, help="backup tree (state before the trim)")
    parser.add_argument("--after", required=True, help="trimmed tree")
    return parser


def check_flags():
    parser = argparse.ArgumentParser(add_help=False)
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
    return parser


def build_parser(apply):
    formatter = argparse.RawDescriptionHelpFormatter
    if not apply:
        return argparse.ArgumentParser(description=__doc__, formatter_class=formatter,
                                       parents=[tree_flags(), check_flags()])
    parser = argparse.ArgumentParser(prog="trim_report.py apply", description=APPLY_HELP, allow_abbrev=False,
                                     formatter_class=formatter, parents=[tree_flags(), check_flags()])
    parser.add_argument("--orig", required=True, help="the copy of the planner before the plan")
    parser.add_argument("--target", required=True, help="the copy of the planner after the plan")
    parser.add_argument("--delete", action="append", default=[], metavar="PATH",
                        help="a file that the user approved for deletion, relative to --after. One flag per file.")
    return parser


def parse_args(argv):
    apply = bool(argv) and argv[0] == "apply"
    args = build_parser(apply).parse_args(argv[1:] if apply else argv)
    args.apply = apply
    roots = [("before", args.before), ("after", args.after)]
    if apply:
        roots += [("orig", args.orig), ("target", args.target)]
    for name, value in roots:
        if not Path(value).is_dir():
            usage_error(f"--{name} is not a directory: {value}")
    resolved = [(name, Path(value).resolve()) for name, value in roots]
    for index, (first, one) in enumerate(resolved):
        for second, other in resolved[index + 1:]:
            if one == other or one in other.parents or other in one.parents:
                copies = "backup and the scratch copies" if apply else "backup"
                usage_error(f"the {first} tree and the {second} tree must not contain each other. "
                            f"Keep the {copies} outside the workspace.")
    try:
        args.id_res = [re.compile(r) for r in args.id_regex]
        args.protected_res = [re.compile(r, re.MULTILINE) for r in args.protected_regex]
        args.allow_res = [re.compile(r) for r in args.allow_changed]
    except re.error as exc:
        usage_error(f"bad regex: {exc}")
    if apply:
        args.deletions = {approved_path(raw) for raw in args.delete}
    return args


def approved_path(raw):
    """The path of a --delete flag in the form of a tree key: relative, with forward slashes."""
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or path.as_posix() == ".":
        usage_error(f"--delete needs a path relative to --after: {json.dumps(raw)}")
    return path.as_posix()


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


def checks(before, after, args):
    """The integrity checks of both forms: ids, protected blocks, and references to deleted files."""
    failed = id_check(before, after, args.id_res)
    failed |= protected_check(before, after, args.protected_res, args.allow_res)
    failed |= dangling_check(before, after)
    return failed


def captured(function, *args):
    """Run function, and return its result and the lines that it printed."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = function(*args)
    return result, buffer.getvalue().splitlines()


def is_link(path):
    """True for a symbolic link, and on Windows also for a junction or another reparse point."""
    try:
        info = os.lstat(str(path))
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def path_problem(root, rel):
    """Why the script must not write or delete root/rel, or None."""
    current, parts = Path(root), PurePosixPath(rel).parts
    for index, part in enumerate(parts):
        parent, current = current, current / part
        if is_link(current):
            return "a link is on its path in --after"
        if not os.path.lexists(str(current)):
            return None
        if part not in os.listdir(str(parent)):
            return "a name on its path differs only by case in --after"
        if index < len(parts) - 1 and not current.is_dir():
            return "a file is on its path in --after"
    return None if current.is_file() else "it is not a regular file in --after"


def read_or_none(path):
    return path.read_bytes() if os.path.lexists(str(path)) else None


def file_state(args, backup, path, old, new):
    """Return ("todo", None), ("done", None), or ("refused", reason) for one file that the plan touches."""
    after = Path(args.after)
    problem = path_problem(after, path)
    if problem:
        return "refused", problem
    if new is None and path not in args.deletions:
        return "refused", "the plan deletes it, but no --delete flag approves it"
    if old is not None and backup.get(path) != old:
        return "refused", "the backup copy is missing or differs from --orig"
    try:
        here = read_or_none(after / path)
    except OSError as exc:
        return "refused", f"cannot read it: {exc.strerror or exc}"
    if here == new:
        return "done", None
    if here == old:
        return "todo", None
    if old is None:
        return "refused", "it exists in --after already"
    if here is None:
        return "refused", "it is missing in --after"
    return "refused", "it differs from --orig and from --target. Plan this batch again from the workspace of now"


def plan_actions(args, orig, target, backup):
    """Sort each file that the plan touches into an action, done, or a refusal."""
    actions, done, refusals = [], [], []
    for path in sorted(set(orig) | set(target)):
        old, new = orig.get(path), target.get(path)
        if old == new:
            continue
        state, reason = file_state(args, backup, path, old, new)
        if state == "todo":
            actions.append(("NEW" if old is None else "DELETE" if new is None else "CHANGE", path, old, new))
        elif state == "done":
            done.append(path)
        else:
            refusals.append(f"REFUSED {path}: {reason}.")
    return actions, done, refusals


def remove_empty_parents(root, rel):
    """Remove the folders above root/rel that are empty now, up to root itself. Yield the path of each one."""
    folder = (Path(root) / rel).parent
    while folder != Path(root) and folder.is_dir() and not is_link(folder):
        with os.scandir(str(folder)) as entries:
            if any(True for _ in entries):
                break
        os.rmdir(str(folder))
        yield folder.relative_to(root).as_posix()
        folder = folder.parent


def remove_folders(root, deleted, lines):
    """Remove the folders that the deleted files emptied. Return None, or the error line of the first failure."""
    for path in deleted:
        try:
            for folder in remove_empty_parents(root, path):
                lines.append(f"REMOVED FOLDER {folder}")
        except OSError as exc:
            return f"FAILED the folder of {path}: {exc.strerror or exc}"
    return None


def run_actions(root, actions, lines):
    """Write, then delete. Return None, or the error line of the first failed action and its number."""
    order = [a for a in actions if a[0] != "DELETE"] + [a for a in actions if a[0] == "DELETE"]
    labels = {"CHANGE": "CHANGED", "NEW": "NEW", "DELETE": "DELETED"}
    for number, (kind, path, old, data) in enumerate(order):
        target = Path(root) / path
        try:
            if read_or_none(target) != old:
                return f"FAILED {path}: it changed after the test of this run", number
            if kind == "DELETE":
                os.remove(str(target))
            else:
                if kind == "NEW":
                    target.parent.mkdir(parents=True, exist_ok=True)
                with open(str(target), "xb" if kind == "NEW" else "wb") as handle:
                    handle.write(data)
            lines.append(f"{labels[kind]} {path}")
        except OSError as exc:
            return f"FAILED {path}: {exc.strerror or exc}", number
    return None


def finish(lines, result, code, whole=""):
    """Print at most MAX_LINES lines of at most LINE_CHARS characters, then the result line. Return code.

    whole is the sentence of the CUT line that says how to get the whole output.
    """
    for line in lines[:MAX_LINES]:
        print(line if len(line) <= LINE_CHARS else line[:LINE_CHARS] + " ...")
    if len(lines) > MAX_LINES:
        print(f"CUT: {len(lines) - MAX_LINES} more lines.{whole}")
    print(result)
    return code


def apply_plan(args):
    orig, target = load_tree(args.orig, args.glob), load_tree(args.target, args.glob)
    backup = load_tree(args.before, args.glob)
    load_tree(args.after, args.glob)  # A workspace that the script cannot read stops the run before a write.
    for name, tree, root in (("--orig", orig, args.orig), ("--before", backup, args.before)):
        if not tree:
            usage_error(f"no files match {args.glob!r} under {root} ({name})")
    odd = sorted(p for p in set(orig) | set(target) if not p.isprintable())
    if odd:
        usage_error(f"a path holds a character that is not printable: {json.dumps(odd[0])}")
    outside = sorted(p for p in set(orig) | set(target) if ".." in PurePosixPath(p).parts)
    if outside:
        usage_error(f"--glob must not leave the trees with '..': {json.dumps(outside[0])}")
    unknown = sorted(args.deletions - set(orig))
    if unknown:
        usage_error(f"--delete names no file of --orig: {unknown[0]}")
    plan_failed, plan_lines = captured(checks, orig, target, args)
    if plan_failed:
        lines = ["REFUSED: the plan fails its checks on --orig against --target. Repeat the dry run of step 4.",
                 ""] + plan_lines
        return finish(lines, REFUSED, 3, WHOLE_PLAN)
    actions, done, refusals = plan_actions(args, orig, target, backup)
    if refusals:
        return finish(refusals, REFUSED, 3)
    acted = []
    failure = run_actions(args.after, actions, acted)
    if not failure:
        line = remove_folders(args.after, sorted(set(orig) - set(target)), acted)
        failure = (line, len(actions)) if line else None
    if failure:
        line, number = failure
        return finish([line] + acted, f"RESULT: FAILED. {number} of {len(actions)} actions are done. "
                      "Fix the cause, then run apply again. It skips each file that is done.", 4)
    acted += [f"DONE BEFORE {path}" for path in done]
    acted = [f"KEPT {path}: this batch keeps it, so its --delete flag does nothing"
             for path in sorted(args.deletions) if target.get(path) == orig[path]] + acted
    counts = Counter(action[0] for action in actions)
    folders = sum(1 for line in acted if line.startswith("REMOVED FOLDER "))
    after = load_tree(args.after, args.glob)
    failed, check_lines = captured(checks, backup, after, args)
    _, size_lines = captured(size_table, backup, after, args.target_percent)
    lines = ["PLAN CHECK: PASS (--orig against --target)",
             f"APPLIED: {counts['CHANGE']} changed, {counts['NEW']} new, {counts['DELETE']} deleted, "
             f"{folders} folders removed, {len(done)} done before.",
             "", "## Checks (--before against --after)", ""]
    lines += check_lines + ["## Files", ""] + acted + [""] + size_lines
    return finish(lines, "RESULT: FAIL" if failed else "RESULT: PASS", 1 if failed else 0, WHOLE_REPORT)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    encoding = {"encoding": "utf-8"} if argv[:1] == ["apply"] else {}
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace", **encoding)
    args = parse_args(argv)
    if args.apply:
        return apply_plan(args)
    before, after = load_tree(args.before, args.glob), load_tree(args.after, args.glob)
    if not before:
        usage_error(f"no files match {args.glob!r} under {args.before}")
    size_table(before, after, args.target_percent)
    failed = checks(before, after, args)
    print("RESULT: FAIL" if failed else "RESULT: PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
