#!/usr/bin/env python3
"""Find out whether the fix commit of a review round broke a build, test, or lint command.

Phase 6 of the review-loop skill runs this script after a failed build, test,
or lint run and after the Phase 7 commit. It needs Python 3.7 or later, git,
and bash, and uses only the standard library. On Windows, it runs the command
with the bash of Git for Windows.

Steps:
  1. Read `git status` of the main worktree. Paths that match an --ignore glob
     do not count. The main worktree is clean if nothing else is listed and
     HEAD is the fix commit.
  2. Run the command at the fix commit: in the main worktree if it is clean,
     else in a temporary worktree at the fix commit.
  3. If the command fails at the fix commit, run it in a temporary worktree at
     the commit before the fix commit.
  4. Remove each temporary worktree and export that this run made, in every case.

If `git worktree add` fails and makes no folder, the script writes the files of
the commit into that folder as a temporary export, and runs the command there.
An export is the checkout of a worktree with no git data: git writes the files
with the same line ends, links, and modes, and does not run the post-checkout
hook. In a repository with a sparse checkout, an export holds each file of the
commit. In an export, git finds no repository. So a command that reads git
data, for example a build that reads the commit, fails or gives another result
in an export. Then the verdict can be OTHER, or SAME-AT-PARENT if both runs
fail in the same way because the git data is missing. If the command passes
only in an export, the verdict is OTHER. If both runs fail and a run in an
export prints no error line, the verdict is OTHER too, because the script
cannot see a git error.

The command runs with `bash -c`, in the same folder relative to the work tree
root as --cwd, and stops after --timeout seconds. The temporary worktrees and
exports are in a new folder below the system temporary folder, outside the
repository.

Output on stdout, in this order. Each line holds one fact:
  FIX <sha> PARENT <sha>      the fix commit and the commit before it
  MAIN WORKTREE: <state>      clean or not clean, and the commit of HEAD
  CHANGED: <path>             a path that git status lists
  MADE <path>                 a temporary worktree that this run made
  NO WORKTREE: <text>         the error of git worktree add, before an export
  EXPORTED <path>             a temporary export that this run made
  RUN <side> <sha> in <folder>: <result>
                              a run of the command, with its exit code or its stop
    ERROR | <line>            an error line of that run
    TAIL  | <line>            one of the last 15 lines of that run
  REMOVED <path>              a temporary worktree or export that this run removed
  WARN: <text>                a worktree or a folder that the script cannot delete
  VERDICT: <token>
  REASON: <text>
The MADE line, or the NO WORKTREE and EXPORTED lines, and the RUN, ERROR, and
TAIL lines come one time for each run. After 20 CHANGED lines, and after 20
ERROR lines of a run, one more line of that kind gives the count of the other
paths or lines. An ERROR or TAIL line shows at most 300 characters of an
output line, and then the count of the other characters. A path with a
character that is not printable prints as a JSON string. Each error message
of the script goes to stderr.

The last two lines are the verdict and its reason:
  VERDICT: UNCOMMITTED     passes at the fix commit, so the main worktree causes the failure
  VERDICT: REGRESSION      fails at the fix commit and passes at the commit before it
  VERDICT: SAME-AT-PARENT  fails at both commits with the same exit code and the same lines
                           to compare, each with the same count
  VERDICT: OTHER           any other result, for example another error, a time-out, or a
                           command that cannot start
An error word is fail, traceback, or a word that ends with error or exception. A line with an
error word is an error line. With an error line, the lines to compare are each error line and
the lines from the first error line on, but at most the last 15 lines that are not blank. If a
line above them names a place, its text counts too, with the line and column numbers of its
first place left out. So a hit that moved to another line stays the same. So does a new hit
with the same text at another line of the same file, after a fix removed the old hit. A place
is a file name with an extension and a line number, for example src/a.py:3 or A.java:[3,5]. A
name with no extension needs a ":" after the number, as in Makefile:3: text. A 3:5 at the
start of a word, a (3,5) after a name, and a line of a code frame such as "3 | x = 1" are places
too. So is a line of Python such as File "a.py", line 3. So is a line with only a file path or
a file name and a ":", with no space. Examples are the file line of eslint stylish and of
grouped ruff. A digit of a file name stays.
With no error line, the lines to compare are each line that is not blank. Each line counts
with the number of times that it comes. A run with an error line never matches a run with none.
Before the compare, a root folder at the start of a path becomes a token. So do each time,
address, worker of pytest-xdist such as [gw1], and count of passed or skipped tests. A time
with more than one unit, such as 1s 318ms, is one time. The estimate after the time of Jest
and the parts of the duration of Vitest do not count. A count of failures or errors stays.
The line of a single test also stays, for example a PASSED line of pytest -v or an ok line of
unittest -v. So a new test can still give OTHER: its line is in the last lines, it holds an
error word or names a place, or no line of the output holds an error word.
A coverage table, for example of pytest-cov, keeps its numbers. So a fix commit that changes
covered code gives OTHER, also for the same failure.
A temporary worktree holds only the files of the commit. If the command needs a tool that the
project keeps in an ignored folder, such as node_modules, the run there fails in another way.
With a clean main worktree, the verdict is then OTHER. With a main worktree that is not clean,
both runs are in a temporary worktree and fail in the same way. Then the verdict can be
SAME-AT-PARENT for a failure that the fix commit brought. The TAIL lines then show the error of
the missing tool.
A build in the clean main worktree can skip the files that did not change. Then it prints fewer
warnings than the build at the commit before. A warning line that names a place then gives OTHER.
If the command prints the same lines for two different failures, for example only a banner,
the verdict is also SAME-AT-PARENT. A lint that prints one line for each file prints the same
lines for a new problem in a file that already fails. Then the verdict is SAME-AT-PARENT too.
In an export, such output with no error line gives OTHER.
Each MADE or EXPORTED line has a REMOVED line after it. A MADE line with no REMOVED
line names a worktree that is still there. Remove it with `git worktree remove --force`.
An EXPORTED line with no REMOVED line names a plain folder that is still there. Delete it.
A WARN line names a worktree or a folder that the script cannot delete. On Windows, a stop
runs taskkill for the process tree of the command, and then ends each process of the job object
of the command. If the command cannot join a job, taskkill can miss a Git Bash program of it.

Exit codes: 0 = a verdict is printed, 1 = the script failed with a Python traceback,
2 = usage error, setup error, or stop by a signal.

Example:
  python3 -I failure_check.py --fix-commit 1a2b3c4 --command "python3 -m unittest" \\
      --cwd /path/to/repo --ignore "notes/Reviews/my-branch-*"
"""
import argparse
import collections
import contextlib
import fnmatch
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

ERROR = re.compile(r"\b\w*?(errors?|exceptions?)\b|\b(fail(ed|ure|ures|s)?|traceback)\b", re.IGNORECASE)
# A path starts where no character of a file name comes before it.
NAME_START = r"(?<![\w./\\~-])"
# An option such as -I or the start of a file URL can come before a root.
PATH_START = NAME_START + r"(?:-{1,2}[A-Za-z][\w-]*|file:/{0,3})?"
# A line with only a file name comes first, so a name such as a(1).py: is not the place a(1).
PLACE = re.compile(r"^\S*[/\\][^\s/\\]*\.[A-Za-z]\w*:?$|^[^\s/\\:]+\.[A-Za-z]\w*:$"
                   r"|\.[A-Za-z]\w*:\[?\d+([:,]\d+)?\b|(?<![\w.:])\d+:\d+\b|\w\(\d+(,\d+){0,3}\)|^\s*\d+ +\|"
                   r"|File \"[^\"]*\", line \d+\b|(?<![\w.:/\\-])[A-Za-z_]\w*:\d+(:\d+)?:")
# A number of a place: after a space, ":", "[", ",", or "(", and before a space, ":", "]", ",", ")", or the end.
# After a ")" or a "]", the same rule holds. So in a file line, a digit of v2.py, 1-a.py, or a(1).py stays.
PLACE_NUMBER = re.compile(r"(?<![^\s:\[,(])\d+(?![^\s:\],)])(?![)\]][^\s:,)\]])")
PYTEST_COUNT = re.compile(r"\b\d+ ((subtests )?(passed|skipped)|deselected|xfailed|xpassed)\b")
TEST_COUNT = re.compile(r"\b\d+ (passed|skipped|todo|total|tests?)\b|\(\d+\)$")


def pytest_counts(match):
    """The summary line of pytest, with a token for each count of passed, skipped, deselected, xfailed, and xpassed tests."""
    return PYTEST_COUNT.sub(r"<n> \1", match.group())


def test_counts(match):
    """A count line of Jest or Vitest, with a token for each count that is not a count of failures."""
    def token(count):
        word = count.group(1)
        if word is None:
            return "(<n>)"
        return "<n> tests" if word.startswith("test") else f"<n> {word}"

    return TEST_COUNT.sub(token, match.group())


NOISE = [
    (re.compile(r"\x1b\[[0-9;]*m"), ""),
    (re.compile(NAME_START + r"(?:file:/{0,3})?(?:[A-Za-z]:)?[\w./\\~-]*review-loop-fc-\w+[/\\](fix|parent)"), "<root>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<addr>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?"), "<time>"),
    (re.compile(r"\[\d+:\d{2}<\d+:\d{2}, [^\]]*\]"), "[<time>]"),
    (re.compile(r"(?<![:.])\b\d{1,2}:\d{2}:\d{2}(\.\d+)?\b"), "<time>"),
    (re.compile(r"\b\d+(\.\d+)?\s?(ms|s|sec|secs|seconds|m|min)\b"), "<time>"),
    # A time with more than one unit, such as 1s 318ms, is one token, as 683ms is.
    (re.compile(r"<time>(?: <time>)+"), "<time>"),
    # Jest adds an estimate to its time when it knows the time of an earlier run in the same folder.
    (re.compile(r"(?<=<time>), estimated <time>"), ""),
    # Vitest adds the parts of its duration in percent, in another order in each run.
    (re.compile(r"^(\s*Duration\s+<time>) \(.*\)$"), r"\1"),
    # The worker of pytest-xdist that runs a test can change from run to run.
    (re.compile(r"\[gw\d+\]"), "[gw<n>]"),
    (re.compile(r"\bduration_ms:?\s+\d+(\.\d+)?"), "duration_ms <time>"),
    # The count rules come after the time rules, because some of them look for the token <time>.
    (re.compile(r"\bRan \d+ tests? in <time>"), "Ran <n> tests in <time>"),
    (re.compile(r"^((OK|FAILED) \(.*\bskipped=)\d+"), r"\1<n>"),
    (re.compile(r"^=+ (.*) =+$"), r"\1"),
    (re.compile(r"^\d+ [a-z]+( [a-z]+)?(, \d+ [a-z]+( [a-z]+)?)* in <time>( \(<time>\))?$"), pytest_counts),
    (re.compile(r"\[\s*\d{1,3}%\]$"), "[<n>%]"),
    (re.compile(r"\b(Passed|Skipped|Total):\s+\d+(?=, (Skipped|Total|Duration):)"), r"\1: <n>"),
    (re.compile(r"^  (total|succeeded|skipped): \d+$"), r"\1: <n>"),
    # The summary lines of Jest and Vitest, and the file line of Vitest, such as (3 tests | 1 failed).
    (re.compile(r"^(Tests|Test Suites):\s.*"), test_counts),
    (re.compile(r"^\s*(Test Files|Tests)  .*\(\d+\)$"), test_counts),
    (re.compile(r"\(\d+ tests? \|[^)]*\)"), test_counts),
    # The counts of a test assembly of Microsoft.Testing.Platform: [+<passed>/x<failed>/?<skipped>].
    (re.compile(r"\[\+\d+/x(\d+)/\?\d+\]"), r"[+<n>/x\1/?<n>]"),
]
NOT_STARTED = (126, 127)
CHANGED_LINES = 20
ERROR_LINES = 20
TAIL_LINES = 15
LINE_CHARS = 300
DEFAULT_TIMEOUT = 280
JOB_WAIT_SECONDS = 5

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    PROCESS_TERMINATE, PROCESS_SET_QUOTA, SYNCHRONIZE = 0x0001, 0x0100, 0x00100000
    JobObjectBasicProcessIdList = 3

    class JobProcessIds(ctypes.Structure):
        """The JOBOBJECT_BASIC_PROCESS_ID_LIST structure, with room for 1024 process ids."""

        _fields_ = [("assigned", wintypes.DWORD), ("listed", wintypes.DWORD), ("ids", ctypes.c_size_t * 1024)]

    KERNEL32 = ctypes.WinDLL("kernel32")
    KERNEL32.CreateJobObjectW.restype = wintypes.HANDLE
    KERNEL32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
    KERNEL32.OpenProcess.restype = wintypes.HANDLE
    KERNEL32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    KERNEL32.AssignProcessToJobObject.restype = wintypes.BOOL
    KERNEL32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    KERNEL32.TerminateJobObject.restype = wintypes.BOOL
    KERNEL32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    KERNEL32.CloseHandle.restype = wintypes.BOOL
    KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
    KERNEL32.QueryInformationJobObject.restype = wintypes.BOOL
    KERNEL32.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
                                                   wintypes.LPDWORD)
    KERNEL32.WaitForSingleObject.restype = wintypes.DWORD
    KERNEL32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)


class Stop(Exception):
    """A usage error or a setup error. main() prints its text and returns exit code 2."""


class Interrupted(BaseException):
    """A stop signal. It is not an Exception, so only main() catches it."""


def git_result(cwd, *args, env=None):
    """Run git with no input. Return its exit code, its stdout, and its stderr as one line."""
    result = subprocess.run(["git", "-C", str(cwd), *args], stdin=subprocess.DEVNULL, capture_output=True, env=env)
    err = " ".join(result.stderr.decode("utf-8", "replace").split())
    return result.returncode, result.stdout.decode("utf-8", "surrogateescape"), err


def git(cwd, *args):
    """Run git and return its stdout. A git command that fails stops the script."""
    code, out, err = git_result(cwd, *args)
    if code != 0:
        raise Stop(f"git {args[0]} failed: {err}")
    return out


def show(path):
    """The path for one output line. A path with a character that is not printable becomes a JSON string."""
    return path if path.isprintable() else json.dumps(path)


def cut(line):
    """The line for the report, with at most LINE_CHARS characters of it."""
    if len(line) <= LINE_CHARS:
        return line
    return f"{line[:LINE_CHARS]} ... {len(line) - LINE_CHARS} more characters"


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


def path_forms(path):
    """The forms in which a tool can print a folder: native, with slashes, as Git Bash, and in a file URL."""
    forms = {str(path), path.as_posix(), urllib.parse.quote(path.as_posix(), safe="/:")}
    if path.drive:
        forms.add("/" + path.drive[0].lower() + path.as_posix()[len(path.drive):])
    return forms


def changed_paths(top, ignore):
    out = git(top, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    items, paths, i = out.split("\0"), [], 0
    while i < len(items) and items[i]:
        status, path = items[i][:2], items[i][3:]
        i += 2 if status[0] in "RC" or status[1] in "RC" else 1
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in ignore):
            paths.append(path)
    return paths


class Run:
    """One run of the command at one commit, and its result."""

    def __init__(self, side, sha, folder, where):
        self.side, self.sha, self.folder, self.where = side, sha, folder, where
        self.code = None
        self.timed_out = False
        self.start_error = None
        self.seconds = 0.0
        self.lines = []
        self.limit = None

    @property
    def passed(self):
        return self.code == 0 and not self.timed_out

    @property
    def runnable_failure(self):
        return not self.passed and not self.timed_out and self.start_error is None and self.code not in NOT_STARTED

    def signature(self, roots):
        """The lines to compare and their counts, with a token for each root folder, time, address, and count of tests.

        With an error line, it takes the error lines, the last lines that are not blank from the first error line on,
        and each line that names a place, such as src/a.py:3, with a token for the numbers of the place.
        With no error line, it takes each line that is not blank.
        """
        # The longest root comes first, because one root can be the start of another root.
        ordered = sorted(roots, key=lambda root: (-len(root), root))
        rules = [(re.compile(PATH_START + re.escape(root)), "<root>") for root in ordered] + NOISE
        found = collections.Counter()
        texts = []
        for line in self.lines:
            text = line
            for pattern, token in rules:
                text = pattern.sub(token, text)
            texts.append(text)
        first = next((i for i, line in enumerate(self.lines) if ERROR.search(line)), None)
        # A blank line does not count, so one more blank line in one run does not move the last lines.
        filled = [i for i, text in enumerate(texts) if text.strip()]
        last = filled[-TAIL_LINES] if len(filled) >= TAIL_LINES else 0
        start = 0 if first is None else max(first, last)
        for i, (line, text) in enumerate(zip(self.lines, texts)):
            if i >= start or ERROR.search(line):
                found[text.strip()] += 1
            elif PLACE.search(text):
                # A fix commit often moves an old hit, so the numbers of its place do not count.
                found[PLACE.sub(lambda match: PLACE_NUMBER.sub("<n>", match.group()), text, count=1).strip()] += 1
        # The flag keeps a run with an error line apart from a run with none, also with the same lines.
        return {(first is None, text, count) for text, count in found.items() if text}

    def report(self):
        if self.start_error:
            state = f"could not start: {cut(self.start_error)}"
        elif self.timed_out:
            state = f"stopped after the time limit of {self.limit} s ({self.seconds:.0f} s with the stop)"
        else:
            state = f"exit {self.code} after {self.seconds:.1f} s"
        print(f"RUN {self.side} {self.sha[:12]} in {self.where} {self.folder}: {state}")
        errors = [line for line in self.lines if ERROR.search(line)]
        for line in errors[:ERROR_LINES]:
            print(f"  ERROR | {cut(line)}")
        if len(errors) > ERROR_LINES:
            print(f"  ERROR | ... {len(errors) - ERROR_LINES} more error lines")
        for line in self.lines[-TAIL_LINES:]:
            print(f"  TAIL  | {cut(line)}")


def join_job(proc):
    """On Windows, put the shell in a new job object. Return the job, or None if the shell cannot join it.

    Each process that the shell starts is then in the job too, also a Git Bash process whose Windows parent
    is gone. The job has no kill-on-close limit. With a breakaway limit, Git Bash programs leave the job.
    """
    if os.name != "nt":
        return None
    job = KERNEL32.CreateJobObjectW(None, None)
    process = KERNEL32.OpenProcess(PROCESS_TERMINATE | PROCESS_SET_QUOTA, False, proc.pid)
    joined = bool(job and process and KERNEL32.AssignProcessToJobObject(job, process))
    if process:
        KERNEL32.CloseHandle(process)
    if joined:
        return job
    if job:
        KERNEL32.CloseHandle(job)
    return None


def open_job_processes(job, handles):
    """Add a handle for a wait on each process that is in the job now, at most 1024. The key is the process id."""
    ids = JobProcessIds()
    KERNEL32.QueryInformationJobObject(job, JobObjectBasicProcessIdList, ctypes.byref(ids), ctypes.sizeof(ids),
                                       None)
    for pid in ids.ids[:ids.listed]:
        handle = None if pid in handles else KERNEL32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            handles[pid] = handle


def stop_job(job, pid):
    """End the process tree of the shell and the job. Then wait for the job processes, at most JOB_WAIT_SECONDS.

    taskkill reaches a process that started outside the job, and the job reaches a process whose parent is gone.
    An ended process keeps its files open for a short time, so the script waits before it deletes its folder.
    """
    handles = {}
    try:
        open_job_processes(job, handles)
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        finally:
            open_job_processes(job, handles)
            KERNEL32.TerminateJobObject(job, 1)
        deadline = time.monotonic() + JOB_WAIT_SECONDS
        for handle in handles.values():
            KERNEL32.WaitForSingleObject(handle, int(max(0.0, deadline - time.monotonic()) * 1000))
    finally:
        for handle in handles.values():
            KERNEL32.CloseHandle(handle)


def kill_tree(proc, job=None):
    """Stop the process, its children, and its job. A kill that fails means that they ended before it."""
    if os.name == "nt":
        if job is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            stop_job(job, proc.pid)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def wait(proc, deadline):
    """Wait in short steps. On Windows, a signal handler runs only between the steps."""
    while True:
        try:
            return proc.wait(timeout=max(0.0, min(0.5, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            if time.monotonic() >= deadline:
                raise


def run_command(run, bash, command, timeout, log, env=None):
    run.limit = timeout
    if not Path(run.folder).is_dir():
        run.start_error = f"the folder {run.folder} does not exist at this commit"
        return run
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    start = time.monotonic()
    with open(log, "wb") as out:
        try:
            proc = subprocess.Popen([bash, "-c", command], cwd=run.folder, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=subprocess.STDOUT, env=env, **options)
        except OSError as error:
            run.start_error = str(error)
            return run
        job = None
        try:
            job = join_job(proc)
            run.code = wait(proc, start + timeout)
        except subprocess.TimeoutExpired:
            run.timed_out = True
            kill_tree(proc, job)
        except BaseException:
            kill_tree(proc, job)
            raise
        finally:
            if job is not None:
                KERNEL32.CloseHandle(job)
    run.seconds = time.monotonic() - start
    run.lines = Path(log).read_bytes().decode("utf-8", "backslashreplace").splitlines()
    return run


def delete_tree(path):
    """Delete a folder. A failure leaves the rest of it. A read-only file of Windows becomes writable first."""
    def retry(function, target, _error):
        if os.name == "nt":
            with contextlib.suppress(OSError):
                os.chmod(target, stat.S_IWRITE)
                function(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)


class Worktrees:
    """The temporary worktrees and exports of this run. remove() deletes only these."""

    def __init__(self, top):
        self.top, self.made, self.exported = top, [], []
        self.root = Path(tempfile.mkdtemp(prefix="review-loop-fc-")).resolve()
        if Path(top).resolve() in self.root.parents:
            self.remove()
            raise Stop(f"the temporary folder {self.root} is inside the repository. Set TMPDIR to another folder")

    def add(self, name, sha):
        path = self.root / name
        try:
            code, _, err = git_result(self.top, "worktree", "add", "--detach", str(path), sha)
        finally:
            if path.exists():
                self.made.append(path)
                print(f"MADE {path}", flush=True)
        return (path, None) if code == 0 else (None, err)

    def export(self, name, sha):
        """Write the files of the commit into a new folder with no git data, as git checks out a worktree.

        The index of this export is a file in the temporary folder, so the index of the repository stays as it is.
        The export folder is the work tree of the checkout, so git reads the attributes of the commit.
        """
        path = self.root / name
        try:
            path.mkdir()
        except OSError as error:
            return None, str(error)
        self.exported.append(path)
        print(f"EXPORTED {path}", flush=True)
        env = dict(os.environ, GIT_INDEX_FILE=str(self.root / f"{name}.index"))
        code, _, err = git_result(self.top, "read-tree", sha, env=env)
        if code == 0:
            code, _, err = git_result(self.top, f"--work-tree={path}", "checkout-index", "--all", env=env)
        return (path, None) if code == 0 else (None, err)

    def command_env(self):
        """The environment of a command in an export. In it, git finds no repository above the temporary folder."""
        ceilings = [str(self.root), os.environ.get("GIT_CEILING_DIRECTORIES", "")]
        return dict(os.environ, GIT_CEILING_DIRECTORIES=os.pathsep.join(part for part in ceilings if part))

    def remove(self):
        failed = []
        for path in self.made:
            code, _, err = git_result(self.top, "worktree", "remove", "--force", str(path))
            if code == 0:
                print(f"REMOVED {path}", flush=True)
            else:
                failed.append((path, err))
        self.made = []
        exported, self.exported = self.exported, []
        delete_tree(self.root)
        for path in exported:
            if not path.exists():
                print(f"REMOVED {path}", flush=True)
        if self.root.exists():
            print(f"WARN: could not delete the folder {self.root}", flush=True)
        for path, err in failed:
            if not path.exists() and git_result(self.top, "worktree", "remove", "--force", str(path))[0] == 0:
                print(f"REMOVED {path}", flush=True)
            else:
                print(f"WARN: could not remove the worktree {path}: {err}", flush=True)


def verdict(clean, fix, parent, roots):
    """The verdict token and its reason. The parent run exists only after a fix run that failed with an exit code."""
    if fix.passed:
        if clean:
            return "OTHER", "the command passed in a second run in the clean main worktree."
        if fix.where == "temporary export":
            return "OTHER", "the command passes at the fix commit only in a temporary export, which has no git data."
        return "UNCOMMITTED", "the command passes at the fix commit, so the state of the main worktree causes the failure."
    if not fix.runnable_failure:
        return "OTHER", "the command did not run to an end at the fix commit."
    if parent.passed and parent.where == "temporary export":
        return "OTHER", ("the command passes at the commit before the fix commit only in a temporary export, "
                         "which has no git data.")
    if parent.passed:
        return "REGRESSION", "the command fails at the fix commit and passes at the commit before it."
    if not parent.runnable_failure:
        return "OTHER", "the command did not run to an end at the commit before the fix commit."
    in_export = "temporary export" in (fix.where, parent.where)
    if in_export and not any(ERROR.search(line) for line in fix.lines + parent.lines):
        return "OTHER", ("the command fails at both commits, and a temporary export has no git data. "
                         "No output line holds an error word, so the script cannot rule out missing git data.")
    signature = fix.signature(roots)
    if not signature:
        return "OTHER", ("the command fails at both commits, but the output at the fix commit has no line to "
                         "compare. It holds no error line and no line that is not blank.")
    if parent.code == fix.code and signature == parent.signature(roots):
        return "SAME-AT-PARENT", ("the command fails at both commits with the same exit code, the same error lines, "
                                  "and the same last lines after the first error line. "
                                  "With no error line, each line that is not blank and its count are the same.")
    return "OTHER", ("the command fails at both commits, but the exit code or the lines to compare differ. "
                     "With an error line, these are the error lines, the last lines after the first error line, "
                     "and the lines that name a place. With no error line, these are the lines that are not blank. "
                     "A line that comes another number of times also differs.")


def run_in_worktree(trees, side, sha, rel, args, bash):
    """Run the command in a temporary worktree at the commit, or in an export if git adds no worktree and no folder."""
    path, err = trees.add(side, sha)
    where, error, env = "temporary worktree", f"git worktree add failed: {err}", None
    if path is None and not (trees.root / side).exists():
        print(f"NO WORKTREE: {cut(err)}", flush=True)
        where, env = "temporary export", trees.command_env()
        path, export_err = trees.export(side, sha)
        error = f"git worktree add failed, and the export failed too: {export_err}"
    run = Run(side, sha, (path or trees.root / side) / rel, where)
    if path is None:
        run.start_error = error
    else:
        run_command(run, bash, args.command, args.timeout, trees.root / f"{side}.log", env)
    return run


def check(args, bash):
    cwd = Path(args.cwd).resolve()
    top = Path(git(cwd, "rev-parse", "--show-toplevel").strip()).resolve()
    try:
        rel = cwd.relative_to(top)
    except ValueError:
        raise Stop(f"the folder {cwd} is not inside the work tree {top}") from None
    if args.fix_commit.startswith("-"):
        raise Stop("the fix commit must not start with '-'")
    code, out, _ = git_result(top, "rev-parse", "--verify", "--quiet", args.fix_commit + "^{commit}")
    if code != 0:
        raise Stop(f"the fix commit {args.fix_commit} is not a commit")
    fix = out.strip()
    code, out, _ = git_result(top, "rev-parse", "--verify", "--quiet", fix + "^1^{commit}")
    if code != 0:
        if git(top, "rev-parse", "--is-shallow-repository").strip() == "true":
            raise Stop("the commit before the fix commit is not in this shallow clone. Run git fetch --deepen=1")
        raise Stop("the fix commit has no parent commit")
    parent_sha = out.strip()
    head = git(top, "rev-parse", "HEAD").strip()
    changed = changed_paths(top, args.ignore)
    clean = not changed and head == fix
    print(f"FIX {fix[:12]} PARENT {parent_sha[:12]}")
    print(f"MAIN WORKTREE: {'clean' if clean else 'not clean'}, HEAD is {head[:12]}"
          + ("" if head == fix else ", not the fix commit"))
    for path in changed[:CHANGED_LINES]:
        print(f"CHANGED: {show(path)}")
    if len(changed) > CHANGED_LINES:
        print(f"CHANGED: ... {len(changed) - CHANGED_LINES} more paths")
    trees = Worktrees(top)
    roots = path_forms(top) | path_forms(trees.root / "fix") | path_forms(trees.root / "parent")
    try:
        if clean:
            fix_run = run_command(Run("fix", fix, cwd, "main worktree"), bash, args.command, args.timeout,
                                  trees.root / "fix.log")
        else:
            fix_run = run_in_worktree(trees, "fix", fix, rel, args, bash)
        fix_run.report()
        parent_run = None
        if fix_run.runnable_failure:
            parent_run = run_in_worktree(trees, "parent", parent_sha, rel, args, bash)
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
    parser.add_argument("--command", required=True, help="the build, test, or lint command that failed, as one bash string")
    parser.add_argument("--cwd", default=".", help="the folder where Phase 6 ran the command (default: the current folder)")
    parser.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                        help="a path glob, relative to the work tree root, that git status must ignore (repeatable)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="seconds for each run of the command (default: %(default)s)")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
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
        print("error: stopped by a signal, so there is no verdict", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
