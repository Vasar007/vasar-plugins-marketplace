"""Tests for the scripts of tools/wsl.

The shell form tests read each tracked .sh file of tools/. The other tests run the Windows parts with a
stand-in wsl.exe. The stand-in drops the options of wsl.exe and runs the command on this machine, with a
temporary folder as the home folder and with no network share in front of each Linux path. So a test runs
the Windows part and the Linux part together, on a small repository, and calls no model. The tests of the
stand-in need Linux: the Linux parts use flock and unshare, and each path of a test is a Linux path.
"""
import json
import os
import re
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
# Like wsl.exe, it reads all its standard input before the command starts.
printf '%s\\n' "$*" >> "$WSL_STUB_LOG"
printf 'env %s %s\\n' "${MSYS_NO_PATHCONV:-}" "${MSYS2_ARG_CONV_EXCL:-}" >> "$WSL_STUB_LOG"
input=$(mktemp)
cat > "$input"
while [ $# -gt 0 ]; do
    case "$1" in
        -d | --cd) shift 2 ;;
        -e) shift; break ;;
        *) shift ;;
    esac
done
cd "$HOME"
code=0
"$@" < "$input" || code=$?
rm -f "$input"
exit "$code"
"""
BROKEN_WSL = """#!/usr/bin/env bash
# Stand-in for a wsl.exe that does not know the distribution: UTF-16 text on standard output, and exit code 255.
printf 'T\\0h\\0e\\0r\\0e\\0 \\0i\\0s\\0 \\0n\\0o\\0\\r\\0\\n\\0'
exit 255
"""
COMPARE_STUB = """import json, os, pathlib, sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index("--out") + 1])
out.mkdir(parents=True, exist_ok=True)
(out / "args.json").write_text(json.dumps(args))
(out / "env.json").write_text(json.dumps({"TMPDIR": os.environ.get("TMPDIR")}))
(out / "baseline.json").write_text(json.dumps({"costUsd": 0.1}))
if "--exit-code" in args:
    sys.exit(int(args[args.index("--exit-code") + 1]))
"""
ENV_TEST = """import os, pathlib, unittest

class E(unittest.TestCase):
    def test_env(self):
        self.assertTrue(os.environ["SIMPLE_ENGLISH_DIR"].endswith("/simple-english-v9.9.9"))
        self.assertTrue(os.environ["TMPDIR"].endswith("/.cache/plugin-evals/tmp"))
        marker = os.environ.get("MOUNT_MARKER")
        if marker:
            pathlib.Path("/tmp/plugin-evals", marker).write_text("x")
"""
CLAUDE_STUB = """#!/bin/sh
printf '%s\\n' '{' '  "loggedIn": true,' '  "authMethod": "AUTH"' '}'
"""
SLOW_CLAUDE_STUB = """#!/bin/sh
# The sign-in line comes first. Then comes more text than a pipe holds.
printf '%s\\n' '{' '  "authMethod": "claude.ai",'
head -c 200000 /dev/zero | tr '\\0' 'x'
printf '\\n}\\n'
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


@unittest.skipIf(sys.platform == "win32", "the Linux parts need flock, unshare, and Linux paths")
class WslCase(ScratchCase):
    def setUp(self):
        for tool in ("git", "bash", "python3", "flock"):
            if shutil.which(tool) is None:
                tool_missing(self, f"{tool} not found")
        super().setUp()
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.stubs = self.tmp / "stubs"
        self.stubs.mkdir()
        self.write_exe(self.stubs / "wsl.exe", STUB_WSL)
        self.log = self.tmp / "wsl.log"
        config = self.tmp / "gitconfig"
        config.write_bytes(b"")
        self.env = clean_env(drop=("ANTHROPIC_API_KEY", "WSL_DISTRO", "TOOLS_DIR", "MOUNT_MARKER"),
                             PATH=f"{self.stubs}{os.pathsep}{os.environ['PATH']}", HOME=str(self.home),
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
        self.commit("tests/test_env.py", ENV_TEST, "a test of the variables of the run")
        self.commit("tests/evals/compare_versions.py", COMPARE_STUB, "a stand-in compare script")
        self.git("checkout", "-q", "-b", "bad")
        self.commit("tests/test_bad.py", "import unittest\n\nclass B(unittest.TestCase):\n    def test_bad(self):\n"
                    "        self.fail('planted')\n", "a failing test")
        self.git("checkout", "-q", "main")
        return self.repo

    def script(self, name, *args, env=None, code=0, timeout=120):
        result = run(["bash", WSL / name, *args], env=env or self.env, timeout=timeout, stdin="")
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
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("-d Ubuntu --cd ~ -e", log)
        self.assertIn("env 1 *\n", log)
        self.assertNotIn("env  \n", log)

    def test_no_known_ref_stops(self):
        self.assertIn("STOP: no ref of the list exists", self.script("bundle.sh", self.repo, "x", "nope", code=3))

    def test_too_few_arguments_is_a_usage_error(self):
        self.script("bundle.sh", self.repo, "x", code=2)

    def test_script_in_a_read_loop_leaves_the_other_lines(self):
        loop = 'while read -r name; do bash "$0" "$1" "$name" main > /dev/null || exit; echo "did $name"; done'
        done = run(["bash", "-c", loop, WSL / "bundle.sh", self.repo], env=self.env, stdin="one\ntwo\n")
        self.assertResult(done, 0)
        self.assertEqual(done.stdout, "did one\ndid two\n")

    def test_unknown_distribution_stops_with_a_reason(self):
        self.write_exe(self.stubs / "wsl.exe", BROKEN_WSL)
        out = self.script("bundle.sh", self.repo, "x", "main", code=3)
        self.assertIn("STOP: cannot read the home folder of WSL2 distribution Ubuntu", out)
        self.assertNotIn("null byte", out)

    def test_help_prints_the_usage_and_the_options(self):
        for name, text in (("bundle.sh", "<ref>..."), ("unit-tests.sh", "--no-private-mount"),
                           ("run-eval.sh", "--no-wait")):
            with self.subTest(name=name):
                out = self.script(name, "--help")
                self.assertIn("Usage: " + name, out)
                self.assertIn(text, out)
                self.assertFalse(self.log.exists(), "no call of wsl.exe")


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
        self.assertEqual(list((self.tools / "bundles").iterdir()), [], "the runner removes its bundle")
        self.assertFalse((self.tools / "nuget-private").exists(), "no private mount")
        self.assertIn(" -e bash -lc bash ", self.log.read_text(encoding="utf-8"))

    def test_failed_suite_gives_its_exit_code(self):
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", "--no-private-mount", self.repo, "bad", code=1)
        self.assertIn("FAIL: test_bad", out)

    def test_private_mount(self):
        if subprocess.run(["unshare", "-r", "-m", "true"], capture_output=True).returncode != 0:
            self.skipTest("unshare -r -m is not allowed here")
        marker = f"marker-{os.getpid()}"

        def remove_stray_marker():
            try:
                os.remove(os.path.join("/tmp/plugin-evals", marker))
            except OSError:
                pass

        self.addCleanup(remove_stray_marker)
        env = dict(self.env, MOUNT_MARKER=marker)
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", self.repo, "work/one", env=env)
        self.assertIn("\nOK\n", out)
        self.assertTrue((self.tools / "nuget-private" / marker).is_file(), "the run wrote into the private folder")

    def test_usage_errors(self):
        self.script("unit-tests.sh", self.repo, code=2)
        self.script("unit-tests.sh", "--tail", "x", self.repo, "work/one", code=2)
        self.script("unit-tests.sh", "--bogus", self.repo, "work/one", code=2)

    def test_branch_that_the_repository_lacks_stops(self):
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", "--no-private-mount", self.repo, "nope", code=3)
        self.assertIn("STOP: the bundle has no branch nope", out)
        self.assertFalse((self.tools / "test-clones").exists(), "no clone and no log")

    def test_failed_copy_of_the_linux_part_stops(self):
        self.tools.mkdir(parents=True, exist_ok=True)
        (self.tools / "bin").write_text("not a folder", encoding="utf-8")
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", "--no-private-mount", self.repo, "work/one",
                          code=3)
        self.assertIn("STOP: cannot copy unit-tests-clone.sh into WSL2", out)

    def test_lock_file_of_another_bundle_does_not_stop_the_run(self):
        (self.tools / "bundles").mkdir(parents=True)
        (self.tools / "bundles" / "unit-work_one.bundle.lock").write_text("", encoding="utf-8")
        out = self.script("unit-tests.sh", "--linter-tag", "v9.9.9", "--no-private-mount", self.repo, "work/one")
        self.assertIn("\nOK\n", out)

    def linter_origin(self, *tags):
        """Make a local repository with these tags, and let git take it in place of the linter URL."""
        origin = git_init(self.tmp / "linter-origin")
        run(["git", "-C", origin, "commit", "-q", "--allow-empty", "-m", "linter"], env=self.env, check=True)
        for tag in tags:
            run(["git", "-C", origin, "tag", tag], env=self.env, check=True)
        run(["git", "config", "--file", self.tmp / "gitconfig", f"url.{origin.as_uri()}.insteadOf",
             "https://github.com/AminBlg/SimpleEnglish.git"], check=True)

    def test_latest_linter_is_the_newest_release_tag(self):
        self.linter_origin("v1.2.0", "v1.10.0", "v1.11.0-rc1")
        # The branch main has no tests folder, so the suite ends with exit code 1.
        out = self.script("unit-tests.sh", "--no-private-mount", self.repo, "main", code=1)
        self.assertIn("LINTER: v1.10.0 ", out)
        self.assertEqual(sorted(p.name for p in self.tools.glob("simple-english-*")),
                         ["simple-english-v1.10.0", "simple-english-v9.9.9"], "one clone, and no folder of the run")

    def test_linux_part_stops_on_a_bundle_that_it_cannot_use(self):
        part = WSL / "linux" / "unit-tests-clone.sh"
        on_windows = run(["bash", part, self.tools, "/mnt/c/x.bundle", "main", "v9.9.9", "8", "no"], env=self.env)
        self.assertResult(on_windows, 3, "STOP: the bundle is on a Windows drive")
        missing = run(["bash", part, self.tools, self.tmp / "none.bundle", "main", "v9.9.9", "8", "no"], env=self.env)
        self.assertResult(missing, 3, "STOP: no bundle")


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
        env = json.loads((result / "env.json").read_text(encoding="utf-8"))
        self.assertEqual(env["TMPDIR"], str(self.home / ".cache" / "plugin-evals" / "tmp"))

    def test_api_key_stops(self):
        self.claude()
        env = dict(self.env, ANTHROPIC_API_KEY="x")
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "r", "baseline", env=env, code=3)
        self.assertIn("STOP: ANTHROPIC_API_KEY is set", out)

    def test_other_sign_in_stops(self):
        self.claude("api_key")
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "r", "baseline", code=3)
        self.assertIn("STOP: not signed in with claude.ai", out)

    def test_out_and_claude_arguments_are_refused(self):
        self.claude()
        for number, extra in enumerate((["--out", "x"], ["--out=x"], ["--claude", "x"], ["--claude=x"])):
            with self.subTest(extra=extra):
                out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / f"r{number}",
                                  "baseline", *extra, code=2)
                self.assertIn(f"STOP: the script sets {extra[0]} itself", out)

    def test_clone_option_names_the_eval_clone(self):
        self.claude()
        clone = self.home / "other" / "clone"
        self.script("run-eval.sh", "--no-wait", "--clone", clone, self.repo, "work/one", self.tmp / "r", "baseline")
        self.assertTrue((clone / ".git").is_dir())
        self.assertFalse((self.tools / "eval-clone").exists())

    def test_bundle_on_a_windows_drive_stops(self):
        out = run(["bash", WSL / "linux" / "eval-run.sh", "/mnt/c/x.bundle", "main", "/tmp/o", "/tmp/c", "no",
                   "baseline"], env=self.env)
        self.assertResult(out, 3, "STOP: the bundle is on a Windows drive")

    def test_branch_that_the_repository_lacks_stops(self):
        self.claude()
        self.script("run-eval.sh", "--no-wait", self.repo, "bad", self.tmp / "r1", "baseline")
        self.git("branch", "-q", "-D", "bad")
        out = self.script("run-eval.sh", "--no-wait", self.repo, "bad", self.tmp / "r2", "baseline", code=3)
        self.assertIn("STOP: the bundle has no branch bad", out)
        self.assertEqual(list((self.tmp / "r2").iterdir()), [], "no run at the old commit of the branch")

    def test_two_runs_in_one_second_get_two_result_folders(self):
        self.claude()
        self.write_exe(self.stubs / "date", "#!/bin/sh\necho 20260101-000000\n")
        folders = []
        for name in ("r1", "r2"):
            out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / name, "baseline")
            folders.append(re.search(r"^LINUX RESULT FOLDER: (.+)$", out, re.M).group(1))
        self.assertNotEqual(folders[0], folders[1])

    def test_exit_code_of_the_compare_script_passes_through(self):
        self.claude()
        result = self.tmp / "result"
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", result, "baseline", "--exit-code", "7",
                          code=7)
        self.assertIn("EXIT: 7 at ", out)
        self.assertTrue((result / "args.json").is_file(), "the result of a failed run comes back too")

    def end(self, process):
        process.kill()
        process.communicate()

    def test_second_run_waits_for_the_lock_of_the_eval_clone(self):
        self.claude()
        self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "r0", "baseline")
        # The holder frees the lock after one line on its standard input, or after 60 seconds.
        holder = subprocess.Popen(["bash", "-c", 'exec 9> "$0"; flock 9; echo held; read -r -t 60 line',
                                   str(self.tools / "eval-clone.lock")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True)
        self.addCleanup(self.end, holder)
        self.assertEqual(holder.stdout.readline(), "held\n")
        runner = subprocess.Popen(["bash", str(WSL / "run-eval.sh"), "--no-wait", str(self.repo), "work/one",
                                   str(self.tmp / "r1"), "baseline"], env=self.env, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.end, runner)
        lines = []
        for line in runner.stdout:
            lines.append(line)
            if line.startswith("WAIT: another run holds "):
                self.assertFalse((self.tmp / "r1" / "args.json").exists(), "the run did not start under the lock")
                holder.stdin.write("\n")
                holder.stdin.flush()
        self.assertEqual(runner.wait(), 0, "".join(lines))
        starts = [line.split(":")[0] for line in lines]
        self.assertIn("WAIT", starts)
        self.assertLess(starts.index("WAIT"), starts.index("HEAD"))
        self.assertTrue((self.tmp / "r1" / "args.json").is_file())

    def test_result_folder_with_older_files_stops_before_the_run(self):
        self.claude()
        result = self.tmp / "result"
        result.mkdir()
        (result / "baseline.json").write_text("{}", encoding="utf-8")
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", result, "baseline", code=3)
        self.assertIn("STOP: the result folder is not empty", out)
        self.assertFalse(self.log.exists(), "no call of wsl.exe")

    def test_result_folder_that_cannot_exist_stops_before_the_run(self):
        self.claude()
        (self.tmp / "file").write_text("x", encoding="utf-8")
        out = self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "file" / "r", "baseline",
                          code=3)
        self.assertIn("STOP: cannot make the result folder", out)
        self.assertFalse(self.log.exists(), "no call of wsl.exe")

    def test_sign_in_test_reads_the_whole_output(self):
        self.write_exe(self.home / ".local" / "bin" / "claude", SLOW_CLAUDE_STUB)
        self.script("run-eval.sh", "--no-wait", self.repo, "work/one", self.tmp / "r", "baseline")


if __name__ == "__main__":
    unittest.main()
