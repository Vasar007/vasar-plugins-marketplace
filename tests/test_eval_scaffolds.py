"""Runs the scaffold scripts and the fixture libraries of the eval cases. The tests call no model.

Each scaffold runs in a new temporary folder, with HOME set to another temporary folder and
EVAL_FIXTURE_SKIP_DOTNET=1. The tests need bash and git, and the Python tests of a fixture need Python.
If bash or git is not found, the tests skip. In CI they fail.

One test runs the .NET probe scaffolds with a real restore and build, and then runs dotnet test.
It needs the .NET SDK 10 or newer, the .NET 10 runtime, and network access for the first restore. As in a real run, the packages
go to /tmp/plugin-evals/nuget, and the scaffold copies them into the NuGet folder of HOME.

Three tests run dotnet_warm with a fake dotnet on PATH and a cache folder of the test. They need flock (util-linux).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unittest
from types import SimpleNamespace

from support import REPO, tool_missing
from test_eval_cases import load_cases, plugin_roots
from testkit import ScratchCase, remove_tree, run

SCAFFOLD_SECONDS = 120
DOTNET_SECONDS = 900
# The branch that a scaffold must leave checked out. A case that is not listed only needs a branch.
EXPECTED_BRANCH = {
    "probe-git-sandbox": "main",
    "probe-dotnet-sandbox": "work/probe-dotnet-sandbox",
    "probe-test-fixture": "work/tests",
    "rl-off-by-one": "feature/paging",
    "rl-null-guard": "feature/display-name",
    "rl-unbounded-query": "feature/recent-orders",
    "rl-clean-branch": "feature/clamp",
    "rl-pr-head-gate": "main",
    "fp-e1-seeded-defects": "work/seeded-defects",
    "fp-e1-clean-change": "work/clean-change",
    "fp-e1-border-auth": "work/border-auth",
    "fp-e2-untracked-file": "work/untracked-file",
    "fp-e3-autonomous-main": "main",
    "fp-e4-package-bump": "work/package-bump",
    "fp-e5-breaking-change": "work/breaking-change",
    "fp-e8-rename-across-projects": "work/rename-across-projects",
    "fp-free-text": "work/free-text",
    "wt-one-class": "work/tests",
    "wt-pricing-folder": "work/tests",
}
# The start content that a task needs. A scaffold that sets it too early or too late gives a no-op task.
START_CONTENT = {
    "fp-e4-package-bump": ("Directory.Packages.props", '<PackageVersion Include="NUnit" Version="4.6.1" />'),
}
BRANCH_LOG_PATH = re.compile(r"(?:^|/)logs/refs/heads/(.+)$")
# The cases whose Python tests fail on purpose. The value is the number of failing tests.
FAILING_TESTS = {"so-two-fixes": 2}
# The commit grader of each case that asks for a commit on the users repo.
COMMIT_GRADERS = {"so-rename-small": "committed", "so-rename-large": "committed", "so-two-fixes": "two-commits",
                  "rirr-retry-limit": "committed"}
PUBLISH_CALL = re.compile(r"^\s*fixture_publish\s+(\S+)((?:\s+\d+:\S+)*)", re.MULTILINE)
DOTNET_PROBES = ("probe-dotnet-sandbox", "probe-test-fixture")
FAILING_TEST = """namespace Billing.Domain.Tests;

[TestFixture]
public sealed class FailingProbeTests
{
    [Test]
    public void AlwaysFails()
    {
        Assert.That(1, Is.EqualTo(2));
    }
}
"""


FAKE_DOTNET = """#!/usr/bin/env bash
# A fake dotnet: a restore into the shared folder logs its start and its end, and prints FAKE_DOTNET_ERROR as dotnet does.
case " $* " in
    *" --packages "*)
        if [ -e /dev/fd/9 ]; then echo lock-descriptor-open >>"$FAKE_DOTNET_LOG"; fi
        echo start >>"$FAKE_DOTNET_LOG"
        sleep 1
        echo end >>"$FAKE_DOTNET_LOG"
        if [ -n "${FAKE_DOTNET_ERROR:-}" ]; then echo "$FAKE_DOTNET_ERROR"; exit 1; fi
        ;;
esac
"""


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


def branch_path_problems(case, branch):
    """A grader path under logs/refs/heads/ must name the branch of the scaffold. A glob path is skipped."""
    problems = []
    for name, (options, _body) in sorted(case.graders.items()):
        target = options.get("target")
        path = options.get("path") or (target.get("path") if isinstance(target, dict) else None)
        found = BRANCH_LOG_PATH.search(path.replace("\\", "/")) if isinstance(path, str) else None
        if found and "*" not in found.group(1) and found.group(1) != branch:
            problems.append(f"{case.label}/graders/{name}.md: the path names {found.group(1)}, but the scaffold branch is {branch}")
    return problems


class DotnetVersionParseTests(unittest.TestCase):
    def test_sdk_major_reads_the_first_number(self):
        self.assertEqual(sdk_major("11.0.100"), 11)
        self.assertEqual(sdk_major("10.0.100-rc.1.123"), 10)
        self.assertEqual(sdk_major(""), 0)
        self.assertEqual(sdk_major("error text"), 0)

    def test_runtime_10_must_be_in_the_list(self):
        listed = "Microsoft.AspNetCore.App 10.0.15 [x]\nMicrosoft.NETCore.App 9.0.23 [x]\nMicrosoft.NETCore.App 11.0.0 [x]\n"
        self.assertFalse(has_runtime_10(listed))
        self.assertTrue(has_runtime_10(listed + "Microsoft.NETCore.App 10.0.15 [x]\n"))
        self.assertFalse(has_runtime_10(""))


class GraderBranchTests(unittest.TestCase):
    def test_grader_paths_name_the_branch_of_the_scaffold(self):
        cases = [case for root in plugin_roots() for case in load_cases(root) if case.name in EXPECTED_BRANCH and case.name.startswith("fp-")]
        self.assertTrue(cases, "No fp case is listed in EXPECTED_BRANCH.")
        self.assertEqual([p for case in cases for p in branch_path_problems(case, EXPECTED_BRANCH[case.name])], [])

    def test_a_typo_in_a_branch_path_is_found(self):
        case = SimpleNamespace(label="fp-x", graders={
            "committed": ({"type": "regex", "target": {"source": "file", "path": ".git/logs/refs/heads/work/a"}}, ""),
            "no-push": ({"type": "file_exists", "path": ".remote/origin.git/logs/refs/heads/work/b"}, ""),
            "any-push": ({"type": "file_exists", "path": ".remote/origin.git/logs/refs/heads/*/*"}, ""),
        })
        problems = branch_path_problems(case, "work/a")
        self.assertEqual(len(problems), 1)
        self.assertIn("no-push", problems[0])


class FixtureCase(ScratchCase):
    """Helpers to run bash and git in a temporary folder."""

    def setUp(self):
        self.bash = shutil.which("bash")
        if self.bash is None:
            tool_missing(self, "bash not found")
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        super().setUp()
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
        done = run([self.bash, *arguments], env=self.environment(skip_dotnet), cwd=cwd, timeout=timeout)
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
        repo = self.repo_folder(workspace)

        subjects = self.git(repo, "log", "--all", "--format=%s")[1].splitlines()
        self.assertTrue(subjects, "the scaffold made no commit")
        self.assertEqual([s for s in subjects if not s.startswith("fixture:")], [], "commit subjects need the prefix fixture:")
        branch = self.git(repo, "rev-parse", "--abbrev-ref", "HEAD")[1]
        self.assertEqual(branch, EXPECTED_BRANCH.get(case.name, branch))
        self.assertNotEqual(branch, "HEAD", "the checkout is detached")
        self.assertEqual(self.git(repo, "diff", "--quiet", "HEAD")[0], 0, "a tracked file has a change")
        self.check_report_folders(case, workspace)

        text = script.read_text(encoding="utf-8")
        if case.name in START_CONTENT:
            name, expected = START_CONTENT[case.name]
            self.assertIn(expected, (repo / name).read_text(encoding="utf-8"), f"{name} has another start content")
        if "SCRATCH_CONTENT=" in text:
            self.assertEqual(self.git(repo, "status", "--porcelain")[1], "?? scratch.txt", "the scratch file must stay untracked")
        bare = repo / ".remote" / "origin.git"
        if bare.exists():
            self.check_remote(repo, bare, text)
            self.check_mocked_pull_request(case, bare)
        if (repo / "tests").is_dir() and not list(repo.glob("*.sln")):
            self.check_python_tests(case, repo)
        return self.refs(repo)

    @staticmethod
    def repo_folder(workspace):
        """The workspace is the repo, except in the bug-hunt fixture, where the repo is project/."""
        project = workspace / "project"
        return project if (project / ".git").is_dir() and not (workspace / ".git").exists() else workspace

    def check_report_folders(self, case, workspace):
        """A bug hunt asks a question if the report folder is missing, so the scaffold must make it."""
        prompt = (case.path / "prompt.md").read_text(encoding="utf-8") if (case.path / "prompt.md").is_file() else ""
        for folder in re.findall(r"--report-dir=\./(\S+?)(?=\s|$)", prompt):
            self.assertTrue((workspace / folder).is_dir(), f"the prompt names the report folder {folder}, but the scaffold made none")

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

    def check_mocked_pull_request(self, case, bare):
        """The head SHA in the mock of pull_request_read must be the commit of the pull request ref. An issue mock has no head."""
        mock = case.path / "mocks" / "github" / "fixtures" / "get.json"
        if not mock.is_file():
            return
        pull = json.loads(mock.read_text(encoding="utf-8"))
        if "head" not in pull:
            return
        ref = f"refs/pull/{pull['number']}/head"
        self.assertEqual(pull["head"]["sha"], self.git(bare, "rev-parse", "--verify", ref)[1],
                         f"the head SHA in {mock.name} is not the commit of {ref}")

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


def sdk_major(version):
    """The major number of a `dotnet --version` output, or 0 if the output does not start with one."""
    head = version.split(".", 1)[0]
    return int(head) if head.isdigit() else 0


def has_runtime_10(runtimes):
    """True if the output of `dotnet --list-runtimes` lists a Microsoft.NETCore.App runtime of major version 10."""
    return re.search(r"^Microsoft\.NETCore\.App 10\.", runtimes, re.MULTILINE) is not None


class DotnetProbeTests(FixtureCase):
    """The .NET probe scaffolds with a real restore and build, then a test run with its marker files."""

    def require_dotnet(self):
        dotnet = shutil.which("dotnet")
        if dotnet is None:
            tool_missing(self, "dotnet not found. Install the .NET SDK 10 or newer to run this test.")
        version = subprocess.run([dotnet, "--version"], capture_output=True, text=True).stdout.strip()
        if sdk_major(version) < 10:
            tool_missing(self, f"The .NET SDK 10 or newer is needed, but dotnet --version prints {version!r}.")
        runtimes = subprocess.run([dotnet, "--list-runtimes"], capture_output=True, text=True).stdout
        if not has_runtime_10(runtimes):
            tool_missing(self, "The .NET 10 runtime is needed, but dotnet --list-runtimes lists none.")
        return dotnet

    def test_probe_scaffolds_build_and_leave_marker_files_after_dotnet_test(self):
        dotnet = self.require_dotnet()
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

    def test_run_marker_says_failed_when_a_test_fails(self):
        dotnet = self.require_dotnet()
        script = next(script for case, script in scaffold_cases() if case.name == "probe-test-fixture")
        workspace = self.workspace("probe-test-fixture")
        self.run_bash([script.as_posix()], workspace, timeout=DOTNET_SECONDS, skip_dotnet=False)
        failing = workspace / "tests" / "Billing.Domain.Tests" / "FailingProbeTests.cs"
        failing.write_text(FAILING_TEST, encoding="utf-8")
        solution = next(workspace.glob("*.sln")).name
        done = subprocess.run([dotnet, "test", solution, "--no-restore"], cwd=workspace,
                              env=self.environment(skip_dotnet=False), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=DOTNET_SECONDS)
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        runs = workspace / ".test-runs"
        self.assertTrue(list(runs.glob("started-*")), "the run left no start file")
        self.assertEqual((runs / "last.txt").read_text(encoding="utf-8"), "Failed")


class DotnetWarmTests(FixtureCase):
    """dotnet_warm with a fake dotnet on PATH and a cache folder of the test, so that the tests need no .NET SDK."""

    def setUp(self):
        super().setUp()
        if shutil.which("flock") is None:
            tool_missing(self, "flock not found")
        folder = self.tmp / "bin"
        folder.mkdir()
        (folder / "dotnet").write_bytes(FAKE_DOTNET.encode("utf-8"))
        (folder / "dotnet").chmod(0o755)
        self.log = self.tmp / "dotnet.log"

    def start_warm(self, name, error=""):
        """Start dotnet_warm with its own HOME, as each eval run has."""
        home = self.tmp / name
        home.mkdir()
        env = self.environment(skip_dotnet=False)
        env.update({
            "HOME": home.as_posix(),
            "PATH": f"{(self.tmp / 'bin').as_posix()}{os.pathsep}{env['PATH']}",
            "EVAL_FIXTURE_DOTNET_CACHE": (self.tmp / "cache").as_posix(),
            "FAKE_DOTNET_LOG": self.log.as_posix(),
            "FAKE_DOTNET_ERROR": error,
        })
        library = REPO / "essentials" / "dev-essentials" / "evals" / "_lib" / "dotnet-fixture.sh"
        return subprocess.Popen([self.bash, "-c", f'source "{library.as_posix()}"\ndotnet_warm Fake.sln'], cwd=self.tmp,
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_two_scaffolds_restore_into_the_shared_folder_one_after_the_other(self):
        processes = [self.start_warm("run-1"), self.start_warm("run-2")]
        for process in processes:
            _out, err = process.communicate(timeout=SCAFFOLD_SECONDS)
            self.assertEqual(process.returncode, 0, err)
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), ["start", "end", "start", "end"])

    def test_the_error_of_a_dotnet_command_goes_to_stderr(self):
        process = self.start_warm("run-1", "error : planted restore failure")
        _out, err = process.communicate(timeout=SCAFFOLD_SECONDS)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("planted restore failure", err)

    def test_every_dotnet_scaffold_runs_with_the_fake_dotnet(self):
        pairs = [(case, script) for case, script in scaffold_cases() if "dotnet_warm" in script.read_text(encoding="utf-8")]
        self.assertTrue(pairs, "No scaffold calls dotnet_warm.")
        for case, script in pairs:
            with self.subTest(case=case.name):
                home = self.tmp / f"home-{case.name}"
                home.mkdir()
                env = self.environment(skip_dotnet=False)
                env.update({
                    "HOME": home.as_posix(),
                    "PATH": f"{(self.tmp / 'bin').as_posix()}{os.pathsep}{env['PATH']}",
                    "EVAL_FIXTURE_DOTNET_CACHE": (self.tmp / "cache").as_posix(),
                    "FAKE_DOTNET_LOG": self.log.as_posix(),
                })
                done = run([self.bash, script.as_posix()], env=env, cwd=self.workspace(case.name), timeout=SCAFFOLD_SECONDS)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


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

    def test_paging_branch_has_the_planted_defect_and_passing_tests(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"),
                         "make_pager_repo\nadd_paging_branch")
        self.assertEqual(self.git(workspace, "rev-parse", "--abbrev-ref", "HEAD")[1], "feature/paging")
        self.assertIn("end = start + size - 1", (workspace / "src" / "pager.py").read_text(encoding="utf-8"))
        self.assertEqual(self.git(workspace, "rev-list", "--count", "main..feature/paging")[1], "1")
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

    def test_pipeline_context_has_a_provider_section_only_for_with_provider(self):
        for variant, has_provider in (("with-provider", True), ("no-provider", False)):
            with self.subTest(variant=variant):
                workspace = self.workspace(variant)
                self.run_snippet(workspace, self.libs("essentials/dev-essentials", "pipeline-fixture.sh"),
                                 f"fixture_init\nfp_write_context {variant}")
                text = (workspace / ".claude" / "feature-pipeline-context.md").read_text(encoding="utf-8")
                self.assertEqual("## Task Provider" in text, has_provider)
                self.assertIn("**Branch template:** `work/{task-id}`", text)
                self.assertIn("- `.pipeline`", text)
                self.assertNotIn("REVIEW.md", text)

    def test_pipeline_context_refuses_another_variant(self):
        workspace = self.workspace()
        with self.assertRaises(AssertionError):
            self.run_snippet(workspace, self.libs("essentials/dev-essentials", "pipeline-fixture.sh"),
                             "fixture_init\nfp_write_context other")

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

    def test_a_push_of_the_pull_request_branch_moves_the_pull_ref(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"),
                         "make_pager_repo\ngit checkout -q -b feature/x\n"
                         "printf 'x\\n' > x.txt\nfixture_commit 'add x'\nfixture_publish feature/x 42:feature/x")
        bare = workspace / ".remote" / "origin.git"
        self.run_snippet(workspace, [], "git commit -q --allow-empty -m 'run commit'\ngit push -q origin feature/x")
        tip = self.git(workspace, "rev-parse", "HEAD")[1]
        self.assertEqual(self.git(bare, "rev-parse", "refs/pull/42/head")[1], tip)

    def test_the_pull_ref_hook_runs_when_the_global_hooks_path_is_set(self):
        workspace = self.workspace()
        other_hooks = self.tmp / "other-hooks"
        other_hooks.mkdir()
        global_config = self.tmp / "global.gitconfig"
        global_config.write_text(f"[core]\n\thooksPath = {other_hooks.as_posix()}\n", encoding="utf-8")
        self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"),
                         f"export GIT_CONFIG_GLOBAL='{global_config.as_posix()}'\n"
                         "make_pager_repo\ngit checkout -q -b feature/x\n"
                         "printf 'x\n' > x.txt\nfixture_commit 'add x'\nfixture_publish feature/x 42:feature/x\n"
                         "git commit -q --allow-empty -m 'run commit'\ngit push -q origin feature/x")
        tip = self.git(workspace, "rev-parse", "HEAD")[1]
        self.assertEqual(self.git(workspace / ".remote" / "origin.git", "rev-parse", "refs/pull/42/head")[1], tip)

    def test_the_pull_ref_hook_runs_when_hooks_are_pinned_off_for_the_push(self):
        """An eval run pins hooks off in the environment of git. Git drops that environment for the receiving side of a local remote.
        A failing pre-push hook in the workspace shows that the pins work for the pushing side."""
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"),
                         "make_pager_repo\ngit checkout -q -b feature/x\n"
                         "printf 'x\\n' > x.txt\nfixture_commit 'add x'\nfixture_publish feature/x 42:feature/x\n"
                         "printf '#!/bin/sh\\nexit 1\\n' > .git/hooks/pre-push\nchmod +x .git/hooks/pre-push")
        environment_pins = ("export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null "
                            "GIT_CONFIG_KEY_1=hook.post-receive.enabled GIT_CONFIG_VALUE_1=false\n")
        argument_push = "git -c core.hooksPath=/dev/null -c hook.post-receive.enabled=false push -q origin feature/x"
        for pins, push in ((environment_pins, "git push -q origin feature/x"), ("", argument_push)):
            with self.subTest(push=push):
                self.run_snippet(workspace, [], f"{pins}git commit -q --allow-empty -m 'run commit'\n{push}")
                tip = self.git(workspace, "rev-parse", "HEAD")[1]
                self.assertEqual(self.git(workspace / ".remote" / "origin.git", "rev-parse", "refs/pull/42/head")[1], tip)

    def test_fixture_commit_uses_the_prefix_and_fixed_dates(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials"),
                         "fixture_init\nprintf 'a\\n' > a.txt\nfixture_commit 'one'\n"
                         "printf 'b\\n' > b.txt\nfixture_commit 'fixture: two'")
        subjects = self.git(workspace, "log", "--format=%s|%at|%ct", "--reverse")[1].splitlines()
        self.assertEqual(subjects, ["fixture: one|1767225660|1767225660", "fixture: two|1767225720|1767225720"])


class CommitGraderTests(FixtureCase):
    """The commit graders read the HEAD reflog of the main work tree. As in an eval run, git runs no hook."""

    @classmethod
    def setUpClass(cls):
        cases = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}
        cls.cases = {name: (cases[name], cases[name].graders[grader][0]) for name, grader in COMMIT_GRADERS.items()}

    def environment(self, skip_dotnet=True):
        env = super().environment(skip_dotnet)
        env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null"})
        return env

    def scaffold(self, name, folder):
        workspace = self.workspace(folder)
        self.run_bash([(self.cases[name][0].path / "scaffold.sh").as_posix()], workspace)
        return workspace

    def passes(self, name, workspace):
        """The verdict of the regex grader on its target file, for the default match or "count:N"."""
        options = self.cases[name][1]
        text = (workspace / options["target"]["path"]).read_text(encoding="utf-8")
        count = len(re.findall(options["pattern"], text))
        match = options.get("match")
        return count == int(match.split(":")[1]) if match else count > 0

    def run_git(self, cwd, *args):
        code, output = self.git(cwd, *args)
        self.assertEqual(code, 0, output)

    def commit(self, tree, paths, message):
        """Add a line to each file, and commit only these files."""
        for path in paths:
            with (tree / path).open("a", encoding="utf-8") as stream:
                stream.write(f"# {message}\n")
        self.run_git(tree, "add", *paths)
        self.run_git(tree, "commit", "-q", "-m", message)

    def worktree_commits(self, workspace, paths):
        """Commit each file in its own linked worktree on the branch fix-<n>."""
        for number, path in enumerate(paths, 1):
            tree = workspace / ".claude" / "worktrees" / f"fix-{number}"
            self.run_git(workspace, "worktree", "add", "-q", str(tree), "-b", f"fix-{number}")
            self.commit(tree, [path], f"fix {number} in a worktree")

    def merge_and_commit(self, workspace, branch):
        """Merge with no commit, then commit. Git writes the line "commit (merge):"."""
        self.run_git(workspace, "merge", "-q", "--no-ff", "--no-commit", branch)
        self.run_git(workspace, "commit", "-q", "--no-edit")

    def amend_the_fixture_commit(self, workspace, paths):
        """Add a line to each file in the last fixture commit. Git writes the line "commit (amend):"."""
        for path in paths:
            with (workspace / path).open("a", encoding="utf-8") as stream:
                stream.write("# changed on main\n")
        self.run_git(workspace, "add", *paths)
        self.run_git(workspace, "commit", "-q", "--amend", "--no-edit")

    def cherry_pick_with_a_conflict(self, workspace, branch, path):
        """Cherry-pick a commit that stops on a conflict, and commit the result. Git writes "commit (cherry-pick):"."""
        code, output = self.git(workspace, "cherry-pick", branch)
        self.assertNotEqual(code, 0, output)
        self.run_git(workspace, "checkout", "--theirs", "--", path)
        self.run_git(workspace, "add", path)
        self.run_git(workspace, "commit", "-q", "--no-edit")

    def check_shapes(self, name, shapes):
        for shape, expected in shapes.items():
            with self.subTest(case=name, shape=shape.__name__):
                workspace = self.scaffold(name, f"{name}-{shape.__name__}")
                shape(workspace)
                self.assertEqual(self.passes(name, workspace), expected)

    def test_the_rename_graders_count_a_commit_that_reaches_the_main_work_tree(self):
        path = ["app/users.py"]

        def no_commit(workspace):
            pass

        def a_commit_on_a_new_branch(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "run-branch")
            self.commit(workspace, path, "rename")

        def a_commit_with_the_fixture_prefix(workspace):
            self.commit(workspace, path, "fixture: rename")

        def a_worktree_commit_and_a_fast_forward_merge(workspace):
            self.worktree_commits(workspace, path)
            self.run_git(workspace, "merge", "-q", "--ff-only", "fix-1")

        def a_worktree_commit_and_a_merge_that_stops_before_the_commit(workspace):
            self.worktree_commits(workspace, path)
            self.merge_and_commit(workspace, "fix-1")

        def a_worktree_commit_and_a_cherry_pick(workspace):
            self.worktree_commits(workspace, path)
            self.run_git(workspace, "cherry-pick", "fix-1")

        def a_worktree_commit_and_a_cherry_pick_with_a_conflict(workspace):
            self.worktree_commits(workspace, path)
            self.amend_the_fixture_commit(workspace, path)
            self.cherry_pick_with_a_conflict(workspace, "fix-1", path[0])

        def a_worktree_commit_only(workspace):
            self.worktree_commits(workspace, path)

        def an_amend_of_the_fixture_commit(workspace):
            self.run_git(workspace, "commit", "-q", "--amend", "--allow-empty", "-m", "fixture: amended")

        for name in ("so-rename-small", "so-rename-large", "rirr-retry-limit"):
            self.check_shapes(name, {
                no_commit: False,
                a_commit_on_a_new_branch: True,
                a_commit_with_the_fixture_prefix: False,
                a_worktree_commit_and_a_fast_forward_merge: True,
                a_worktree_commit_and_a_merge_that_stops_before_the_commit: True,
                a_worktree_commit_and_a_cherry_pick: True,
                a_worktree_commit_and_a_cherry_pick_with_a_conflict: True,
                a_worktree_commit_only: False,
                an_amend_of_the_fixture_commit: False,
            })

    def test_the_fix_grader_needs_one_commit_for_each_fix_in_the_main_work_tree(self):
        fixes = ["app/billing.py", "app/shipping.py"]

        def no_commit(workspace):
            pass

        def one_commit_with_both_fixes(workspace):
            self.commit(workspace, fixes, "fix both")

        def one_fix_commit_and_one_commit_with_the_fixture_prefix(workspace):
            self.commit(workspace, fixes[:1], "fix 1")
            self.commit(workspace, fixes[1:], "fixture: fix 2")

        def two_commits_on_a_new_branch(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "run-branch")
            for number, path in enumerate(fixes, 1):
                self.commit(workspace, [path], f"fix {number}")

        def two_commits_on_a_new_branch_and_a_merge_to_main(workspace):
            two_commits_on_a_new_branch(workspace)
            self.run_git(workspace, "checkout", "-q", "main")
            self.run_git(workspace, "merge", "-q", "--ff-only", "run-branch")

        def one_combined_commit_on_a_new_branch_and_a_merge_to_main(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "run-branch")
            self.commit(workspace, fixes, "fix both")
            self.run_git(workspace, "checkout", "-q", "main")
            self.run_git(workspace, "merge", "-q", "--ff-only", "run-branch")

        def two_fix_commits_and_a_third_commit(workspace):
            for number, path in enumerate(fixes, 1):
                self.commit(workspace, [path], f"fix {number}")
            self.commit(workspace, ["README.md"], "docs")

        # A known limit: the grader cannot see the files of a commit.
        def one_combined_commit_and_one_more_commit(workspace):
            self.commit(workspace, fixes, "fix both")
            self.commit(workspace, ["README.md"], "docs")

        def worktree_commits_and_a_merge_of_each(workspace):
            self.worktree_commits(workspace, fixes)
            self.run_git(workspace, "merge", "-q", "--no-edit", "fix-1")
            self.run_git(workspace, "merge", "-q", "--no-edit", "fix-2")

        def worktree_commits_and_a_merge_of_each_that_stops_before_the_commit(workspace):
            self.worktree_commits(workspace, fixes)
            self.merge_and_commit(workspace, "fix-1")
            self.merge_and_commit(workspace, "fix-2")

        def worktree_commits_and_a_cherry_pick_of_each(workspace):
            self.worktree_commits(workspace, fixes)
            self.run_git(workspace, "cherry-pick", "fix-1", "fix-2")

        def worktree_commits_and_a_cherry_pick_of_each_with_a_conflict(workspace):
            self.worktree_commits(workspace, fixes)
            self.amend_the_fixture_commit(workspace, fixes)
            for number, path in enumerate(fixes, 1):
                self.cherry_pick_with_a_conflict(workspace, f"fix-{number}", path)

        # A known limit: a combined commit and its merge give the same two lines.
        def one_fix_commit_and_a_merge_of_a_worktree_commit(workspace):
            self.worktree_commits(workspace, fixes)
            self.commit(workspace, fixes[:1], "fix 1 on main")
            self.run_git(workspace, "merge", "-q", "--no-edit", "fix-2")

        def two_commits_in_one_worktree(workspace):
            tree = workspace / ".claude" / "worktrees" / "fixes"
            self.run_git(workspace, "worktree", "add", "-q", str(tree), "-b", "fixes")
            for number, path in enumerate(fixes, 1):
                self.commit(tree, [path], f"fix {number} in a worktree")

        def two_commits_in_one_worktree_and_one_fast_forward_merge(workspace):
            two_commits_in_one_worktree(workspace)
            self.run_git(workspace, "merge", "-q", "--ff-only", "fixes")

        def two_commits_in_one_worktree_and_a_pull(workspace):
            two_commits_in_one_worktree(workspace)
            self.run_git(workspace, "push", "-q", "origin", "fixes")
            self.run_git(workspace, "pull", "-q", "--ff-only", "origin", "fixes")

        def two_commits_in_one_worktree_and_a_reset_of_main(workspace):
            two_commits_in_one_worktree(workspace)
            self.run_git(workspace, "reset", "-q", "--hard", "fixes")

        def two_commits_in_one_worktree_and_a_rebase_of_main(workspace):
            two_commits_in_one_worktree(workspace)
            self.run_git(workspace, "rebase", "-q", "fixes")

        def worktree_commits_and_a_second_commit_of_each_fix(workspace):
            self.worktree_commits(workspace, fixes)
            for number, path in enumerate(fixes, 1):
                self.commit(workspace, [path], f"fix {number} on main")

        def worktree_commits_and_one_combined_commit(workspace):
            self.worktree_commits(workspace, fixes)
            self.commit(workspace, fixes, "fix both")

        def worktree_commits_only(workspace):
            self.worktree_commits(workspace, fixes)

        self.check_shapes("so-two-fixes", {
            no_commit: False,
            one_commit_with_both_fixes: False,
            one_fix_commit_and_one_commit_with_the_fixture_prefix: False,
            two_commits_on_a_new_branch: True,
            two_commits_on_a_new_branch_and_a_merge_to_main: True,
            one_combined_commit_on_a_new_branch_and_a_merge_to_main: False,
            two_fix_commits_and_a_third_commit: True,
            one_combined_commit_and_one_more_commit: True,
            worktree_commits_and_a_merge_of_each: True,
            worktree_commits_and_a_merge_of_each_that_stops_before_the_commit: True,
            worktree_commits_and_a_cherry_pick_of_each: True,
            worktree_commits_and_a_cherry_pick_of_each_with_a_conflict: True,
            one_fix_commit_and_a_merge_of_a_worktree_commit: False,
            two_commits_in_one_worktree_and_one_fast_forward_merge: False,
            two_commits_in_one_worktree_and_a_pull: False,
            two_commits_in_one_worktree_and_a_reset_of_main: False,
            two_commits_in_one_worktree_and_a_rebase_of_main: False,
            worktree_commits_and_a_second_commit_of_each_fix: True,
            worktree_commits_and_one_combined_commit: False,
            worktree_commits_only: False,
        })

    def test_the_retry_limit_change_turns_the_http_client_test_red(self):
        workspace = self.scaffold("rirr-retry-limit", "rirr-red")
        settings = workspace / "config" / "settings.py"
        settings.write_text(settings.read_text(encoding="utf-8").replace("HTTP_RETRY_LIMIT = 5", "HTTP_RETRY_LIMIT = 3"),
                            encoding="utf-8")
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                              env={**self.environment(), "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertNotEqual(done.returncode, 0, done.stderr)
        self.assertIn("test_get_uses_the_retry_limit_of_the_settings", done.stderr)


if __name__ == "__main__":
    unittest.main()
