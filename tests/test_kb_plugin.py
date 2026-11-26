"""Tests for the scripts of the kb plugin: the hook launcher and the setup check.

Each test builds a fake KB clone with stub hook scripts in a temporary folder and runs the real launcher against it.
"""
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from support import REPO, tool_missing
from testkit import ScratchCase, clean_env, git_bash_pwd_stub, git_init, run

PLUGIN = REPO / "knowledge/kb"
LAUNCHER = PLUGIN / "scripts/kb-hook.sh"
CHECK = PLUGIN / "skills/setup/check.sh"
NOTES_RULE = REPO / "essentials/dev-essentials/references/notes-root.md"
MERGE_PR = REPO / "essentials/dev-essentials/skills/merge-pr/SKILL.md"
NO_CLONE_LINE = "KB plugin: no KB clone found. Set KB_DIR with /kb:setup."
EVENTS = {
    "SessionStart": "session-start",
    "SubagentStart": "subagent-start",
    "PreToolUse": ["guard", "allow-read"],
    "Stop": "stop",
    "SessionEnd": "session-end",
}
OLD_RULES = (
    "Bash(bash _claude/tools/kb-search.sh *)",
    "Bash(python3 -B _claude/tools/ste-check.py *)",
    "Bash(python3 -B _claude/tools/md-check.py *)",
)
GIT_SUBCOMMANDS = ("status", "log", "show")


def script_rules(kb_path):
    """The allow rules of the three KB scripts, with the full path of the clone."""
    return [f"Bash(bash {kb_path}/_claude/tools/kb-search.sh *)",
            f"Bash(python3 -B {kb_path}/_claude/tools/ste-check.py *)",
            f"Bash(python3 -B {kb_path}/_claude/tools/md-check.py *)"]


def rules(kb_path):
    """The allow list and the ask list that make every rule piece of check.sh complete for this KB path."""
    allow = [*script_rules(kb_path), *(f"Bash(git -C {kb_path} {sub} *)" for sub in GIT_SUBCOMMANDS)]
    return allow, [f"Bash(git -C {kb_path} * --output*)"]


class BashCase(ScratchCase):
    def setUp(self):
        self.bash = shutil.which("bash")
        if self.bash is None:
            tool_missing(self, "bash not found")
        super().setUp()

    def env(self, **extra):
        return clean_env(("KB_DIR", "CLAUDE_PROJECT_DIR"), **extra)

    def make_clone(self, root):
        """A fake KB clone whose hook scripts print their name and their stdin, and exit with a set code."""
        (root / "_claude/hooks").mkdir(parents=True)
        (root / "_claude/RULES.md").write_text("rules\n", encoding="utf-8")
        for name in ("session-start", "subagent-start", "guard", "allow-read", "session-end"):
            (root / f"_claude/hooks/{name}.sh").write_text(
                f'echo "{name}:$(cat)"\n[ "{name}" = guard ] && exit 2\nexit 0\n', encoding="utf-8")
        (root / "_claude/kb-sync.sh").write_text('echo "sync:$*"\n', encoding="utf-8")
        return root

    def launch(self, name, cwd, stdin="", **env):
        return run([self.bash, LAUNCHER, name], stdin=stdin, env=self.env(**env), cwd=cwd, timeout=30)


class LauncherTests(BashCase):
    def test_no_clone_prints_one_line_at_session_start(self):
        done = self.launch("session-start", self.tmp)
        self.assertEqual((done.returncode, done.stdout.splitlines()), (0, [NO_CLONE_LINE]))

    def test_no_clone_is_silent_for_the_other_hooks(self):
        for name in ("guard", "allow-read", "subagent-start", "stop", "session-end"):
            with self.subTest(hook=name):
                done = self.launch(name, self.tmp, stdin="{}")
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_kb_dir_runs_the_script_of_the_same_name_with_stdin(self):
        clone = self.make_clone(self.tmp / "clone")
        done = self.launch("session-start", self.tmp, stdin="input1", KB_DIR=str(clone))
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "session-start:input1"))

    def test_exit_code_of_the_guard_reaches_the_caller(self):
        clone = self.make_clone(self.tmp / "clone")
        done = self.launch("guard", self.tmp, stdin="{}", KB_DIR=str(clone))
        self.assertEqual((done.returncode, done.stdout.strip()), (2, "guard:{}"))

    def test_allow_read_gets_the_stdin_and_returns_the_stdout(self):
        clone = self.make_clone(self.tmp / "clone")
        done = self.launch("allow-read", self.tmp, stdin="{}", KB_DIR=str(clone))
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "allow-read:{}"))

    def test_stop_runs_the_sync_wrapper_if_changed(self):
        clone = self.make_clone(self.tmp / "clone")
        done = self.launch("stop", self.tmp, KB_DIR=str(clone))
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "sync:--if-changed"))

    def test_clone_in_the_project_folder_runs_no_script_without_a_full_kb_dir(self):
        # The project folder and its child folder are clones of an unknown repository (issue #129).
        project = self.tmp / "project"
        for root in (project, project / "child"):
            (root / "_claude/hooks").mkdir(parents=True)
            (root / "_claude/RULES.md").write_text("rules\n", encoding="utf-8")
            (root / "_claude/kb-sync.sh").write_text("touch ran-stop\n", encoding="utf-8")
            for name in ("session-start", "subagent-start", "guard", "allow-read", "session-end"):
                (root / f"_claude/hooks/{name}.sh").write_text(f"touch ran-{name}\n", encoding="utf-8")
        for kb_dir in (None, ".", "child"):
            for name in ("session-start", "subagent-start", "guard", "allow-read", "stop", "session-end"):
                with self.subTest(kb_dir=kb_dir, hook=name):
                    extra = {} if kb_dir is None else {"KB_DIR": kb_dir}
                    done = self.launch(name, project, stdin="{}", CLAUDE_PROJECT_DIR=str(project), **extra)
                    expected = [NO_CLONE_LINE] if name == "session-start" else []
                    self.assertEqual((done.returncode, done.stdout.splitlines()), (0, expected))
        self.assertEqual([path.name for path in project.rglob("ran-*")], [])

    def test_session_inside_the_kb_clone_runs_its_hook_with_kb_dir(self):
        clone = self.make_clone(self.tmp / "KB")
        done = self.launch("subagent-start", clone, stdin="x", KB_DIR=str(clone), CLAUDE_PROJECT_DIR=str(clone))
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "subagent-start:x"))

    def test_kb_dir_wins_over_a_clone_in_the_project_folder(self):
        project = self.tmp / "project"
        self.make_clone(project / "KB")
        chosen = self.make_clone(self.tmp / "chosen")
        (chosen / "_claude/hooks/subagent-start.sh").write_text('echo chosen\n', encoding="utf-8")
        done = self.launch("subagent-start", project, KB_DIR=str(chosen), CLAUDE_PROJECT_DIR=str(project))
        self.assertEqual(done.stdout.strip(), "chosen")

    def test_paths_with_spaces(self):
        clone = self.make_clone(self.tmp / "my proj" / "K B")
        # On Windows, str gives the C:\... form, and as_posix gives the C:/... form that /kb:setup writes.
        for kb_dir in sorted({str(clone), clone.as_posix()}):
            with self.subTest(kb_dir=kb_dir):
                done = self.launch("subagent-start", self.tmp, stdin="y", KB_DIR=kb_dir)
                self.assertEqual(done.stdout.strip(), "subagent-start:y")

    def test_missing_hook_script_exits_0_and_prints_one_line_at_session_start_only(self):
        clone = self.make_clone(self.tmp / "clone")
        (clone / "_claude/hooks/session-start.sh").unlink()
        (clone / "_claude/hooks/session-end.sh").unlink()
        (clone / "_claude/kb-sync.sh").unlink()
        (clone / "_claude/hooks/allow-read.sh").unlink()
        done = self.launch("session-start", self.tmp, KB_DIR=str(clone))
        self.assertEqual((done.returncode, len(done.stdout.splitlines()), done.stderr), (0, 1, ""))
        for name in ("session-end", "stop", "allow-read"):
            with self.subTest(hook=name):
                done = self.launch(name, self.tmp, KB_DIR=str(clone))
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_kb_dir_without_rules_file_is_ignored(self):
        (self.tmp / "empty").mkdir()
        done = self.launch("session-start", self.tmp, KB_DIR=str(self.tmp / "empty"))
        self.assertEqual(done.stdout.splitlines(), [NO_CLONE_LINE])

    def test_kb_dir_with_no_clone_runs_no_script_of_a_clone_in_the_project_folder(self):
        project = self.make_clone(self.tmp / "project")
        done = self.launch("subagent-start", project, stdin="x", KB_DIR=str(self.tmp / "moved"),
                           CLAUDE_PROJECT_DIR=str(project))
        self.assertEqual((done.returncode, done.stdout), (0, ""))


class NotesRuleTests(BashCase):
    def test_the_rule_and_the_launcher_agree_on_a_kb_clone(self):
        lines = [line.strip() for line in NOTES_RULE.read_text(encoding="utf-8").splitlines()
                 if line.strip().startswith('case "${KB_DIR-}"')]
        self.assertEqual(len(lines), 1, "The rule file must hold exactly one KB test line.")
        script = self.tmp / "kb-test.sh"
        script.write_text(f"{lines[0]}\n", encoding="utf-8", newline="\n")
        clone = self.make_clone(self.tmp / "clone")
        empty = self.tmp / "empty"
        empty.mkdir()
        inputs = (
            ({"KB_DIR": str(clone)}, str(clone)),
            ({"KB_DIR": "clone"}, ""),
            ({"KB_DIR": str(empty)}, ""),
            ({}, ""),
        )
        for extra, expected in inputs:
            with self.subTest(env=extra):
                found = run([self.bash, script], env=self.env(**extra), cwd=self.tmp, timeout=30)
                self.assertEqual(found.stdout.strip(), expected)
                launched = self.launch("session-start", self.tmp, **extra)
                self.assertEqual(NO_CLONE_LINE in launched.stdout, expected == "")


class CrossPluginTests(unittest.TestCase):
    def test_merge_pr_names_only_skills_that_kb_has(self):
        names = set(re.findall(r"`kb:([\w-]+)`", MERGE_PR.read_text(encoding="utf-8")))
        self.assertTrue(names, "merge-pr names no skill of the kb plugin.")
        for name in sorted(names):
            with self.subTest(skill=name):
                self.assertTrue((PLUGIN / "skills" / name / "SKILL.md").is_file())


class HooksFileTests(unittest.TestCase):
    def test_each_event_calls_the_launcher_with_its_hook_name(self):
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(sorted(hooks), sorted(EVENTS))
        for event, name in EVENTS.items():
            with self.subTest(event=event):
                names = [name] if isinstance(name, str) else name
                commands = [h["command"] for group in hooks[event] for h in group["hooks"]]
                self.assertEqual(commands, [f'bash "${{CLAUDE_PLUGIN_ROOT}}/scripts/kb-hook.sh" {n}' for n in names])

    def test_guard_matcher_names_only_documented_tools(self):
        group = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0]
        self.assertEqual(group["matcher"], "Edit|Write|NotebookEdit")

    def test_allow_read_group_matches_bash(self):
        group = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"][1]
        self.assertEqual(group["matcher"], "Bash")
        self.assertEqual([h["command"] for h in group["hooks"]],
                         ['bash "${CLAUDE_PLUGIN_ROOT}/scripts/kb-hook.sh" allow-read'])


class CheckScriptTests(BashCase):
    WIN_KB = "C:/Users/me/Documents/GitHub/KB"

    def setUp(self):
        super().setUp()
        # pwd -W of Git Bash prints the long form of an 8.3 short name, such as RUNNER~1 in TEMP.
        self.tmp = self.tmp.resolve()
        # The Linux branch on every OS. A test of the Windows branch replaces this stub.
        self.stub("uname", "echo Linux")

    def stub(self, name, body):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        path = bin_dir / name
        path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        path.chmod(0o755)

    def check_env(self, home, **extra):
        path = f"{self.tmp / 'bin'}{os.pathsep}{os.environ['PATH']}"
        values = {"HOME": str(home), "PATH": path, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
        values.update(extra)
        return self.env(**values)

    def run_check(self, home, **extra):
        return run([self.bash, CHECK], env=self.check_env(home, **extra), cwd=self.tmp, timeout=30)

    def bash_home(self, home):
        """The value of $HOME in bash. Git Bash shows a Windows path in its own form, such as /tmp/tmpx/home."""
        return run([self.bash, "-c", 'printf %s "$HOME"'], env=self.env(HOME=str(home)), timeout=30).stdout

    def make_clone_with_hooks_path(self, root):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        (root / "_claude").mkdir(parents=True)
        (root / "_claude/RULES.md").write_text("rules\n", encoding="utf-8")
        git_init(root)
        subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", "_claude/git-hooks"], check=True)
        return root

    def complete_home(self, additional_dir=None, rule_dir=None):
        """A home folder with every piece in place. Returns the home folder, the clone, and the git config file."""
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        clone = self.make_clone_with_hooks_path(self.tmp / "KB")
        allow, ask = rules(rule_dir or clone.as_posix())
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": str(clone)},
            "permissions": {"allow": allow, "ask": ask,
                            "additionalDirectories": [additional_dir or str(clone)]},
        }, indent=2), encoding="utf-8")
        (home / ".claude/CLAUDE.md").write_text(
            f"@{clone}/_claude/CLAUDE.global.md\n@{clone}/_claude/RULES.md\n\nKB root: `{clone}`\n", encoding="utf-8")
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("[git-sync]\n\tsyncEnabled = true\n\tsyncNewFiles = true\n[core]\n\tlongpaths = true\n",
                             encoding="utf-8")
        return home, clone, gitconfig

    def use_windows_stubs(self, scheduled=True, windows_path=None):
        self.stub("uname", "echo MINGW64_NT-10.0")
        self.stub("schtasks.exe", "exit 0" if scheduled else "exit 1")
        return git_bash_pwd_stub(self.tmp / "bash_env.sh", windows_path or self.WIN_KB)

    def run_complete(self, home, clone, gitconfig, **extra):
        env = self.check_env(home, **{"KB_DIR": str(clone), "GIT_CONFIG_GLOBAL": str(gitconfig), **extra})
        return run([self.bash, CHECK], env=env, cwd=self.tmp, timeout=30)

    @staticmethod
    def missing_lines(done):
        return [line for line in done.stdout.splitlines() if line.startswith("MISSING: ")]

    @staticmethod
    def stale_lines(done):
        return [line for line in done.stdout.splitlines() if line.startswith("STALE: ")]

    def snapshot(self, *roots):
        found = {}
        for root in roots:
            paths = [Path(root)] if Path(root).is_file() else sorted(Path(root).rglob("*"))
            for path in paths:
                stat = path.stat()
                found[str(path)] = (stat.st_size, stat.st_mtime_ns)
        return found

    def test_empty_home_reports_the_missing_pieces_and_exits_0(self):
        home = self.tmp / "home"
        home.mkdir()
        self.stub("crontab", "exit 1")
        done = self.run_check(home)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "")
        lines = done.stdout.splitlines()
        self.assertTrue(lines[0].startswith("OS: "), lines)
        missing = self.missing_lines(done)
        for piece in ("KB clone:", "KB_DIR:", "import line: @.../_claude/CLAUDE.global.md",
                      "import line: @.../_claude/RULES.md", "KB root line:", "sync timer:", "git-sync.syncEnabled:",
                      "git-sync.syncNewFiles:"):
            with self.subTest(piece=piece):
                self.assertTrue(any(line.startswith(f"MISSING: {piece}") for line in missing), missing)
        self.assertNotIn("All pieces are in place.", lines)
        self.assertFalse(any(line.startswith(("MISSING: allow rule:", "MISSING: ask rule:")) for line in missing), missing)

    def test_complete_home_on_linux_reports_all_pieces_in_place(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "*/5 * * * * bash /x/kb-sync.sh"')
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(), ["OS: linux", "All pieces are in place."])

    def test_missing_rules_are_reported_in_order_with_the_clone_path(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        self.settings_with(home, clone, [])
        settings = f"{self.bash_home(home)}/.claude/settings.json"
        allow, ask = rules(clone.as_posix())
        expected = [f"MISSING: allow rule: {rule} is not in permissions.allow in {settings}." for rule in allow]
        expected += [f"MISSING: ask rule: {rule} is not in permissions.ask in {settings}." for rule in ask]
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(self.missing_lines(done), expected)

    def test_ask_rule_in_the_allow_list_is_reported_once(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(clone.as_posix())
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": str(clone)},
            "permissions": {"allow": allow + ask, "additionalDirectories": [str(clone)]},
        }, indent=2), encoding="utf-8")
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig))
        self.assertEqual(len(missing), 1, missing)
        self.assertTrue(missing[0].startswith("MISSING: ask rule:"), missing)

    def settings_with(self, home, clone, allow, ask=(), deny=(), newline="\n"):
        text = json.dumps({
            "env": {"KB_DIR": str(clone)},
            "permissions": {"allow": allow, "ask": list(ask), "deny": list(deny), "additionalDirectories": [str(clone)]},
        }, indent=2).replace("\n", newline)
        with open(home / ".claude/settings.json", "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def test_complete_settings_with_crlf_line_ends_are_in_place(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(clone.as_posix())
        self.settings_with(home, clone, allow, ask, newline="\r\n")
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(done.stdout.splitlines(), ["OS: linux", "All pieces are in place."])

    def test_rules_only_in_the_deny_list_are_reported(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(clone.as_posix())
        self.settings_with(home, clone, [], deny=allow + ask)
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig))
        self.assertEqual(len(missing), len(allow) + 1, missing)
        self.assertEqual(len([line for line in missing if line.startswith("MISSING: allow rule:")]), len(allow), missing)
        self.assertEqual(len([line for line in missing if line.startswith("MISSING: ask rule:")]), 1, missing)

    def test_path_rules_with_a_different_case_are_reported_on_linux(self):
        home, clone, gitconfig = self.complete_home(rule_dir=(self.tmp / "KB").as_posix().upper())
        self.stub("crontab", 'echo "kb-sync.sh"')
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig))
        self.assertEqual(len([line for line in missing if line.startswith("MISSING: allow rule: Bash(git -C ")]),
                         len(GIT_SUBCOMMANDS), missing)
        self.assertEqual(len([line for line in missing if line.startswith("MISSING: ask rule:")]), 1, missing)
        self.assertEqual(len([line for line in missing if "/_claude/tools/" in line]), 3, missing)

    def test_a_bracket_inside_an_earlier_allow_entry_hides_no_rule(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(clone.as_posix())
        self.settings_with(home, clone, ["Bash(ls [a-z]*)", *allow], ask)
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(done.stdout.splitlines(), ["OS: linux", "All pieces are in place."])

    def test_a_longer_entry_that_contains_a_rule_does_not_count(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(clone.as_posix())
        longer_allow = [f"x{rule}" for rule in allow]
        longer_ask = [f"x{rule}" for rule in ask]
        self.settings_with(home, clone, longer_allow, longer_ask)
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig))
        self.assertEqual(len(missing), 7, missing)

    def test_the_plain_git_diff_rule_is_not_asked_for(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        self.settings_with(home, clone, [])
        done = self.run_complete(home, clone, gitconfig)
        self.assertFalse(any(" diff *" in line for line in done.stdout.splitlines()), done.stdout)

    def test_old_relative_rules_in_the_allow_list_are_reported_as_stale(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(clone.as_posix())
        self.settings_with(home, clone, [*OLD_RULES, *allow], ask)
        settings = f"{self.bash_home(home)}/.claude/settings.json"
        expected = [f"STALE: allow rule: {rule} is in permissions.allow in {settings}. "
                    "Remove it: its relative path matches a script in any project." for rule in OLD_RULES]
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(done.stdout.splitlines(), ["OS: linux", *expected])

    def test_old_relative_rules_outside_the_allow_list_are_not_stale(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(clone.as_posix())
        self.settings_with(home, clone, allow, [*ask, *OLD_RULES], deny=OLD_RULES)
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(done.stdout.splitlines(), ["OS: linux", "All pieces are in place."])

    def test_stale_rules_are_reported_without_a_clone(self):
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude/settings.json").write_text(json.dumps({"permissions": {"allow": list(OLD_RULES)}}),
                                                    encoding="utf-8")
        self.stub("crontab", "exit 1")
        self.assertEqual(len(self.stale_lines(self.run_check(home))), len(OLD_RULES))

    def test_a_clone_path_with_a_space_or_a_star_gets_no_script_rule(self):
        home, _, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        names = ["K B"] if os.name == "nt" else ["K B", "K*B"]
        for name in names:
            with self.subTest(name=name):
                clone = self.make_clone_with_hooks_path(self.tmp / name)
                allow, ask = rules(clone.as_posix())
                self.settings_with(home, clone, allow, ask)
                missing = self.missing_lines(self.run_complete(home, clone, gitconfig))
                self.assertEqual(len(missing), 1, missing)
                self.assertTrue(missing[0].startswith("MISSING: allow rules: the clone path "), missing)
                self.assertNotIn("kb-search.sh *", missing[0])

    def test_a_clone_from_the_project_folder_or_a_relative_kb_dir_gets_no_path_rule(self):
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        project = self.make_clone_with_hooks_path(self.tmp / "project")
        self.stub("crontab", "exit 1")
        for extra in ({"CLAUDE_PROJECT_DIR": str(project)}, {"KB_DIR": "project"}):
            with self.subTest(extra=extra):
                missing = self.missing_lines(self.run_check(home, **extra))
                self.assertFalse(any("/_claude/tools/" in line or "git -C" in line for line in missing), missing)
                self.assertEqual(len([line for line in missing if line.startswith("MISSING: allow rules: ")]), 1, missing)

    def test_the_full_kb_dir_of_the_environment_wins_over_a_relative_kb_dir_in_the_settings(self):
        home, _, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        named = self.make_clone_with_hooks_path(self.tmp / "named")
        allow, ask = rules(named.as_posix())
        self.settings_with(home, "KB", allow, ask)
        missing = self.missing_lines(self.run_complete(home, named, gitconfig))
        self.assertEqual([line for line in missing if "allow rule" in line or "ask rule" in line], [], missing)

    def test_windows_branch_names_the_windows_path_in_the_path_rules(self):
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB)
        self.stub("crontab", 'echo "kb-sync.sh"')
        bash_env = self.use_windows_stubs()
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env))
        self.assertEqual(len(missing), 7, missing)
        self.assertTrue(all(f"git -C {self.WIN_KB} " in line or f" {self.WIN_KB}/_claude/tools/" in line for line in missing), missing)

    def test_windows_branch_ignores_the_case_of_the_drive_letter_in_rules(self):
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB, rule_dir=self.WIN_KB.replace("C:", "c:", 1))
        bash_env = self.use_windows_stubs()
        done = self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env)
        self.assertEqual(done.stdout.splitlines(), ["OS: windows", "All pieces are in place."])

    def test_windows_branch_reports_a_folder_name_with_a_different_case(self):
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB, rule_dir=self.WIN_KB.replace("KB", "kb"))
        bash_env = self.use_windows_stubs()
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env))
        self.assertEqual(len(missing), 7, missing)

    def test_windows_branch_accepts_an_ampersand_in_the_path_for_the_git_rules(self):
        self.WIN_KB = "C:/Users/A&B/KB"
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB, rule_dir=self.WIN_KB.replace("C:", "c:", 1))
        settings_file = home / ".claude/settings.json"
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        data["permissions"]["allow"] = [rule for rule in data["permissions"]["allow"] if " status *" not in rule]
        settings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        bash_env = self.use_windows_stubs()
        done = self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env)
        missing = self.missing_lines(done)
        settings = f"{self.bash_home(home)}/.claude/settings.json"
        self.assertEqual(len(missing), 2, missing)
        self.assertTrue(missing[0].startswith(f"MISSING: allow rules: the clone path {self.WIN_KB} has a character"), missing)
        self.assertEqual(missing[1], f"MISSING: allow rule: Bash(git -C {self.WIN_KB} status *) is not in permissions.allow in {settings}.")

    def test_missing_cron_line_is_reported(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "0 * * * * other.sh"')
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(self.missing_lines(done), [line for line in self.missing_lines(done)
                                                    if line.startswith("MISSING: sync timer:")])
        self.assertEqual(len(self.missing_lines(done)), 1)

    def test_windows_branch_with_all_pieces_in_place(self):
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB, rule_dir=self.WIN_KB)
        bash_env = self.use_windows_stubs()
        done = self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(), ["OS: windows", "All pieces are in place."])

    def test_windows_branch_names_the_windows_form_of_the_clone_path(self):
        home, clone, gitconfig = self.complete_home(rule_dir=self.WIN_KB)
        bash_env = self.use_windows_stubs()
        done = self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env)
        missing = self.missing_lines(done)
        self.assertEqual(len(missing), 1, missing)
        self.assertTrue(missing[0].startswith(f"MISSING: additionalDirectories: {self.WIN_KB} "), missing)

    def test_windows_branch_reports_an_empty_list_when_kb_dir_has_the_same_path(self):
        home, clone, gitconfig = self.complete_home()
        (self.tmp / "settings-kb/_claude").mkdir(parents=True)
        (self.tmp / "settings-kb/_claude/RULES.md").write_text("rules\n", encoding="utf-8")
        kb = (self.tmp / "settings-kb").as_posix()
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": kb},
            "permissions": {"allow": rules(kb)[0], "ask": rules(kb)[1], "additionalDirectories": []},
        }, indent=2), encoding="utf-8")
        bash_env = self.use_windows_stubs(windows_path=kb)
        done = self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env)
        missing = self.missing_lines(done)
        self.assertEqual(len([line for line in missing if line.startswith("MISSING: additionalDirectories:")]), 1, missing)

    def test_check_sees_a_write_to_the_global_git_config(self):
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("a\n", encoding="utf-8")
        before = self.snapshot(gitconfig)
        gitconfig.write_text("a\nb\n", encoding="utf-8")
        self.assertNotEqual(self.snapshot(gitconfig), before)

    def test_windows_branch_reports_a_missing_scheduled_task(self):
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB, rule_dir=self.WIN_KB)
        bash_env = self.use_windows_stubs(scheduled=False)
        done = self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env)
        missing = self.missing_lines(done)
        self.assertEqual(len(missing), 1, missing)
        self.assertTrue(missing[0].startswith("MISSING: sync timer:"), missing)

    def test_stale_kb_dir_value_in_settings_is_reported(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        settings = home / ".claude/settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        data["env"]["KB_DIR"] = "/nonexistent/KB"
        settings.write_text(json.dumps(data, indent=2), encoding="utf-8")
        done = self.run_complete(home, clone, gitconfig)
        missing = self.missing_lines(done)
        self.assertTrue(any(line.startswith("MISSING: KB_DIR: /nonexistent/KB has no _claude/RULES.md") for line in missing),
                        missing)

    def test_stale_kb_dir_value_with_backslashes_is_reported_with_slashes(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        settings = home / ".claude/settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        data["env"]["KB_DIR"] = "C:\\nonexistent\\KB"
        settings.write_text(json.dumps(data, indent=2), encoding="utf-8")
        done = self.run_complete(home, clone, gitconfig)
        missing = self.missing_lines(done)
        self.assertTrue(any(line.startswith("MISSING: KB_DIR: C:/nonexistent/KB has no _claude/RULES.md") for line in missing),
                        missing)

    @unittest.skipUnless(os.name == "nt", "the real uname and pwd -W of Git Bash exist only on Windows")
    def test_git_bash_takes_the_windows_branch_with_the_windows_form_of_the_path(self):
        (self.tmp / "bin/uname").unlink()
        self.stub("schtasks.exe", "exit 0")
        home, clone, gitconfig = self.complete_home()
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(done.stdout.splitlines(), ["OS: windows", "All pieces are in place."])

    def test_check_changes_nothing(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        empty_home = self.tmp / "empty"
        empty_home.mkdir()
        roots = (home, clone, gitconfig, empty_home)
        before = self.snapshot(*roots)
        self.run_complete(home, clone, gitconfig)
        self.run_check(empty_home)
        self.assertEqual(self.snapshot(*roots), before)


if __name__ == "__main__":
    unittest.main()
