#!/usr/bin/env python3
"""Merge the Claude Code project folders of git worktrees into the main project folder of their repository.

The command merge-worktree-projects runs this script. Claude Code keeps one project folder for each working
folder, in the folder projects/ of its configuration folder. A worktree folder W belongs to a main folder M
when the name of W is the name of M, then "--claude-worktrees-" or "--worktrees-", then more text. The case
of a leading drive letter ("C--" or "c--") does not count. A main folder name has neither of the two parts.

For each pair (M, W), the script does these steps:
1. It skips W if a file or a folder in W changed in the last 2 hours, unless --allow-recent names W.
   It also skips W if W is a link, if W matches two main folders, or if it cannot read W.
2. It stops the pair if W holds a link, or if M has an entry with the name of a top-level entry of W.
   The folder memory/ and the file MEMORY.md of W do not count. A stopped pair changes nothing.
3. It merges the files of W/memory into M/memory. A file with a new name moves. A file with the same
   bytes as the file of M is dropped. A file with other bytes moves as <stem>-2<ext>, or as the first free
   name up to <stem>-9<ext>. With no free name, or for a folder, the entry stays in W/memory.
4. It merges the memory index of W (W/memory/MEMORY.md, else W/MEMORY.md) into the index of M
   (M/memory/MEMORY.md, else M/MEMORY.md). It appends each pointer line of W whose link target, after
   the renames of step 3, the index of M does not name. With no index in M, it creates
   M/memory/MEMORY.md from the index of W. It removes the index of W, but it keeps it if a pointer line
   of W names a file that stays. Then it deletes W/memory if it is empty.
5. It moves the other top-level entries of W into M. It deletes W only if W is then empty.

Names compare without case on each system, so a plan is the same on Windows and on Linux.
The script never overwrites an entry, never copies, and never deletes a folder that is not empty.

Without --apply, the script prints the plan and changes nothing. The plan ends with the line PLAN <code>.
With --apply, the script needs --confirm <code> from the plan that the user approved. It makes the plan
again, and it changes nothing if the code differs. At the first failed action, it stops the run.

Output lines: DRY RUN or APPLY first, then ROOT, MAIN, EXCLUDED, SKIP, STOP, MEMORY, INDEX, MOVE,
DELETE, KEEP, NOTE, CUT, and FAILED. The last lines are TOTAL, PLAN, and RESULT. A line has at most 300
characters, and at most 120 lines come before TOTAL. Each name, path, index line, and error text
that a line holds goes through show(): text with a character that is not printable, for example a
line break, prints as a JSON string. So no name can start a line of its own.

Exit codes: 0 = plan printed or applied, 1 = an action failed, 2 = usage error,
3 = a keyword matches no main folder or more than one, 4 = the plan differs from --confirm.

It needs Python 3.7 or later and only the standard library.

Examples:
  python3 -I merge_projects.py
  python3 -I merge_projects.py my-repo --exclude=feature-x
  python3 -I merge_projects.py my-repo --apply --confirm 1a2b3c4d5e6f
"""
import argparse
import copy
import filecmp
import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path

SEGMENTS = ("--claude-worktrees-", "--worktrees-")
DRIVE = re.compile(r"^[A-Za-z]--")
LINK = re.compile(r"\]\(([^)\s]+)\)")
RECENT_SECONDS = 2 * 60 * 60
LINE_CHARS = 300
MAX_LINES = 120
MAX_DETAIL = 20
MEMORY = "memory"
INDEX = "MEMORY.md"
NOT_MIGRATED = " (not migrated, see manual resolution)"


def usage_error(message):
    print(f"error: {message}\nRun with --help for the flags.", file=sys.stderr)
    sys.exit(2)


def show(name):
    """The name for one output line. A name with a character that is not printable becomes a JSON string."""
    return name if name.isprintable() else json.dumps(name)


def cut(line):
    """The line for the output, with at most LINE_CHARS characters of it."""
    if len(line) <= LINE_CHARS:
        return line
    return f"{line[:LINE_CHARS]} ... {len(line) - LINE_CHARS} more characters"


def is_link(path):
    """True for a symbolic link, and on Windows also for a junction or another reparse point."""
    try:
        info = os.lstat(str(path))
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def key(name):
    """The form of a name for a comparison: names compare without case."""
    return name.lower()


def is_worktree_name(name):
    return any(segment in name for segment in SEGMENTS)


def is_sibling(main, name):
    """True if name is main, then a worktree segment, then more text. The case of a drive letter does not count."""
    for segment in SEGMENTS:
        prefix = main + segment
        start = name[:len(prefix)]
        if len(name) <= len(prefix):
            continue
        if DRIVE.match(prefix):
            if start[:1].lower() == prefix[:1].lower() and start[1:] == prefix[1:]:
                return True
        elif start == prefix:
            return True
    return False


def read_text(path):
    with open(str(path), encoding="utf-8", newline="") as handle:
        return handle.read()


def raise_error(error):
    raise error


def newest_change(folder):
    """The newest modification time of a file or a folder inside folder. It does not follow links."""
    newest = 0.0
    for top, dirs, files in os.walk(str(folder), onerror=raise_error):
        for name in dirs + files:
            newest = max(newest, os.lstat(os.path.join(top, name)).st_mtime)
    return newest


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keywords", nargs="*",
                        help="main folder names or keywords. A keyword matches a main folder name without case. "
                             "With none, the script takes each main folder that has a worktree folder.")
    parser.add_argument("--exclude", action="append", default=[], metavar="TEXT[,TEXT...]",
                        help="skip each folder whose name holds one of these texts, without case. "
                             "An excluded main folder skips its whole group.")
    parser.add_argument("--allow-recent", action="append", default=[], metavar="NAME",
                        help="the exact name of a worktree folder to merge although it changed in the last 2 hours")
    parser.add_argument("--root", help="the projects folder (default: $CLAUDE_CONFIG_DIR/projects, "
                                       "else ~/.claude/projects)")
    parser.add_argument("--apply", action="store_true", help="do the plan. It needs --confirm.")
    parser.add_argument("--confirm", metavar="CODE", help="the PLAN code of the dry run that the user approved")
    args = parser.parse_args(argv)
    if args.apply and not args.confirm:
        usage_error("--apply needs --confirm <code> from the PLAN line of the approved dry run.")
    if args.confirm and not args.apply:
        usage_error("--confirm works only with --apply.")
    for name in args.keywords + args.allow_recent:
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            usage_error(f"not a folder name: {show(name)}")
    if args.root:
        root = Path(args.root).expanduser()
    elif os.environ.get("CLAUDE_CONFIG_DIR"):
        root = Path(os.environ["CLAUDE_CONFIG_DIR"]).expanduser() / "projects"
    else:
        root = Path.home() / ".claude" / "projects"
    args.root = Path(os.path.abspath(str(root)))
    if not args.root.is_dir():
        usage_error(f"the projects folder does not exist: {show(str(args.root))}")
    args.exclude = [part.strip().lower() for value in args.exclude for part in value.split(",") if part.strip()]
    return args


def find_groups(root, keywords):
    """Return (groups, owners, problems).

    groups maps each chosen main folder name to its sorted worktree folder names. owners maps each worktree
    folder name to the main folder names that it matches. problems lists the keywords with no single match.
    """
    names = sorted(e.name for e in os.scandir(str(root)) if e.is_dir() or is_link(e.path))
    mains = [n for n in names if not is_worktree_name(n)]
    owners = {w: [m for m in mains if is_sibling(m, w)] for w in names if is_worktree_name(w)}
    problems, chosen = [], set()
    if keywords:
        for word in keywords:
            hits = [word] if word in mains else [m for m in mains if word.lower() in m.lower()]
            if len(hits) == 1:
                chosen.add(hits[0])
            elif not hits:
                problems.append(f"NOMATCH {show(word)}: no main folder name holds it")
            else:
                more = f" ... {len(hits) - 10} more" if len(hits) > 10 else ""
                problems.append(f"AMBIGUOUS {show(word)}: {len(hits)} main folders match: "
                                + ", ".join(show(h) for h in hits[:10]) + more)
    else:
        chosen = {m for found in owners.values() for m in found}
    groups = {m: sorted(w for w, found in owners.items() if m in found) for m in sorted(chosen)}
    return groups, owners, problems


class MainState:
    """What the main folder holds after the planned actions of the earlier pairs of its group."""

    def __init__(self, path):
        self.path = path
        self.top = {key(e.name) for e in os.scandir(str(path))}
        memory = path / MEMORY
        self.memory_exists = memory.is_dir()
        self.memory = {}
        if self.memory_exists:
            self.memory = {key(e.name): Path(e.path) for e in os.scandir(str(memory)) if e.name != INDEX}
        self.index = next((p for p in (memory / INDEX, path / INDEX) if p.is_file()), None)
        self.index_text = read_text(self.index) if self.index else None
        self.refs = set(LINK.findall(self.index_text or ""))


class Plan:
    """The actions and the output lines of one run. Making a plan reads the disk and changes nothing."""

    def __init__(self, root, exclude, allow_recent, now):
        self.root, self.exclude, self.allow_recent, self.now = root, exclude, set(allow_recent), now
        self.lines, self.actions, self.keys, self.deletes = [], [], [], []
        self.totals = {"pairs": 0, "moved": 0, "skipped": 0, "stopped": 0}

    def rel(self, path):
        return Path(path).relative_to(self.root).as_posix()

    def say(self, line, plan_key=None):
        """Add an output line. A plan key also goes into the PLAN code."""
        self.lines.append(line)
        if plan_key is not None:
            self.keys.append(plan_key)

    def act(self, action, *paths, data=None):
        self.actions.append((action, paths, data))
        self.keys.append(" ".join([action] + [self.rel(p) for p in paths] + ([json.dumps(data)] if data else [])))

    def excluded(self, name):
        return any(text in name.lower() for text in self.exclude)

    def group(self, main, siblings, owners):
        path = self.root / main
        self.say(f"MAIN {show(main)}: {len(siblings)} worktree folders", f"MAIN {main} {siblings}")
        if self.excluded(main):
            self.say(f"EXCLUDED {show(main)}: the main folder, so the whole group is skipped", f"EXCLUDED {main}")
            return
        if is_link(path):
            self.say(f"SKIP {show(main)}: the main folder is a link", f"SKIP {main} link")
            return
        try:
            state = MainState(path)
        except (OSError, ValueError) as error:
            self.say(f"SKIP {show(main)}: cannot read the main folder: {show(str(error))}", f"SKIP {main} unreadable")
            return
        for name in siblings:
            self.pair(state, name, owners[name])

    def skip(self, name, reason, plan_reason):
        self.say(f"SKIP {show(name)}: {reason}", f"SKIP {name} {plan_reason}")
        self.totals["skipped"] += 1

    def pair(self, state, name, owners):
        path = self.root / name
        if self.excluded(name):
            self.say(f"EXCLUDED {show(name)}", f"EXCLUDED {name}")
            return
        if len(owners) > 1:
            self.skip(name, f"matches {len(owners)} main folders: " + ", ".join(show(o) for o in owners), "owners")
            return
        if is_link(path):
            self.skip(name, "the folder is a link", "link")
            return
        try:
            age = self.now - newest_change(path)
        except OSError as error:
            self.skip(name, f"cannot read the folder: {show(str(error))}", "unreadable")
            return
        if age < RECENT_SECONDS and name not in self.allow_recent:
            self.skip(name, f"recent activity, the newest change is {int(age // 60)} minutes old. "
                            "Make sure that it is safe to merge.", "recent")
            return
        saved = (len(self.lines), len(self.actions), len(self.keys), copy.deepcopy(state.__dict__))
        try:
            PairPlan(self, state, name).build()
        except (OSError, ValueError) as error:
            del self.lines[saved[0]:], self.actions[saved[1]:], self.keys[saved[2]:]
            state.__dict__.update(saved[3])
            self.say(f"STOP {show(name)}: cannot read a file: {show(str(error))}", f"STOP {name} unreadable")
            self.totals["stopped"] += 1


class PairPlan:
    """The plan of one pair (M, W). It adds actions and lines to the Plan, and updates the MainState."""

    def __init__(self, plan, state, name):
        self.plan, self.state, self.name = plan, state, name
        self.path = plan.root / name
        self.renames, self.stays = {}, set()

    def detail(self, details, kind):
        for line in details[:MAX_DETAIL]:
            self.plan.say(line, line)
        if len(details) > MAX_DETAIL:
            self.plan.say(f"{kind} {show(self.name)}: ... {len(details) - MAX_DETAIL} more lines",
                          "\n".join(details[MAX_DETAIL:]))

    def stop(self, reason, names):
        more = f" ... {len(names) - MAX_DETAIL} more" if len(names) > MAX_DETAIL else ""
        self.plan.say(f"STOP {show(self.name)}: {reason}: " + ", ".join(show(n) for n in names[:MAX_DETAIL]) + more,
                      f"STOP {self.name} {reason} {names}")
        self.plan.totals["stopped"] += 1

    def build(self):
        top = sorted(os.scandir(str(self.path)), key=lambda e: e.name)
        memory = self.path / MEMORY
        has_memory = memory.is_dir() and not is_link(memory)
        facts = sorted(os.scandir(str(memory)), key=lambda e: e.name) if has_memory else []
        nested, flat = memory / INDEX, self.path / INDEX
        index = nested if nested.is_file() else flat if flat.is_file() else None
        index_text = read_text(index) if index else None
        links = [e.name for e in top if is_link(e.path)] + [f"{MEMORY}/{e.name}" for e in facts if is_link(e.path)]
        if links:
            self.stop("it holds a link, and the script never follows a link", links)
            return
        others = [e for e in top if e.name not in (MEMORY, INDEX)]
        clash = [e.name for e in others if key(e.name) in self.state.top]
        if clash:
            self.stop("the main folder has an entry with the same name", clash)
            return
        mark = len(self.plan.actions)
        self.merge_facts([e for e in facts if e.name != INDEX])
        keep_index = self.merge_index(index, index_text) if index else False
        if not keep_index and index:
            self.plan.act("remove", index)
        left = []
        if has_memory:
            if self.stays or (keep_index and index == nested):
                left.append(MEMORY)
            else:
                self.plan.act("rmdir", memory)
        if flat.is_file() and (keep_index or index != flat):
            left.append(INDEX)
        folders = sum(1 for e in others if e.is_dir(follow_symlinks=False))
        for entry in others:
            self.plan.act("move", Path(entry.path), self.state.path / entry.name)
            self.state.top.add(key(entry.name))
        if others:
            self.plan.say(f"MOVE {show(self.name)}: {len(others)} entries to the main folder "
                          f"({len(others) - folders} files, {folders} folders)")
        self.plan.totals["pairs"] += 1
        self.plan.totals["moved"] += len(others)
        if left:
            self.plan.say(f"KEEP {show(self.name)}: not empty after the merge, it still holds " + ", ".join(left),
                          f"KEEP {self.name} {left}")
        else:
            self.plan.act("rmdir", self.path)
            self.plan.deletes.append(self.name)
            self.plan.say(f"DELETE {show(self.name)}")
        if len(self.plan.actions) == mark + 1 and not left:
            self.plan.say(f"NOTE {show(self.name)}: the folder is empty")

    def merge_facts(self, facts):
        """Plan the files of W/memory, except the index."""
        state, details, moved, dropped = self.state, [], 0, 0
        target = state.path / MEMORY
        for entry in facts:
            if entry.is_dir(follow_symlinks=False):
                self.stays.add(key(entry.name))
                details.append(f"MEMORY {show(self.name)}: {show(entry.name)} stays, it is a folder")
                continue
            final = entry.name
            if key(final) in state.memory:
                if filecmp.cmp(entry.path, str(state.memory[key(final)]), shallow=False):
                    self.plan.act("drop", Path(entry.path), state.memory[key(final)])
                    dropped += 1
                    continue
                stem, ext = os.path.splitext(entry.name)
                free = [f"{stem}-{n}{ext}" for n in range(2, 10) if key(f"{stem}-{n}{ext}") not in state.memory]
                if not free:
                    self.stays.add(key(entry.name))
                    details.append(f"MEMORY {show(self.name)}: {show(entry.name)} stays, "
                                   f"no free name up to {show(stem + '-9' + ext)}")
                    continue
                final = self.renames[entry.name] = free[0]
                details.append(f"MEMORY {show(self.name)}: {show(entry.name)} moves as {show(final)}, "
                               "it needs a manual merge or review")
            if not state.memory_exists:
                self.plan.act("mkdir", target)
                state.memory_exists = True
            self.plan.act("move", Path(entry.path), target / final)
            state.memory[key(final)] = target / final
            moved += 1
        if moved or dropped:
            self.plan.say(f"MEMORY {show(self.name)}: {moved} files move, "
                          f"{dropped} files with the same bytes as in the main folder are dropped")
        self.detail(details, "MEMORY")

    def rewrite(self, line):
        """The line with each link target that merge_facts renamed replaced by its new name."""
        def swap(match):
            target = match.group(1)
            base = target.replace("\\", "/").rsplit("/", 1)[-1]
            if base not in self.renames:
                return match.group(0)
            return "](" + target[:len(target) - len(base)] + self.renames[base] + ")"
        return LINK.sub(swap, line)

    def stays_target(self, line):
        targets = LINK.findall(line)
        return bool(targets) and key(targets[0].replace("\\", "/").rsplit("/", 1)[-1]) in self.stays

    def merge_index(self, index, text):
        """Plan the memory index of W. Return True if the index of W stays."""
        state, details, keep = self.state, [], False
        newline = "\r\n" if "\r\n" in text else "\n"
        lines = text.splitlines()
        if state.index is not None:
            added = []
            for line in lines:
                if not LINK.search(line):
                    continue
                if self.stays_target(line):
                    keep = True
                    details.append(f"INDEX {show(self.name)}: keeps its index, a line points at a file that "
                                   f"stays: {show(line)}")
                    continue
                new_line = self.rewrite(line)
                target = LINK.findall(new_line)[0]
                if target in state.refs:
                    continue
                state.refs.add(target)
                added.append(new_line)
            if added:
                base = state.index_text or ""
                chunk = ("" if not base or base.endswith("\n") else newline) + "".join(a + newline for a in added)
                state.index_text = base + chunk
                self.plan.act("append", state.index, data=chunk)
            self.plan.say(f"INDEX {show(self.name)}: {len(added)} lines are appended to "
                          f"{show(self.plan.rel(state.index))}")
            details += [f"INDEX LINE {show(a)}" for a in added]
        else:
            new_lines = [line + NOT_MIGRATED if self.stays_target(line) else self.rewrite(line) for line in lines]
            created = "".join(n + newline for n in new_lines)
            if not state.memory_exists:
                self.plan.act("mkdir", state.path / MEMORY)
                state.memory_exists = True
            state.index, state.index_text = state.path / MEMORY / INDEX, created
            state.refs = set(LINK.findall(created))
            self.plan.act("create", state.index, data=created)
            self.plan.say(f"INDEX {show(self.name)}: creates {show(self.plan.rel(state.index))} from "
                          f"{show(self.plan.rel(index))}, {len(new_lines)} lines")
            details += [f"INDEX LINE {show(n)}" for n in new_lines]
        self.detail(details, "INDEX")
        return keep


def make_plan(args, now):
    groups, owners, problems = find_groups(args.root, args.keywords)
    plan = Plan(args.root, args.exclude, args.allow_recent, now)
    if problems:
        return plan, problems
    for main, siblings in groups.items():
        if siblings:
            plan.group(main, siblings, owners)
        else:
            plan.say(f"MAIN {show(main)}: no worktree folder", f"MAIN {main} none")
    named = {w for siblings in groups.values() for w in siblings}
    for name in sorted(set(args.allow_recent) - named):
        plan.say(f"NOTE --allow-recent {show(name)}: no worktree folder of this run has this name")
    return plan, []


def plan_code(plan):
    text = "\n".join(str(k) for k in plan.keys)
    return hashlib.sha256(text.encode("utf-8", "backslashreplace")).hexdigest()[:12]


def run_action(action, paths, data):
    """Do one action. Before a write, the action makes sure again that it overwrites nothing."""
    first = str(paths[0])
    if action == "move":
        target = str(paths[1])
        if is_link(first) or not os.path.lexists(first):
            raise OSError(f"the source is gone or is a link: {show(first)}")
        if os.path.lexists(target):
            raise OSError(f"the target exists: {show(target)}")
        os.rename(first, target)
    elif action == "drop":
        if not filecmp.cmp(first, str(paths[1]), shallow=False):
            raise OSError(f"the bytes differ now: {show(first)}")
        os.remove(first)
    elif action == "mkdir":
        os.mkdir(first)
    elif action in ("append", "create"):
        with open(first, "a" if action == "append" else "x", encoding="utf-8", newline="") as handle:
            handle.write(data)
    elif action == "remove":
        os.remove(first)
    elif action == "rmdir":
        os.rmdir(first)
    else:
        raise ValueError(f"unknown action: {action}")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args(argv)
    plan, problems = make_plan(args, time.time())
    if problems:
        for line in problems:
            print(cut(line))
        print("RESULT: NO PLAN. Ask the user which main folder each keyword names, and run again.")
        return 3
    code = plan_code(plan)
    print("APPLY: the approved plan." if args.apply else "DRY RUN: no file was moved, merged, or deleted.")
    lines = [f"ROOT {show(str(plan.root))}"] + plan.lines
    for line in lines[:MAX_LINES]:
        print(cut(line))
    if len(lines) > MAX_LINES:
        print(f"CUT: {len(lines) - MAX_LINES} more lines. Run the script again for one main folder.")
    totals = plan.totals
    print(f"TOTAL: {totals['pairs']} pairs merge, {totals['moved']} entries move, {len(plan.deletes)} folders "
          f"are deleted, {totals['skipped']} skipped, {totals['stopped']} stopped.")
    print(f"PLAN {code}")
    if not args.apply:
        print(f"RESULT: DRY RUN. After the user approves this plan, run again with --apply --confirm {code}.")
        return 0
    if args.confirm != code:
        print(f"RESULT: PLAN CHANGED. The plan is now {code}, not {show(args.confirm)}. Nothing changed. "
              "Show the new plan to the user.")
        return 4
    for action, paths, data in plan.actions:
        try:
            run_action(action, paths, data)
        except OSError as error:
            print(cut(f"FAILED {action} {' '.join(show(plan.rel(p)) for p in paths)}: {show(str(error))}"))
            print("RESULT: FAILED. The run stopped at the first failed action. Run a dry run again.")
            return 1
    print(f"RESULT: APPLIED {code}. {len(plan.actions)} actions done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
