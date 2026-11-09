"""Keeps the README files and the files in docs/ free of counts of hooks, skills, agents, and commands.

Such a count goes stale when a plugin adds or removes one of these units.
Write "the hooks" instead, and point to the folder or the file that holds them.
"""
import re
import unittest

from support import REPO, tracked_markdown_files

NUMBER = r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
# Up to two words between the number and the unit. A function word or a few verbs end the match, so that
# "step 3 of this skill" and "Rule 7 names the agents" are not counts.
MODIFIER = r"(?:(?!(?:the|of|and|or|in|this|that|a|an|to|for|on|with|is|are|by|from|at|as|per|about|names|hits)\b)[\w`-]+\s+){0,2}"
UNIT_COUNT = re.compile(
    r"(?<![\w.])" + NUMBER + r"\s+" + MODIFIER + r"(?:hook entries|hooks?|skills?|agent types|agents?|commands?)\b",
    re.IGNORECASE)
# Counts that are fine, as (README path, stripped text of the line) -> reason: a fixed limit, or a count with its
# list next to it. An entry covers only lines with exactly that text, so a hit on a line with other text is still reported.
ALLOWED = {}


def count_hits(text):
    """Each count of units in the text, as (line number, hit text, stripped line text)."""
    return [(number, match.group(0), line.strip()) for number, line in enumerate(text.splitlines(), 1)
            for match in UNIT_COUNT.finditer(line)]


def check_hits(hits, allowed):
    """Split hits, as (path, line number, hit text, line text), into the failures and the stale allowed keys."""
    failures = [f"{path}:{number}: {hit}" for path, number, hit, line in hits if (path, line) not in allowed]
    stale = sorted(set(allowed) - {(path, line) for path, _, _, line in hits})
    return failures, stale


def readme_files():
    """The tracked README.md files and the .md files in docs/, which hold the text that moved out of README.md."""
    return [p for p in tracked_markdown_files() if p.split("/")[-1] == "README.md" or p.startswith("docs/")]


class CountHitsTests(unittest.TestCase):
    def test_finds_a_count_of_units(self):
        for line, hit in (("The plugin adds five hooks.", "five hooks"),
                          ("The plugin adds six hook entries.", "six hook entries"),
                          ("The plugin also adds three skills:", "three skills"),
                          ("Pass it to the three plugin agents.", "three plugin agents"),
                          ("Pass it to the three bug hunt agents.", "three bug hunt agents"),
                          ("It ships 2 commands.", "2 commands"),
                          ("Dispatch one of the Three agent types.", "Three agent types")):
            with self.subTest(line=line):
                self.assertEqual(count_hits(f"Intro.\n{line}\n"), [(2, hit, line)])

    def test_allows_text_with_no_count_of_units(self):
        text = ("The plugin adds the hooks in `hooks/hooks.json`.\n"
                "Skip this step in two cases.\n"
                "It also includes the three `git -C <KB root>` allow rules.\n"
                "It needs simple-english 2.1.1 and v2 skills.\n"
                "See step 3 of this skill.\n"
                "Rule 7 names the agents.\n"
                "See section 4 on hooks.\n"
                "Check 5 is about hooks.\n"
                "Add one skill.\n"
                "This follows the twelve-factor way.\n")
        self.assertEqual(count_hits(text), [])


class CheckHitsTests(unittest.TestCase):
    def test_allowed_line_does_not_hide_a_later_identical_hit(self):
        text = "Allowed: it ships five hooks.\nOther: it ships five hooks.\nAllowed: it ships five hooks.\n"
        hits = [("README.md", number, hit, line) for number, hit, line in count_hits(text)]
        failures, stale = check_hits(hits, {("README.md", "Other: it ships five hooks."): "x"})
        self.assertEqual(failures, ["README.md:1: five hooks", "README.md:3: five hooks"])
        self.assertEqual(stale, [])

    def test_reports_a_stale_allowed_entry(self):
        failures, stale = check_hits([], {("README.md", "It ships five hooks."): "x"})
        self.assertEqual((failures, stale), ([], [("README.md", "It ships five hooks.")]))


class ReadmeTextTest(unittest.TestCase):
    def test_no_count_of_units(self):
        files = readme_files()
        self.assertIn("README.md", files)
        self.assertIn("docs/authoring.md", files)
        hits = [(path, number, hit, line) for path in files
                for number, hit, line in count_hits((REPO / path).read_text(encoding="utf-8"))]
        failures, stale = check_hits(hits, ALLOWED)
        self.assertEqual(failures, [], "Write 'the hooks' (or the skills, the agents, the commands), and point to "
                                       "the folder or the file that holds them. A fixed limit or a count with its "
                                       "list next to it can go into ALLOWED, with a reason.")
        self.assertEqual(stale, [], "Remove these ALLOWED entries. The README has no such count now.")


if __name__ == "__main__":
    unittest.main()
