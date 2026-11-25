#!/usr/bin/env python3
"""Move finished notes files to a backup folder outside the workspace.

The save-context command picks the files. This script only moves them, and it
never deletes a file. Without --apply, it prints the plan and changes nothing.
It uses only the standard library and git. If the workspace is not inside a git
work tree, no file counts as tracked.

The script refuses a path in these cases: the path does not exist, is not a
regular file, is a symbolic link, is outside the workspace, or comes twice.
It also refuses a path that git tracks, and a path whose target in the backup
folder exists. If it refuses one path, it moves no file at all.

The backup folder and the workspace must not contain each other. A backup
inside the workspace looks like a notes file to the next cleanup.

Each file keeps its path relative to the workspace inside the backup folder.
The default backup folder is ~/save-context-backups/<workspace name>-<UTC time>.
Pass the BACKUP folder of the plan to the --apply run, so that both runs use
the same folder.

Exit codes: 0 = plan printed or files moved, 1 = a path was refused, 2 = usage error.

Example:
  python3 -I backup_move.py --workspace /path/to/repo notes/Plans/old-plan.md
  python3 -I backup_move.py --workspace /path/to/repo \\
      --backup ~/save-context-backups/repo-20261025-101500 --apply notes/Plans/old-plan.md
"""
import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def usage_error(message):
    print(f"error: {message}\nRun with --help for the flags.", file=sys.stderr)
    sys.exit(2)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", default=".",
                        help="root folder of the notes: the repository root, or a notes folder outside git (default: the current folder)")
    parser.add_argument("--backup",
                        help="backup folder outside the workspace "
                             "(default: ~/save-context-backups/<workspace name>-<UTC time>)")
    parser.add_argument("--apply", action="store_true",
                        help="move the files. Without it, the script prints the plan only.")
    parser.add_argument("paths", nargs="+", help="files to move, relative to the workspace or absolute")
    args = parser.parse_args()
    if not Path(args.workspace).is_dir():
        usage_error(f"--workspace is not a folder: {args.workspace}")
    args.workspace = Path(args.workspace).resolve()
    if args.backup:
        args.backup = Path(args.backup).expanduser().resolve()
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        args.backup = (Path.home() / "save-context-backups" / f"{args.workspace.name}-{stamp}").resolve()
    workspace, backup = args.workspace, args.backup
    if backup == workspace or workspace in backup.parents or backup in workspace.parents:
        usage_error("the backup folder and the workspace must not contain each other. "
                    "Keep the backup outside the workspace.")
    if backup.exists() and not backup.is_dir():
        usage_error(f"--backup is not a folder: {backup}")
    return args


def tracked_paths(workspace, keys):
    """The keys that git tracks. Each key is a path relative to the workspace, with forward slashes."""
    if not keys:
        return set()
    inside = subprocess.run(["git", "-C", str(workspace), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return set()
    result = subprocess.run(["git", "--literal-pathspecs", "-C", str(workspace), "ls-files", "-z", "--", *keys],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        usage_error(f"git ls-files failed in {workspace}: {result.stderr.strip()}")
    return {p for p in result.stdout.split("\0") if p}


def plan(args):
    """Return the moves as (key, source, target) and the refusals as (given path, reason)."""
    moves, refusals, seen = [], [], set()
    for given in args.paths:
        path = Path(given)
        if not path.is_absolute():
            path = args.workspace / path
        if path.is_symlink():
            refusals.append((given, "is a symbolic link"))
            continue
        source = path.resolve()
        if not source.exists():
            refusals.append((given, "does not exist"))
            continue
        if not source.is_file():
            refusals.append((given, "is not a regular file"))
            continue
        try:
            rel = source.relative_to(args.workspace)
        except ValueError:
            refusals.append((given, "is outside the workspace"))
            continue
        key = rel.as_posix()
        if key in seen:
            refusals.append((given, "comes twice"))
            continue
        seen.add(key)
        target = args.backup / rel
        if target.exists():
            refusals.append((given, f"exists in the backup folder: {target}"))
            continue
        moves.append((key, source, target))
    tracked = tracked_paths(args.workspace, [key for key, _, _ in moves])
    refusals += [(key, "git tracks it") for key, _, _ in moves if key in tracked]
    moves = [move for move in moves if move[0] not in tracked]
    return moves, refusals


def main():
    args = parse_args()
    sys.stdout.reconfigure(errors="backslashreplace")
    moves, refusals = plan(args)
    print(f"WORKSPACE {args.workspace}")
    print(f"BACKUP {args.backup}")
    for given, reason in refusals:
        print(f"REFUSE {given}: {reason}")
    if refusals:
        print(f"RESULT: REFUSED {len(refusals)}. No file moved.")
        sys.exit(1)
    if not args.apply:
        for key, _, _ in moves:
            print(f"MOVE {key}")
        print(f"RESULT: PLAN {len(moves)}. Run again with --apply to move.")
        return
    for key, source, target in moves:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        print(f"MOVED {key}")
    print(f"RESULT: MOVED {len(moves)}")


if __name__ == "__main__":
    main()
