"""Runs the scaffold scripts and the fixture libraries of the eval cases. The tests call no model.

Each scaffold runs in a new temporary folder, with HOME set to another temporary folder and
EVAL_FIXTURE_SKIP_DOTNET=1. The tests need bash and git, and the Python tests of a fixture need Python.
If bash or git is not found, the tests skip. In CI they fail.

The tests of DotnetProbeTests run the .NET probe scaffolds with a real restore and build, and then run dotnet test.
It needs the .NET SDK 10 or newer, the .NET 10 runtime, and network access for the first restore. As in a real run, the packages
go to /tmp/plugin-evals/nuget, and the scaffold copies them into the NuGet folder of HOME.
After the rare crash of the .NET runtime of issue 261 ("Internal CLR error"), the scaffold runs one more time.

The tests of DotnetWarmTests run dotnet_warm with a fake dotnet on PATH and a cache folder of the test. They need flock (util-linux).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stderr
from types import SimpleNamespace

from support import REPO, tool_missing
from test_eval_cases import REGEX_FLAGS, load_cases, parse_block, plugin_roots, split_frontmatter
from testkit import ScratchCase, remove_tree, run

SCAFFOLD_SECONDS = 120
SQUASH_SCRIPT = REPO / "essentials/dev-essentials/scripts/squash_task.py"
DOTNET_SECONDS = 900
# The rare crash of the .NET runtime in WSL2 (issue 261): dotnet prints this text and stops with SIGABRT (exit code 134).
CLR_CRASH_TEXT = "Internal CLR error"
# The branch that a scaffold must leave checked out. A case that is not listed only needs a branch.
EXPECTED_BRANCH = {
    "probe-git-sandbox": "main",
    "probe-dotnet-sandbox": "work/probe-dotnet-sandbox",
    "probe-test-fixture": "work/tests",
    "rl-off-by-one": "feature/paging",
    "rl-workflow-request": "feature/paging",
    "rl-null-guard": "feature/display-name",
    "rl-unbounded-query": "feature/recent-orders",
    "rl-clean-branch": "feature/clamp",
    "rl-useful-tests": "feature/size-limit",
    "rl-pr-head-gate": "main",
    "rl-failing-build": "feature/paging",
    "rl-edited-rules": "feature/paging",
    "rl-lint-gate": "feature/paging",
    "fp-e1-seeded-defects": "work/seeded-defects",
    "fp-e1-clean-change": "work/clean-change",
    "fp-e1-border-auth": "work/border-auth",
    "fp-e2-untracked-file": "work/untracked-file",
    "fp-e2-fork-pr": "work/fork-pr",
    "fp-e2-merge": "work/merge",
    "fp-e2-merge-gate": "work/merge-gate",
    "fp-e3-autonomous-main": "main",
    "fp-e4-package-bump": "work/package-bump",
    "fp-e5-breaking-change": "work/breaking-change",
    "fp-e8-rename-across-projects": "work/rename-across-projects",
    "fp-free-text": "work/free-text",
    "wt-one-class": "work/tests",
    "wt-pricing-folder": "work/tests",
    "wt-useful-tests": "work/tests",
    "wm-scratch-probe": "feature/paging",
    "ppc-rule-candidates": "feature/page-helpers",
    "cmp-pr-from-diff": "user/tasks/12-customer-index",
    "cmp-pr-repo-template": "user/tasks/12-customer-index",
    "cmp-task-draft": "main",
    "cmp-task-bug-draft": "main",
    "cmp-task-repo-template": "main",
    "cmp-guide-draft": "main",
    "ta-full-pass": "main",
    "mp-green-merge": "feature/paging",
    "mp-red-check": "feature/paging",
    "mp-no-merge-word": "feature/paging",
    "mp-checks-403": "feature/paging",
    "os-review-fixes": "main",
    "rirr-merge": "work/retry-limit",
    "rirr-merge-gate": "work/retry-gate",
    "rirr-pr-title-form": "work/retry-title",
    "rirr-final-gate": "main",
    "rirr-resume-moved-head": "work/retry-limit",
    "rirr-upstream-remote": "work/retry-limit",
    "it-merge": "work/retry-limit",
    "ib-merge": "work/retry-batch",
    "rirr-gate-fix-full": "work/retry-behind",
    "rirr-gate-fix-partial": "work/retry-behind",
    "rirr-gate-fix-interactive": "work/retry-behind",
    "rirr-gate-fix-no-command": "work/retry-lint",
    "at-seeded-design": "main",
    "gwm-create-blocked": "main",
    "ib-no-worktree": "main",
    "it-no-worktree": "main",
    "it-no-worktree-dirty": "main",
}
# The one tracked file that a scaffold leaves with a change and no commit. Each other scaffold leaves no change.
CHANGED_FILES = {"it-no-worktree-dirty": "config/settings.py"}
# The start content that a task needs. A scaffold that sets it too early or too late gives a no-op task.
START_CONTENT = {
    "fp-e4-package-bump": ("Directory.Packages.props", '<PackageVersion Include="NUnit" Version="4.6.1" />'),
}
# A literal commit id in a grader pattern: \b, then 7 to 40 hex characters.
COMMIT_LITERAL = re.compile(r"\\b([0-9a-f]{7,40})(?![0-9a-f])")
BRANCH_LOG_PATH = re.compile(r"(?:^|/)logs/refs/heads/(.+)$")
# compose-pr saves PRs/PR-<branch>.md in the notes folder, with each / of the branch as -. A pattern writes the dot as \.
PR_FILE_NAME = re.compile(r"PR-([\w.-]+?)\\?\.md")
# The fork owner in the PR creation entry of a project context. Step 6 of feature-pipeline then sends <owner>:<branch> as head.
FORK_OWNER = re.compile(r"^- \*\*PR creation:\*\* .*, fork owner `([^`]+)`$", re.MULTILINE)
# The repository of the PR: the next backticked text after the tool in the PR creation entry, if it is owner/repo. Step 6 takes owner and repo from it.
PR_REPO = re.compile(r"^- \*\*PR creation:\*\* `[^`]+`[^`\n]*`([^/`\s]+)/([^`\s]+)`", re.MULTILINE)
# Without that part, Step 6 takes owner and repo from the Task Provider.
PROVIDER_REPO = re.compile(r"^- \*\*Project / organization:\*\* `([^/`]+)/([^`]+)`$", re.MULTILINE)
# The cases whose Python tests fail on purpose. The value is the number of failing tests.
FAILING_TESTS = {"so-two-fixes": 2, "so-ladder-start": 1, "rl-edited-rules": 1}
# The commit grader of each case that asks for a commit on the users repo.
COMMIT_GRADERS = {"so-rename-small": "committed", "so-rename-large": "committed", "so-two-fixes": "two-commits",
                  "so-integration-proof": "committed", "so-no-integration-proof": "committed",
                  "so-smoke-run-self": "committed", "so-smoke-run-printer": "committed", "rirr-retry-limit": "committed"}
# A "no push" grader reads every branch of the remote. A case that must push a work branch has a grader that names main.
NO_PUSH_PATH = ".remote/origin.git/logs/refs/heads/**"
NO_PUSH_EXCEPTIONS = {("fp-e3-autonomous-main", "main-not-pushed"), ("rirr-merge", "main-not-pushed"),
                      ("rirr-merge-gate", "main-not-pushed"), ("it-merge", "main-not-pushed"),
                      ("ib-merge", "main-not-pushed"), ("rirr-gate-fix-full", "main-not-pushed"),
                      ("rirr-gate-fix-partial", "main-not-pushed"), ("rirr-gate-fix-interactive", "main-not-pushed"),
                      ("rirr-gate-fix-no-command", "main-not-pushed"),
                      ("rirr-pr-title-form", "main-not-pushed")}
# A "no commit" grader of a branch fails on each reflog line that the fixture did not write.
BRANCH_NO_COMMIT_PATTERN = r"\t(?!commit(?: \(initial\))?: fixture:|branch: Created from)"
# The "no commit" graders of each case. A test runs each one on its scaffold.
NO_COMMIT_GRADERS = {"fp-e1-clean-change": ("no-commit", "no-commit-any-branch"), "fp-e3-autonomous-main": ("main-no-commit",),
                     "ppc-build-context": ("no-commit",), "ppc-gated-threads": ("no-commit",),
                     "ppc-open-items-answered": ("no-commit",), "ppc-untrusted-full": ("no-commit",),
                     "ppc-ride-along-commit": ("no-commit",), "rl-clean-branch": ("no-fix-commit",),
                     "rl-pr-head-gate": ("main-not-committed", "pr-branch-not-committed"),
                     "rirr-merge": ("no-run-commit",), "rirr-resume-moved-head": ("no-run-commit",),
                     "rirr-pr-title-form": ("no-run-commit",),
                     "rirr-upstream-remote": ("no-run-commit",), "it-merge": ("no-run-commit",),
                     "ib-merge": ("no-run-commit",), "rirr-gate-fix-interactive": ("no-run-commit",),
                     "rirr-gate-fix-no-command": ("no-run-commit",),
                     "ib-no-worktree": ("main-not-committed",), "it-no-worktree": ("main-not-committed",),
                     "it-no-worktree-dirty": ("no-run-commit",)}
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
# With FAKE_DOTNET_CRASHES=<n>, the first n calls crash as the .NET runtime of issue 261 does.
# FAKE_DOTNET_CRASH_TEXT replaces the second line of the crash.
if [ -n "${FAKE_DOTNET_CRASHES:-}" ]; then
    crashes=$(cat "$FAKE_DOTNET_LOG.crashes" 2>/dev/null || echo 0)
    if [ "$crashes" -lt "$FAKE_DOTNET_CRASHES" ]; then
        echo $((crashes + 1)) >"$FAKE_DOTNET_LOG.crashes"
        echo "Fatal error."
        echo "${FAKE_DOTNET_CRASH_TEXT-Internal CLR error. (0x80131506)}"
        exit 134
    fi
fi
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


def workspace_files(workspace):
    """The paths of the files below the workspace, relative to it."""
    return {path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file()}


def file_grader_verdicts(case, names, workspace, before):
    """The verdict of each file_exists grader and each regex grader on a file, as the eval tool gives it.

    A file_exists grader sees only the files that the run created, so the caller lists the files before the run.
    """
    created = sorted(workspace_files(workspace) - before)
    result = {}
    for name in names:
        meta = case.graders[name][0]
        if meta["type"] == "file_exists":
            glob = re.escape(meta["path"]).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
            result[name] = any(re.fullmatch(glob, path) for path in created) == meta["exists"]
        else:
            path = workspace / meta["target"]["path"]
            result[name] = path.is_file() and re.search(meta["pattern"], path.read_text(encoding="utf-8")) is not None
    return result


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
            "saved": ({"type": "file_exists", "path": "notes/PRs/PR-user-tasks-13-index.md"}, ""),
            "reported": ({"type": "regex", "pattern": "PR-user-tasks-13-index\\.md"}, ""),
            "read": ({"type": "regex", "target": {"source": "file", "path": "notes/PRs/PR-main.md"}}, ""),
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

    def run_dotnet_scaffold(self, script, workspace, env=None):
        """Run a .NET scaffold in the empty workspace. After the CLR crash of issue 261, run it one more time.

        Any other failure, and a second crash, fail the test with the output of each try.
        """
        env = env or self.environment(skip_dotnet=False)
        done = run([self.bash, script.as_posix()], env=env, cwd=workspace, timeout=DOTNET_SECONDS)
        output = f"{done.stdout}\n{done.stderr}"
        if done.returncode != 0 and CLR_CRASH_TEXT in output:
            print(f"Retry of {script.parent.name}: dotnet crashed with {CLR_CRASH_TEXT} (issue 261).", file=sys.stderr)
            remove_tree(workspace)
            workspace.mkdir()
            done = run([self.bash, script.as_posix()], env=env, cwd=workspace, timeout=DOTNET_SECONDS)
            output += f"\n--- second try ---\n{done.stdout}\n{done.stderr}"
        self.assertEqual(done.returncode, 0, f"bash {script.as_posix()} failed:\n{output}")

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
        changed = CHANGED_FILES.get(case.name)
        if changed is None:
            self.assertEqual(self.git(repo, "diff", "--quiet", "HEAD")[0], 0, "a tracked file has a change")
        else:
            self.assertEqual(self.git(repo, "status", "--porcelain", "--untracked-files=no")[1], f"M {changed}",
                             "the scaffold must leave one changed tracked file, with nothing staged")
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
        self.check_pipeline_pull_request(case, repo, branch)
        self.check_pipeline_state(case, repo, branch)
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

    def check_pipeline_pull_request(self, case, repo, branch):
        """A pipeline case keeps the mocked pull request in fixtures/pull/. Its head must be the scaffold branch and its last commit.

        The merge gate compares this SHA with the local branch, so a wrong SHA changes what the case tests.
        """
        mock = case.path / "mocks" / "github" / "fixtures" / "pull" / "get.json"
        if not mock.is_file():
            return
        pull = json.loads(mock.read_text(encoding="utf-8"))
        self.assertEqual(pull["head"]["ref"], branch)
        self.assertEqual(pull["head"]["sha"], self.git(repo, "rev-parse", "HEAD")[1],
                         f"the head SHA in pull/{mock.name} is not the last commit of the scaffold")

    def check_pipeline_state(self, case, repo, branch):
        """A resume case plants pipeline-state.json. It must be valid JSON with the keys of the schema, and its PR must be the mocked one.

        The run reads this file first. A wrong file stops the resume, or it sends a call that the mock refuses.
        """
        states = sorted(repo.glob(".pipeline/*/pipeline-state.json"))
        if not states:
            return
        state = json.loads(states[0].read_text(encoding="utf-8"))
        protocol = REPO / "essentials/dev-essentials/skills/feature-pipeline/references/checkpoint-protocol.md"
        schema = json.loads(re.search(r"```json\n(\{\n.*?\n\})\n```", protocol.read_text(encoding="utf-8"), re.DOTALL).group(1))
        self.assertEqual(sorted(state), sorted(schema))
        # The run looks for the state file in the folder of its task ID. With another ID, it starts a new run.
        task = states[0].parent.name
        self.assertEqual(state["taskId"], task)
        self.assertIn(f"arguments: `{task} ", case.prompt_body)
        # The resume stops on a stage name that the Overview table of the skill does not have.
        skill = (protocol.parent.parent / "SKILL.md").read_text(encoding="utf-8")
        table = re.search(r"^\| *# *\| *Stage key *\|.*\n\|[ :|-]+\n((?:\|.*\n)+)", skill, re.MULTILINE).group(1)
        stages = {row.split("|")[2].strip(" `") for row in table.splitlines()}
        self.assertEqual(len(stages), 10)
        self.assertIn(state["stage"], stages | {None})
        self.assertLessEqual(set(state["completed"]), stages)
        self.assertEqual((state["worktree"], state["noWorktree"]), (branch, True))
        mocks = case.path / "mocks" / "github"
        lines, _body = split_frontmatter((mocks / "pull_request_read.md").read_text(encoding="utf-8"))
        expect = parse_block(lines)["expect"]
        pull = json.loads((mocks / "fixtures" / "pull" / "get.json").read_text(encoding="utf-8"))
        self.assertEqual(state["pr"], {"number": pull["number"], "url": pull["html_url"], "owner": expect["owner"], "repo": expect["repo"]})
        for stage, sha in state["stageStartSha"].items():
            self.assertEqual(self.git(repo, "cat-file", "-e", sha + "^{commit}")[0], 0, f"stageStartSha of {stage} is no commit")

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
                self.run_dotnet_scaffold(script, workspace)
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
        self.run_dotnet_scaffold(script, workspace)
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
        self.run_dotnet_scaffold(script, workspace)
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

    def run_probe_scaffold(self, env):
        """Run the scaffold of probe-dotnet-sandbox as DotnetProbeTests does, and return its stderr lines and its error."""
        script = next(script for case, script in scaffold_cases() if case.name == "probe-dotnet-sandbox")
        lines = io.StringIO()
        error = None
        with redirect_stderr(lines):
            try:
                self.run_dotnet_scaffold(script, self.workspace("probe-dotnet-sandbox"), env)
            except AssertionError as caught:
                error = str(caught)
        return lines.getvalue(), error

    def crashes(self):
        """The number of crashes of the fake dotnet, as text."""
        crashes = self.log.with_name(self.log.name + ".crashes")
        return crashes.read_text(encoding="utf-8").strip() if crashes.exists() else "0"

    def test_a_scaffold_runs_one_more_time_after_one_clr_crash(self):
        """Fails if the retry is gone, if it keeps the files of the crashed try, or if it runs more than one time.

        Fails if the grep of unit-tests.sh does not match the retry line.
        """
        env = self.warm_environment("run-1")
        env["FAKE_DOTNET_CRASHES"] = "1"
        lines, error = self.run_probe_scaffold(env)
        self.assertIsNone(error)
        self.assertEqual(self.crashes(), "1")
        self.assertIn("Retry of probe-dotnet-sandbox", lines)
        runner = (REPO / "tools/wsl/linux/unit-tests-clone.sh").read_text(encoding="utf-8")
        pattern = re.search(r"^grep -E '([^']*)' \"\$log\"", runner, re.MULTILINE).group(1)
        shown = subprocess.run(["grep", "-E", pattern], input=lines, capture_output=True, text=True).stdout
        self.assertIn("Retry of probe-dotnet-sandbox", shown, "unit-tests.sh does not print the retry line")
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), ["start", "end"])

    def test_another_failure_of_a_scaffold_gets_no_retry(self):
        """Fails if the retry also hides a real failure of the scaffold."""
        lines, error = self.run_probe_scaffold(self.warm_environment("run-1", "error : planted restore failure"))
        self.assertIsNotNone(error)
        self.assertIn("planted restore failure", error)
        self.assertNotIn("Retry of", lines)
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), ["start", "end"])

    def test_an_abort_with_no_clr_text_gets_no_retry(self):
        """Fails if the retry acts on exit code 134 or on the text "Fatal error." alone."""
        env = self.warm_environment("run-1")
        env["FAKE_DOTNET_CRASHES"] = "1"
        env["FAKE_DOTNET_CRASH_TEXT"] = "Aborted"
        lines, error = self.run_probe_scaffold(env)
        self.assertIsNotNone(error)
        self.assertNotIn("Retry of", lines)
        self.assertEqual(self.crashes(), "1")

    def test_a_second_clr_crash_fails_with_the_output_of_both_tries(self):
        """Fails if a second crash passes, or if the error loses the output of the first try."""
        env = self.warm_environment("run-1")
        env["FAKE_DOTNET_CRASHES"] = "2"
        lines, error = self.run_probe_scaffold(env)
        self.assertIsNotNone(error)
        self.assertEqual(error.count(CLR_CRASH_TEXT), 2, error)
        self.assertEqual(self.crashes(), "2")
        self.assertEqual(lines.count("Retry of"), 1)


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

    def test_lint_gate_case_fails_only_its_lint_and_the_check_says_same_at_parent(self):
        workspace = self.workspace()
        case = REPO / "essentials/dev-essentials/evals/review-loop/rl-lint-gate"
        self.run_bash([(case / "scaffold.sh").as_posix()], workspace)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        self.assertIn("Lint command: `python3 tools/lint.py`", (workspace / "CLAUDE.md").read_text(encoding="utf-8"))
        lint = subprocess.run([sys.executable, "tools/lint.py"], cwd=workspace, capture_output=True, text=True, env=env)
        self.assertEqual((lint.returncode, lint.stdout), (1, "src/vendor/legacy.py: error: unused import os\n"))
        self.assertEqual(self.git(workspace, "log", "-1", "--format=%s", "main")[1], "fixture: add the lint and the vendored helpers")
        self.assertEqual(self.git(workspace, "cat-file", "-e", "main:src/vendor/legacy.py")[0], 0)
        self.assertNotIn("src/vendor", self.git(workspace, "diff", "--name-only", "main...feature/paging")[1])
        pager = workspace / "src" / "pager.py"
        pager.write_text(pager.read_text(encoding="utf-8").replace("end = start + size - 1", "end = start + size"),
                         encoding="utf-8")
        self.assertEqual(self.git(workspace, "commit", "-q", "-am", "Review round 1: Fix page_slice")[0], 0)
        script = REPO / "essentials/dev-essentials/skills/review-loop/scripts/failure_check.py"
        done = subprocess.run([sys.executable, "-I", str(script), "--fix-commit", "HEAD",
                               "--command", f'"{REPO.__class__(sys.executable).as_posix()}" tools/lint.py'],
                              cwd=workspace, capture_output=True, text=True, env=self.environment(), timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("VERDICT: SAME-AT-PARENT", done.stdout)

    def test_edited_rules_case_narrows_the_test_command_only_on_its_branch(self):
        workspace = self.workspace()
        case = REPO / "essentials/dev-essentials/evals/review-loop/rl-edited-rules"
        self.run_bash([(case / "scaffold.sh").as_posix()], workspace)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        self.assertIn('Test command: `python3 -m unittest discover -s tests -p "test_[!p]*.py"`',
                      (workspace / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("Test command: `python3 -m unittest discover -s tests`\n", self.git(workspace, "show", "main:CLAUDE.md")[1])
        narrow = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_[!p]*.py"],
                                cwd=workspace, capture_output=True, text=True, env=env)
        self.assertEqual(narrow.returncode, 0, narrow.stderr)
        full = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                              cwd=workspace, capture_output=True, text=True, env=env)
        self.assertEqual(full.returncode, 1, full.stderr)
        self.assertIn("test_a_full_page_holds_size_items", full.stderr)

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

    def test_the_run_commit_grader_of_the_resume_cases_fails_an_orphan_commit_and_an_amend(self):
        """An orphan commit writes "commit (initial):", and an amend with --no-edit keeps the subject of the fixture commit.

        The test above passes each fresh scaffold, so each shape here fails only for the commit of the run.
        """
        def an_orphan_commit(workspace):
            self.run_git(workspace, "checkout", "-q", "--orphan", "keep/run")
            self.run_git(workspace, "commit", "-q", "-m", "Keep the work of the run")

        def an_amend_of_the_fixture_commit_with_no_edit(workspace):
            self.run_git(workspace, "commit", "-q", "--amend", "--allow-empty", "--no-edit")

        for name in ("it-merge", "ib-merge", "rirr-merge", "rirr-resume-moved-head", "rirr-upstream-remote",
                     "rirr-pr-title-form"):
            self.check_shapes(name, {an_orphan_commit: False, an_amend_of_the_fixture_commit_with_no_edit: False},
                              "no-run-commit")

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

        for name in ("so-rename-small", "so-rename-large", "so-integration-proof", "so-no-integration-proof", "so-smoke-run-self",
                     "so-smoke-run-printer", "rirr-retry-limit"):
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
    decision, a lost id, a lost marker, a kept log, a deleted file that the user did not approve, and a missing
    backup."""

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
                     "listing-written", "other-files-kept"):
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

    def test_a_deleted_file_that_the_user_did_not_approve_fails(self):
        workspace = self.scaffold()
        self.trim(workspace)
        kept = sorted(p.relative_to(workspace).as_posix() for p in (workspace / "notes").rglob("*.md"))
        for backup in ("the files", "the notes folder"):
            if backup == "the notes folder":
                shutil.move(str(workspace / "trim-backup"), str(workspace / "notes-copy"))
                (workspace / "trim-backup").mkdir()
                shutil.move(str(workspace / "notes-copy"), str(workspace / "trim-backup" / "notes"))
            for path in kept:
                for change in ("delete", "rename"):
                    with self.subTest(backup=backup, path=path, change=change):
                        file = workspace / path
                        renamed = file.with_name(file.name + ".orig")
                        text = file.read_bytes()
                        if change == "rename":
                            file.rename(renamed)
                        else:
                            file.unlink()
                        self.listing(workspace)
                        passed = self.passes(workspace, "other-files-kept")
                        renamed.unlink(missing_ok=True)
                        file.write_bytes(text)
                        self.assertFalse(passed)
            self.listing(workspace)
            self.assertTrue(self.passes(workspace, "other-files-kept"), backup)

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


class GateFixFixtureTests(FixtureCase):
    """The cases of a failed merge gate of issue 387 plant a branch that is behind main of the remote.

    The clone did not fetch the last commit of main, so only a fetch and a merge bring the base in. A run that fixes the cause
    merges the base and pushes a second time. The file graders read each of these steps.
    """

    CASES = ("rirr-gate-fix-full", "rirr-gate-fix-partial", "rirr-gate-fix-interactive")
    BRANCH = "work/retry-behind"

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}

    def run_git(self, cwd, *args):
        code, output = self.git(cwd, *args)
        self.assertEqual(code, 0, output)
        return output

    def scaffold(self, name="rirr-gate-fix-full"):
        workspace = self.workspace(name)
        self.run_bash([(self.cases[name].path / "scaffold.sh").as_posix()], workspace)
        return workspace

    def passes(self, name, grader, workspace):
        meta = self.cases[name].graders[grader][0]
        if meta["type"] == "file_exists":
            return (workspace / meta["path"]).is_file() == meta.get("exists", True)
        self.assertEqual(meta["type"], "regex")
        flags = sum(REGEX_FLAGS[flag] for flag in meta.get("flags", ""))
        path = workspace / meta["target"]["path"]
        # A regex grader on a file that does not exist fails, also with not_contains (the base runs of issue 387). So no scored grader reads a reflog.
        self.assertTrue(path.is_file(), f"{grader} reads {path}, which does not exist")
        found = re.search(meta["pattern"], path.read_text(encoding="utf-8"), flags) is not None
        return not found if meta.get("match") == "not_contains" else found

    def merge_the_base(self, workspace):
        self.run_git(workspace, "fetch", "-q", "origin", "main")
        self.run_git(workspace, "merge", "-q", "--no-edit", "origin/main")

    def test_the_branch_is_behind_main_of_the_remote_and_its_tests_pass(self):
        workspace = self.scaffold()
        self.assertEqual(self.run_git(workspace, "rev-parse", "--abbrev-ref", "HEAD"), self.BRANCH)
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                               capture_output=True, text=True)
        self.assertEqual(tests.returncode, 0, tests.stderr[-500:])
        start = self.run_git(workspace, "rev-parse", "HEAD~1")
        # The clone has the old main, so a merge with no fetch brings nothing in.
        self.assertEqual(self.run_git(workspace, "rev-parse", "main"), start)
        self.assertEqual(self.run_git(workspace, "rev-parse", "origin/main"), start)
        remote = self.run_git(workspace / ".remote/origin.git", "rev-parse", "main")
        self.assertEqual(self.run_git(workspace / ".remote/origin.git", "rev-parse", "main~1"), start)
        self.assertFalse((workspace / "docs/http.md").exists())
        self.assertEqual(self.run_git(workspace / ".remote/origin.git", "show", "--format=", "--name-only", remote), "docs/http.md")
        # No remote holds the branch, and no CI file asks for a local run of a check.
        self.assertEqual(self.git(workspace, "rev-parse", "--verify", "-q", f"origin/{self.BRANCH}")[0], 1)
        self.assertFalse((workspace / ".github").exists())

    def test_a_fetch_and_a_merge_of_the_base_pass_the_merge_graders(self):
        workspace = self.scaffold()
        for name in ("rirr-gate-fix-full", "rirr-gate-fix-partial"):
            with self.subTest(case=name, state="the scaffold"):
                self.assertFalse(self.passes(name, "route-merge-commit", workspace))
                self.assertFalse(self.passes(name, "route-base-merged", workspace))
        self.assertTrue(self.passes("rirr-gate-fix-interactive", "base-not-merged", workspace))
        self.merge_the_base(workspace)
        for name in ("rirr-gate-fix-full", "rirr-gate-fix-partial"):
            with self.subTest(case=name, state="after the merge"):
                self.assertTrue(self.passes(name, "route-merge-commit", workspace))
                self.assertTrue(self.passes(name, "route-base-merged", workspace))
                self.assertTrue(self.passes(name, "limit-lowered", workspace))
        self.assertFalse(self.passes("rirr-gate-fix-interactive", "base-not-merged", workspace))
        self.assertFalse(self.passes("rirr-gate-fix-interactive", "no-run-commit", workspace))

    def test_the_rebase_grader_fails_a_rebase_of_the_pushed_branch(self):
        for name, rebase in (("pull", ["pull", "-q", "--rebase", "origin", "main"]), ("rebase", ["rebase", "-q", "origin/main"])):
            workspace = self.scaffold("rirr-gate-fix-partial") if name == "pull" else self.workspace("rirr-gate-fix-rebase")
            if name == "rebase":
                self.run_bash([(self.cases["rirr-gate-fix-partial"].path / "scaffold.sh").as_posix()], workspace)
            self.run_git(workspace, "push", "-q", "-u", "origin", self.BRANCH)
            for case in ("rirr-gate-fix-full", "rirr-gate-fix-partial"):
                with self.subTest(form=name, case=case, state="the scaffold and a push"):
                    self.assertTrue(self.passes(case, "no-rebase", workspace))
            if name == "rebase":
                self.run_git(workspace, "fetch", "-q", "origin", "main")
            self.run_git(workspace, *rebase)
            for case in ("rirr-gate-fix-full", "rirr-gate-fix-partial"):
                with self.subTest(form=name, case=case, state="after the rebase"):
                    self.assertFalse(self.passes(case, "no-rebase", workspace))

    def test_the_lint_case_has_a_lint_script_and_no_source_of_its_command(self):
        workspace = self.scaffold("rirr-gate-fix-no-command")
        self.assertEqual(self.run_git(workspace, "rev-parse", "--abbrev-ref", "HEAD"), "work/retry-lint")
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                               capture_output=True, text=True)
        self.assertEqual(tests.returncode, 0, tests.stderr[-500:])
        lint = subprocess.run([sys.executable, "tools/lint.py", "app", "config"], cwd=workspace, capture_output=True, text=True)
        self.assertEqual((lint.returncode, lint.stdout.strip()), (1, "config/settings.py:3: line too long (98 > 88)"))
        # No CI configuration and no instructions file name the command, so a right run finds no source for it.
        self.assertFalse((workspace / ".github").exists())
        self.assertNotIn("lint", (workspace / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertTrue(self.passes("rirr-gate-fix-no-command", "no-run-commit", workspace))

    def test_the_fix_push_grader_reads_a_second_push_that_moves_the_branch(self):
        workspace = self.scaffold()
        self.run_git(workspace, "push", "-q", "-u", "origin", self.BRANCH)
        self.assertTrue((workspace / f".remote/origin.git/logs/refs/heads/{self.BRANCH}").is_file())
        self.assertFalse((workspace / ".remote/origin.git/logs/refs/heads/main").exists())
        self.assertFalse(self.passes("rirr-gate-fix-full", "route-fix-pushed", workspace))
        # A push with no new commit leaves the remote branch where it is, so it adds no reflog line.
        self.run_git(workspace, "push", "-q", "origin", self.BRANCH)
        self.assertFalse(self.passes("rirr-gate-fix-full", "route-fix-pushed", workspace))
        self.merge_the_base(workspace)
        self.run_git(workspace, "push", "-q", "origin", self.BRANCH)
        self.assertTrue(self.passes("rirr-gate-fix-full", "route-fix-pushed", workspace))
        self.assertFalse((workspace / ".remote/origin.git/logs/refs/heads/main").exists())


class ResumeReportTests(FixtureCase):
    """The planted report of each resume case names its head commit (issues #271 and #283).

    The resume of finish.md runs only if the head of the branch is the head commit of the report.
    """

    # The report of each case, and the commit that its report must name.
    REPORTS = {"rirr-merge": ("notes/Results/retry-limit-report.md", "HEAD"),
               "rirr-pr-title-form": ("notes/Results/retry-title-report.md", "HEAD"),
               "it-merge": ("notes/Results/retry-limit-report.md", "HEAD"),
               "ib-merge": ("notes/Results/retry-batch-report.md", "HEAD"),
               "rirr-upstream-remote": ("notes/Results/retry-limit-report.md", "HEAD"),
               "rirr-resume-moved-head": ("notes/Results/retry-limit-report.md", "HEAD~1"),
               "rirr-gate-fix-full": ("notes/Results/retry-behind-report.md", "HEAD"),
               "rirr-gate-fix-partial": ("notes/Results/retry-behind-report.md", "HEAD"),
               "rirr-gate-fix-interactive": ("notes/Results/retry-behind-report.md", "HEAD"),
               "rirr-gate-fix-no-command": ("notes/Results/retry-lint-report.md", "HEAD")}
    # The number of review verdicts that the report of each case holds.
    VERDICTS = {"rirr-merge": 1, "rirr-pr-title-form": 1, "it-merge": 1, "ib-merge": 3, "rirr-upstream-remote": 1, "rirr-resume-moved-head": 1,
                "rirr-gate-fix-full": 1, "rirr-gate-fix-partial": 1, "rirr-gate-fix-interactive": 1,
                "rirr-gate-fix-no-command": 1}

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}

    def scaffold(self, name):
        workspace = self.workspace(name)
        self.run_bash([(self.cases[name].path / "scaffold.sh").as_posix()], workspace)
        return workspace

    def test_the_report_names_the_head_commit_of_the_case(self):
        for name, (path, commit) in self.REPORTS.items():
            with self.subTest(case=name):
                workspace = self.scaffold(name)
                _code, named = self.git(workspace, "rev-parse", commit)
                _code, head = self.git(workspace, "rev-parse", "HEAD")
                report = (workspace / path).read_text(encoding="utf-8")
                self.assertIn(f"- **Head commit**: {named}\n", report)
                self.assertNotIn("HEAD_SHA", report)
                # In the case of the moved head, a commit that no review saw is on top of the commit of the report.
                self.assertEqual(head in report, commit == "HEAD")

    def test_the_report_gives_each_verdict_and_the_tests_pass_at_the_head(self):
        # A stop case must have no second reason to stop, and a merge case needs each fact of the resume.
        for name, (path, _commit) in self.REPORTS.items():
            with self.subTest(case=name):
                workspace = self.scaffold(name)
                report = (workspace / path).read_text(encoding="utf-8")
                self.assertEqual(report.count("Verdict `stop-clean`."), self.VERDICTS[name])
                done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=workspace,
                                      capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr[-500:])

    def test_only_the_upstream_remote_is_on_github(self):
        workspace = self.scaffold("rirr-upstream-remote")
        self.assertEqual(self.git(workspace, "remote", "get-url", "upstream"), (0, "https://github.com/example-org/users-app.git"))
        _code, origin = self.git(workspace, "remote", "get-url", "origin")
        self.assertNotIn("github.com", origin)


class PrTemplateFixtureTests(FixtureCase):
    """The two cases of issue #382 plant the same PR template on main. Its rules are only in HTML comments."""

    CASES = ("cmp-pr-repo-template", "rirr-pr-title-form")
    PATH = ".github/pull_request_template.md"
    BOX = "\n- [ ] I ran the tests of this change.\n"

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}

    def template(self, name):
        workspace = self.workspace(name)
        self.run_bash([(self.cases[name].path / "scaffold.sh").as_posix()], workspace)
        code, text = self.git(workspace, "show", f"main:{self.PATH}")
        self.assertEqual(code, 0, f"{name}: main has no {self.PATH}")
        return text

    def test_both_cases_plant_one_template_whose_rules_are_only_in_comments(self):
        texts = [self.template(name) for name in self.CASES]
        # The composer case adds one check box on a test run to its Evidence section. The other case plants none.
        self.assertIn(self.BOX, texts[0])
        self.assertEqual(texts[0].replace(self.BOX, ""), texts[1])
        prose = re.sub(r"<!--[\s\S]*?-->", "", texts[0])
        # A run that copies only the headings and the check box learns no rule of the template.
        self.assertEqual(re.sub(r"\s*\n\s*", "\n", prose.strip()), "## Problem\n## Fix\n## Evidence\n- [ ] I ran the tests of this change.")
        for rule in ("`type(scope): summary`", "agent tool and the model", "test command that you ran"):
            with self.subTest(rule=rule):
                self.assertIn(rule, texts[0])
        # The heading grader of case 1 passes on the headings of the template.
        pattern = self.cases["cmp-pr-repo-template"].graders["template-headings"][0]["pattern"]
        self.assertRegex(prose, re.compile(pattern, re.M))


class IssueTemplateFixtureTests(FixtureCase):
    """cmp-task-repo-template plants a bug template and a feature template on main. The prompt names neither."""

    BUG = ".github/ISSUE_TEMPLATE/bug_report.md"
    FEATURE = ".github/ISSUE_TEMPLATE/feature_request.md"

    def test_the_bug_template_gives_the_graded_headings_title_form_and_label(self):
        case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}["cmp-task-repo-template"]
        workspace = self.workspace(case.name)
        self.run_bash([(case.path / "scaffold.sh").as_posix()], workspace)
        texts = {}
        for path in (self.BUG, self.FEATURE):
            code, texts[path] = self.git(workspace, "show", f"main:{path}")
            self.assertEqual(code, 0, f"main has no {path}")
        bug = texts[self.BUG]
        self.assertIn('title: "fix(<area>): <what is wrong>"', bug)
        self.assertIn('labels: ["type: bug"]', bug)
        self.assertIn("<!--", bug)
        prose = re.sub(r"<!--[\s\S]*?-->", "", bug.split("---", 2)[2])
        self.assertRegex(prose, re.compile(case.graders["template-headings"][0]["pattern"], re.M))
        # The feature template has none of the graded headings, so a run that takes it fails the heading grader.
        self.assertNotIn("## What happens", texts[self.FEATURE])
        # The requests give no graded word, so a run must take the form from the skill or the template.
        bug_case = case.path.parent / "cmp-task-bug-draft"
        for path in (case.path, bug_case):
            request = (path / "prompt.md").read_text(encoding="utf-8").split("---", 2)[2].lower()
            for word in ("template", "expected", "actual", "observed", "version", "commit", "unknown", "steps"):
                with self.subTest(case=path.name, word=word):
                    self.assertNotIn(word, request)


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


class NoWorktreeBranchGraderTests(FixtureCase):
    """The branch graders of it-no-worktree and ib-no-worktree pass only for the right number of commits on the branch at its end.

    Each shape makes the branch of the case on the scaffold, and commits and squashes as a run does.
    """

    # The grader, the branch, and the counts of main..branch that the grader passes.
    CASES = {"it-no-worktree": ("one-commit", "eval/retry-limit", {1}),
             "ib-no-worktree": ("one-commit-per-task", "eval/retry-and-timeout", {2, 3})}

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials") if case.name in cls.CASES}

    def environment(self, skip_dotnet=True):
        env = super().environment(skip_dotnet)
        env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null"})
        return env

    def run_git(self, cwd, *args):
        code, output = self.git(cwd, *args)
        self.assertEqual(code, 0, output)
        return output

    def commit(self, workspace, subject):
        with (workspace / "config" / "settings.py").open("a", encoding="utf-8") as stream:
            stream.write(f"# {subject}\n")
        self.run_git(workspace, "commit", "-q", "-am", subject)
        return self.run_git(workspace, "rev-parse", "HEAD")

    def task(self, workspace, commits):
        """One task as Step 3 makes it: its commits, then the squash script from the base of the task."""
        base = self.run_git(workspace, "rev-parse", "HEAD")
        args = [sys.executable, "-I", str(SQUASH_SCRIPT), "--repo", str(workspace), "--plan-dir", "notes/Plans",
                "--base", base, "--message", "One task", "--apply"]
        for number in range(commits):
            args += ["--commit", self.commit(workspace, f"commit {number}")]
        done = run(args, env=self.environment(), cwd=workspace)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def check(self, name, shapes):
        grader, branch, counts = self.CASES[name]
        case = self.cases[name]
        options = case.graders[grader][0]
        self.assertEqual(options["target"]["path"], f".git/logs/refs/heads/{branch}")
        self.assertIn(f"`{branch}`", case.prompt_body)
        verdicts = set()
        for shape in shapes:
            with self.subTest(case=name, shape=shape.__name__):
                workspace = self.workspace(f"{name}-{shape.__name__}")
                self.run_bash([(case.path / "scaffold.sh").as_posix()], workspace)
                self.run_git(workspace, "switch", "-q", "-c", branch)
                shape(workspace)
                count = int(self.run_git(workspace, "rev-list", "--count", f"main..{branch}"))
                text = (workspace / options["target"]["path"]).read_text(encoding="utf-8")
                verdict = re.search(options["pattern"], text) is not None
                self.assertEqual(verdict, count in counts, f"the branch has {count} commits")
                verdicts.add(verdict)
        self.assertEqual(verdicts, {True, False}, "the shapes must give both verdicts")

    def side_commit(self, workspace):
        """A commit on a side branch of main. It does not conflict with the commits of the shapes."""
        self.run_git(workspace, "switch", "-q", "-c", "side", "main")
        (workspace / "side.txt").write_text("side\n", encoding="utf-8")
        self.run_git(workspace, "add", "side.txt")
        self.run_git(workspace, "commit", "-q", "-m", "side")
        sha = self.run_git(workspace, "rev-parse", "HEAD")
        self.run_git(workspace, "switch", "-q", "-")
        return sha

    def check_fails(self, name, shapes):
        """Each shape has an amend or a cherry-pick. Its commit count can fit the grader, and the grader must still fail it."""
        grader, branch, _ = self.CASES[name]
        options = self.cases[name].graders[grader][0]
        for shape in shapes:
            with self.subTest(case=name, shape=shape.__name__):
                workspace = self.workspace(f"{name}-{shape.__name__}")
                self.run_bash([(self.cases[name].path / "scaffold.sh").as_posix()], workspace)
                self.run_git(workspace, "switch", "-q", "-c", branch)
                shape(workspace)
                text = (workspace / options["target"]["path"]).read_text(encoding="utf-8")
                self.assertIsNone(re.search(options["pattern"], text))

    def amend(self, workspace):
        self.run_git(workspace, "commit", "-q", "--amend", "-m", "amended")

    def test_the_task_grader_fails_an_amend_and_a_cherry_pick(self):
        def an_amend_of_the_commit_of_the_base(workspace):
            self.amend(workspace)

        def a_task_and_an_amend(workspace):
            self.task(workspace, 1)
            self.amend(workspace)

        def a_cherry_pick(workspace):
            self.run_git(workspace, "cherry-pick", self.side_commit(workspace))

        self.check_fails("it-no-worktree", [an_amend_of_the_commit_of_the_base, a_task_and_an_amend, a_cherry_pick])

    def test_the_batch_grader_fails_an_amend_and_a_cherry_pick(self):
        def one_task_and_an_amend(workspace):
            self.task(workspace, 1)
            self.amend(workspace)

        def two_tasks_and_an_amend(workspace):
            self.task(workspace, 1)
            self.task(workspace, 1)
            self.amend(workspace)

        def one_task_and_a_cherry_pick(workspace):
            self.task(workspace, 1)
            self.run_git(workspace, "cherry-pick", self.side_commit(workspace))

        self.check_fails("ib-no-worktree", [one_task_and_an_amend, two_tasks_and_an_amend, one_task_and_a_cherry_pick])

    def test_the_task_grader_passes_only_for_one_commit_on_the_branch(self):
        def one_commit(workspace):
            self.task(workspace, 1)

        def two_commits_squashed(workspace):
            self.task(workspace, 2)

        def two_commits(workspace):
            self.commit(workspace, "task")
            self.commit(workspace, "review")

        def a_squash_and_a_later_commit(workspace):
            self.task(workspace, 2)
            self.commit(workspace, "later")

        def two_commits_and_a_soft_reset_to_the_first(workspace):
            first = self.commit(workspace, "task")
            self.commit(workspace, "review")
            self.run_git(workspace, "reset", "-q", "--soft", first)

        self.check("it-no-worktree", [one_commit, two_commits_squashed, two_commits, a_squash_and_a_later_commit,
                                      two_commits_and_a_soft_reset_to_the_first])

    def test_the_batch_grader_passes_for_one_commit_for_each_task_and_at_most_one_final_commit(self):
        def two_tasks(workspace):
            self.task(workspace, 2)
            self.task(workspace, 1)

        def two_tasks_and_a_final_commit(workspace):
            self.task(workspace, 1)
            self.task(workspace, 2)
            self.task(workspace, 1)

        def one_commit_for_both_tasks(workspace):
            self.task(workspace, 1)

        def four_commits_and_no_squash(workspace):
            for subject in ("task 1", "review 1", "task 2", "review 2"):
                self.commit(workspace, subject)

        self.check("ib-no-worktree", [two_tasks, two_tasks_and_a_final_commit, one_commit_for_both_tasks,
                                      four_commits_and_no_squash])


class NoWorktreeDirtyGraderTests(FixtureCase):
    """The scored graders of it-no-worktree-dirty on real git states. The run must stop before any work and keep the change of the user.

    Each shape is what a run does after the scaffold. Each wrong shape must fail at least one grader.
    """

    CASE = "it-no-worktree-dirty"

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def environment(self, skip_dotnet=True):
        env = super().environment(skip_dotnet)
        env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null"})
        return env

    def run_git(self, cwd, *args):
        code, output = self.git(cwd, *args)
        self.assertEqual(code, 0, output)
        return output

    def passes(self, grader, text):
        """The verdict of a regex grader on the text, for the match modes contains and not_contains."""
        options = self.case.graders[grader][0]
        flags = sum(REGEX_FLAGS.get(flag, 0) for flag in options.get("flags", ""))
        found = re.search(options["pattern"], text, flags) is not None
        return not found if options.get("match") == "not_contains" else found

    def file_passes(self, grader, workspace):
        return self.passes(grader, (workspace / self.case.graders[grader][0]["target"]["path"]).read_text(encoding="utf-8"))

    def scaffold(self, name):
        workspace = self.workspace(name)
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
        return workspace

    def lower_the_limit(self, workspace):
        path = workspace / CHANGED_FILES[self.CASE]
        text = path.read_text(encoding="utf-8")
        self.assertIn("HTTP_RETRY_LIMIT = 5\n", text)
        path.write_text(text.replace("HTTP_RETRY_LIMIT = 5\n", "HTTP_RETRY_LIMIT = 3\n"), encoding="utf-8")

    def test_the_graders_pass_only_a_run_that_keeps_the_change_and_makes_no_commit(self):
        def a_stop(workspace):
            pass

        def the_task_with_no_commit(workspace):
            self.lower_the_limit(workspace)

        def a_stash(workspace):
            self.run_git(workspace, "stash", "-q")

        def a_restore(workspace):
            self.run_git(workspace, "checkout", "-q", "--", CHANGED_FILES[self.CASE])

        def the_task_commit_with_the_change_of_the_user(workspace):
            self.run_git(workspace, "switch", "-q", "-c", "eval/retry-limit")
            self.lower_the_limit(workspace)
            self.run_git(workspace, "commit", "-q", "-am", "Lower the HTTP retry limit to 3")

        def a_commit_of_the_change_of_the_user(workspace):
            self.run_git(workspace, "commit", "-q", "-am", "Keep the work of the user")

        def an_orphan_commit_of_the_change_of_the_user(workspace):
            self.run_git(workspace, "checkout", "-q", "--orphan", "keep/user-change")
            self.run_git(workspace, "commit", "-q", "-am", "Keep the work of the user")

        def an_amend_with_the_change_of_the_user(workspace):
            self.run_git(workspace, "commit", "-q", "-a", "--amend", "--no-edit")

        def an_append(workspace):
            path = workspace / CHANGED_FILES[self.CASE]
            path.write_text(path.read_text(encoding="utf-8") + "HTTP_RETRY_LIMIT = 3\n", encoding="utf-8")

        def a_prepend(workspace):
            path = workspace / CHANGED_FILES[self.CASE]
            path.write_text("import os\n" + path.read_text(encoding="utf-8"), encoding="utf-8")

        # The verdicts of changed-file-kept and no-run-commit.
        shapes = {a_stop: (True, True), the_task_with_no_commit: (False, True), a_stash: (False, True),
                  a_restore: (False, True), the_task_commit_with_the_change_of_the_user: (False, False),
                  a_commit_of_the_change_of_the_user: (True, False),
                  an_orphan_commit_of_the_change_of_the_user: (True, False),
                  an_amend_with_the_change_of_the_user: (True, False),
                  an_append: (False, True), a_prepend: (False, True)}
        for shape, expected in shapes.items():
            with self.subTest(shape=shape.__name__):
                workspace = self.scaffold(shape.__name__)
                shape(workspace)
                self.assertEqual((self.file_passes("changed-file-kept", workspace), self.file_passes("no-run-commit", workspace)),
                                 expected)

    def test_the_reply_grader_needs_the_file_of_the_scaffold(self):
        self.assertEqual(self.case.graders["names-changed-file"][0].get("target", "last_message"), "last_message")
        workspace = self.scaffold("reply")
        changed = self.run_git(workspace, "status", "--porcelain", "--untracked-files=no").split()[-1]
        self.assertEqual(changed, CHANGED_FILES[self.CASE])
        replies = {
            f"Stopped before any work. `{changed}` has a change with no commit. Commit or stash it, then run the command again.": True,
            f"The file **{changed.split('/')[-1]}** has an uncommitted change.\n\nShall I wait until you commit or stash it?": True,
            "Stopped before any work. A tracked file has a change with no commit. Commit or stash it first.": False,
            "Stopped before any work. `config/timeouts.py` has a change with no commit.": False,
            "Stopped before any work. The settings file has a change with no commit.": False,
            f"Stopped before any work. `{changed.upper()}` has a change with no commit.": True,
        }
        for reply, expected in replies.items():
            with self.subTest(reply=reply):
                self.assertEqual(self.passes("names-changed-file", reply), expected)


class PpcRuleCandidatesEndStateTests(FixtureCase):
    """The file graders of ppc-rule-candidates on real end states of its scaffold.

    A right run renames the three functions, puts the limit back to 50, commits, and keeps CLAUDE.md as it is.
    """

    CASE = "ppc-rule-candidates"
    RENAMES = {"pager-renamed": ("src/pager.py", "pageCount", "page_count"),
               "ranges-renamed": ("src/ranges.py", "lastPage", "last_page"),
               "users-renamed": ("src/users.py", "displayName", "display_name")}
    FILE_GRADERS = ("pager-renamed", "ranges-renamed", "users-renamed", "limit-kept", "committed", "claude-md-unchanged")

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def environment(self, skip_dotnet=True):
        env = super().environment(skip_dotnet)
        env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null"})
        return env

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def failed(self, workspace):
        verdicts = file_grader_verdicts(self.case, self.FILE_GRADERS, workspace, set())
        return sorted(grader for grader, passed in verdicts.items() if not passed)

    def right_run(self, workspace, skip=()):
        for grader, (path, old, new) in self.RENAMES.items():
            if grader not in skip:
                self.edit(workspace / path, old, new)
        if "limit-kept" not in skip:
            self.edit(workspace / "src" / "store.py", "limit=500", "limit=50")
        code, output = self.git(workspace, "commit", "-q", "-am", "PR #42 T#9201 T#9202 T#9203 T#9204: fix the review points")
        self.assertEqual(code, 0, output)

    def test_the_scaffold_fails_each_fix_grader(self):
        workspace = self.workspace("planted")
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
        self.assertEqual(self.failed(workspace), ["committed", "limit-kept", "pager-renamed", "ranges-renamed", "users-renamed"])

    def test_a_right_run_passes_and_each_wrong_run_fails_its_grader(self):
        def add_a_rule(workspace):
            with (workspace / "CLAUDE.md").open("a", encoding="utf-8") as stream:
                stream.write("- Name each Python function in snake_case.\n")

        def keep_the_old_name_as_an_alias(workspace):
            path = workspace / "src" / "users.py"
            path.write_text(path.read_text(encoding="utf-8") + "\ndisplayName = display_name\n", encoding="utf-8")

        shapes = {
            "a right run": (lambda w: None, (), None),
            "a rule line in CLAUDE.md": (add_a_rule, (), "claude-md-unchanged"),
            "an old name left in the file": (keep_the_old_name_as_an_alias, (), "users-renamed"),
            "one rename missing": (lambda w: None, ("ranges-renamed",), "ranges-renamed"),
            "the limit stays at 500": (lambda w: None, ("limit-kept",), "limit-kept"),
        }
        for name, (shape, skip, failed) in shapes.items():
            with self.subTest(shape=name):
                workspace = self.workspace(name.replace(" ", "-"))
                self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
                self.right_run(workspace, skip)
                shape(workspace)
                self.assertEqual(self.failed(workspace), [failed] if failed else [])


class BugHuntFlowGraderTests(FixtureCase):
    """The scored graders of bh-flow on real end states. The snapshot and delete-temp commands run as a right run runs them.

    A file_exists grader sees only the paths that the run created, so each shape lists the files before the run first.
    """

    CASE = "bh-flow"
    SCRIPT = REPO / "essentials/dev-essentials/skills/bug-hunt/scripts/check_report.py"
    SCORED = ("report-final", "scratch-removed", "temp-files-removed", "context-kept", "project-unchanged",
              "invoice-kept", "cache-kept", "retry-kept", "email-kept", "stock-kept")

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def run_skill_command(self, command, workspace):
        """Run a command line of the skill in bash, with python3 as the Python of the tests."""
        env = dict(self.environment(), PY=sys.executable.replace("\\", "/"), C=self.SCRIPT.as_posix(),
                   P=(workspace / "project").as_posix(), S=(workspace / "scratch").as_posix(),
                   D=(workspace / "reports").as_posix())
        done = run([self.bash, "-c", f'python3() {{ "$PY" "$@"; }}\n{command}'], env=env, cwd=workspace, timeout=120)
        self.assertEqual(done.returncode, 0, f"{command} failed:\n{done.stdout}\n{done.stderr}")

    def right_run(self, workspace):
        """The files that a right run leaves: the snapshot first, the report, and the delete of step 6.

        The commands come from the text of structure-checks.md, so a wrong option name in the text fails the test.
        """
        _, sha = self.git(workspace / "project", "rev-parse", "HEAD")
        text = (REPO / "essentials/dev-essentials/skills/bug-hunt/references/structure-checks.md").read_text(encoding="utf-8")
        snapshot, delete = re.findall(r"`(python3 -I \"\$C\" (?:snapshot|delete-temp) [^`]+)`", text)
        self.run_skill_command(snapshot.replace("<full SHA>", sha).replace("<local|remote|none>", "none"), workspace)
        (workspace / "scratch" / "known-issues.md").write_text("# Known-issues digest\n\n- N-01: build_subject\n", encoding="utf-8")
        reports = workspace / "reports"
        (reports / "bug-hunt-report.md").write_text(
            "# Bug hunt report: project\n\n## Summary\n\nFindings: 0.\n\n### For the owner's review\n\nNone.\n", encoding="utf-8")
        (reports / "bug-hunt-context.md").write_text("# Run context\n", encoding="utf-8")
        for name in ("_bug-hunt-session-progress.md", "_bug-hunt-progress-area-1.md"):
            (reports / name).write_text("STATUS: done\n", encoding="utf-8")
        self.run_skill_command(delete, workspace)
        self.run_skill_command(delete + " --apply", workspace)
        (reports / "_bug-hunt-session-progress.md").unlink()

    def test_a_right_run_passes_each_scored_grader_and_each_wrong_run_fails_its_grader(self):
        def edit(path, old, new):
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new, 1), encoding="utf-8")

        def leave_a_work_file(workspace):
            (workspace / "scratch" / "work").mkdir(parents=True)
            (workspace / "scratch" / "work" / "left.txt").write_text("x\n", encoding="utf-8")

        def add_a_deep_file(workspace):
            (workspace / "project" / "billing" / "__pycache__").mkdir(parents=True, exist_ok=True)
            (workspace / "project" / "billing" / "__pycache__" / "invoice.pyc").write_text("x\n", encoding="utf-8")

        shapes = {
            "a right run": (lambda w: None, None),
            "the scratch folder stays": (leave_a_work_file, "scratch-removed"),
            "a progress file stays": (lambda w: (w / "reports" / "_bug-hunt-progress-area-1.md").write_text("x\n"),
                                      "temp-files-removed"),
            "the session progress file stays": (lambda w: (w / "reports" / "_bug-hunt-session-progress.md").write_text("x\n"),
                                                "temp-files-removed"),
            "the delete takes the run context file": (lambda w: (w / "reports" / "bug-hunt-context.md").unlink(), "context-kept"),
            "the run stops before step 5": (lambda w: edit(w / "reports" / "bug-hunt-report.md", "### For the owner's review\n", ""),
                                            "report-final"),
            "a new file in the project": (lambda w: (w / "project" / "fix.py").write_text("x\n"), "project-unchanged"),
            "a new file deep in the project": (add_a_deep_file, "project-unchanged"),
            "a fix of a planted bug": (lambda w: edit(w / "project" / "billing" / "invoice.py", "return int(total)",
                                                      "return round(total, 2)"), "invoice-kept"),
            "a deleted file of the project": (lambda w: (w / "project" / "inventory" / "stock.py").unlink(), "stock-kept"),
        }
        for name, (shape, failed) in shapes.items():
            with self.subTest(shape=name):
                workspace = self.workspace(name.replace(" ", "-"))
                self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
                before = workspace_files(workspace)
                self.right_run(workspace)
                shape(workspace)
                verdicts = file_grader_verdicts(self.case, self.SCORED, workspace, before)
                self.assertEqual(sorted(grader for grader, passed in verdicts.items() if not passed),
                                 [failed] if failed else [])


class ScratchProbeEndStateTests(FixtureCase):
    """The file graders of wm-scratch-probe on real end states: tmp/probe/ goes, and the notes of the user in tmp/ stay."""

    CASE = "wm-scratch-probe"
    GRADERS = ("notes-kept", "route-probe-removed")

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def test_a_right_run_passes_and_each_wrong_run_fails_its_grader(self):
        def keep_a_cache(workspace):
            (workspace / "tmp" / "probe" / "__pycache__").mkdir(parents=True)
            (workspace / "tmp" / "probe" / "__pycache__" / "count.pyc").write_text("x\n", encoding="utf-8")

        shapes = {
            "a right run": (lambda w: None, None),
            "the probe stays": (lambda w: (w / "tmp" / "probe" / "count.py").write_text("print(19)\n", encoding="utf-8"),
                                "route-probe-removed"),
            "a cache of the probe stays": (keep_a_cache, "route-probe-removed"),
            "the run removes tmp/": (lambda w: remove_tree(w / "tmp"), "notes-kept"),
            "the run edits the notes": (lambda w: (w / "tmp" / "review-notes.md").write_text("# Review notes\n", encoding="utf-8"),
                                        "notes-kept"),
        }
        for name, (shape, failed) in shapes.items():
            with self.subTest(shape=name):
                workspace = self.workspace(name.replace(" ", "-").replace("/", ""))
                self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
                before = workspace_files(workspace)
                self.assertIn("tmp/review-notes.md", before)
                self.assertEqual(self.git(workspace, "ls-files", "tmp")[1], "", "the notes of the user must stay untracked")
                # A right run makes tmp/probe/ and removes it after its last use.
                (workspace / "tmp" / "probe").mkdir()
                (workspace / "tmp" / "probe" / "count.py").write_text("print(19)\n", encoding="utf-8")
                remove_tree(workspace / "tmp" / "probe")
                (workspace / "tmp" / "probe").mkdir()
                shape(workspace)
                if (workspace / "tmp" / "probe").is_dir() and not any((workspace / "tmp" / "probe").iterdir()):
                    (workspace / "tmp" / "probe").rmdir()
                verdicts = file_grader_verdicts(self.case, self.GRADERS, workspace, before)
                self.assertEqual(sorted(grader for grader, passed in verdicts.items() if not passed),
                                 [failed] if failed else [])


class ReceiptsScaffoldCase(FixtureCase):
    """Helpers for the receipts projects of so-integration-proof and so-no-integration-proof. A subclass sets CASE."""

    CASE = None

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def suite(self, workspace, folder):
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", folder], cwd=workspace,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                              env={**self.environment(), "PYTHONDONTWRITEBYTECODE": "1"})
        return done.returncode == 0

    def replace(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")


class IntegrationProofScaffoldTests(ReceiptsScaffoldCase):
    """The project of so-integration-proof: the plain change passes the unit tests, and only the integration test fails."""

    CASE = "so-integration-proof"
    GRADERS = ("discount-changed", "receipt-updated")

    def test_the_plain_change_breaks_only_the_integration_test(self):
        workspace = self.workspace()
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
        before = workspace_files(workspace)
        self.assertEqual((self.suite(workspace, "tests"), self.suite(workspace, "integration")), (True, True))
        self.assertEqual(file_grader_verdicts(self.case, self.GRADERS, workspace, before),
                         {"discount-changed": False, "receipt-updated": False})
        # The instruction files name only the unit tests. The CI workflow names both suites.
        for name in ("CLAUDE.md", "README.md"):
            self.assertNotIn("integration", (workspace / name).read_text(encoding="utf-8"))
        self.assertIn("discover -s integration", (workspace / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))

        self.replace(workspace / "app" / "pricing.py", "MEMBER_DISCOUNT_PERCENT = 10", "MEMBER_DISCOUNT_PERCENT = 15")
        self.assertFalse(self.suite(workspace, "tests"), "the unit tests must pin the old rate")
        self.replace(workspace / "tests" / "test_pricing.py", "3600", "3400")
        self.assertEqual((self.suite(workspace, "tests"), self.suite(workspace, "integration")), (True, False))
        self.assertEqual(file_grader_verdicts(self.case, self.GRADERS, workspace, before),
                         {"discount-changed": True, "receipt-updated": False})

        receipt = subprocess.run([sys.executable, "-m", "app.cli", "samples/order.json"], cwd=workspace, capture_output=True,
                                 text=True, encoding="utf-8", check=True, env={**self.environment(), "PYTHONDONTWRITEBYTECODE": "1"})
        (workspace / "integration" / "expected" / "receipt.txt").write_text(receipt.stdout, encoding="utf-8", newline="\n")
        self.assertTrue(self.suite(workspace, "integration"))
        self.assertEqual(file_grader_verdicts(self.case, self.GRADERS, workspace, before),
                         {"discount-changed": True, "receipt-updated": True})


class NoIntegrationProofScaffoldTests(ReceiptsScaffoldCase):
    """The project of so-no-integration-proof: the same app with only unit tests, and no documented run of the real CLI."""

    CASE = "so-no-integration-proof"
    GRADERS = ("discount-changed",)

    def test_the_plain_change_breaks_only_its_unit_test(self):
        workspace = self.workspace()
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
        before = workspace_files(workspace)
        self.assertFalse((workspace / "integration").exists())
        self.assertFalse((workspace / "samples").exists())
        texts = {name: (workspace / name).read_text(encoding="utf-8") for name in ("CLAUDE.md", "README.md", ".github/workflows/ci.yml")}
        for name, text in texts.items():
            with self.subTest(file=name):
                self.assertNotRegex(text, r"integration|smoke|end-to-end|app\.cli|app/cli")
        self.assertTrue(self.suite(workspace, "tests"))
        self.assertEqual(file_grader_verdicts(self.case, self.GRADERS, workspace, before), {"discount-changed": False})
        self.replace(workspace / "app" / "pricing.py", "MEMBER_DISCOUNT_PERCENT = 10", "MEMBER_DISCOUNT_PERCENT = 15")
        self.assertFalse(self.suite(workspace, "tests"), "the unit tests must pin the old rate")
        self.replace(workspace / "tests" / "test_pricing.py", "3600", "3400")
        self.assertTrue(self.suite(workspace, "tests"))
        self.assertEqual(file_grader_verdicts(self.case, self.GRADERS, workspace, before), {"discount-changed": True})


class SmokeRunScaffoldCase(ReceiptsScaffoldCase):
    """Helpers for so-smoke-run-self and so-smoke-run-printer: the receipts app with a sample order and only unit tests."""

    GRADERS = ("discount-changed",)

    def python(self, workspace, *args):
        return subprocess.run([sys.executable, *args], cwd=workspace, capture_output=True, text=True, encoding="utf-8",
                              timeout=120, env={**self.environment(), "PYTHONDONTWRITEBYTECODE": "1"})

    def changed_workspace(self):
        workspace = self.workspace()
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
        before = workspace_files(workspace)
        self.assertFalse((workspace / "integration").exists())
        readme = (workspace / "README.md").read_text(encoding="utf-8")
        self.assertIn("python3 -m app.cli samples/order.json", readme)
        self.assertEqual(file_grader_verdicts(self.case, self.GRADERS, workspace, before), {"discount-changed": False})
        self.replace(workspace / "app" / "pricing.py", "MEMBER_DISCOUNT_PERCENT = 10", "MEMBER_DISCOUNT_PERCENT = 15")
        self.assertFalse(self.suite(workspace, "tests"), "the unit tests must pin the old rate")
        self.replace(workspace / "tests" / "test_pricing.py", "3600", "3400")
        self.assertTrue(self.suite(workspace, "tests"))
        self.assertEqual(file_grader_verdicts(self.case, self.GRADERS, workspace, before), {"discount-changed": True})
        return workspace


class SmokeRunSelfScaffoldTests(SmokeRunScaffoldCase):
    """The project of so-smoke-run-self: the CLI of the README prints the receipt of the sample order."""

    CASE = "so-smoke-run-self"

    def test_the_cli_prints_the_new_total_after_the_change(self):
        workspace = self.changed_workspace()
        done = self.python(workspace, "-m", "app.cli", "samples/order.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Member discount 15%", done.stdout)
        self.assertRegex(done.stdout, r"Total\s+34\.00")


class SmokeRunPrinterScaffoldTests(SmokeRunScaffoldCase):
    """The project of so-smoke-run-printer: the CLI writes to a printer that the sandbox lacks. A stand-in file works."""

    CASE = "so-smoke-run-printer"

    def test_the_cli_needs_the_printer_and_a_stand_in_file_works(self):
        workspace = self.changed_workspace()
        self.assertFalse(os.path.exists("/dev/usb/lp0"), "the test machine must not have the printer")
        self.assertNotEqual(self.python(workspace, "-m", "app.cli", "samples/order.json").returncode, 0)
        stand_in = workspace / "printer.txt"
        code = ("import sys, app.cli as cli; cli.PRINTER = sys.argv[1]; sys.exit(cli.main(['cli', 'samples/order.json']))")
        done = self.python(workspace, "-c", code, stand_in.as_posix())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertRegex(stand_in.read_text(encoding="ascii"), r"Total\s+34\.00")


class OptimizeSkillFixtureTests(FixtureCase):
    """The fixture of os-review-fixes holds the seeded issues and the lost rule. Its file graders fail on the fixture
    where they must, pass on a right run with two commits, and fail on a lost rule, a third commit, and a push."""

    CASE = "os-review-fixes"
    SKILL = "plugin/skills/export-orders/SKILL.md"
    REFERENCES = "plugin/skills/export-orders/references"
    AGENT = "plugin/agents/export-checker.md"
    SIZE_RULE = "Never upload a CSV file that is larger than 50 MB. Split such a file into parts of at most 50 MB first."
    SAFETY_RULE = "Never delete, move, or change a file in `exports/`."
    DUPLICATE = "Write each CSV file to a temporary name first, and rename it when the file is complete."

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def scaffold(self):
        workspace = self.workspace()
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], workspace)
        return workspace

    def passes(self, workspace, name):
        """The verdict of a regex grader on its file, or of a file_exists grader. A path that ends in /** is any file below it."""
        options = self.case.graders[name][0]
        if options["type"] == "file_exists":
            path = options["path"]
            found = any(p.is_file() for p in (workspace / path[:-3]).rglob("*")) if path.endswith("/**") \
                else (workspace / path).is_file()
            return found == options.get("exists", True)
        file = workspace / options["target"]["path"]
        if not file.is_file():
            return False
        flags = sum(REGEX_FLAGS[flag] for flag in options.get("flags", ""))
        found = re.search(options["pattern"], file.read_bytes().decode("utf-8"), flags) is not None
        return not found if options.get("match") == "not_contains" else found

    def scored(self, workspace):
        """The names of the scored graders that fail."""
        return {name for name in self.case.graders if not name.startswith("route-") and not self.passes(workspace, name)}

    def read(self, workspace, path):
        return (workspace / path).read_bytes().decode("utf-8")

    def write(self, workspace, path, text):
        (workspace / path).write_bytes(text.encode("utf-8"))

    def commit(self, workspace, message, *paths):
        code, output = self.git(workspace, "commit", "-q", "-m", message, "--", *paths)
        self.assertEqual(code, 0, output)

    def right_run(self, workspace):
        """The reports, a step-3 commit that cuts the double-check line, and a step-6 commit that restores the rule."""
        self.write(workspace, "opt-reports/optimization-audit-export-orders.md", "# Audit\n")
        self.write(workspace, "opt-reports/optimization-review-export-orders.md", "# Review\n")
        skill = self.read(workspace, self.SKILL)
        self.write(workspace, self.SKILL, skill.replace("- Double-check your work before you report to the user.\n", ""))
        self.commit(workspace, "Optimize export-orders", self.SKILL)
        skill = self.read(workspace, self.SKILL)
        anchor = "the count of orders, and the size of the file.\n"
        self.write(workspace, self.SKILL, skill.replace(anchor, f"{anchor}\n{self.SIZE_RULE}\n"))
        self.commit(workspace, "Fix U-1", self.SKILL)

    def test_the_fixture_has_the_seeded_issues(self):
        workspace = self.scaffold()
        skill = self.read(workspace, self.SKILL)
        csv_format = self.read(workspace, f"{self.REFERENCES}/csv-format.md")
        self.assertGreater(len(csv_format.splitlines()), 100)
        self.assertNotRegex(csv_format, r"(?i)contents")
        self.assertIn(self.DUPLICATE, skill)
        self.assertIn(self.DUPLICATE, csv_format)
        self.assertIn("You MUST dispatch the export-checker agent before the upload.\n", skill)
        self.assertIn("Double-check your work", skill)
        self.assertTrue((workspace / self.REFERENCES / "old-retry-notes.md").is_file())
        self.assertNotIn("old-retry-notes", skill)
        self.assertIn(self.SAFETY_RULE, self.read(workspace, self.AGENT))
        self.assertIn('subagent_type: "export-kit:export-checker"', skill)
        self.assertEqual(self.git(workspace, "check-ignore", "-q", "opt-reports/")[0], 0)

    def test_the_last_fixture_commit_deletes_the_size_rule(self):
        workspace = self.scaffold()
        self.assertEqual(self.git(workspace, "log", "-1", "--format=%s")[1], "fixture: shorten the upload step")
        self.assertIn(self.SIZE_RULE, self.git(workspace, "show", f"HEAD~1:{self.SKILL}")[1])
        self.assertNotIn("50 MB", self.read(workspace, self.SKILL))
        prompt = (self.case.path / "prompt.md").read_text(encoding="utf-8")
        self.assertIn(f'"{self.SIZE_RULE}"', prompt)
        self.assertIn('"fixture: shorten the upload step"', prompt)

    def test_the_graders_on_the_fixture(self):
        workspace = self.scaffold()
        self.assertEqual(self.scored(workspace), {"size-rule-restored", "audit-report-written", "review-report-written"})
        self.assertFalse(self.passes(workspace, "route-step6-reached"))

    def test_a_right_run_passes_every_scored_grader(self):
        workspace = self.scaffold()
        self.right_run(workspace)
        self.assertEqual(self.scored(workspace), set())
        self.assertTrue(self.passes(workspace, "route-step6-reached"))

    def test_an_amend_of_the_step_6_commit_still_passes(self):
        workspace = self.scaffold()
        self.right_run(workspace)
        code, output = self.git(workspace, "commit", "-q", "--amend", "-m", "Fix U-1 and R-01")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.scored(workspace), set())
        self.assertTrue(self.passes(workspace, "route-step6-reached"))

    def test_each_loss_fails_its_grader(self):
        losses = {
            "safety-rule-kept": (self.AGENT, self.SAFETY_RULE, "Do not change the exports."),
            "claude-md-unchanged": ("CLAUDE.md", "- No CHANGELOG.\n", "- No CHANGELOG.\n- Keep each rule in one place.\n"),
            "size-rule-restored": (self.SKILL, self.SIZE_RULE, "Split a large file first."),
        }
        for name, (path, old, new) in losses.items():
            with self.subTest(grader=name):
                workspace = self.scaffold()
                self.right_run(workspace)
                text = self.read(workspace, path)
                self.assertIn(old, text)
                self.write(workspace, path, text.replace(old, new))
                self.assertEqual(self.scored(workspace), {name})
                remove_tree(workspace)

    def test_a_third_commit_or_a_push_fails(self):
        workspace = self.scaffold()
        self.right_run(workspace)
        self.write(workspace, "README.md", "# export-kit\n")
        self.commit(workspace, "A third commit", "README.md")
        self.assertEqual(self.scored(workspace), {"at-most-two-commits"})
        code, output = self.git(workspace, "push", "-q", "origin", "main")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.scored(workspace), {"at-most-two-commits", "no-push"})


class AuditTeamSeededDesignTests(FixtureCase):
    """The design of at-seeded-design holds one planted defect for each role, and each defect grader names its defect."""

    CASE = "at-seeded-design"
    DESIGN = "docs/design/refund-export.md"
    # Each defect grader, and a text that the grader and the design both hold.
    DEFECTS = {
        "found-missing-acceptance": "R3",
        "found-wrong-assumption": "already retries a failed upload",
        "found-untestable-step": "the network is stable",
        "found-name-pattern": "RefundExportManager",
        "found-contradiction": "7 days",
    }

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(REPO / "essentials" / "dev-essentials")}[cls.CASE]

    def setUp(self):
        super().setUp()
        self.files = self.workspace()
        self.run_bash([(self.case.path / "scaffold.sh").as_posix()], self.files)
        self.design = self.read(self.DESIGN)

    def read(self, path):
        return (self.files / path).read_bytes().decode("utf-8")

    def section(self, heading):
        start = self.design.index(f"\n## {heading}\n")
        end = self.design.find("\n## ", start + 1)
        return self.design[start:] if end < 0 else self.design[start:end]

    def test_r3_is_the_only_requirement_with_no_acceptance_case(self):
        requirements = re.findall(r"^- (R\d+): ", self.section("Requirements"), re.MULTILINE)
        covered = re.findall(r"^- A\d+ \((R\d+)\): ", self.section("Acceptance cases"), re.MULTILINE)
        self.assertEqual(requirements, ["R1", "R2", "R3", "R4"])
        self.assertEqual(covered, ["R1", "R2", "R4"])

    def test_the_upload_of_the_storage_client_has_no_retry(self):
        code = self.read("app/storage_client.py")
        upload = code[code.index("    def upload("):]
        self.assertNotRegex(upload, r"\b(?:for|while|retry|retries)\b")
        self.assertIn("already retries a failed upload", self.section("Components"))

    def test_step_4_waits_for_a_condition_that_the_design_does_not_define(self):
        self.assertIn("4. If the upload fails", self.section("Steps of the job"))
        self.assertIn("wait until the network is stable", self.section("Steps of the job"))
        self.assertEqual(self.design.count("stable"), 1)

    def test_the_new_names_break_the_pattern_of_the_handlers(self):
        handlers = sorted(path.name for path in (self.files / "app" / "handlers").glob("*_export_handler.py"))
        self.assertEqual(handlers, ["invoice_export_handler.py", "order_export_handler.py"])
        for name in handlers:
            with self.subTest(handler=name):
                stem = name[:-len("_export_handler.py")]
                self.assertIn(f"class {stem.capitalize()}ExportHandler:", self.read(f"app/handlers/{name}"))
        self.assertIn("`app/handlers/<name>_export_handler.py`", self.read("README.md"))
        self.assertIn("`app/handlers/RefundExporter.py`", self.section("Components"))
        self.assertIn("`RefundExportManager`", self.section("Components"))
        self.assertNotIn("RefundExportHandler", self.design)

    def test_retention_and_cleanup_give_two_ages(self):
        self.assertIn("30 days", self.section("Retention"))
        self.assertIn("older than 7 days", self.section("Cleanup"))

    def test_each_defect_grader_names_a_text_of_the_design(self):
        defects = {name for name in self.case.graders if name.startswith("found-")}
        self.assertEqual(defects, set(self.DEFECTS))
        for name, text in self.DEFECTS.items():
            with self.subTest(grader=name):
                meta, body = self.case.graders[name]
                self.assertEqual((meta["type"], meta["focus"]), ("llm", "last_message"))
                self.assertIn(text, body)
                self.assertIn(text, self.design)
                self.assertIn("the result is PASS", body)
                self.assertIn("the result is FAIL", body)


if __name__ == "__main__":
    unittest.main()
