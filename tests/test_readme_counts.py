"""Keeps the README files free of counts of hooks, skills, agents, and commands.

Such a count goes stale when a plugin adds or removes one of these units.
Write "the hooks" instead, and point to the folder or the file that holds them.
"""
import re
import unittest

from support import REPO, tracked_markdown_files

NUMBER = r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
UNIT_COUNT = re.compile(
    r"\b" + NUMBER + r"\s+(?:[\w`-]+\s+)?(?:hook entries|hooks?|skills?|agent types|agents?|commands?)\b",
    re.IGNORECASE)
# Counts that are fine, as (README path, hit text) -> reason: a fixed limit, or a count with its list next to it.
ALLOWED = {}


def count_hits(text):
    """Each count of units in the text, as (line number, hit text)."""
    return [(number, match.group(0)) for number, line in enumerate(text.splitlines(), 1)
            for match in UNIT_COUNT.finditer(line)]


def readme_files():
    return [p for p in tracked_markdown_files() if p.split("/")[-1] == "README.md"]


class CountHitsTests(unittest.TestCase):
    def test_finds_a_count_of_units(self):
        for line, hit in (("The plugin adds five hooks.", "five hooks"),
                          ("The plugin adds six hook entries.", "six hook entries"),
                          ("The plugin also adds three skills:", "three skills"),
                          ("Pass it to the three plugin agents.", "three plugin agents"),
                          ("It ships 2 commands.", "2 commands"),
                          ("Dispatch one of the Three agent types.", "Three agent types")):
            with self.subTest(line=line):
                self.assertEqual(count_hits(f"Intro.\n{line}\n"), [(2, hit)])

    def test_allows_text_with_no_count_of_units(self):
        text = ("The plugin adds the hooks in `hooks/hooks.json`.\n"
                "Skip this step in two cases.\n"
                "It also includes the three `git -C <KB root>` allow rules.\n"
                "It needs simple-english 2.1.1 and v2 skills.\n")
        self.assertEqual(count_hits(text), [])


class ReadmeTextTest(unittest.TestCase):
    def test_no_count_of_units(self):
        files = readme_files()
        self.assertIn("README.md", files)
        hits = [(path, number, hit) for path in files
                for number, hit in count_hits((REPO / path).read_text(encoding="utf-8"))]
        failures = [f"{path}:{number}: {hit}" for path, number, hit in hits if (path, hit) not in ALLOWED]
        self.assertEqual(failures, [], "Write 'the hooks' (or the skills, the agents, the commands), and point to "
                                       "the folder or the file that holds them. A fixed limit or a count with its "
                                       "list next to it can go into ALLOWED, with a reason.")
        stale = sorted(set(ALLOWED) - {(path, hit) for path, _, hit in hits})
        self.assertEqual(stale, [], "Remove these ALLOWED entries. The README has no such count now.")


if __name__ == "__main__":
    unittest.main()
