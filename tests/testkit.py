"""Generic helpers for unittest tests: a temporary folder, environment copies, child processes, and git.

Another repository keeps a byte copy of this file. Make each change here, and keep the file generic:
use only the standard library, name no path of this repository, and use no syntax newer than Python 3.7.
"""
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RUN_SECONDS = 60


def remove_tree(path):
    """Delete a folder. Make a read-only file writable and try again, because git makes read-only files on Windows."""
    def fix(function, target, _error):
        os.chmod(target, stat.S_IWRITE)
        function(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=fix)
    else:
        shutil.rmtree(path, onerror=fix)


class ScratchCase(unittest.TestCase):
    """A test case with a new temporary folder in self.tmp. A cleanup deletes the folder after each test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(remove_tree, self.tmp)

    def assertResult(self, result, code, *texts):
        """Fail unless the process exited with code, and its stdout and stderr together contain each text."""
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, output)
        for text in texts:
            self.assertIn(text, output)


def clean_env(drop=(), **values):
    """A copy of os.environ without the keys in drop, and with the values added."""
    env = {key: value for key, value in os.environ.items() if key not in drop}
    env.update(values)
    return env


def run(cmd, stdin=None, env=None, cwd=None, timeout=RUN_SECONDS):
    """Run cmd, and capture stdout and stderr as UTF-8 text. A byte that is not UTF-8 becomes U+FFFD."""
    return subprocess.run([str(part) for part in cmd], input=stdin, env=env, cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def git_init(path):
    """Make an empty git repository in path, and return path."""
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    return path


def git_bash_pwd_stub(path, windows_path):
    """Write a bash file in which "pwd -W" prints windows_path, as Git Bash prints the Windows form of the folder.

    Give the returned path to bash in BASH_ENV. Plain pwd stays the builtin.
    """
    Path(path).write_text(f'pwd() {{ if [ "$1" = -W ]; then echo "{windows_path}"; else builtin pwd "$@"; fi; }}\n',
                          encoding="utf-8")
    return str(path)


def load_module(name, path):
    """Import the Python file at path as a module with the given name."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
