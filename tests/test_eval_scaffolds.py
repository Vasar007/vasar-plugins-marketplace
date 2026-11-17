"""Runs the scaffold scripts and the fixture libraries of the eval cases. The tests call no model.

Each scaffold runs in a new temporary folder, with HOME set to another temporary folder and
EVAL_FIXTURE_SKIP_DOTNET=1. The tests need bash and git, and the Python tests of a fixture need Python.
If bash or git is not found, the tests skip. In CI they fail.

The tests of DotnetProbeTests run the .NET probe scaffolds with a real restore and build, and then run dotnet test.
It needs the .NET SDK 10 or newer, the .NET 10 runtime, and network access for the first restore. As in a real run, the packages
go to /tmp/plugin-evals/nuget, and the scaffold copies them into the NuGet folder of HOME.

The tests of DotnetWarmTests run dotnet_warm with a fake dotnet on PATH and a cache folder of the test. They need flock (util-linux).
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
from test_eval_cases import REGEX_FLAGS, load_cases, parse_block, plugin_roots, split_frontmatter
from testkit import ScratchCase, remove_tree, run

SCAFFOLD_SECONDS = 120
SQUASH_SCRIPT = REPO / "essentials/dev-essentials/scripts/squash_task.py"
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
    "rl-failing-build": "feature/paging",
    "fp-e1-seeded-defects": "work/seeded-defects",
    "fp-e1-clean-change": "work/clean-change",
    "fp-e1-border-auth": "work/border-auth",
    "fp-e2-untracked-file": "work/untracked-file",
    "fp-e2-fork-pr": "work/fork-pr",
    "fp-e3-autonomous-main": "main",
    "fp-e4-package-bump": "work/package-bump",
    "fp-e5-breaking-change": "work/breaking-change",
    "fp-e8-rename-across-projects": "work/rename-across-projects",
    "fp-free-text": "work/free-text",
    "wt-one-class": "work/tests",
    "wt-pricing-folder": "work/tests",
    "cmp-pr-from-diff": "user/tasks/12-customer-index",
    "cmp-task-draft": "main",
    "cmp-guide-draft": "main",
    "ta-full-pass": "main",
}
# The start content that a task needs. A scaffold that sets it too early or too late gives a no-op task.
START_CONTENT = {
    "fp-e4-package-bump": ("Directory.Packages.props", '<PackageVersion Include="NUnit" Version="4.6.1" />'),
}
# A literal commit id in a grader pattern: \b, then 7 to 40 hex characters.
COMMIT_LITERAL = re.compile(r"\\b([0-9a-f]{7,40})(?![0-9a-f])")
BRANCH_LOG_PATH = re.compile(r"(?:^|/)logs/refs/heads/(.+)$")
# compose-pr saves Notes/PRs/PR-<branch>.md, with each / of the branch as -. A pattern writes the dot as \.
PR_FILE_NAME = re.compile(r"PR-([\w.-]+?)\\?\.md")
# The fork owner in the PR creation entry of a project context. Step 6 of feature-pipeline then sends <owner>:<branch> as head.
FORK_OWNER = re.compile(r"^- \*\*PR creation:\*\* .*, fork owner `([^`]+)`$", re.MULTILINE)
# The repository of the PR: the next backticked text after the tool in the PR creation entry, if it is owner/repo. Step 6 takes owner and repo from it.
PR_REPO = re.compile(r"^- \*\*PR creation:\*\* `[^`]+`[^`\n]*`([^/`\s]+)/([^`\s]+)`", re.MULTILINE)
# Without that part, Step 6 takes owner and repo from the Task Provider.
PROVIDER_REPO = re.compile(r"^- \*\*Project / organization:\*\* `([^/`]+)/([^`]+)`$", re.MULTILINE)
# The cases whose Python tests fail on purpose. The value is the number of failing tests.
FAILING_TESTS = {"so-two-fixes": 2}
# The commit grader of each case that asks for a commit on the users repo.
COMMIT_GRADERS = {"so-rename-small": "committed", "so-rename-large": "committed", "so-two-fixes": "two-commits",
                  "rirr-retry-limit": "committed"}
# A "no push" grader reads every branch of the remote. fp-e3-autonomous-main must push a work branch, so its grader names main.
NO_PUSH_PATH = ".remote/origin.git/logs/refs/heads/**"
NO_PUSH_EXCEPTIONS = {("fp-e3-autonomous-main", "main-not-pushed")}
# A "no commit" grader of a branch fails on each reflog line that the fixture did not write.
BRANCH_NO_COMMIT_PATTERN = r"\t(?!commit(?: \(initial\))?: fixture:|branch: Created from)"
# The "no commit" graders of each case. A test runs each one on its scaffold.
NO_COMMIT_GRADERS = {"fp-e1-clean-change": ("no-commit", "no-commit-any-branch"), "fp-e3-autonomous-main": ("main-no-commit",),
                     "ppc-build-context": ("no-commit",), "ppc-gated-threads": ("no-commit",),
                     "ppc-open-items-answered": ("no-commit",),
                     "ppc-ride-along-commit": ("no-commit",), "rl-clean-branch": ("no-fix-commit",),
                     "rl-pr-head-gate": ("main-not-committed", "pr-branch-not-committed")}
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
CRASHING_TEST = """namespace Billing.Domain.Tests;

[TestFixture]
public sealed class CrashingProbeTests
{
    [Test]
    public void StopsTheTestHost()
    {
        Environment.FailFast("planted crash");
    }
}
"""
BROKEN_SOURCE = """namespace Billing.Domain;

public static class BrokenProbe
{
    public static int Value() => "text";
}
"""


FAKE_DOTNET = """#!/usr/bin/env bash
# A fake dotnet: a restore into the shared folder logs its start and its end, and prints FAKE_DOTNET_ERROR as dotnet does.
case " $* " in
    *" --packages "*)
        if [ -e /dev/fd/9 ]; then echo lock-descriptor-open >>"$FAKE_DOTNET_LOG"; fi
        if [ -f "$2" ]; then grep -o 'Include="[^"]*" Version="[^"]*"' "$2" >>"$FAKE_DOTNET_LOG"; fi
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


def pr_file_problems(case, branch):
    """A grader that names the PR file of compose-pr must name the file of the scaffold branch."""
    expected = branch.replace("/", "-")
    problems = []
    for name, (options, _body) in sorted(case.graders.items()):
        target = options.get("target")
        texts = [options.get("path"), options.get("pattern"), target.get("path") if isinstance(target, dict) else None]
        for text in (t for t in texts if isinstance(t, str)):
            problems += [f"{case.label}/graders/{name}.md: the PR file names {found}, but the scaffold branch gives {expected}"
                         for found in PR_FILE_NAME.findall(text) if found != expected]
    return problems


def shared_form_problems(case):
    """A "no push" grader must read every branch of the remote. A "no commit" grader of a branch must fail on each move of it."""
    problems = []
    for name, (options, _body) in sorted(case.graders.items()):
        path, target = options.get("path"), options.get("target")
        if options.get("type") == "file_exists" and options.get("exists") is False and isinstance(path, str) \
                and path.startswith(".remote/origin.git/logs/") and path != NO_PUSH_PATH \
                and (case.name, name) not in NO_PUSH_EXCEPTIONS:
            problems.append(f"{case.label}/graders/{name}.md: a no-push grader must read {NO_PUSH_PATH}")
        if options.get("type") == "regex" and options.get("match") == "not_contains" and isinstance(target, dict) \
                and str(target.get("path", "")).startswith(".git/logs/refs/heads/") \
                and options.get("pattern") != BRANCH_NO_COMMIT_PATTERN:
            problems.append(f"{case.label}/graders/{name}.md: a no-commit grader of a branch must use {BRANCH_NO_COMMIT_PATTERN}")
    return problems


def commit_literal_problems(case, commits):
    """A commit id in a regex grader pattern must start a commit of the scaffold repository."""
    problems = []
    for name, (options, _body) in sorted(case.graders.items()):
        pattern = options.get("pattern")
        if options.get("type") != "regex" or not isinstance(pattern, str):
            continue
        for literal in COMMIT_LITERAL.findall(pattern):
            if any(c.isdigit() for c in literal) and any(c.isalpha() for c in literal) \
                    and not any(commit.startswith(literal) for commit in commits):
                problems.append(f"{case.label}/graders/{name}.md: the pattern names the commit {literal}, "
                                "but no commit of the scaffold starts with it")
    return problems


def pr_head_problem(context, branch, expect):
    """The head that the PR mock expects must be <fork owner>:<branch>, or the bare branch with no fork owner.

    Return None if the mock guards no head.
    """
    if not isinstance(expect, dict) or "head" not in expect:
        return None
    found = FORK_OWNER.search(context)
    wanted = f"{found.group(1)}:{branch}" if found else branch
    if expect["head"] != wanted:
        return f"the PR mock expects the head {expect['head']}, but the project context gives {wanted}"
    return None


def pr_repo_problem(context, expect):
    """The owner and repo that the PR mock expects must be the repository that the project context gives.

    Return None if the mock guards no repository, or if the context names none.
    """
    if not isinstance(expect, dict) or "owner" not in expect or "repo" not in expect:
        return None
    found = PR_REPO.search(context) or PROVIDER_REPO.search(context)
    if found is None:
        return None
    if (expect["owner"], expect["repo"]) != found.groups():
        return f"the PR mock expects {expect['owner']}/{expect['repo']}, but the project context gives {'/'.join(found.groups())}"
    return None


class PrHeadTests(unittest.TestCase):
    ENTRY = "- **PR creation:** `mcp__plugin_github_github__create_pull_request` for `example-org/inventory`"

    def test_the_head_follows_the_fork_owner_of_the_pr_creation_entry(self):
        fork = self.ENTRY + ", fork owner `eval-user`"
        other = "## Key Conventions\n\n- Each PR names the issue, fork owner `eval-user`"
        runs = {
            "no fork, the bare branch": (self.ENTRY, {"head": "work/a"}, True),
            "a fork, the owner and the branch": (fork, {"head": "eval-user:work/a"}, True),
            "a fork, the bare branch": (fork, {"head": "work/a"}, False),
            "no fork, an owner in the head": (self.ENTRY, {"head": "eval-user:work/a"}, False),
            "a fork, another owner": (fork, {"head": "other:work/a"}, False),
            "a fork owner in another section": (self.ENTRY + "\n" + other, {"head": "work/a"}, True),
            "no head in the mock": (fork, {"owner": "example-org"}, True),
            "no expect block": (fork, None, True),
        }
        for name, (context, expect, right) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(pr_head_problem(context, "work/a", expect) is None, right)

    def test_the_repository_follows_the_pr_creation_entry_or_the_task_provider(self):
        provider = "- **Project / organization:** `example-org/inventory`\n"
        expect = {"owner": "example-org", "repo": "inventory"}
        runs = {
            "the entry names the repository": (provider + self.ENTRY, expect, True),
            "the entry names another repository": (provider + self.ENTRY.replace("inventory", "stock"), expect, False),
            "no repository in the entry, the Task Provider": (provider + "- **PR creation:** `mcp__plugin_github_github__create_pull_request`", expect, True),
            "no repository in the entry, another Task Provider": (provider.replace("inventory", "stock") + "- **PR creation:** `gh pr create`", expect, False),
            "the entry names another repository in other words": (provider + "- **PR creation:** `mcp__plugin_github_github__create_pull_request` for the repository `example-org/stock`", expect, False),
            "another owner": (provider + self.ENTRY, {"owner": "other", "repo": "inventory"}, False),
            "no repository in the context": ("- **PR creation:** `gh pr create`", expect, True),
            "no owner in the mock": (provider + self.ENTRY.replace("inventory", "stock"), {"head": "work/a"}, True),
            "no expect block": (provider + self.ENTRY, None, True),
        }
        for name, (context, wanted, right) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(pr_repo_problem(context, wanted) is None, right)


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

    def test_the_pr_file_of_a_grader_names_the_branch_of_the_scaffold(self):
        cases = [case for root in plugin_roots() for case in load_cases(root) if case.name in EXPECTED_BRANCH]
        self.assertEqual([p for case in cases for p in pr_file_problems(case, EXPECTED_BRANCH[case.name])], [])
        composer = next((case for case in cases if case.name == "cmp-pr-from-diff"), None)
        self.assertIsNotNone(composer, "No case cmp-pr-from-diff is listed in EXPECTED_BRANCH.")
        self.assertTrue(pr_file_problems(composer, "user/tasks/13-other"), "The check reads no PR file of cmp-pr-from-diff.")

    def test_a_pr_file_of_another_branch_is_found(self):
        case = SimpleNamespace(label="cmp-x", graders={
            "saved": ({"type": "file_exists", "path": "Notes/PRs/PR-user-tasks-13-index.md"}, ""),
            "reported": ({"type": "regex", "pattern": "PR-user-tasks-13-index\\.md"}, ""),
            "read": ({"type": "regex", "target": {"source": "file", "path": "Notes/PRs/PR-main.md"}}, ""),
        })
        problems = pr_file_problems(case, "user/tasks/12-index")
        self.assertEqual(len(problems), 3, problems)
        self.assertTrue(any("saved" in p for p in problems) and any("reported" in p for p in problems)
                        and any("read" in p for p in problems), problems)

    def test_a_typo_in_a_branch_path_is_found(self):
        case = SimpleNamespace(label="fp-x", graders={
            "committed": ({"type": "regex", "target": {"source": "file", "path": ".git/logs/refs/heads/work/a"}}, ""),
            "no-push": ({"type": "file_exists", "path": ".remote/origin.git/logs/refs/heads/work/b"}, ""),
            "any-push": ({"type": "file_exists", "path": ".remote/origin.git/logs/refs/heads/*/*"}, ""),
        })
        problems = branch_path_problems(case, "work/a")
        self.assertEqual(len(problems), 1)
        self.assertIn("no-push", problems[0])

    def test_the_no_push_and_no_commit_graders_use_the_shared_forms(self):
        cases = [case for root in plugin_roots() for case in load_cases(root)]
        self.assertEqual([p for case in cases for p in shared_form_problems(case)], [])

    def test_an_old_no_push_or_no_commit_form_is_found(self):
        branch_log = {"source": "file", "path": ".git/logs/refs/heads/feature/a"}
        case = SimpleNamespace(name="rl-x", label="rl-x", graders={
            "committed": ({"type": "regex", "pattern": r"\tcommit: (?!fixture:)", "target": branch_log}, ""),
            "no-commit": ({"type": "regex", "pattern": r"\tcommit: (?!fixture:)", "match": "not_contains",
                           "target": branch_log}, ""),
            "no-push": ({"type": "file_exists", "path": ".remote/origin.git/logs/refs/heads/feature/a", "exists": False}, ""),
            "pushed": ({"type": "file_exists", "path": ".remote/origin.git/logs/refs/heads/feature/a"}, ""),
        })
        problems = shared_form_problems(case)
        self.assertEqual([problem.split(":")[0] for problem in problems], ["rl-x/graders/no-commit.md", "rl-x/graders/no-push.md"])


class CommitLiteralTests(unittest.TestCase):
    COMMITS = ["804a1380000000000000000000000000000000aa", "7a99d1e0000000000000000000000000000000bb"]

    @staticmethod
    def case(**patterns):
        graders = {name: ({"type": "regex", "pattern": pattern}, "") for name, pattern in patterns.items()}
        return SimpleNamespace(label="ppc-x", graders=graders)

    def test_a_literal_that_starts_a_commit_passes(self):
        case = self.case(a=r"\b804a138", b=r"\b9101\b[\s\S]{0,400}\b7a99d1e|\b7a99d1e[\s\S]{0,400}\b9101\b")
        self.assertEqual(commit_literal_problems(case, self.COMMITS), [])

    def test_a_wrong_literal_is_found(self):
        problems = commit_literal_problems(self.case(names=r"\b804a139"), self.COMMITS)
        self.assertEqual(len(problems), 1)
        self.assertIn("ppc-x/graders/names.md", problems[0])
        self.assertIn("804a139", problems[0])

    def test_words_and_numbers_are_not_commit_literals(self):
        case = self.case(a=r"\bdefaced\b", b=r"\b1234567\b", c=r"\bfeature/paging")
        self.assertEqual(commit_literal_problems(case, self.COMMITS), [])

    def test_a_grader_of_another_type_is_skipped(self):
        case = SimpleNamespace(label="ppc-x", graders={"a": ({"type": "file_exists", "pattern": r"\b804a139"}, "")})
        self.assertEqual(commit_literal_problems(case, self.COMMITS), [])


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
        self.check_commit_literals(case, repo)

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
        self.check_pr_head(case, repo, branch)
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

    def check_commit_literals(self, case, repo):
        commits = self.git(repo, "log", "--all", "--format=%H")[1].splitlines()
        self.assertEqual(commit_literal_problems(case, commits), [])

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

    def check_pr_head(self, case, repo, branch):
        """The head, the owner, and the repo in the expect block of the PR mock must be the values that the project context of the scaffold gives."""
        mock = case.path / "mocks" / "github" / "create_pull_request.md"
        context = repo / ".claude" / "feature-pipeline-context.md"
        if not mock.is_file() or not context.is_file():
            return
        lines, _body = split_frontmatter(mock.read_text(encoding="utf-8"))
        text = context.read_text(encoding="utf-8")
        expect = parse_block(lines).get("expect")
        self.assertIsNone(pr_head_problem(text, branch, expect))
        self.assertIsNone(pr_repo_problem(text, expect))

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

    def test_run_marker_follows_the_last_build_and_test_run(self):
        """A failed build after a passing run, or after a deleted source file, leaves Stale. A test host that stops early leaves Started."""
        dotnet = self.require_dotnet()
        script = next(script for case, script in scaffold_cases() if case.name == "probe-test-fixture")
        workspace = self.workspace("probe-test-fixture")
        self.run_bash([script.as_posix()], workspace, timeout=DOTNET_SECONDS, skip_dotnet=False)
        last = workspace / ".test-runs" / "last.txt"

        def dotnet_run(command):
            done = subprocess.run([dotnet, command, "Billing.sln", "--no-restore", "-m:1"], cwd=workspace,
                                  env=self.environment(skip_dotnet=False), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=DOTNET_SECONDS)
            return done.returncode, done.stdout + done.stderr

        code, output = dotnet_run("test")
        self.assertEqual(code, 0, output)
        self.assertEqual(last.read_text(encoding="utf-8").strip(), "Passed")
        code, output = dotnet_run("build")
        self.assertEqual(code, 0, output)
        self.assertEqual(last.read_text(encoding="utf-8").strip(), "Passed", "a build with no change must keep the outcome")
        broken = workspace / "src" / "Billing.Domain" / "BrokenProbe.cs"
        broken.write_text(BROKEN_SOURCE, encoding="utf-8")
        code, output = dotnet_run("test")
        self.assertNotEqual(code, 0, output)
        self.assertEqual(last.read_text(encoding="utf-8").strip(), "Stale", "a failed build must not keep Passed")
        broken.unlink()
        (workspace / "tests" / "Billing.Domain.Tests" / "CrashingProbeTests.cs").write_text(CRASHING_TEST, encoding="utf-8")
        code, output = dotnet_run("test")
        self.assertNotEqual(code, 0, output)
        self.assertEqual(last.read_text(encoding="utf-8").strip(), "Started", "a crash before the teardown must not keep Passed")
        (workspace / "tests" / "Billing.Domain.Tests" / "CrashingProbeTests.cs").unlink()
        code, output = dotnet_run("test")
        self.assertEqual(code, 0, output)
        self.assertEqual(last.read_text(encoding="utf-8").strip(), "Passed")
        (workspace / "src" / "Billing.Domain" / "Money.cs").unlink()
        code, output = dotnet_run("build")
        self.assertNotEqual(code, 0, output)
        self.assertEqual(last.read_text(encoding="utf-8").strip(), "Stale", "a deleted source file must not keep Passed")


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
        self.temp = self.tmp / "temp"
        self.temp.mkdir()

    def warm_environment(self, name, error=""):
        """The environment of a scaffold with the fake dotnet, its own HOME and TMPDIR, and the cache folder of the test."""
        home = self.tmp / name
        home.mkdir()
        env = self.environment(skip_dotnet=False)
        env.update({
            "HOME": home.as_posix(),
            "TMPDIR": self.temp.as_posix(),
            "PATH": f"{(self.tmp / 'bin').as_posix()}{os.pathsep}{env['PATH']}",
            "EVAL_FIXTURE_DOTNET_CACHE": (self.tmp / "cache").as_posix(),
            "FAKE_DOTNET_LOG": self.log.as_posix(),
            "FAKE_DOTNET_ERROR": error,
        })
        return env

    def start_warm(self, name, error="", packages=()):
        """Start dotnet_warm with its own HOME, as each eval run has."""
        library = REPO / "essentials" / "dev-essentials" / "evals" / "_lib" / "dotnet-fixture.sh"
        command = f'source "{library.as_posix()}"\ndotnet_warm Fake.sln {" ".join(packages)}'
        return subprocess.Popen([self.bash, "-c", command], cwd=self.tmp, env=self.warm_environment(name, error),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

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

    def test_a_named_package_goes_into_the_shared_folder_before_the_solution(self):
        process = self.start_warm("run-1", packages=("NUnit@5.0.0",))
        _out, err = process.communicate(timeout=SCAFFOLD_SECONDS)
        self.assertEqual(process.returncode, 0, err)
        self.assertEqual(self.log.read_text(encoding="utf-8").split(),
                         ['Include="NUnit"', 'Version="5.0.0"', "start", "end", "start", "end"])

    def test_two_scaffolds_with_a_named_package_restore_one_after_the_other(self):
        processes = [self.start_warm(f"run-{number}", packages=("NUnit@5.0.0",)) for number in (1, 2)]
        for process in processes:
            _out, err = process.communicate(timeout=SCAFFOLD_SECONDS)
            self.assertEqual(process.returncode, 0, err)
        one_run = ['Include="NUnit"', 'Version="5.0.0"', "start", "end", "start", "end"]
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), one_run + one_run)

    def test_a_failed_package_restore_of_a_scaffold_leaves_no_temporary_folder(self):
        script = next(script for case, script in scaffold_cases() if case.name == "fp-e4-package-bump")
        done = run([self.bash, script.as_posix()], env=self.warm_environment("run-1", "error : planted restore failure"),
                   cwd=self.workspace("fp-e4-package-bump"), timeout=SCAFFOLD_SECONDS)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("planted restore failure", done.stderr)
        self.assertEqual(list(self.temp.iterdir()), [], "the scaffold left a temporary folder")

    def test_every_dotnet_scaffold_runs_with_the_fake_dotnet(self):
        pairs = [(case, script) for case, script in scaffold_cases() if "dotnet_warm" in script.read_text(encoding="utf-8")]
        self.assertTrue(pairs, "No scaffold calls dotnet_warm.")
        for case, script in pairs:
            with self.subTest(case=case.name):
                env = self.warm_environment(f"home-{case.name}")
                done = run([self.bash, script.as_posix()], env=env, cwd=self.workspace(case.name), timeout=SCAFFOLD_SECONDS)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class DotnetNodeReuseTests(FixtureCase):
    """Each dotnet command of dotnet_warm turns off the reuse of MSBuild nodes (issue 250)."""

    FAKE_DOTNET_ARGUMENTS = """#!/usr/bin/env bash
# A fake dotnet that logs the arguments of each call on one line.
echo "$*" >>"$FAKE_DOTNET_LOG"
"""

    def test_every_dotnet_command_of_dotnet_warm_turns_off_node_reuse(self):
        if shutil.which("flock") is None:
            tool_missing(self, "flock not found")
        folder = self.tmp / "bin"
        folder.mkdir()
        (folder / "dotnet").write_bytes(self.FAKE_DOTNET_ARGUMENTS.encode("utf-8"))
        (folder / "dotnet").chmod(0o755)
        log = self.tmp / "dotnet.log"
        temp = self.tmp / "temp"
        temp.mkdir()
        env = self.environment(skip_dotnet=False)
        env.update({
            "TMPDIR": temp.as_posix(),
            "PATH": f"{folder.as_posix()}{os.pathsep}{env['PATH']}",
            "EVAL_FIXTURE_DOTNET_CACHE": (self.tmp / "cache").as_posix(),
            "FAKE_DOTNET_LOG": log.as_posix(),
        })
        library = REPO / "essentials" / "dev-essentials" / "evals" / "_lib" / "dotnet-fixture.sh"
        done = run([self.bash, "-c", f'source "{library.as_posix()}"\ndotnet_warm Fake.sln NUnit@5.0.0'],
                   env=env, cwd=self.tmp, timeout=SCAFFOLD_SECONDS)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        calls = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual([call.split()[0] for call in calls], ["restore", "restore", "restore", "build"])
        self.assertEqual([call for call in calls if "-nodeReuse:false" not in call.split()], [],
                         "a dotnet command can reuse an MSBuild node of an earlier run")


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

    def test_failing_build_case_fails_only_its_build_and_the_check_says_same_at_parent(self):
        workspace = self.workspace()
        case = REPO / "essentials/dev-essentials/evals/review-loop/rl-failing-build"
        self.run_bash([(case / "scaffold.sh").as_posix()], workspace)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        self.assertIn("Build command: `python3 tools/build_docs.py`", (workspace / "CLAUDE.md").read_text(encoding="utf-8"))
        build = subprocess.run([sys.executable, "tools/build_docs.py"], cwd=workspace, capture_output=True, text=True, env=env)
        self.assertEqual(build.returncode, 1, build.stdout)
        self.assertIn("error: the docs theme is missing.", build.stderr)
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                               capture_output=True, text=True, env=env)
        self.assertEqual(tests.returncode, 0, tests.stderr)
        self.assertEqual(self.git(workspace, "log", "-1", "--format=%s", "main")[1], "fixture: add the docs build")
        pager = workspace / "src" / "pager.py"
        pager.write_text(pager.read_text(encoding="utf-8").replace("end = start + size - 1", "end = start + size"),
                         encoding="utf-8")
        self.assertEqual(self.git(workspace, "commit", "-q", "-am", "Review round 1: Fix page_slice")[0], 0)
        script = REPO / "essentials/dev-essentials/skills/review-loop/scripts/failure_check.py"
        done = subprocess.run([sys.executable, "-I", str(script), "--fix-commit", "HEAD",
                               "--command", f'"{REPO.__class__(sys.executable).as_posix()}" tools/build_docs.py'],
                              cwd=workspace, capture_output=True, text=True, env=self.environment(), timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("VERDICT: SAME-AT-PARENT", done.stdout)

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
        A failing pre-push hook in the workspace shows that the core.hooksPath pin works for the pushing side."""
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

    def test_a_push_from_a_linked_worktree_reaches_the_remote(self):
        workspace = self.workspace()
        self.run_snippet(workspace, self.libs("essentials/dev-essentials", "py-fixture.sh"),
                         "make_pager_repo\nfixture_publish main\n"
                         "git worktree add -q .claude/worktrees/x -b feature/x\ncd .claude/worktrees/x\n"
                         "git commit -q --allow-empty -m 'run commit'\ngit push -q origin feature/x\ngit fetch -q origin")
        bare = workspace / ".remote" / "origin.git"
        self.assertTrue((bare / "logs" / "refs" / "heads" / "feature" / "x").is_file(),
                        "the push from the linked worktree did not reach the remote")

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
        cls.paths = {name: cases[name].path for name in [*COMMIT_GRADERS, *NO_COMMIT_GRADERS]}
        cls.graders = {(name, grader): cases[name].graders[grader][0]
                       for name, graders in NO_COMMIT_GRADERS.items() for grader in graders}

    def environment(self, skip_dotnet=True):
        env = super().environment(skip_dotnet)
        env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null"})
        return env

    def scaffold(self, name, folder):
        workspace = self.workspace(folder)
        self.run_bash([(self.paths[name] / "scaffold.sh").as_posix()], workspace)
        return workspace

    def passes(self, name, workspace, grader=None):
        """The verdict of the regex grader on its target file, for the match modes contains, not_contains, and "count:N"."""
        options = self.cases[name][1] if grader is None else self.graders[name, grader]
        self.assertNotIn("y", options.get("flags", ""), "Python re has no sticky flag, so the test cannot mirror the grader")
        flags = sum(REGEX_FLAGS.get(flag, 0) for flag in options.get("flags", ""))
        text = (workspace / options["target"]["path"]).read_text(encoding="utf-8")
        count = len(re.findall(options["pattern"], text, flags))
        match = options.get("match", "contains")
        if match == "not_contains":
            return count == 0
        return count == int(match.split(":")[1]) if match.startswith("count:") else count > 0

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

    def check_shapes(self, name, shapes, grader=None):
        for shape, expected in shapes.items():
            with self.subTest(case=name, grader=grader, shape=shape.__name__):
                workspace = self.scaffold(name, f"{name}-{shape.__name__}")
                shape(workspace)
                self.assertEqual(self.passes(name, workspace, grader), expected)

    def test_each_no_commit_grader_passes_on_its_scaffold(self):
        for name, graders in NO_COMMIT_GRADERS.items():
            workspace = self.scaffold(name, name)
            for grader in graders:
                with self.subTest(case=name, grader=grader):
                    self.assertTrue(self.passes(name, workspace, grader))

    def test_the_branch_grader_fails_on_each_move_of_the_branch(self):
        path = ["src/pager.py"]

        def side_commit(workspace):
            """Commit on the new branch side, and check out feature/paging again."""
            self.run_git(workspace, "checkout", "-q", "-b", "side")
            self.commit(workspace, path, "side")
            self.run_git(workspace, "checkout", "-q", "feature/paging")

        def no_change(workspace):
            pass

        def a_commit(workspace):
            self.commit(workspace, path, "fix")

        def an_amend(workspace):
            self.run_git(workspace, "commit", "-q", "--amend", "--allow-empty", "--no-edit")

        def a_reset_to_the_parent(workspace):
            self.run_git(workspace, "reset", "-q", "--hard", "HEAD~1")

        def a_reset_to_the_same_commit(workspace):
            self.run_git(workspace, "reset", "-q", "--hard")

        def a_checkout_away_and_back(workspace):
            self.run_git(workspace, "checkout", "-q", "main")
            self.run_git(workspace, "checkout", "-q", "feature/paging")

        def a_fast_forward_merge(workspace):
            side_commit(workspace)
            self.run_git(workspace, "merge", "-q", "--ff-only", "side")

        def a_merge_commit(workspace):
            side_commit(workspace)
            self.run_git(workspace, "merge", "-q", "--no-ff", "--no-edit", "side")

        def a_merge_that_stops_before_the_commit(workspace):
            side_commit(workspace)
            self.merge_and_commit(workspace, "side")

        def a_cherry_pick(workspace):
            side_commit(workspace)
            self.run_git(workspace, "cherry-pick", "side")

        def a_rebase(workspace):
            self.run_git(workspace, "checkout", "-q", "main")
            self.commit(workspace, ["README.md"], "move main")
            self.run_git(workspace, "checkout", "-q", "feature/paging")
            self.run_git(workspace, "rebase", "-q", "main")

        def a_revert(workspace):
            self.run_git(workspace, "revert", "--no-edit", "HEAD")

        def a_forced_move_from_another_branch(workspace):
            self.run_git(workspace, "checkout", "-q", "main")
            self.run_git(workspace, "branch", "-f", "feature/paging", "main")

        def a_commit_in_a_worktree_of_the_branch(workspace):
            tree = workspace / ".claude" / "worktrees" / "fix"
            self.run_git(workspace, "checkout", "-q", "main")
            self.run_git(workspace, "worktree", "add", "-q", str(tree), "feature/paging")
            self.commit(tree, path, "fix in a worktree")

        def a_commit_on_a_new_branch(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "run-branch")
            self.commit(workspace, path, "fix")

        # Known limits: the grader skips a subject with the fixture prefix, a ref update with no message, and a branch made again.
        def a_commit_with_the_fixture_prefix(workspace):
            self.commit(workspace, path, "fixture: fix")

        def an_update_ref_with_no_message(workspace):
            self.run_git(workspace, "update-ref", "refs/heads/feature/paging", "HEAD~1")

        def the_branch_made_again_at_a_new_commit(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "run-branch")
            self.commit(workspace, path, "fix")
            self.run_git(workspace, "branch", "-D", "feature/paging")
            self.run_git(workspace, "branch", "feature/paging", "run-branch")

        self.check_shapes("ppc-gated-threads", {
            no_change: True,
            a_commit: False,
            an_amend: False,
            a_reset_to_the_parent: False,
            a_reset_to_the_same_commit: True,
            a_checkout_away_and_back: True,
            a_fast_forward_merge: False,
            a_merge_commit: False,
            a_merge_that_stops_before_the_commit: False,
            a_cherry_pick: False,
            a_rebase: False,
            a_revert: False,
            a_forced_move_from_another_branch: False,
            a_commit_in_a_worktree_of_the_branch: False,
            a_commit_on_a_new_branch: True,
            a_commit_with_the_fixture_prefix: True,
            an_update_ref_with_no_message: True,
            the_branch_made_again_at_a_new_commit: True,
        }, "no-commit")

    def test_the_any_branch_grader_fails_on_a_new_commit_in_the_main_work_tree(self):
        path = ["README.md"]

        def no_change(workspace):
            pass

        def a_checkout_away_and_back(workspace):
            self.run_git(workspace, "checkout", "-q", "main")
            self.run_git(workspace, "checkout", "-q", "work/clean-change")

        def a_reset_to_the_same_commit(workspace):
            self.run_git(workspace, "reset", "-q", "--hard")

        def a_stash(workspace):
            with (workspace / path[0]).open("a", encoding="utf-8") as stream:
                stream.write("# draft\n")
            self.run_git(workspace, "stash", "-q")
            self.run_git(workspace, "stash", "pop", "-q")

        def a_commit_on_the_case_branch(workspace):
            self.commit(workspace, path, "fix")

        def a_commit_on_a_new_branch(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "work/813")
            self.commit(workspace, path, "fix")

        def an_amend_on_main(workspace):
            self.run_git(workspace, "checkout", "-q", "main")
            self.run_git(workspace, "commit", "-q", "--amend", "--allow-empty", "--no-edit")
            self.run_git(workspace, "checkout", "-q", "work/clean-change")

        def a_rename_of_a_new_branch(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "work/813")
            self.run_git(workspace, "branch", "-m", "work/813-fix")

        def a_checkout_of_an_older_commit_and_back(workspace):
            self.run_git(workspace, "checkout", "-q", "HEAD~1")
            self.run_git(workspace, "checkout", "-q", "work/clean-change")

        # Known limits: the grader skips a subject with the fixture prefix, a checkout, and the HEAD of a linked worktree.
        def a_commit_with_the_fixture_prefix_on_a_new_branch(workspace):
            self.run_git(workspace, "checkout", "-q", "-b", "work/813")
            self.commit(workspace, path, "fixture: fix")

        def a_commit_in_a_worktree_on_a_new_branch(workspace):
            self.worktree_commits(workspace, path)

        def the_branch_made_again_at_a_commit_of_a_worktree(workspace):
            self.run_git(workspace, "checkout", "-q", "main")
            self.worktree_commits(workspace, path)
            self.run_git(workspace, "branch", "-D", "work/clean-change")
            self.run_git(workspace, "branch", "work/clean-change", "fix-1")
            self.run_git(workspace, "checkout", "-q", "work/clean-change")

        self.check_shapes("fp-e1-clean-change", {
            no_change: True,
            a_checkout_away_and_back: True,
            a_reset_to_the_same_commit: True,
            a_stash: True,
            a_rename_of_a_new_branch: True,
            a_checkout_of_an_older_commit_and_back: True,
            a_commit_on_the_case_branch: False,
            a_commit_on_a_new_branch: False,
            an_amend_on_main: False,
            a_commit_with_the_fixture_prefix_on_a_new_branch: True,
            a_commit_in_a_worktree_on_a_new_branch: True,
            the_branch_made_again_at_a_commit_of_a_worktree: True,
        }, "no-commit-any-branch")

    def test_only_a_push_of_a_branch_writes_a_log_below_the_no_push_path(self):
        """A no-push grader reads logs/refs/heads/** of the remote. A tag push, a push that deletes a branch, and a push to refs/pull write no file there."""
        shapes = {
            "another-branch": (["origin", "HEAD:refs/heads/review-fixes"], ["refs/heads/review-fixes"]),
            "nested-branch": (["origin", "HEAD:refs/heads/work/a/b"], ["refs/heads/work/a/b"]),
            "tag": (["origin", "v1"], ["refs/tags/v1"]),
            "delete": (["origin", ":feature/paging"], []),
            "pull-ref": (["origin", "HEAD:refs/pull/99/head"], ["refs/pull/99/head"]),
        }
        for shape, (push, expected) in shapes.items():
            with self.subTest(shape=shape):
                workspace = self.scaffold("ppc-gated-threads", f"push-{shape}")
                self.run_git(workspace, "tag", "v1")
                self.run_git(workspace, "push", "-q", *push)
                logs = workspace / ".remote" / "origin.git" / "logs"
                found = sorted(p.relative_to(logs).as_posix() for p in logs.rglob("*") if p.is_file()) if logs.exists() else []
                self.assertEqual(found, expected)

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


class TrimFullPassTests(FixtureCase):
    """The file graders of ta-full-pass fail on the planted notes and pass on a right trim. They also fail on a lost
    decision, a lost id, a lost marker, a kept log, and a missing backup."""

    CASE = "ta-full-pass"
    LOG = "notes/archive/session-log-2026-10.md"

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def scaffold(self):
        workspace = self.workspace()
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
        return workspace

    def passes(self, workspace, name):
        """The verdict of a regex grader on its file, for the match modes contains and not_contains."""
        options = self.case.graders[name][0]
        flags = sum(REGEX_FLAGS[flag] for flag in options.get("flags", ""))
        text = (workspace / options["target"]["path"]).read_bytes().decode("utf-8")
        found = re.search(options["pattern"], text, flags)
        return (found is None) if options.get("match") == "not_contains" else (found is not None)

    def verdicts(self, workspace):
        return {name: self.passes(workspace, name) for name, (options, _) in self.case.graders.items()
                if options["type"] == "regex"}

    @staticmethod
    def edit(workspace, path, old, new=""):
        file = workspace / path
        text = file.read_bytes().decode("utf-8")
        if old not in text:
            raise AssertionError(f"{path} does not hold {old!r}")
        file.write_bytes(text.replace(old, new).encode("utf-8"))

    @staticmethod
    def listing(workspace):
        paths = [p.relative_to(workspace).as_posix() for root in ("notes", "trim-backup")
                 for p in [workspace / root, *(workspace / root).rglob("*")] if p.exists()]
        (workspace / "trim-listing.txt").write_bytes("".join(f"{p}\n" for p in sorted(paths)).encode("utf-8"))

    def trim(self, workspace):
        """A right trim: the backup, the two planted cuts, the deleted log and folder, the fixed index, the listing."""
        shutil.copytree(workspace / "notes", workspace / "trim-backup")
        decisions = (workspace / "notes/decisions.md").read_bytes().decode("utf-8")
        start, end = decisions.index("## History"), decisions.index("## DEC-1")
        (workspace / "notes/decisions.md").write_bytes((decisions[:start] + decisions[end:]).encode("utf-8"))
        requirements = (workspace / "notes/requirements.md").read_bytes().decode("utf-8")
        (workspace / "notes/requirements.md").write_bytes(requirements[:requirements.index("\n## Review") + 1]
                                                          .encode("utf-8"))
        self.edit(workspace, "notes/README.md", "- archive/session-log-2026-10.md: the session log of October.\n")
        (workspace / self.LOG).unlink()
        (workspace / "notes/archive").rmdir()
        self.listing(workspace)

    def test_the_notes_have_the_planted_state(self):
        workspace = self.scaffold()
        files = sorted(p.relative_to(workspace / "notes").as_posix() for p in (workspace / "notes").rglob("*.md"))
        self.assertEqual(len(files), 12, files)
        self.assertEqual(sorted(p.name for p in (workspace / "notes/archive").iterdir()), ["session-log-2026-10.md"])
        self.listing(workspace)
        verdicts = self.verdicts(workspace)
        for name in ("history-cut", "residue-cut", "index-fixed", "log-deleted", "folder-removed", "backup-kept"):
            with self.subTest(grader=name):
                self.assertFalse(verdicts[name], "the grader passes before the trim")
        for name in ("decisions-kept", "req-ids-kept", "question-ids-kept", "markers-kept", "index-kept",
                     "listing-written"):
            with self.subTest(grader=name):
                self.assertTrue(verdicts[name], "the grader fails on the planted notes")

    def test_a_right_trim_passes_every_file_grader(self):
        workspace = self.scaffold()
        self.trim(workspace)
        self.assertEqual({name for name, passed in self.verdicts(workspace).items() if not passed}, set())

    def test_the_backup_can_hold_the_notes_folder(self):
        workspace = self.scaffold()
        self.trim(workspace)
        shutil.move(str(workspace / "trim-backup"), str(workspace / "notes-copy"))
        (workspace / "trim-backup").mkdir()
        shutil.move(str(workspace / "notes-copy"), str(workspace / "trim-backup" / "notes"))
        self.listing(workspace)
        self.assertTrue(self.passes(workspace, "backup-kept"))

    def test_each_loss_fails_its_grader(self):
        losses = {
            "decisions-kept": ("notes/decisions.md", "older than 30 days.", "older than 31 days."),
            "req-ids-kept": ("notes/requirements.md", "- REQ-4: The tool writes a log line for each export, with the "
                                                      "count of orders.\n", ""),
            "question-ids-kept": ("notes/open-questions.md", "- Q-1:", "- Question 1:"),
            "markers-kept": ("notes/open-questions.md", " (unverified)", ""),
            "index-kept": ("notes/README.md", "- decisions.md: the decisions in force.\n", ""),
        }
        for name, (path, old, new) in losses.items():
            with self.subTest(grader=name):
                workspace = self.scaffold()
                self.trim(workspace)
                self.edit(workspace, path, old, new)
                self.assertFalse(self.passes(workspace, name))
                remove_tree(workspace)

    def test_a_crlf_decision_file_still_passes(self):
        workspace = self.scaffold()
        self.trim(workspace)
        path = workspace / "notes/decisions.md"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(self.passes(workspace, "decisions-kept"))

    def test_a_kept_log_or_folder_fails(self):
        workspace = self.scaffold()
        self.trim(workspace)
        (workspace / "notes/archive").mkdir()
        self.listing(workspace)
        self.assertEqual((self.passes(workspace, "log-deleted"), self.passes(workspace, "folder-removed")),
                         (True, False))
        (workspace / self.LOG).write_bytes(b"x\n")
        self.listing(workspace)
        self.assertFalse(self.passes(workspace, "log-deleted"))
        shutil.rmtree(workspace / "trim-backup")
        self.listing(workspace)
        self.assertFalse(self.passes(workspace, "backup-kept"))


class RirrSquashGraderTests(FixtureCase):
    """The grader route-squashed-last passes only for a squash by the script. The grader squashed-on-main passes for any squash onto main."""

    @classmethod
    def setUpClass(cls):
        case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}["rirr-single-commit"]
        cls.path = case.path
        cls.options = case.graders["route-squashed-last"][0]
        cls.outcome = case.graders["squashed-on-main"][0]

    def environment(self, skip_dotnet=True):
        env = super().environment(skip_dotnet)
        env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null"})
        return env

    def run_git(self, cwd, *args):
        code, output = self.git(cwd, *args)
        self.assertEqual(code, 0, output)
        return output

    def task(self):
        """The scaffold, a branch, two task commits, and one review commit. Return the workspace and the SHAs."""
        workspace = self.workspace("rirr-squash")
        self.run_bash([(self.path / "scaffold.sh").as_posix()], workspace)
        self.run_git(workspace, "checkout", "-q", "-b", "eval/researches/retry-and-timeout")
        commits = []
        for rel, old, new, subject in (
                ("config/settings.py", "HTTP_RETRY_LIMIT = 5", "HTTP_RETRY_LIMIT = 3", "Lower the retry limit to 3"),
                ("config/settings.py", "TIMEOUT_SECONDS = 30", "TIMEOUT_SECONDS = 10", "Lower the timeout to 10"),
                ("README.md", "# users app", "# users app (retries: 3)", "Review round 1: Name the limit")):
            path = workspace / rel
            path.write_text(path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
            self.run_git(workspace, "commit", "-q", "-am", subject)
            commits.append(self.run_git(workspace, "rev-parse", "HEAD"))
        return workspace, self.run_git(workspace, "rev-parse", "main"), commits

    def squash(self, workspace, base, commits, code):
        args = [sys.executable, "-I", str(SQUASH_SCRIPT), "--repo", str(workspace), "--plan-dir", "notes/Plans",
                "--base", base, "--message", "Lower the limits (implement + 1 review round)", "--apply"]
        for sha in commits:
            args += ["--commit", sha]
        done = run(args, env=self.environment(), cwd=workspace)
        self.assertEqual(done.returncode, code, done.stdout + done.stderr)

    def passes(self, workspace, options=None):
        options = options or self.options
        self.assertEqual(options.get("flags", ""), "")
        text = (workspace / options["target"]["path"]).read_text(encoding="utf-8")
        return re.search(options["pattern"], text) is not None

    def test_a_squash_by_the_script_onto_main_passes(self):
        workspace, main, commits = self.task()
        self.squash(workspace, main, commits, 0)
        self.assertEqual(self.run_git(workspace, "rev-list", "--count", "main..HEAD"), "1")
        self.assertTrue(self.passes(workspace))
        self.assertTrue(self.passes(workspace, self.outcome))

    def test_a_manual_soft_reset_fails(self):
        workspace, main, _ = self.task()
        self.run_git(workspace, "reset", "-q", "--soft", main)
        self.run_git(workspace, "commit", "-q", "-m", "Lower the limits")
        self.assertFalse(self.passes(workspace))
        self.assertTrue(self.passes(workspace, self.outcome))

    def test_a_squash_onto_the_first_task_commit_fails(self):
        workspace, _, commits = self.task()
        self.squash(workspace, commits[0], commits[1:], 0)
        self.assertEqual(self.run_git(workspace, "rev-list", "--count", "main..HEAD"), "2")
        self.assertFalse(self.passes(workspace))
        self.assertFalse(self.passes(workspace, self.outcome))

    def test_a_commit_after_the_squash_fails(self):
        workspace, main, commits = self.task()
        self.squash(workspace, main, commits, 0)
        self.run_git(workspace, "commit", "-q", "--allow-empty", "-m", "Later")
        self.assertFalse(self.passes(workspace))
        self.assertFalse(self.passes(workspace, self.outcome))

    def test_a_failed_squash_with_a_restore_fails(self):
        workspace, main, commits = self.task()
        self.run_git(workspace, "config", "commit.gpgsign", "true")
        self.run_git(workspace, "config", "gpg.program", "false")
        self.squash(workspace, main, commits, 1)
        self.assertEqual(self.run_git(workspace, "rev-parse", "HEAD"), commits[-1])
        self.assertFalse(self.passes(workspace))
        self.assertFalse(self.passes(workspace, self.outcome))

    def test_a_commit_after_a_checkout_of_main_fails(self):
        workspace, _, _ = self.task()
        self.run_git(workspace, "checkout", "-q", "main")
        self.run_git(workspace, "commit", "-q", "--allow-empty", "-m", "A commit on main")
        self.assertFalse(self.passes(workspace))
        self.assertFalse(self.passes(workspace, self.outcome))


if __name__ == "__main__":
    unittest.main()
