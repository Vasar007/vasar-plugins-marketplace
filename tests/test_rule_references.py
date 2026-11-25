"""Tests for the references to the numbered rules of the skill engineering-discipline.

Many plugin files point at a rule by its number, for example "Rule 8 of `dev-essentials:engineering-discipline`".
A table row whose first cell is that skill points at each rule that it names.
These tests fail if a rule loses its number or its heading, or if create-tests stops pointing at the rule for useful tests.
"""
import re
import unittest

from support import REPO

HOME = REPO / "essentials" / "dev-essentials" / "skills" / "engineering-discipline" / "SKILL.md"
CREATE_TESTS = REPO / "dotnet" / "dotnet-backend-dev" / "skills" / "create-tests" / "SKILL.md"
SKILL = r"`dev-essentials:engineering-discipline`"
REFERENCE = re.compile(rf"{SKILL} Rule (\d+)|Rule (\d+) of {SKILL}")
TABLE_ROW = re.compile(rf"^\|\s*{SKILL}\s*\|(.*)$", re.MULTILINE)
HEADING = re.compile(r"^## Rule (\d+) — (.+)$", re.MULTILINE)


def rule_titles():
    """The title of each numbered rule of the home skill, by its number."""
    return {int(number): title for number, title in HEADING.findall(HOME.read_text(encoding="utf-8"))}


def references(text):
    """The rule numbers that a text points at."""
    in_rows = [int(n) for row in TABLE_ROW.findall(text) for n in re.findall(r"\bRule (\d+)\b", row)]
    return [int(a or b) for a, b in REFERENCE.findall(text)] + in_rows


class RuleReferenceTests(unittest.TestCase):
    def test_each_reference_names_an_existing_rule(self):
        titles = rule_titles()
        files = [p for base in ("essentials", "dotnet", "knowledge") for p in (REPO / base).rglob("*.md")]
        found = 0
        for path in files:
            for number in references(path.read_text(encoding="utf-8")):
                found += 1
                with self.subTest(path=path.relative_to(REPO).as_posix(), rule=number):
                    self.assertIn(number, titles)
        self.assertGreater(found, 0, "No file points at a rule of engineering-discipline.")

    def test_create_tests_points_at_the_rule_for_useful_tests(self):
        titles = rule_titles()
        text = CREATE_TESTS.read_text(encoding="utf-8")
        section = re.search(r"^## Useful Tests\n(.*?)^## ", text, re.S | re.M)
        self.assertIsNotNone(section, "create-tests has no section Useful Tests.")
        numbers = references(section.group(1))
        self.assertTrue(numbers, "The section Useful Tests of create-tests points at no rule of engineering-discipline.")
        for number in numbers:
            with self.subTest(rule=number):
                self.assertIn("useful tests", titles.get(number, "").lower())


PLUGIN_ROOT_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)")
NOTES_RULE = "references/notes-root.md"
DEV_ESSENTIALS = REPO / "essentials" / "dev-essentials"


def plugin_folder(path):
    """The nearest parent folder of a file that holds .claude-plugin/plugin.json."""
    for parent in path.parents:
        if (parent / ".claude-plugin" / "plugin.json").is_file():
            return parent
    return None


def dev_essentials_units():
    """Each command file and each skill folder of dev-essentials, as a list of its Markdown files."""
    units = [[path] for path in sorted((DEV_ESSENTIALS / "commands").glob("*.md"))]
    for folder in sorted(path for path in (DEV_ESSENTIALS / "skills").iterdir() if path.is_dir()):
        units.append(sorted(folder.rglob("*.md")))
    return units


class NotesFolderRuleTests(unittest.TestCase):
    def test_each_plugin_root_path_names_a_file_of_its_plugin(self):
        found = 0
        for base in ("essentials", "dotnet", "knowledge"):
            for path in (REPO / base).rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                for match in PLUGIN_ROOT_PATH.findall(text):
                    found += 1
                    relative = match.rstrip(".")
                    with self.subTest(path=path.relative_to(REPO).as_posix(), pointer=relative):
                        folder = plugin_folder(path)
                        self.assertIsNotNone(folder, "The file is in no plugin.")
                        self.assertTrue((folder / relative).exists(), f"{relative} is not in the plugin.")
        self.assertGreater(found, 0, "No file uses a path below CLAUDE_PLUGIN_ROOT.")

    def test_each_unit_with_a_notes_folder_points_at_the_rule(self):
        checked = 0
        for files in dev_essentials_units():
            texts = [path.read_text(encoding="utf-8") for path in files]
            if not any("notes folder" in text.lower() for text in texts):
                continue
            checked += 1
            with self.subTest(unit=files[0].relative_to(REPO).as_posix()):
                self.assertTrue(any(NOTES_RULE in text for text in texts), f"No file of the unit names {NOTES_RULE}.")
        self.assertGreater(checked, 0, "No unit of dev-essentials names a notes folder.")


if __name__ == "__main__":
    unittest.main()
