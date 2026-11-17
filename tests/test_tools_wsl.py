"""Tests for the scripts of tools/wsl.

The shell form tests read each tracked .sh file of tools/. The other tests run the Windows parts with a
stand-in wsl.exe. The stand-in drops the options of wsl.exe and runs the command on this machine, with a
temporary folder as the home folder and with no network share in front of each Linux path. So a test runs
the Windows part and the Linux part together, on a small repository, and calls no model. The tests of the
stand-in need Linux, because Git Bash cannot start a bash file with the name wsl.exe.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import unittest

from support import REPO, tool_missing
from testkit import ScratchCase, clean_env, git_init, run

WSL = REPO / "tools" / "wsl"
SHEBANG = "#!/usr/bin/env bash"
STRICT = "set -euo pipefail"
SOURCED = {"tools/wsl/common.sh"}
STUB_WSL = """#!/usr/bin/env bash
# Stand-in for wsl.exe: log the arguments, drop the options of wsl.exe, and run the command here.
printf '%s\\n' "$*" >> "$WSL_STUB_LOG"
while [ $# -gt 0 ]; do
    case "$1" in
        -d | --cd) shift 2 ;;
        -e) shift; break ;;
        *) shift ;;
    esac
done
cd "$HOME"
exec "$@"
"""
COMPARE_STUB = """import json, pathlib, sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index("--out") + 1])
out.mkdir(parents=True, exist_ok=True)
(out / "args.json").write_text(json.dumps(args))
(out / "baseline.json").write_text(json.dumps({"costUsd": 0.1}))
"""
CLAUDE_STUB = """#!/bin/sh
printf '%s\\n' '{' '  "loggedIn": true,' '  "authMethod": "AUTH"' '}'
"""


def tracked_shell_files():
    out = run(["git", "-C", REPO, "ls-files", "-s", "-z", "--", "tools"], check=True, text=False).stdout
    files = {}
    for entry in out.decode("utf-8").split("\0"):
        meta, _, path = entry.partition("\t")
        if path.endswith(".sh"):
            files[path] = meta.split()[0]
    return files


class ShellFormTests(unittest.TestCase):
    def test_each_shell_file_has_the_form_of_the_repository(self):
        files = tracked_shell_files()
        self.assertIn("tools/wsl/bundle.sh", files)
        bash = shutil.which("bash")
        for path, mode in sorted(files.items()):
            with self.subTest(path=path):
                data = (REPO / path).read_bytes()
                self.assertNotIn(b"\r", data, "LF line ends only")
                self.assertEqual(mode, "100755")
                text = data.decode("utf-8")
                self.assertTrue(text.startswith(SHEBANG + "\n"))
                if path not in SOURCED:
                    self.assertIn("\n" + STRICT + "\n", text)
                if bash:
                    done = run([bash, "-n"], stdin=data, text=False)
                    self.assertEqual(done.returncode, 0, done.stderr)


@unittest.skipIf(sys.platform == "win32", "Git Bash cannot start the bash stand-in with the name wsl.exe")
class WslCase(ScratchCase):
    def setUp(self):
        for tool in ("git", "bash", "python3"):
            if shutil.which(tool) is None:
                tool_missing(self, f"{tool} not found")
        super().setUp()
        self.home = self.tmp / "home"
        self.home.mkdir()
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        self.write_exe(stubs / "wsl.exe", STUB_WSL)
        self.log = self.tmp / "wsl.log"
        config = self.tmp / "gitconfig"
        config.write_bytes(b"")
        self.env = clean_env(drop=("ANTHROPIC_API_KEY", "WSL_DISTRO", "TOOLS_DIR"),
                             PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}", HOME=str(self.home),
                             WSL_UNC_ROOT="", WSL_STUB_LOG=str(self.log), GIT_CONFIG_GLOBAL=str(config),
                             GIT_CONFIG_NOSYSTEM="1")
        self.tools = self.home / ".cache" / "marketplace-tools"
        self.repo = self.make_repo()

    def write_exe(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def git(self, *args):
        return run(["git", "-C", self.repo, *args], env=self.env, check=True).stdout.strip()

    def commit(self, rel, text, subject):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.git("add", "--", rel)
        self.git("commit", "-q", "-m", subject)

    def make_repo(self):
        self.repo = git_init(self.tmp / "repo")
        self.git("checkout", "-q", "-b", "main")
        self.commit("README.md", "demo\n", "base")
        self.git("checkout", "-q", "-b", "work/one")
        self.commit("tests/test_ok.py", "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n"
                    "        pass\n", "a passing test")
        self.commit("tests/evals/compare_versions.py", COMPARE_STUB, "a stand-in compare script")
        self.git("checkout", "-q", "-b", "bad")
        self.commit("tests/test_bad.py", "import unittest\n\nclass B(unittest.TestCase):\n    def test_bad(self):\n"
                    "        self.fail('planted')\n", "a failing test")
        self.git("checkout", "-q", "main")
        return self.repo

    def script(self, name, *args, env=None, code=0, timeout=120):
        result = run(["bash", WSL / name, *args], env=env or self.env, timeout=timeout)
        self.assertResult(result, code)
        return result.stdout + result.stderr

    def claude(self, method="claude.ai"):
        self.write_exe(self.home / ".local" / "bin" / "claude", CLAUDE_STUB.replace("AUTH", method))


class BundleTests(WslCase):
    def test_bundle_holds_the_refs_and_its_linux_path_prints(self):
        out = self.script("bundle.sh", self.repo, "work/one", "main", "work/one", "no-such-ref")
        path = self.tools / "bundles" / "work_one.bundle"
        self.assertEqual(out.strip(), str(path))
        heads = run(["git", "bundle", "list-heads", path], env=self.env, check=True).stdout
        self.assertIn("refs/heads/main", heads)
        self.assertIn("refs/heads/work/one", heads)
        self.assertIn("-d Ubuntu --cd ~ -e", self.log.read_text(encoding="utf-8"))

    def test_no_known_ref_stops(self):
        self.assertIn("STOP: no ref of the list exists", self.script("bundle.sh", self.repo, "x", "nope", code=3))

    def test_too_few_arguments_is_a_usage_error(self):
        self.script("bundle.sh", self.repo, "x", code=2)


class UnitTestsTests(WslCase):
    def setUp(self):
        super().setUp()
        git_init(self.tools / "simple-english-v9.9.9")

    def test_suite_of_the_branch_runs_in_a_fresh_clone(self):
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", "--no-private-mount", self.repo, "work/one")
        self.assertIn("HEAD: ", out)
        self.assertIn("a stand-in compare script", out)
        self.assertIn("LINTER: v9.9.9", out)
        self.assertIn("\nOK\n", out)
        clones = self.tools / "test-clones"
        self.assertEqual([p.suffix for p in clones.iterdir()], [".log"], "the clone is gone, the log stays")

    def test_failed_suite_gives_its_exit_code(self):
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", "--no-private-mount", self.repo, "bad", code=1)
        self.assertIn("FAIL: test_bad", out)

    def test_private_mount(self):
        if subprocess.run(["unshare", "-r", "-m", "true"], capture_output=True).returncode != 0:
            self.skipTest("unshare -r -m is not allowed here")
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", self.repo, "work/one")
        self.assertIn("\nOK\n", out)
        self.assertTrue((self.tools / "nuget-private").is_dir())

    def test_usage_errors(self):
        self.script("unit-tests.sh", self.repo, code=2)
        self.script("unit-tests.sh", "--tail", "x", self.repo, "work/one", code=2)
        self.script("unit-tests.sh", "--bogus", self.repo, "work/one", code=2)


class RunEvalTests(WslCase):
    def test_each_argument_reaches_the_compare_script_as_it_is(self):
        self.claude()
        result = self.tmp / "result"
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", result, "baseline", "--case", "a b",
                          "--note", "it's $HOME")
        self.assertIn("COPIED TO: ", out)
        args = json.loads((result / "args.json").read_text(encoding="utf-8"))
        self.assertEqual(args[:5], ["baseline", "--case", "a b", "--note", "it's $HOME"])
        self.assertEqual(args[5], "--out")
        self.assertTrue(args[6].startswith(str(self.tools / "out") + "/"))
        self.assertEqual(args[7:], ["--claude", str(self.home / ".local" / "bin" / "claude")])
        self.assertTrue((self.tools / "eval-clone" / ".git").is_dir())

    def test_api_key_stops(self):
        self.claude()
        env = dict(self.env, ANTHROPIC_API_KEY="x")
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "r", "baseline", env=env, code=3)
        self.assertIn("STOP: ANTHROPIC_API_KEY is set", out)

    def test_other_sign_in_stops(self):
        self.claude("api_key")
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "r", "baseline", code=3)
        self.assertIn("STOP: not signed in with claude.ai", out)

    def test_out_argument_is_refused(self):
        self.claude()
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "r", "baseline", "--out",
                          "x", code=2)
        self.assertIn("STOP: the script sets --out itself", out)

    def test_bundle_on_a_windows_drive_stops(self):
        out = run(["bash", WSL / "linux" / "eval-run.sh", "/mnt/c/x.bundle", "main", "/tmp/o", "/tmp/c", "no",
                   "baseline"], env=self.env)
        self.assertResult(out, 3, "STOP: the bundle is on a Windows drive")


if __name__ == "__main__":
    unittest.main()
