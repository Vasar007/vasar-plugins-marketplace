"""Tests for the scripts of the kb plugin: the hook launcher and the setup check.

Each test builds a fake KB clone with stub hook scripts in a temporary folder and runs the real launcher against it.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO, tool_missing

PLUGIN = REPO / "knowledge/kb"
LAUNCHER = PLUGIN / "scripts/kb-hook.sh"
CHECK = PLUGIN / "skills/setup/check.sh"
NO_CLONE_LINE = "KB plugin: no KB clone found. Set KB_DIR with /kb:setup."
EVENTS = {
    "SessionStart": "session-start",
    "SubagentStart": "subagent-start",
    "PreToolUse": ["guard", "allow-read"],
    "Stop": "stop",
    "SessionEnd": "session-end",
}
TEXT_CHECK_RULES = (
    "Bash(python3 -B _claude/tools/ste-check.py *)",
    "Bash(python3 -B _claude/tools/md-check.py *)",
)
GIT_SUBCOMMANDS = ("status", "log", "diff", "show")


def rules(kb_path):
    """The allow list and the ask list that make every rule piece of check.sh complete for this KB path."""
    allow = ["Bash(bash _claude/tools/kb-search.sh *)", *TEXT_CHECK_RULES,
             *(f"Bash(git -C {kb_path} {sub} *)" for sub in GIT_SUBCOMMANDS)]
    return allow, [f"Bash(git -C {kb_path} * --output*)"]


class BashCase(unittest.TestCase):
    def setUp(self):
        self.bash = shutil.which("bash")
        if self.bash is None:
            tool_missing(self, "bash not found")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in ("KB_DIR", "CLAUDE_PROJECT_DIR")}
        env.update(extra)
        return env

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
        return subprocess.run([self.bash, str(LAUNCHER), name], cwd=cwd, env=self.env(**env), input=stdin,
                              capture_output=True, text=True, timeout=30)


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

    def test_clone_in_a_child_folder_of_the_project_folder(self):
        project = self.tmp / "projects"
        self.make_clone(project / "KB")
        done = self.launch("subagent-start", project, stdin="x")
        self.assertEqual(done.stdout.strip(), "subagent-start:x")

    def test_claude_project_dir_names_the_folder_to_search(self):
        project = self.tmp / "project"
        self.make_clone(project / "KB")
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        done = self.launch("subagent-start", elsewhere, stdin="x", CLAUDE_PROJECT_DIR=str(project))
        self.assertEqual(done.stdout.strip(), "subagent-start:x")

    def test_kb_dir_wins_over_a_clone_in_the_project_folder(self):
        project = self.tmp / "project"
        self.make_clone(project / "KB")
        chosen = self.make_clone(self.tmp / "chosen")
        (chosen / "_claude/hooks/subagent-start.sh").write_text('echo chosen\n', encoding="utf-8")
        done = self.launch("subagent-start", project, KB_DIR=str(chosen), CLAUDE_PROJECT_DIR=str(project))
        self.assertEqual(done.stdout.strip(), "chosen")

    def test_project_folder_that_is_the_clone_wins_over_a_child_clone(self):
        project = self.make_clone(self.tmp / "project")
        child = self.make_clone(project / "KB")
        (child / "_claude/hooks/subagent-start.sh").write_text('echo child\n', encoding="utf-8")
        done = self.launch("subagent-start", self.tmp, stdin="x", CLAUDE_PROJECT_DIR=str(project))
        self.assertEqual(done.stdout.strip(), "subagent-start:x")

    def test_paths_with_spaces(self):
        project = self.tmp / "my proj"
        self.make_clone(project / "K B")
        done = self.launch("subagent-start", self.tmp, stdin="x", CLAUDE_PROJECT_DIR=str(project))
        self.assertEqual(done.stdout.strip(), "subagent-start:x")
        done = self.launch("subagent-start", self.tmp, stdin="y", KB_DIR=str(project / "K B"))
        self.assertEqual(done.stdout.strip(), "subagent-start:y")

    def test_missing_hook_script_exits_0_and_prints_one_line_at_session_start_only(self):
        clone = self.make_clone(self.tmp / "clone")
        (clone / "_claude/hooks/session-start.sh").unlink()
        (clone / "_claude/hooks/session-end.sh").unlink()
        (clone / "_claude/kb-sync.sh").unlink()
        done = self.launch("session-start", self.tmp, KB_DIR=str(clone))
        self.assertEqual((done.returncode, len(done.stdout.splitlines()), done.stderr), (0, 1, ""))
        for name in ("session-end", "stop"):
            with self.subTest(hook=name):
                done = self.launch(name, self.tmp, KB_DIR=str(clone))
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_kb_dir_without_rules_file_is_ignored(self):
        (self.tmp / "empty").mkdir()
        done = self.launch("session-start", self.tmp, KB_DIR=str(self.tmp / "empty"))
        self.assertEqual(done.stdout.splitlines(), [NO_CLONE_LINE])


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
        return subprocess.run([self.bash, str(CHECK)], cwd=self.tmp, env=self.check_env(home, **extra),
                              capture_output=True, text=True, timeout=30)

    def make_clone_with_hooks_path(self, root):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        (root / "_claude").mkdir(parents=True)
        (root / "_claude/RULES.md").write_text("rules\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", "_claude/git-hooks"], check=True)
        return root

    def complete_home(self, additional_dir=None, rule_dir=None):
        """A home folder with every piece in place. Returns the home folder, the clone, and the git config file."""
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        clone = self.make_clone_with_hooks_path(self.tmp / "KB")
        allow, ask = rules(rule_dir or str(clone))
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": str(clone)},
            "permissions": {"allow": allow, "ask": ask,
                            "additionalDirectories": [additional_dir or str(clone)]},
        }), encoding="utf-8")
        (home / ".claude/CLAUDE.md").write_text(
            f"@{clone}/_claude/CLAUDE.global.md\n@{clone}/_claude/RULES.md\n\nKB root: `{clone}`\n", encoding="utf-8")
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("[git-sync]\n\tsyncEnabled = true\n\tsyncNewFiles = true\n[core]\n\tlongpaths = true\n",
                             encoding="utf-8")
        return home, clone, gitconfig

    def use_windows_stubs(self, scheduled=True):
        self.stub("uname", "echo MINGW64_NT-10.0")
        self.stub("schtasks.exe", "exit 0" if scheduled else "exit 1")
        # In Git Bash, "pwd -W" prints the Windows form of the current folder.
        bash_env = self.tmp / "bash_env.sh"
        bash_env.write_text(f'pwd() {{ if [ "$1" = -W ]; then echo "{self.WIN_KB}"; else builtin pwd "$@"; fi; }}\n',
                            encoding="utf-8")
        return str(bash_env)

    def run_complete(self, home, clone, gitconfig, **extra):
        return subprocess.run([self.bash, str(CHECK)], cwd=self.tmp, capture_output=True, text=True, timeout=30,
                              env=self.check_env(home, **{"KB_DIR": str(clone), "GIT_CONFIG_GLOBAL": str(gitconfig), **extra}))

    @staticmethod
    def missing_lines(done):
        return [line for line in done.stdout.splitlines() if line.startswith("MISSING: ")]

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
        lines = done.stdout.splitlines()
        self.assertTrue(lines[0].startswith("OS: "), lines)
        missing = self.missing_lines(done)
        for piece in ("KB clone:", "KB_DIR:", "allow rule:", "import line: @.../_claude/CLAUDE.global.md",
                      "import line: @.../_claude/RULES.md", "KB root line:", "sync timer:", "git-sync.syncEnabled:",
                      "git-sync.syncNewFiles:"):
            with self.subTest(piece=piece):
                self.assertTrue(any(line.startswith(f"MISSING: {piece}") for line in missing), missing)
        self.assertNotIn("All pieces are in place.", lines)
        for rule in TEXT_CHECK_RULES:
            self.assertIn(f"MISSING: allow rule: {rule} is not in permissions.allow in {home}/.claude/settings.json.", missing)
        self.assertFalse(any("git -C" in line for line in missing), missing)

    def test_complete_home_on_linux_reports_all_pieces_in_place(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "*/5 * * * * bash /x/kb-sync.sh"')
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(), ["OS: linux", "All pieces are in place."])

    def test_missing_rules_are_reported_in_order_and_pin_the_rule_set(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": str(clone)},
            "permissions": {"allow": ["Bash(bash _claude/tools/kb-search.sh *)"], "additionalDirectories": [str(clone)]},
        }), encoding="utf-8")
        settings = f"{home}/.claude/settings.json"
        expected = [f"MISSING: allow rule: {rule} is not in permissions.allow in {settings}." for rule in TEXT_CHECK_RULES]
        expected += [f"MISSING: allow rule: Bash(git -C {clone} {sub} *) is not in permissions.allow in {settings}."
                     for sub in GIT_SUBCOMMANDS]
        expected.append(f"MISSING: ask rule: Bash(git -C {clone} * --output*) is not in permissions.ask in {settings}.")
        done = self.run_complete(home, clone, gitconfig)
        self.assertEqual(self.missing_lines(done), expected)

    def test_ask_rule_in_the_allow_list_is_reported_once(self):
        home, clone, gitconfig = self.complete_home()
        self.stub("crontab", 'echo "kb-sync.sh"')
        allow, ask = rules(str(clone))
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": str(clone)},
            "permissions": {"allow": allow + ask, "additionalDirectories": [str(clone)]},
        }), encoding="utf-8")
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig))
        self.assertEqual(len(missing), 1, missing)
        self.assertTrue(missing[0].startswith("MISSING: ask rule:"), missing)

    def test_windows_branch_names_the_windows_path_in_the_git_rules(self):
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB)
        self.stub("crontab", 'echo "kb-sync.sh"')
        bash_env = self.use_windows_stubs()
        missing = self.missing_lines(self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env))
        self.assertEqual(len(missing), 5, missing)
        self.assertTrue(all(f"git -C {self.WIN_KB} " in line for line in missing), missing)

    def test_windows_branch_ignores_the_case_of_the_drive_letter_in_rules(self):
        home, clone, gitconfig = self.complete_home(additional_dir=self.WIN_KB, rule_dir=self.WIN_KB.replace("C:", "c:", 1))
        bash_env = self.use_windows_stubs()
        done = self.run_complete(home, clone, gitconfig, BASH_ENV=bash_env)
        self.assertEqual(done.stdout.splitlines(), ["OS: windows", "All pieces are in place."])

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
        (self.tmp / self.WIN_KB / "_claude").mkdir(parents=True)
        (self.tmp / self.WIN_KB / "_claude/RULES.md").write_text("rules\n", encoding="utf-8")
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": self.WIN_KB},
            "permissions": {"allow": rules(self.WIN_KB)[0], "ask": rules(self.WIN_KB)[1], "additionalDirectories": []},
        }), encoding="utf-8")
        bash_env = self.use_windows_stubs()
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
        settings.write_text(settings.read_text(encoding="utf-8").replace(str(clone), "/nonexistent/KB", 1),
                            encoding="utf-8")
        done = self.run_complete(home, clone, gitconfig)
        missing = self.missing_lines(done)
        self.assertTrue(any(line.startswith("MISSING: KB_DIR: /nonexistent/KB has no _claude/RULES.md") for line in missing),
                        missing)

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
