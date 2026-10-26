"""Runs the scaffold scripts and the fixture libraries of the eval cases. The tests call no model.

Each scaffold runs in a new temporary folder, with HOME set to another temporary folder and
EVAL_FIXTURE_SKIP_DOTNET=1. The tests need bash and git, and the Python tests of a fixture need Python.
If bash or git is not found, the tests skip. In CI they fail.

One test runs the .NET probe scaffolds with a real restore and build, and then runs dotnet test.
It needs the .NET SDK 10 and network access for the first restore. As in a real run, the packages
go to /tmp/plugin-evals/nuget, and the scaffold copies them into the NuGet folder of HOME.
"""
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from support import REPO, tool_missing
from test_eval_cases import load_cases, plugin_roots

SCAFFOLD_SECONDS = 120
DOTNET_SECONDS = 900
# The branch that a scaffold must leave checked out. A case that is not listed only needs a branch.
EXPECTED_BRANCH = {
    "probe-git-sandbox": "main",
    "probe-dotnet-sandbox": "work/probe-dotnet-sandbox",
    "probe-test-fixture": "work/tests",
}
# The cases whose Python tests fail on purpose. The value is the number of failing tests.
FAILING_TESTS = {"so-two-fixes": 2}
PUBLISH_CALL = re.compile(r"^\s*fixture_publish\s+(\S+)((?:\s+\d+:\S+)*)", re.MULTILINE)
DOTNET_PROBES = ("probe-dotnet-sandbox", "probe-test-fixture")


def remove_tree(path):
    """Delete a folder. Git makes read-only files on Windows."""
    def fix(function, target, error):
        os.chmod(target, stat.S_IWRITE)
        function(target)

    shutil.rmtree(path, onexc=fix)


def scaffold_cases():
    """The (case, script path) pairs of every case that names a scaffold script."""
    pairs = []
    for root in plugin_roots():
        for case in load_cases(root):
            context = (case.case_yaml or {}).get("context")
            script = context.get("scaffold_script") if isinstance(context, dict) else None
            if isinstance(script, str):
                pairs.append((case, case.path / script))
    return pairs


class FixtureCase(unittest.TestCase):
    """Helpers to run bash and git in a temporary folder."""

    def setUp(self):
        self.bash = shutil.which("bash")
        if self.bash is None:
            tool_missing(self, "bash not found")
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(remove_tree, self.tmp)
        self.home = self.tmp / "home"
        self.home.mkdir()

    def environment(self, skip_dotnet=True):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update({"HOME": str(self.home), "TERM": "dumb", "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
        if skip_dotnet:
            env["EVAL_FIXTURE_SKIP_DOTNET"] = "1"
        else:
            env.pop("EVAL_FIXTURE_SKIP_DOTNET", None)
        return env

    def workspace(self, name="workspace"):
        folder = self.tmp / name
        folder.mkdir()
        return folder

    def run_bash(self, arguments, cwd, timeout=SCAFFOLD_SECONDS, skip_dotnet=True):
        done = subprocess.run([self.bash, *arguments], cwd=cwd, env=self.environment(skip_dotnet), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)
        self.assertEqual(done.returncode, 0, f"bash {arguments} failed:\n{done.stdout}\n{done.stderr}")
        return done.stdout

    def run_snippet(self, cwd, libraries, snippet):
        """Source libraries from the _lib folder of a plugin, and run the snippet in the folder."""
        sources = "".join(f'source "{library.as_posix()}"\n' for library in libraries)
        return self.run_bash(["-c", f"set -euo pipefail\n{sources}{snippet}"], cwd)

    def git(self, cwd, *args):
        done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8",
                              env=self.environment())
        return done.returncode, done.stdout.strip()


class ScaffoldTests(FixtureCase):
    def refs(self, workspace):
        return self.git(workspace, "for-each-ref", "--format=%(refname) %(objectname)")[1]

    def check_scaffold(self, case, script):
        workspace = self.workspace()
        started = time.monotonic()
        self.run_bash([script.as_posix()], workspace)
        self.assertLess(time.monotonic() - started, SCAFFOLD_SECONDS)

        subjects = self.git(workspace, "log", "--all", "--format=%s")[1].splitlines()
        self.assertTrue(subjects, "the scaffold made no commit")
        self.assertEqual([s for s in subjects if not s.startswith("fixture:")], [], "commit subjects need the prefix fixture:")
        branch = self.git(workspace, "rev-parse", "--abbrev-ref", "HEAD")[1]
        self.assertEqual(branch, EXPECTED_BRANCH.get(case.name, branch))
        self.assertNotEqual(branch, "HEAD", "the checkout is detached")
        self.assertEqual(self.git(workspace, "diff", "--quiet", "HEAD")[0], 0, "a tracked file has a change")

        text = script.read_text(encoding="utf-8")
        bare = workspace / ".remote" / "origin.git"
        if bare.exists():
            self.check_remote(workspace, bare, text)
        if (workspace / "tests").is_dir() and not list(workspace.glob("*.sln")):
            self.check_python_tests(case, workspace)
        return self.refs(workspace)

    def check_remote(self, workspace, bare, script_text):
        self.assertEqual(self.git(bare, "rev-parse", "--is-bare-repository")[1], "true")
        self.assertEqual(self.git(workspace, "rev-parse", "--abbrev-ref", "origin/HEAD")[1], "origin/main")
        self.assertEqual(self.git(bare, "config", "core.logAllRefUpdates")[1], "always")
        self.assertFalse((bare / "logs" / "refs").exists(), "the remote has a reflog, so a grader cannot tell a push")
        self.assertIn(".remote/", (workspace / ".git" / "info" / "exclude").read_text(encoding="utf-8"))
        for work, pulls in PUBLISH_CALL.findall(script_text):
            self.assertEqual(self.git(workspace, "rev-parse", "--abbrev-ref", f"{work}@{{upstream}}")[1], f"origin/{work}")
            for pull in pulls.split():
                number = pull.split(":")[0]
                self.assertEqual(self.git(bare, "rev-parse", "--verify", "-q", f"refs/pull/{number}/head")[0], 0)

    def check_python_tests(self, case, workspace):
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                              env={**self.environment(), "PYTHONDONTWRITEBYTECODE": "1"})
        failing = FAILING_TESTS.get(case.name, 0)
        if failing:
            self.assertNotEqual(done.returncode, 0, done.stderr)
            self.assertRegex(done.stderr, rf"FAILED \((?:failures|errors)={failing}\)")
        else:
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_every_scaffold_runs_and_gives_the_same_commits_twice(self):
        pairs = scaffold_cases()
        self.assertTrue(pairs, "No case names a scaffold script.")
        for case, script in pairs:
            with self.subTest(case=case.name):
                first = self.check_scaffold(case, script)
                remove_tree(self.tmp / "workspace")
                second = self.check_scaffold(case, script)
                self.assertEqual(first, second, "two runs give different commit ids")
                remove_tree(self.tmp / "workspace")


class DotnetProbeTests(FixtureCase):
    """The .NET probe scaffolds with a real restore and build, then a test run with its marker files."""

    def test_probe_scaffolds_build_and_leave_marker_files_after_dotnet_test(self):
        dotnet = shutil.which("dotnet")
        if dotnet is None:
            tool_missing(self, "dotnet not found. Install the .NET SDK 10 to run this test.")
        version = subprocess.run([dotnet, "--version"], capture_output=True, text=True).stdout.strip()
        if not version.startswith("10."):
            tool_missing(self, f"The .NET SDK 10 is needed, but dotnet --version prints {version!r}.")
        probes = {case.name: script for case, script in scaffold_cases() if case.name in DOTNET_PROBES}
        self.assertEqual(sorted(probes), sorted(DOTNET_PROBES))
        for name, script in probes.items():
            with self.subTest(case=name):
                workspace = self.workspace(name)
                self.run_bash([script.as_posix()], workspace, timeout=DOTNET_SECONDS, skip_dotnet=False)
                self.assertFalse((workspace / ".test-runs").exists(), "the scaffold must not run the tests")
                solution = next(workspace.glob("*.sln")).name
                done = subprocess.run([dotnet, "test", solution, "--no-restore"], cwd=workspace,
                                      env=self.environment(skip_dotnet=False), capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", timeout=DOTNET_SECONDS)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                runs = workspace / ".test-runs"
                self.assertTrue(list(runs.glob("started-*")), "the run left no start file")
                self.assertEqual((runs / "last.txt").read_text(encoding="utf-8"), "Passed")
                self.assertEqual(self.git(workspace, "status", "--porcelain")[1], "", "build files are not ignored")


class LibraryTests(FixtureCase):
    """The fixture functions that no probe uses yet."""

    def libs(self, root, *names):
        return [REPO / root / "evals" / "_lib" / name for name in ("git-fixture.sh", *names)]

    def test_pager_repo_has_the_decoy_and_passing_tests(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"), "make_pager_repo")
        self.assertIn("range(1, count + 1)", (workspace / "src" / "ranges.py").read_text(encoding="utf-8"))
        self.assertIn("1-based, inclusive", (workspace / "src" / "ranges.py").read_text(encoding="utf-8"))
        self.assertIn("python3 -m unittest discover -s tests", (workspace / "CLAUDE.md").read_text(encoding="utf-8"))
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                              capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_users_repos_have_the_named_number_of_modules_and_callers(self):
        for modules, callers in ((6, 3), (40, 25)):
            with self.subTest(modules=modules):
                workspace = self.workspace(f"users-{modules}")
                self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"),
                                 f"make_users_repo {modules}")
                files = [p for p in (workspace / "app").rglob("*.py") if p.name != "__init__.py"]
                self.assertEqual(len(files), modules)
                called = [p for p in files if "fetch_user(" in p.read_text(encoding="utf-8") and p.name != "users.py"]
                self.assertEqual(len(called), callers)
                self.assertIn("HTTP_RETRY_LIMIT = 5", (workspace / "config" / "settings.py").read_text(encoding="utf-8"))
                done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                                      capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_users_repo_refuses_another_number_of_modules(self):
        workspace = self.workspace()
        with self.assertRaises(AssertionError):
            self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"), "make_users_repo 7")

    def test_shop_workspace_has_the_planted_lines(self):
        workspace = self.workspace()
        lines = self.run_snippet(workspace, self.libs("essentials/dev-essentials", "shop-fixture.sh"),
                                 'make_shop_workspace\necho "$SHOP_LINE_BILLING $SHOP_LINE_INVENTORY $SHOP_LINE_NOTIFY"')
        billing, inventory, notify = (int(n) for n in lines.split())
        project = workspace / "project"
        self.assertFalse((workspace / ".git").exists(), "the workspace root must not be a repo")
        self.assertTrue((project / ".git").exists())
        for number, path, text in ((billing, "billing/invoice.py", "int(total)"),
                                   (inventory, "inventory/cache.py", "key = sku"),
                                   (notify, "notify/retry.py", "if max_retries and")):
            with self.subTest(path=path):
                self.assertIn(text, (project / path).read_text(encoding="utf-8").splitlines()[number - 1])
        self.assertIn("N-01", (project / "NOTES.md").read_text(encoding="utf-8"))
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=project,
                              capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_cli_repo_runs(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("workflows/gop-pipeline", "py-fixture.sh"), "make_cli_repo")
        done = subprocess.run([sys.executable, "cli.py", "--name", "Ada"], cwd=workspace, capture_output=True,
                              text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.stdout.strip(), "Hello, Ada!")

    def test_publish_makes_pull_refs_and_a_clean_remote_log(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"),
                         "make_pager_repo\ngit checkout -q -b feature/x\n"
                         "printf 'x\\n' > x.txt\nfixture_commit 'add x'\nfixture_publish feature/x 42:feature/x")
        bare = workspace / ".remote" / "origin.git"
        self.assertEqual(self.git(bare, "rev-parse", "--verify", "-q", "refs/pull/42/head")[0], 0)
        self.assertEqual(self.git(workspace, "rev-parse", "--abbrev-ref", "@{upstream}")[1], "origin/feature/x")
        self.assertFalse((bare / "logs" / "refs").exists())
        self.run_snippet(workspace, [], "git commit -q --allow-empty -m 'run commit'\ngit push -q origin feature/x")
        self.assertTrue((bare / "logs" / "refs" / "heads" / "feature" / "x").is_file(),
                        "a push after the scaffold must leave a reflog file")

    def test_fixture_commit_uses_the_prefix_and_fixed_dates(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials"),
                         "fixture_init\nprintf 'a\\n' > a.txt\nfixture_commit 'one'\n"
                         "printf 'b\\n' > b.txt\nfixture_commit 'fixture: two'")
        subjects = self.git(workspace, "log", "--format=%s|%at|%ct", "--reverse")[1].splitlines()
        self.assertEqual(subjects, ["fixture: one|1767225660|1767225660", "fixture: two|1767225720|1767225720"])


if __name__ == "__main__":
    unittest.main()
