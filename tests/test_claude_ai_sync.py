"""Checks for the problems that claude.ai reports as warnings when it syncs the marketplace.

The claude.ai sync strips an unknown top-level key of plugin.json, for example "$schema".
It also reads text in angle brackets in a description as an XML tag, and removes the brackets.
It skips a plugin that holds a .claude-plugin folder below its root.
"""
import json
import subprocess
import unittest
from pathlib import PurePosixPath

from support import REPO

PLUGIN_GLOB = "*/*/.claude-plugin/plugin.json"
ENTITY_GLOBS = ("skills/*/SKILL.md", "agents/*.md", "commands/*.md")


def plugin_roots():
    return sorted(path.parent.parent for path in REPO.glob(PLUGIN_GLOB))


def frontmatter_description(text):
    """The description value of a Markdown frontmatter block, with its indented continuation lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    value = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if value is not None:
            if line.startswith((" ", "\t")):
                value += " " + line.strip()
                continue
            break
        if line.startswith("description:"):
            value = line[len("description:"):].strip()
    return value


class FrontmatterDescriptionTests(unittest.TestCase):
    def test_reads_a_one_line_and_a_folded_description(self):
        self.assertEqual(frontmatter_description("---\nname: a\ndescription: One line.\n---\n"), "One line.")
        self.assertEqual(frontmatter_description("---\ndescription: >\n  Two\n  lines.\nname: a\n---\n"), "> Two lines.")
        self.assertIsNone(frontmatter_description("# No frontmatter\n"))


def tracked_files(root):
    """The tracked files of one plugin, as POSIX paths relative to the plugin root."""
    prefix = root.relative_to(REPO).as_posix()
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--", prefix],
                         capture_output=True, text=True, check=True).stdout
    return [PurePosixPath(p).relative_to(prefix).as_posix() for p in out.split("\0") if p]


def nested_manifest_paths(paths):
    """The paths in a .claude-plugin folder below the plugin root. Each path is relative to the plugin root."""
    return sorted(p for p in paths if ".claude-plugin" in PurePosixPath(p).parts[1:])


class NestedManifestPathsTests(unittest.TestCase):
    def test_the_manifest_of_the_root_passes(self):
        self.assertEqual(nested_manifest_paths([".claude-plugin/plugin.json", "skills/a/SKILL.md"]), [])

    def test_a_nested_manifest_folder_fails(self):
        paths = ["eval-stubs/github/.claude-plugin/plugin.json", "x/y/.claude-plugin/marketplace.json"]
        self.assertEqual(nested_manifest_paths(paths), sorted(paths))

    def test_similar_names_pass(self):
        self.assertEqual(nested_manifest_paths([".codex-plugin/plugin.json", "docs/claude-plugin.md", "a/plugin.json"]), [])


class ClaudeAiSyncTest(unittest.TestCase):
    def test_plugins_have_no_nested_manifest_folder(self):
        failures = [f"{root.relative_to(REPO).as_posix()}/{path}"
                    for root in plugin_roots() for path in nested_manifest_paths(tracked_files(root))]
        self.assertEqual(failures, [], "Move these files out of the plugin folder, for example to tests/evals/stubs/. "
                                       "The claude.ai sync skips a plugin with a .claude-plugin folder below its root.")

    def test_the_glob_finds_every_marketplace_plugin(self):
        marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        sources = {PurePosixPath(plugin["source"]).as_posix() for plugin in marketplace["plugins"]}
        roots = {root.relative_to(REPO).as_posix() for root in plugin_roots()}
        self.assertEqual(roots, sources, f"Every marketplace source must match {PLUGIN_GLOB}, or the tests skip it.")

    def test_plugin_manifests_have_no_schema_key(self):
        roots = plugin_roots()
        self.assertTrue(roots, f"No plugin manifest matches {PLUGIN_GLOB}.")
        failures = [str(root.relative_to(REPO)) for root in roots
                    if "$schema" in json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))]
        self.assertEqual(failures, [], "Remove \"$schema\" from plugin.json. The claude.ai sync strips it and warns.")

    def test_descriptions_have_no_angle_brackets(self):
        failures = []
        for root in plugin_roots():
            for pattern in ENTITY_GLOBS:
                for path in sorted(root.glob(pattern)):
                    description = frontmatter_description(path.read_text(encoding="utf-8"))
                    if description and ("<" in description or ">" in description.lstrip(">")):
                        failures.append(str(path.relative_to(REPO)))
        self.assertEqual(failures, [], "Remove the angle brackets from the description. claude.ai reads them as XML tags.")


if __name__ == "__main__":
    unittest.main()
