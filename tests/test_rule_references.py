"""Tests for the references to the numbered rules of the skill engineering-discipline.

Many plugin files point at a rule by its number, for example "Rule 8 of `dev-essentials:engineering-discipline`".
These tests fail if a rule loses its number or its heading, or if create-tests stops pointing at the rule for useful tests.
"""
import re
import unittest

from support import REPO

HOME = REPO / "essentials" / "dev-essentials" / "skills" / "engineering-discipline" / "SKILL.md"
CREATE_TESTS = REPO / "dotnet" / "dotnet-backend-dev" / "skills" / "create-tests" / "SKILL.md"
SKILL = r"`dev-essentials:engineering-discipline`"
REFERENCE = re.compile(rf"{SKILL} Rule (\d+)|Rule (\d+) of {SKILL}")
HEADING = re.compile(r"^## Rule (\d+) — (.+)$", re.MULTILINE)


def rule_titles():
    """The title of each numbered rule of the home skill, by its number."""
    return {int(number): title for number, title in HEADING.findall(HOME.read_text(encoding="utf-8"))}


def references(text):
    """The rule numbers that a text points at."""
    return [int(a or b) for a, b in REFERENCE.findall(text)]


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


if __name__ == "__main__":
    unittest.main()
