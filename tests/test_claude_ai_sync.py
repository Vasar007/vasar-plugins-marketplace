"""Checks for the problems that claude.ai reports when it syncs the marketplace. docs/authoring.md lists the rules.

The sync strips each top-level key of plugin.json that it does not know, also a documented one such as "icon".
It removes angle brackets from a description. It skips a plugin with a nested .claude-plugin or a top-level bin/ folder.
"""
import json
import struct
import subprocess
import unittest
from pathlib import PurePosixPath

from support import REPO

PLUGIN_GLOB = "*/*/.claude-plugin/plugin.json"
ENTITY_GLOBS = ("skills/*/SKILL.md", "agents/*.md", "commands/*.md")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# The keys that the claude.ai sync of release 4.11.1 took with no warning. The sync documents no list of its own.
# A new key goes here in the PR that adds it, and the owner reads the next sync page (docs/authoring.md).
SYNC_PLUGIN_KEYS = {"name", "version", "description", "author", "repository", "keywords", "dependencies", "userConfig"}
SYNC_MARKETPLACE_KEYS = {"name", "description", "owner", "plugins", "renames"}
SYNC_ENTRY_KEYS = {"name", "source", "description"}


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


def unknown_keys(data, known):
    """The keys of a JSON object that are not in the known set, sorted."""
    return sorted(set(data) - known)


class UnknownKeysTests(unittest.TestCase):
    def test_lists_only_the_keys_outside_the_set(self):
        self.assertEqual(unknown_keys({"name": "a", "icon": "x", "$schema": "y"}, {"name"}), ["$schema", "icon"])
        self.assertEqual(unknown_keys({"name": "a"}, {"name", "version"}), [])


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


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

    def test_plugin_manifests_use_only_the_keys_that_the_sync_takes(self):
        roots = plugin_roots()
        self.assertTrue(roots, f"No plugin manifest matches {PLUGIN_GLOB}.")
        failures = {root.relative_to(REPO).as_posix(): unknown_keys(load_json(root / ".claude-plugin" / "plugin.json"),
                                                                    SYNC_PLUGIN_KEYS) for root in roots}
        failures = {root: keys for root, keys in failures.items() if keys}
        self.assertEqual(failures, {}, "The claude.ai sync strips these plugin.json keys and warns, also documented "
                                       "keys such as \"$schema\" and \"icon\". Remove them, or see docs/authoring.md.")

    def test_the_marketplace_uses_only_the_keys_that_the_sync_takes(self):
        marketplace = load_json(REPO / ".claude-plugin" / "marketplace.json")
        failures = unknown_keys(marketplace, SYNC_MARKETPLACE_KEYS)
        failures += [f"plugins[{index}].{key}" for index, entry in enumerate(marketplace["plugins"])
                     for key in unknown_keys(entry, SYNC_ENTRY_KEYS)]
        self.assertEqual(failures, [], "No claude.ai sync took these marketplace.json keys yet. See docs/authoring.md.")

    def test_plugin_sources_start_with_dot_slash(self):
        marketplace = load_json(REPO / ".claude-plugin" / "marketplace.json")
        failures = [entry["name"] for entry in marketplace["plugins"] if not str(entry["source"]).startswith("./")]
        self.assertEqual(failures, [], "The claude.ai sync takes a relative plugin source only when it starts with ./.")

    def test_plugins_have_no_top_level_bin_folder(self):
        failures = [root.relative_to(REPO).as_posix() for root in plugin_roots()
                    if any(path.startswith("bin/") for path in tracked_files(root))]
        self.assertEqual(failures, [], "claude.ai rejects a plugin with a top-level bin/ folder. Move the files to scripts/.")

    def test_descriptions_have_no_angle_brackets(self):
        failures = []
        for root in plugin_roots():
            for pattern in ENTITY_GLOBS:
                for path in sorted(root.glob(pattern)):
                    description = frontmatter_description(path.read_text(encoding="utf-8"))
                    if description and ("<" in description or ">" in description.lstrip(">")):
                        failures.append(str(path.relative_to(REPO)))
        self.assertEqual(failures, [], "Remove the angle brackets from the description. claude.ai reads them as XML tags.")


class PluginIconTest(unittest.TestCase):
    """Each plugin has the icon file that CLAUDE.md asks for: a square PNG of 512 to 2048 px, under 2 MB.

    claude plugin validate finds assets/icon.png by its path. So plugin.json does not name it.
    """

    def test_each_plugin_has_a_square_png_icon_file(self):
        roots = plugin_roots()
        self.assertTrue(roots, f"No plugin manifest matches {PLUGIN_GLOB}.")
        for root in roots:
            with self.subTest(plugin=root.relative_to(REPO).as_posix()):
                icon = root / "assets" / "icon.png"
                self.assertTrue(icon.is_file(), f"{icon} is missing.")
                data = icon.read_bytes()
                self.assertEqual((data[:8], data[12:16]), (PNG_SIGNATURE, b"IHDR"))
                width, height = struct.unpack(">II", data[16:24])
                self.assertEqual(width, height)
                self.assertTrue(512 <= width <= 2048, f"The icon is {width} px wide.")
                self.assertLess(len(data), 2 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
