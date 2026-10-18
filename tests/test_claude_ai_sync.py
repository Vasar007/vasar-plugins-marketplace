"""Checks for the problems that claude.ai reports as warnings when it syncs the marketplace.

The claude.ai sync strips an unknown top-level key of plugin.json, for example "$schema".
It also reads text in angle brackets in a description as an XML tag, and removes the brackets.
"""
import json
import unittest

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


class ClaudeAiSyncTest(unittest.TestCase):
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
