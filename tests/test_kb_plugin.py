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
    "PreToolUse": "guard",
    "Stop": "stop",
    "SessionEnd": "session-end",
}


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
        for name in ("session-start", "subagent-start", "guard", "session-end"):
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
        for name in ("guard", "subagent-start", "stop", "session-end"):
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

    def test_stop_runs_the_sync_wrapper_if_changed(self):
        clone = self.make_clone(self.tmp / "clone")
        done = self.launch("stop", self.tmp, KB_DIR=str(clone))
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "sync:--if-changed"))

    def test_clone_in_a_child_folder_of_the_project_folder(self):
        project = self.tmp / "projects"
        self.make_clone(project / "KB")
        done = self.launch("subagent-start", project, stdin="x")
        self.assertEqual(done.stdout.strip(), "subagent-start:x")

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
                commands = [h["command"] for group in hooks[event] for h in group["hooks"]]
                self.assertEqual(commands, [f'bash "${{CLAUDE_PLUGIN_ROOT}}/scripts/kb-hook.sh" {name}'])

    def test_guard_matcher_names_only_documented_tools(self):
        group = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0]
        self.assertEqual(group["matcher"], "Edit|Write|NotebookEdit")


class CheckScriptTests(BashCase):
    def run_check(self, home):
        return subprocess.run([self.bash, str(CHECK)], cwd=self.tmp, env=self.env(HOME=str(home),
                              GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull),
                              capture_output=True, text=True, timeout=30)

    def test_empty_home_reports_the_missing_pieces_and_exits_0(self):
        home = self.tmp / "home"
        home.mkdir()
        done = self.run_check(home)
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = done.stdout.splitlines()
        self.assertTrue(lines[0].startswith("OS: "), lines)
        missing = [line for line in lines if line.startswith("MISSING: ")]
        for piece in ("KB_DIR:", "allow rule:", "import line: @.../_claude/CLAUDE.global.md",
                      "import line: @.../_claude/RULES.md", "KB root line:", "git-sync.syncEnabled:",
                      "git-sync.syncNewFiles:"):
            with self.subTest(piece=piece):
                self.assertTrue(any(line.startswith(f"MISSING: {piece}") for line in missing), missing)

    def test_complete_home_reports_no_missing_piece(self):
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        clone = self.make_clone_with_hooks_path(self.tmp / "KB")
        (home / ".claude/settings.json").write_text(json.dumps({
            "env": {"KB_DIR": str(clone)},
            "permissions": {"allow": ["Bash(bash _claude/tools/kb-search.sh *)"], "additionalDirectories": [str(clone)]},
        }), encoding="utf-8")
        (home / ".claude/CLAUDE.md").write_text(
            f"@{clone}/_claude/CLAUDE.global.md\n@{clone}/_claude/RULES.md\n\nKB root: `{clone}`\n", encoding="utf-8")
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("[git-sync]\n\tsyncEnabled = true\n\tsyncNewFiles = true\n[core]\n\tlongpaths = true\n",
                             encoding="utf-8")
        env = self.env(HOME=str(home), KB_DIR=str(clone), GIT_CONFIG_GLOBAL=str(gitconfig), GIT_CONFIG_SYSTEM=os.devnull)
        done = subprocess.run([self.bash, str(CHECK)], cwd=self.tmp, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        missing = [line for line in done.stdout.splitlines() if line.startswith("MISSING: ")]
        # The sync timer depends on the machine. Every other piece is in place.
        self.assertTrue(all(line.startswith("MISSING: sync timer:") for line in missing), missing)

    def make_clone_with_hooks_path(self, root):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        (root / "_claude").mkdir(parents=True)
        (root / "_claude/RULES.md").write_text("rules\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", "_claude/git-hooks"], check=True)
        return root


if __name__ == "__main__":
    unittest.main()
