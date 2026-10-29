"""Tests for testkit.py, the generic test helpers."""
import ast
import io
import os
import shutil
import stat
import subprocess
import sys
import tokenize
import unittest
from pathlib import Path
from unittest import mock

import testkit
from support import tool_missing
from testkit import ScratchCase, clean_env, git_bash_pwd_stub, git_init, load_module, remove_tree, run

SOURCE = Path(testkit.__file__).read_text(encoding="utf-8")
WINDOWS_PATH = "C:/Users/A&B/Notes"
TRICKY_PATH = r"\\server\share\$HOME\it's"


class SourceTests(unittest.TestCase):
    @unittest.skipUnless(sys.version_info >= (3, 8), "ast.parse has feature_version from Python 3.8 on")
    def test_syntax_is_valid_for_python_3_7(self):
        """A best-effort guard: ast.parse with feature_version (3, 7), and a token check for f"{x=}" below.

        Some later forms still pass, for example a with in parentheses (3.9) and return *a, *b (3.8).
        """
        ast.parse(SOURCE, feature_version=(3, 7))

    @unittest.skipUnless(hasattr(tokenize, "FSTRING_START"), "before Python 3.12, an f-string is one STRING token")
    def test_has_no_self_documenting_f_string(self):
        # Python 3.12 and later accept f"{x=}" under feature_version (3, 7), so look at the tokens.
        tokens = list(tokenize.generate_tokens(io.StringIO(SOURCE).readline))
        flagged = [first.start[0] for first, second in zip(tokens, tokens[1:])
                   if first.type == tokenize.OP and first.string == "="
                   and second.type == tokenize.OP and second.string in ("}", "!", ":")]
        self.assertEqual(flagged, [])

    def test_has_no_type_hints(self):
        # Python 3.7 evaluates a hint such as list[str] when it defines the function, and fails.
        hints = [node.lineno for node in ast.walk(ast.parse(SOURCE))
                 if isinstance(node, ast.AnnAssign) or getattr(node, "returns", None) is not None
                 or (isinstance(node, ast.arg) and node.annotation is not None)]
        self.assertEqual(hints, [])

    @unittest.skipUnless(sys.version_info >= (3, 10), "sys.stdlib_module_names is from Python 3.10 on")
    def test_imports_only_the_standard_library(self):
        names = set()
        for node in ast.walk(ast.parse(SOURCE)):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        self.assertEqual(sorted(names - sys.stdlib_module_names), [])


class ScratchCaseTests(unittest.TestCase):
    def test_folder_exists_in_the_test_and_is_gone_after_the_cleanup(self):
        case = ScratchCase()
        case.setUp()
        (case.tmp / "a/b").mkdir(parents=True)
        (case.tmp / "a/b/c.txt").write_text("x", encoding="utf-8")
        case.doCleanups()
        self.assertFalse(case.tmp.exists())

    def test_assert_result_checks_the_code_and_each_text(self):
        case = ScratchCase()
        done = subprocess.CompletedProcess([], 1, stdout="out text\n", stderr="err text\n")
        case.assertResult(done, 1, "out text", "err text")
        with self.assertRaises(AssertionError):
            case.assertResult(done, 0)
        with self.assertRaises(AssertionError):
            case.assertResult(done, 1, "no such text")


class RemoveTreeTests(ScratchCase):
    def test_runs_the_handler_when_unlink_fails(self):
        # On Linux a read-only file does not block unlink, so make the first unlink fail.
        folder = self.tmp / "tree"
        folder.mkdir()
        (folder / "a.txt").write_text("x", encoding="utf-8")
        real_unlink = os.unlink
        calls = []

        def unlink(*args, **kwargs):
            calls.append(args)
            if len(calls) == 1:
                raise PermissionError("blocked")
            return real_unlink(*args, **kwargs)

        with mock.patch("os.unlink", side_effect=unlink):
            remove_tree(folder)
        self.assertFalse(folder.exists())
        self.assertEqual(len(calls), 2)

    def test_removes_a_tree_with_a_read_only_file(self):
        folder = self.tmp / "tree"
        (folder / "sub").mkdir(parents=True)
        locked = folder / "sub/locked.txt"
        locked.write_text("x", encoding="utf-8")
        locked.chmod(stat.S_IREAD)
        remove_tree(folder)
        self.assertFalse(folder.exists())


class CleanEnvTests(unittest.TestCase):
    def test_drops_the_named_keys_and_adds_the_values(self):
        with mock.patch.dict(os.environ, {"TESTKIT_DROP": "1", "TESTKIT_KEEP": "2"}):
            env = clean_env(("TESTKIT_DROP",), TESTKIT_NEW="3")
            self.assertNotIn("TESTKIT_DROP", env)
            self.assertEqual((env["TESTKIT_KEEP"], env["TESTKIT_NEW"]), ("2", "3"))
            self.assertEqual(os.environ["TESTKIT_DROP"], "1")
            self.assertNotIn("TESTKIT_NEW", os.environ)


class RunTests(ScratchCase):
    def test_passes_stdin_env_and_cwd_and_captures_both_streams(self):
        code = ("import os, sys; print(sys.stdin.read() + os.environ['TESTKIT_X']); "
                "print(os.getcwd(), file=sys.stderr); sys.exit(3)")
        done = run([Path(sys.executable), "-c", code], stdin="in-", env=clean_env(TESTKIT_X="x"), cwd=self.tmp)
        self.assertEqual((done.returncode, done.stdout), (3, "in-x\n"))
        self.assertEqual(Path(done.stderr.strip()).resolve(), self.tmp.resolve())

    def test_replaces_bytes_that_are_not_utf_8(self):
        done = run([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'a\\xffb')"])
        self.assertEqual(done.stdout, "a\ufffdb")

    def test_timeout_stops_the_process(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)


class GitInitTests(ScratchCase):
    def test_makes_a_repository_and_returns_the_path(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        repo = git_init(self.tmp / "repo")
        self.assertEqual(repo, self.tmp / "repo")
        self.assertTrue((repo / ".git").is_dir())


class PwdStubTests(ScratchCase):
    def test_pwd_w_prints_the_windows_path_and_plain_pwd_does_not(self):
        bash = shutil.which("bash")
        if bash is None:
            tool_missing(self, "bash not found")
        for expected in (WINDOWS_PATH, TRICKY_PATH):
            with self.subTest(expected=expected):
                bash_env = git_bash_pwd_stub(self.tmp / "bash_env.sh", expected)
                # A CR byte breaks bash, but Path.write_text adds it only on Windows.
                self.assertNotIn(b"\r", Path(bash_env).read_bytes())
                done = run([bash, "-c", "pwd -W; pwd"], env=clean_env(BASH_ENV=bash_env), cwd=self.tmp)
                lines = done.stdout.splitlines()
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(lines[:1], [expected], done.stderr)
                self.assertNotEqual(lines[1:2], [expected])


class LoadModuleTests(ScratchCase):
    def test_loads_a_file_as_a_module(self):
        path = self.tmp / "sample_module.py"
        path.write_text("VALUE = 42\n", encoding="utf-8")
        module = load_module("sample_module", path)
        self.assertEqual((module.__name__, module.VALUE), ("sample_module", 42))


if __name__ == "__main__":
    unittest.main()
