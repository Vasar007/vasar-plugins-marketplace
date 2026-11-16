#!/usr/bin/env python3
"""Find out whether the fix commit of a review round broke a build or a test command.

Phase 6 of the review-loop skill runs this script after a failed build or test
run and after the Phase 7 commit. It uses only the standard library, git, and
bash. On Windows, it runs the command with the bash of Git for Windows.

Steps:
  1. Read `git status` of the main worktree. Paths that match an --ignore glob
     do not count. The main worktree is clean if nothing else is listed and
     HEAD is the fix commit.
  2. Run the command at the fix commit: in the main worktree if it is clean,
     else in a temporary worktree at the fix commit.
  3. If the command fails at the fix commit, run it in a temporary worktree at
     the commit before the fix commit.
  4. Remove each temporary worktree that this run made, in every case.

The command runs with `bash -c`, in the same folder relative to the work tree
root as --cwd, and stops after --timeout seconds. The temporary worktrees are
in a new folder below the system temporary folder, outside the repository.

The last two lines are the verdict and its reason:
  VERDICT: UNCOMMITTED     passes at the fix commit, so the main worktree causes the failure
  VERDICT: REGRESSION      fails at the fix commit and passes at the commit before it
  VERDICT: SAME-AT-PARENT  fails at both commits with the same exit code and the same error lines
  VERDICT: OTHER           any other result, for example another error, a time-out, or a
                           command that cannot start
Each MADE line has a REMOVED line after it. A MADE line with no REMOVED line
names a worktree that is still there. Remove it with `git worktree remove --force`.

Exit codes: 0 = a verdict is printed, 2 = usage error, setup error, or stop by a signal.

Example:
  python3 -I failure_check.py --fix-commit 1a2b3c4 --command "python3 -m unittest" \\
      --cwd /path/to/repo --ignore "Notes/Reviews/my-branch-*"
"""
import argparse
import fnmatch
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ERROR = re.compile(r"\b(errors?|fail(ed|ure|ures)?|exception|traceback)\b", re.IGNORECASE)
NOISE = [
    (re.compile(r"[^\s'\"]*review-loop-fc-[^/\\\s]+[/\\](fix|parent)"), "<root>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<addr>"),
    (re.compile(r"\b\d{1,2}:\d{2}:\d{2}(\.\d+)?\b"), "<time>"),
    (re.compile(r"\b\d+(\.\d+)?\s?(ms|s|sec|secs|seconds|m|min)\b"), "<time>"),
]
NOT_STARTED = (126, 127)
ERROR_LINES = 20
TAIL_LINES = 15


class Stop(Exception):
    pass


class Interrupted(BaseException):
    pass


def git(cwd, *args, check=True):
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)
    out = result.stdout.decode("utf-8", "surrogateescape")
    if check and result.returncode != 0:
        raise Stop(f"git {args[0]} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return out if check else (result.returncode, out, result.stderr.decode("utf-8", "replace"))


def find_bash():
    """Git Bash on Windows, found next to git. A plain "bash" there can start WSL. On other systems, bash on PATH."""
    if os.name != "nt":
        return shutil.which("bash")
    exec_path = Path(git(".", "--exec-path").strip())
    for root in exec_path.parents:
        for candidate in (root / "usr" / "bin" / "bash.exe", root / "bin" / "bash.exe"):
            if candidate.is_file():
                return str(candidate)
    return None


def changed_paths(top, ignore):
    out = git(top, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    items, paths, i = out.split("\0"), [], 0
    while i < len(items) and items[i]:
        status, path = items[i][:2], items[i][3:]
        i += 2 if status[0] in "RC" else 1
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in ignore):
            paths.append(path)
    return paths


class Run:
    def __init__(self, side, sha, folder, where):
        self.side, self.sha, self.folder, self.where = side, sha, folder, where
        self.code, self.timed_out, self.start_error, self.seconds, self.lines = None, False, None, 0.0, []

    @property
    def passed(self):
        return self.code == 0 and not self.timed_out

    @property
    def runnable_failure(self):
        return not self.passed and not self.timed_out and self.start_error is None and self.code not in NOT_STARTED

    def signature(self, roots):
        found = set()
        for line in self.lines:
            if ERROR.search(line):
                for root in roots:
                    line = line.replace(root, "<root>")
                for pattern, token in NOISE:
                    line = pattern.sub(token, line)
                found.add(line.strip())
        return found

    def report(self):
        if self.start_error:
            state = f"could not start: {self.start_error}"
        elif self.timed_out:
            state = f"stopped after the time limit of {self.seconds:.0f} s"
        else:
            state = f"exit {self.code} after {self.seconds:.1f} s"
        print(f"RUN {self.side} {self.sha[:12]} in {self.where} {self.folder}: {state}")
        errors = [line for line in self.lines if ERROR.search(line)]
        for line in errors[:ERROR_LINES]:
            print(f"  ERROR | {line}")
        if len(errors) > ERROR_LINES:
            print(f"  ERROR | ... {len(errors) - ERROR_LINES} more error lines")
        for line in self.lines[-TAIL_LINES:]:
            print(f"  TAIL  | {line}")


def kill_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait()


def wait(proc, deadline):
    """Wait in short steps. On Windows, a signal handler runs only between the steps."""
    while True:
        try:
            return proc.wait(timeout=max(0.0, min(0.5, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            if time.monotonic() >= deadline:
                raise


def run_command(run, bash, command, timeout, log):
    if not Path(run.folder).is_dir():
        run.start_error = f"the folder {run.folder} does not exist at this commit"
        return run
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    start = time.monotonic()
    with open(log, "wb") as out:
        try:
            proc = subprocess.Popen([bash, "-c", command], cwd=run.folder, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=subprocess.STDOUT, **options)
        except OSError as error:
            run.start_error = str(error)
            return run
        try:
            run.code = wait(proc, start + timeout)
        except subprocess.TimeoutExpired:
            run.timed_out = True
            kill_tree(proc)
        except BaseException:
            kill_tree(proc)
            raise
    run.seconds = time.monotonic() - start
    run.lines = Path(log).read_bytes().decode("utf-8", "replace").splitlines()
    return run


class Worktrees:
    """The temporary worktrees of this run. remove() deletes only these."""

    def __init__(self, top):
        self.top, self.made = top, []
        self.root = Path(tempfile.mkdtemp(prefix="review-loop-fc-")).resolve()
        try:
            self.root.relative_to(Path(top).resolve())
        except ValueError:
            pass
        else:
            self.remove()
            raise Stop(f"the temporary folder {self.root} is inside the repository. Set TMPDIR to another folder")

    def add(self, name, sha):
        path = self.root / name
        code, _, err = git(self.top, "worktree", "add", "--detach", str(path), sha, check=False)
        if code != 0:
            return None, err.strip()
        self.made.append(path)
        print(f"MADE {path}", flush=True)
        return path, None

    def remove(self):
        for path in self.made:
            code, _, err = git(self.top, "worktree", "remove", "--force", str(path), check=False)
            if code == 0:
                print(f"REMOVED {path}", flush=True)
            else:
                print(f"WARN: could not remove the worktree {path}: {err.strip()}", flush=True)
        self.made = []
        shutil.rmtree(self.root, ignore_errors=True)
        if self.root.exists():
            print(f"WARN: could not delete the folder {self.root}", flush=True)
        git(self.top, "worktree", "prune", check=False)


def verdict(clean, fix, parent, roots):
    if fix.passed:
        if clean:
            return "OTHER", "the command passed in a second run in the clean main worktree."
        return "UNCOMMITTED", "the command passes at the fix commit, so the state of the main worktree causes the failure."
    if not fix.runnable_failure:
        return "OTHER", "the command did not run to an end at the fix commit."
    if parent is None:
        return "OTHER", "the command did not run at the commit before the fix commit."
    if parent.passed:
        return "REGRESSION", "the command fails at the fix commit and passes at the commit before it."
    same = (parent.runnable_failure and parent.code == fix.code
            and fix.signature(roots) and fix.signature(roots) == parent.signature(roots))
    if same:
        return "SAME-AT-PARENT", "the command fails at both commits with the same exit code and the same error lines."
    return "OTHER", "the command fails at both commits, but the exit code or the error lines differ."


def check(args, bash):
    cwd = Path(args.cwd).resolve()
    top = Path(git(cwd, "rev-parse", "--show-toplevel").strip()).resolve()
    try:
        rel = cwd.relative_to(top)
    except ValueError:
        raise Stop(f"the folder {cwd} is not inside the work tree {top}")
    if args.fix_commit.startswith("-"):
        raise Stop("the fix commit must not start with '-'")
    fix = git(top, "rev-parse", "--verify", "--quiet", args.fix_commit + "^{commit}", check=False)
    if fix[0] != 0:
        raise Stop(f"the fix commit {args.fix_commit} is not a commit")
    fix = fix[1].strip()
    code, out, _ = git(top, "rev-parse", "--verify", "--quiet", fix + "^1^{commit}", check=False)
    if code != 0:
        raise Stop("the fix commit has no parent commit")
    parent_sha = out.strip()
    head = git(top, "rev-parse", "HEAD").strip()
    changed = changed_paths(top, args.ignore)
    clean = not changed and head == fix
    print(f"FIX {fix[:12]} PARENT {parent_sha[:12]}")
    print(f"MAIN WORKTREE: {'clean' if clean else 'not clean'}, HEAD is {head[:12]}"
          + ("" if head == fix else ", not the fix commit"))
    for path in changed:
        print(f"CHANGED: {path}")
    roots = {str(top), top.as_posix()}
    if top.drive:
        roots.add("/" + top.drive[0].lower() + top.as_posix()[len(top.drive):])
    trees = Worktrees(top)
    logs = trees.root
    try:
        if clean:
            fix_run = run_command(Run("fix", fix, cwd, "main worktree"), bash, args.command, args.timeout,
                                  logs / "fix.log")
        else:
            path, err = trees.add("fix", fix)
            fix_run = Run("fix", fix, path / rel if path else cwd, "temporary worktree")
            if path is None:
                fix_run.start_error = f"git worktree add failed: {err}"
            else:
                run_command(fix_run, bash, args.command, args.timeout, logs / "fix.log")
        fix_run.report()
        parent_run = None
        if fix_run.runnable_failure:
            path, err = trees.add("parent", parent_sha)
            parent_run = Run("parent", parent_sha, path / rel if path else cwd, "temporary worktree")
            if path is None:
                parent_run.start_error = f"git worktree add failed: {err}"
            else:
                run_command(parent_run, bash, args.command, args.timeout, logs / "parent.log")
            parent_run.report()
    finally:
        trees.remove()
    token, reason = verdict(clean, fix_run, parent_run, roots)
    print(f"VERDICT: {token}")
    print(f"REASON: {reason}")


def on_signal(number, _frame):
    raise Interrupted(number)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fix-commit", required=True, help="the Phase 7 commit of the review fixes of this round")
    parser.add_argument("--command", required=True, help="the build or test command that failed, as one bash string")
    parser.add_argument("--cwd", default=".", help="the folder where Phase 6 ran the command (default: the current folder)")
    parser.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                        help="a path glob, relative to the work tree root, that git status must ignore (repeatable)")
    parser.add_argument("--timeout", type=int, default=280, help="seconds for each run of the command (default: 280)")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be a positive number of seconds")
    for name in ("SIGTERM", "SIGHUP", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), on_signal)
    try:
        bash = find_bash()
        if bash is None:
            raise Stop("bash not found. On Windows, install Git for Windows")
        check(args, bash)
    except Stop as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (Interrupted, KeyboardInterrupt):
        print("error: stopped by a signal. The temporary worktrees are removed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
