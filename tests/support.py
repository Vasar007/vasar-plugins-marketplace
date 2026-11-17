"""Paths and helpers that the repository tests share."""
import os
import subprocess
import sys
from pathlib import Path

from testkit import load_module  # Re-export: three test files import it from here.

# Keep __pycache__ folders out of the plugin folders, which ship to users.
sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parent.parent
IN_CI = os.environ.get("CI") == "true"


# Folders with copies of third-party text. The lint tests skip them, because the upstream project owns the text.
VENDORED = {
    "tests/evals/stubs/simple-english/": "Byte copy of simple-english 2.1.1 (MIT) for the eval runs. "
                                         "The upstream project owns the text.",
}


def without_vendored(paths):
    """The paths that are not under a VENDORED folder."""
    return [p for p in paths if not p.startswith(tuple(VENDORED))]


def tracked_markdown_files():
    """The tracked .md files that are in the work tree and not vendored, as paths relative to the repository root."""
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--", "*.md"],
                         capture_output=True, text=True, check=True).stdout
    return sorted(p for p in without_vendored(out.split("\0")) if p and (REPO / p).is_file())


def run_with_open_stdin(cmd, env=None, timeout=60):
    """Run cmd with a pipe as stdin that stays open and gets no data. Return (exit code, stdout, stderr) as text.

    Return None if cmd still runs after timeout seconds. Then cmd, or a child of cmd, waits for input.
    In that case, the function closes the pipe and waits until cmd ends.
    """
    read_end, write_end = os.pipe()
    try:
        proc = subprocess.Popen([str(part) for part in cmd], stdin=read_end, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env)
    finally:
        os.close(read_end)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        out = None
    os.close(write_end)
    if out is None:
        proc.communicate()
        return None
    return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def tool_missing(test, message):
    """Skip on a developer machine. Fail in CI, where every tool must exist."""
    if IN_CI:
        test.fail(message)
    test.skipTest(message)
