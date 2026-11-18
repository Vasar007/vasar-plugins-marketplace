#!/usr/bin/env python3
"""Make, remove, and prune the git worktrees of a repository below its folder .claude/worktrees/.

The skill git-worktree-management runs this script. It needs Python 3.7 or later and git 2.31 or later,
and it uses only the standard library. It asks for no input: git gets no terminal prompt, so a fetch that
needs a password fails. The repository root is the main worktree, the first entry of "git worktree list".
The folder of a branch is <root>/.claude/worktrees/<branch>, with the slashes of the branch name. The
script refuses each path outside that folder.

Subcommands:
  create <branch> [--base <branch>] [--add-exclude] [--notes-dir <folder>] [--plan]
      1. Check the branch name, the path, and the ignore rule for .claude/worktrees/. If no rule ignores
         the folder, refuse, or with --add-exclude add the line ".claude/worktrees/" to the local file
         info/exclude of git. Git does not track that file.
      2. Pick the case. B: the local branch exists. C: only origin has the branch. A: a new branch from
         origin/<base>. Without --base, the base is the branch of origin/HEAD.
      3. Fetch the start branch from origin (cases A and C), and run "git worktree add". In cases A and C,
         the new branch has no upstream (--no-track).
      4. Bootstrap: remove the upstream of the branch if it has one, copy .claude/settings.local.json of
         the main worktree if git ignores that file and the new worktree has no such file, and make the
         notes folder (default Notes).
      With --plan, do step 1 and step 2 only: print the plan and change nothing. A missing ignore rule
      then gives an IGNORE line and no refusal.
  remove <branch> [--apply]
      Without --apply, print the plan and change nothing. With --apply, run "git worktree remove <path>".
      It refuses a folder that git does not list, a locked worktree, a worktree with a change or an
      untracked file, and a run from a folder inside the worktree. It never passes --force. The removal
      also deletes the ignored files of the worktree, and an IGNORED line names each one first. The branch
      and its commits stay.
  prune [--apply]
      Without --apply, print the entries that "git worktree prune" removes and change nothing. With
      --apply, run it. It refuses if an entry is outside .claude/worktrees/. A prune deletes no folder. It
      removes only the git data of a worktree whose folder is gone.

Each subcommand also takes --repo <folder> (default: the current folder).

Output on stdout, one fact on each line: MODE, REPO, REF, PATH, CASE, BASE, IGNORE, EXCLUDE, FETCHED,
MADE, UPSTREAM, SETTINGS, NOTES, BRANCH, HEAD, FOLDER, CHANGED, IGNORED, PRUNE, REFUSED, STEP, FAILED,
LEFT, and REMOVED. The last line is RESULT. A line shows at most 300 characters, and then the count of
the other characters. At most 20 lines of each kind of path come, and then one line gives the count of
the others. A path or a name with a character that is not printable prints as a JSON string.

If a create stops after a FAILED line, each LEFT line names what the failed step left: a branch, a
folder, or a worktree that git lists. If a bootstrap step fails, the worktree exists, and the RESULT line
says so. Do that step by hand.

Exit codes: 0 = done, or the plan is ready, 1 = a git step or a bootstrap step failed (a FAILED line),
or the script failed with a Python traceback, 2 = usage error or setup error (no git, git older than
2.31, no git work tree, a bare repository, or a git command that fails during the checks), 3 = refused
(a REFUSED line). Nothing changes with exit code 2 or 3.

Examples:
  python3 -I worktree.py create feature/tasks/1370383-add-export --base main --add-exclude
  python3 -I worktree.py remove feature/tasks/1370383-add-export --apply
  python3 -I worktree.py prune
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePath

REMOTE = "origin"
FOLDER = (".claude", "worktrees")
EXCLUDE_LINE = ".claude/worktrees/"
SETTINGS = (".claude", "settings.local.json")
DEFAULT_NOTES = "Notes"
MIN_GIT = (2, 31)
LINE_CHARS = 300
MAX_PATHS = 20


class Stop(Exception):
    """A setup error. main() prints its text and returns exit code 2."""


class Refused(Exception):
    """A reason to change nothing. main() prints a REFUSED line and returns exit code 3."""


class Failed(Exception):
    """A git step that failed after the checks. The text names the step and the git error."""


def show(text):
    """The text for one output line. A text with a character that is not printable becomes a JSON string."""
    return text if text.isprintable() else json.dumps(text)


def emit(line):
    """Print one output line with at most LINE_CHARS characters of it."""
    if len(line) > LINE_CHARS:
        line = f"{line[:LINE_CHARS]} ... {len(line) - LINE_CHARS} more characters"
    print(line)


def emit_all(kind, items):
    """Print one line for each item, at most MAX_PATHS of them, and one line with the count of the others."""
    for item in items[:MAX_PATHS]:
        emit(f"{kind} {show(item)}")
    if len(items) > MAX_PATHS:
        emit(f"{kind} ... {len(items) - MAX_PATHS} more")


def git_result(cwd, *args):
    """Run git with no input and no terminal prompt. Return its exit code, its stdout, and its stderr as one line."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-C", str(cwd), *args], stdin=subprocess.DEVNULL, capture_output=True, env=env)
    err = " ".join(result.stderr.decode("utf-8", "replace").split())
    return result.returncode, result.stdout.decode("utf-8", "surrogateescape"), err


def git(cwd, *args):
    """Run git and return its stdout. A git command that fails stops the script with exit code 2."""
    code, out, err = git_result(cwd, *args)
    if code != 0:
        raise Stop(f"git {args[0]} failed: {err}")
    return out


def norm(path):
    """The real path in a form that compares right, also on a file system with no case."""
    return os.path.normcase(os.path.realpath(str(path)))


def inside(path, folder):
    """True if path is below folder, after links are resolved."""
    child, parent = norm(path), norm(folder)
    try:
        return child != parent and os.path.commonpath([child, parent]) == parent
    except ValueError:  # Two drives on Windows.
        return False


class Entry:
    """One worktree that "git worktree list --porcelain" prints."""

    def __init__(self, fields):
        self.path = Path(fields["worktree"])
        self.head = fields.get("HEAD", "")
        self.branch = fields.get("branch")
        self.bare = "bare" in fields
        self.locked = fields.get("locked")
        self.prunable = fields.get("prunable")


def list_worktrees(cwd):
    entries = []
    for block in git(cwd, "worktree", "list", "--porcelain").split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if "worktree" in fields:
            entries.append(Entry(fields))
    return entries


class Repo:
    """The main worktree and the folder of the worktrees of the repository that holds --repo."""

    def __init__(self, folder):
        code, _, err = git_result(folder, "rev-parse", "--git-dir")
        if code != 0:
            raise Stop(f"not inside a git repository ({err}): {show(str(folder))}")
        entries = list_worktrees(folder)
        if not entries or entries[0].bare:
            raise Stop("a bare repository has no main worktree")
        self.root = entries[0].path
        if "\n" in str(self.root):
            raise Stop("the path of the repository has a line break")
        self.folder = self.root.joinpath(*FOLDER)
        if not inside(self.folder, self.root):
            raise Stop(f"the folder {show(str(self.folder))} is not inside the repository")

    def entries(self):
        return list_worktrees(self.root)

    def entry_at(self, path):
        return next((entry for entry in self.entries() if norm(entry.path) == norm(path)), None)

    def path_of(self, ref):
        path = self.folder.joinpath(*ref.split("/"))
        if not inside(path, self.folder):
            raise Refused(f"the path {show(str(path))} is outside {EXCLUDE_LINE}")
        return path


def check_branch(repo, name, what):
    """Refuse a name that is not a valid branch name, for example one with '..', '@{', or a leading '.' or '-'."""
    if not name or name == "@" or not name.isprintable():
        raise Refused(f"{what} {show(name)} is not a valid branch name")
    code, out, _ = git_result(repo.root, "check-ref-format", "--branch", name)
    if code != 0 or out.strip() != name:
        raise Refused(f"{what} {show(name)} is not a valid branch name")


def has_ref(repo, ref):
    return git_result(repo.root, "show-ref", "--verify", "--quiet", ref)[0] == 0


def short(sha):
    return sha[:12] if sha else "none"


def find_base(repo, base):
    """The base branch: --base, or the branch of origin/HEAD. Return the name and where it came from."""
    if base is not None:
        check_branch(repo, base, "the base")
        return base, "from --base"
    code, out, _ = git_result(repo.root, "symbolic-ref", "--quiet", f"refs/remotes/{REMOTE}/HEAD")
    prefix = f"refs/remotes/{REMOTE}/"
    if code != 0 or not out.strip().startswith(prefix):
        raise Refused(f"{REMOTE}/HEAD is not set, so the base branch is not known. Give --base <branch>")
    name = out.strip()[len(prefix):]
    check_branch(repo, name, "the base")
    return name, f"from {REMOTE}/HEAD"


def ignore_rule(repo):
    """The git rule that ignores the worktree folder, or None. check-ignore needs no real file."""
    code, out, _ = git_result(repo.root, "check-ignore", "-v", "/".join(FOLDER) + "/placeholder")
    if code == 0:
        return out.split("\t", 1)[0].strip()
    return None


def fetch(repo, branch):
    code, _, err = git_result(repo.root, "fetch", "--quiet", REMOTE,
                              f"+refs/heads/{branch}:refs/remotes/{REMOTE}/{branch}")
    if code != 0:
        raise Failed(f"git fetch: {err}")
    emit(f"FETCHED {REMOTE} {show(branch)}")


def plan_create(repo, args):
    """Check everything that create needs. Print the facts and return the case, the start point, and the path."""
    ref = args.ref
    check_branch(repo, ref, "the branch")
    path = repo.path_of(ref)
    emit(f"REF {show(ref)}")
    emit(f"PATH {show(str(path))}")
    entries = repo.entries()
    if any(norm(entry.path) == norm(path) for entry in entries):
        raise Refused("git already lists a worktree at this path. Use it, or remove it first")
    if os.path.lexists(str(path)):
        raise Refused("the folder exists, and git does not list it as a worktree. Look at its files first")
    holder = next((entry for entry in entries if entry.branch == f"refs/heads/{ref}"), None)
    if holder is not None:
        raise Refused(f"the branch is checked out in the worktree {show(str(holder.path))}")
    rule = ignore_rule(repo)
    if rule is None and not args.add_exclude and not args.plan:
        raise Refused(f"no git rule ignores {EXCLUDE_LINE}. Add it to .gitignore, or run again with --add-exclude")
    if has_ref(repo, f"refs/heads/{ref}"):
        case, start = "B", None
        emit("CASE B: the local branch")
    else:
        code, out, err = git_result(repo.root, "ls-remote", "--heads", REMOTE, f"refs/heads/{ref}")
        if code != 0:
            raise Failed(f"git ls-remote: {err}")
        if f"refs/heads/{ref}" in [line.split("\t", 1)[-1] for line in out.splitlines()]:
            case, start = "C", ref
            emit(f"CASE C: a new local branch from {REMOTE}/{show(ref)}")
        else:
            base, source = find_base(repo, args.base)
            case, start = "A", base
            emit(f"CASE A: a new branch from {REMOTE}/{show(base)}")
            emit(f"BASE {show(base)} ({source})")
    if case != "A" and args.base is not None:
        emit(f"BASE {show(args.base)} not used, because the branch exists")
    if rule is not None:
        emit(f"IGNORE {EXCLUDE_LINE} is ignored by {show(rule)}")
    else:
        emit(f"IGNORE none. No git rule ignores {EXCLUDE_LINE}")
    return case, start, path, rule


def add_exclude(repo):
    """Add the ignore line to the local exclude file of the common git folder."""
    common = Path(git(repo.root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    exclude = common / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    text = exclude.read_bytes() if exclude.is_file() else b""
    with open(str(exclude), "ab") as out:
        out.write((b"" if not text or text.endswith(b"\n") else b"\n") + EXCLUDE_LINE.encode("ascii") + b"\n")
    emit(f"EXCLUDE added {EXCLUDE_LINE} to {show(str(exclude))}")


def report_left(repo, path):
    """After a failed step, print a LEFT line for the folder and for the worktree entry of git, if they exist."""
    if os.path.lexists(str(path)):
        emit(f"LEFT folder {show(str(path))}")
    try:
        listed = repo.entry_at(path) is not None
    except Stop as error:
        emit(f"LEFT unknown: {error}")
        return
    if listed:
        emit(f"LEFT worktree {show(str(path))}, which git lists")


def bootstrap(repo, ref, path, notes):
    """The steps after git worktree add. Return the number of steps that failed."""
    failed = 0
    try:
        code, out, _ = git_result(repo.root, "config", "--get", f"branch.{ref}.merge")
        if code == 0:
            git(repo.root, "branch", "--unset-upstream", ref)
            emit(f"UPSTREAM removed, it was {show(out.strip())}")
        else:
            emit("UPSTREAM none")
    except Stop as error:
        failed += 1
        emit(f"FAILED the removal of the upstream: {error}")
    source, target = repo.root.joinpath(*SETTINGS), path.joinpath(*SETTINGS)
    try:
        if not source.is_file():
            emit("SETTINGS none in the main worktree")
        elif os.path.lexists(str(target)):
            emit("SETTINGS the branch has its own .claude/settings.local.json, so it stays")
        elif git_result(path, "check-ignore", "-q", "/".join(SETTINGS))[0] != 0:
            emit("SETTINGS not copied: git does not ignore .claude/settings.local.json, so the copy would be an "
                 "untracked file")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source), str(target))
            emit("SETTINGS copied .claude/settings.local.json")
    except OSError as error:
        failed += 1
        emit(f"FAILED the copy of .claude/settings.local.json: {error}")
    folder = path / notes
    try:
        folder.mkdir(parents=True, exist_ok=True)
        emit(f"NOTES {show(str(folder))}")
    except OSError as error:
        failed += 1
        emit(f"FAILED the notes folder: {error}")
    return failed


def create(repo, args):
    emit("MODE CREATE")
    emit(f"REPO {show(str(repo.root))}")
    try:
        case, start, path, rule = plan_create(repo, args)
    except Failed as error:
        emit(f"FAILED {error}")
        emit("RESULT: FAILED. Nothing changed.")
        return 1
    ref = args.ref
    if case == "B":
        command = ["worktree", "add", str(path), ref]
    else:
        command = ["worktree", "add", "--no-track", "-b", ref, str(path), f"refs/remotes/{REMOTE}/{start}"]
    if args.plan:
        if rule is None and args.add_exclude:
            emit(f"STEP add {EXCLUDE_LINE} to the local exclude file of git")
        if case != "B":
            emit(f"STEP git fetch {REMOTE} {show(start)}")
        emit(f"STEP git {show(' '.join(command))}")
        emit("RESULT: READY. Nothing changed. Run again without --plan.")
        return 0
    try:
        if rule is None:
            add_exclude(repo)
        if case != "B":
            fetch(repo, start)
        code, _, err = git_result(repo.root, *command)
        if code != 0:
            raise Failed(f"git worktree add: {err}")
    except Failed as error:
        emit(f"FAILED {error}")
        code, out, _ = git_result(repo.root, "rev-parse", "--verify", "--quiet", f"refs/heads/{ref}")
        if case != "B" and code == 0:
            emit(f"LEFT branch {show(ref)} at {short(out.strip())}, made by git worktree add -b. It has no new commit")
        report_left(repo, path)
        emit("RESULT: FAILED. No worktree was made.")
        return 1
    emit(f"MADE {show(str(path))}")
    failed = bootstrap(repo, ref, path, args.notes_dir)
    if failed:
        emit(f"RESULT: CREATED, BUT {failed} BOOTSTRAP STEPS FAILED. The worktree of {show(ref)} is at "
             f"{show(str(path))}. Do each FAILED step by hand.")
        return 1
    emit(f"RESULT: CREATED. The worktree of {show(ref)} is at {show(str(path))}.")
    return 0


def changes(path, *extra):
    """The status entries of a worktree, as git status --porcelain prints them, without the NUL ends."""
    out = git(path, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=normal", *extra)
    return [entry for entry in out.split("\0") if entry]


def remove(repo, args):
    emit("MODE REMOVE APPLY" if args.apply else "MODE REMOVE PLAN: nothing changes")
    emit(f"REPO {show(str(repo.root))}")
    ref = args.ref
    check_branch(repo, ref, "the branch")
    path = repo.path_of(ref)
    emit(f"REF {show(ref)}")
    emit(f"PATH {show(str(path))}")
    entry = repo.entry_at(path)
    if entry is None:
        if os.path.lexists(str(path)):
            raise Refused("git does not list this folder as a worktree. The script does not delete it")
        raise Refused("no worktree is at this path")
    branch = entry.branch[len("refs/heads/"):] if entry.branch and entry.branch.startswith("refs/heads/") else None
    emit(f"BRANCH {show(branch) if branch else 'none (detached HEAD)'}")
    emit(f"HEAD {short(entry.head)}")
    refusals = []
    if entry.locked is not None:
        refusals.append(f"the worktree is locked ({show(entry.locked) or 'no reason'}). Run git worktree unlock first")
    if not path.is_dir():
        emit("FOLDER missing. git still lists the worktree")
    else:
        if norm(os.getcwd()) == norm(path) or inside(os.getcwd(), path):
            refusals.append(f"the current folder is inside the worktree. Change to {show(str(repo.root))} first")
        changed = changes(path)
        emit_all("CHANGED", changed)
        if changed:
            refusals.append(f"the worktree has changes or untracked files: {len(changed)}. "
                            "Commit them, or move them out, first")
        ignored = [entry[3:] for entry in changes(path, "--ignored=matching") if entry.startswith("!! ")]
        emit_all("IGNORED", ignored)
    for reason in refusals:
        emit(f"REFUSED: {reason}")
    if refusals:
        emit("RESULT: REFUSED. Nothing changed. Each REFUSED line gives a reason.")
        return 3
    emit(f"STEP git worktree remove {show(str(path))}")
    if not args.apply:
        emit("RESULT: READY. Nothing changed. Run again with the same arguments and --apply.")
        return 0
    code, _, err = git_result(repo.root, "worktree", "remove", str(path))
    if code != 0:
        emit(f"FAILED git worktree remove: {err}")
        report_left(repo, path)
        emit("RESULT: FAILED. Read the LEFT lines.")
        return 1
    emit(f"REMOVED {show(str(path))}")
    emit(f"RESULT: REMOVED. The branch {show(branch) if branch else '(none)'} and its commits stay.")
    return 0


def prune(repo, args):
    emit("MODE PRUNE APPLY" if args.apply else "MODE PRUNE PLAN: nothing changes")
    emit(f"REPO {show(str(repo.root))}")
    stale = [entry for entry in repo.entries() if entry.prunable is not None]
    emit_all("PRUNE", [f"{entry.path} ({entry.prunable or 'no reason'})" for entry in stale])
    outside = [entry for entry in stale if not inside(entry.path, repo.folder)]
    if not stale:
        emit("RESULT: NOTHING TO PRUNE. Nothing changed.")
        return 0
    for entry in outside[:MAX_PATHS]:
        emit(f"REFUSED: the entry {show(str(entry.path))} is outside {EXCLUDE_LINE}")
    if outside:
        emit("RESULT: REFUSED. Nothing changed. Each REFUSED line gives a reason.")
        return 3
    emit("STEP git worktree prune")
    if not args.apply:
        emit("RESULT: READY. Nothing changed. Run again with the same arguments and --apply.")
        return 0
    code, _, err = git_result(repo.root, "worktree", "prune")
    if code != 0:
        emit(f"FAILED git worktree prune: {err}")
        emit("RESULT: FAILED.")
        return 1
    try:
        left = [entry for entry in stale if repo.entry_at(entry.path) is not None]
    except Stop as error:
        emit(f"FAILED the check after the prune: {error}")
        emit("RESULT: FAILED.")
        return 1
    emit_all("LEFT worktree", [str(entry.path) for entry in left])
    if left:
        emit("RESULT: FAILED. git still lists each LEFT worktree.")
        return 1
    emit(f"RESULT: PRUNED. git no longer lists {len(stale)} worktrees.")
    return 0


def check_git():
    if shutil.which("git") is None:
        raise Stop("git not found")
    found = re.search(r"(\d+)\.(\d+)", git(".", "version"))
    if found is None or (int(found.group(1)), int(found.group(2))) < MIN_GIT:
        raise Stop(f"git {MIN_GIT[0]}.{MIN_GIT[1]} or later is needed")


def notes_folder(value):
    """An argparse type: a relative folder that stays inside the worktree."""
    path = PurePath(value)
    if not path.parts or path.is_absolute() or path.drive or path.root or ".." in path.parts:
        raise argparse.ArgumentTypeError(f"not a relative folder inside the worktree: {show(value)}")
    return path


def parse_args(argv):
    common = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    common.add_argument("--repo", default=".", metavar="PATH",
                        help="a folder of the repository (default: the current folder)")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", metavar="{create,remove,prune}")
    commands.required = True
    make = commands.add_parser("create", parents=[common], allow_abbrev=False,
                               help="make the worktree of a branch and bootstrap it")
    make.add_argument("ref", metavar="BRANCH", help="the full branch name, for example feature/tasks/123-add-export")
    make.add_argument("--base", metavar="BRANCH",
                      help="the base branch of a new branch (default: the branch of origin/HEAD)")
    make.add_argument("--add-exclude", action="store_true",
                      help="if no git rule ignores .claude/worktrees/, add it to the local exclude file of git")
    make.add_argument("--notes-dir", type=notes_folder, default=PurePath(DEFAULT_NOTES), metavar="FOLDER",
                      help="the notes folder to make, relative to the worktree (default: %(default)s)")
    make.add_argument("--plan", action="store_true", help="print the plan only, and change nothing")
    drop = commands.add_parser("remove", parents=[common], allow_abbrev=False,
                               help="remove the worktree of a branch. Without --apply, print the plan only")
    drop.add_argument("ref", metavar="BRANCH", help="the full branch name of the worktree")
    drop.add_argument("--apply", action="store_true", help="remove. Without it, the script prints the plan only.")
    clean = commands.add_parser("prune", parents=[common], allow_abbrev=False,
                                help="prune the git data of worktrees whose folder is gone. "
                                     "Without --apply, print the plan only")
    clean.add_argument("--apply", action="store_true", help="prune. Without it, the script prints the plan only.")
    return parser.parse_args(argv)


def execute(args):
    """Run the subcommand. Return the exit code."""
    try:
        check_git()
        repo = Repo(Path(args.repo))
        return {"create": create, "remove": remove, "prune": prune}[args.command](repo, args)
    except Stop as error:
        print(f"error: {error}"[:LINE_CHARS], file=sys.stderr)
        return 2
    except Refused as error:
        emit(f"REFUSED: {error}")
        emit("RESULT: REFUSED. Nothing changed.")
        return 3


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
    return execute(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
