"""Keeps the plugin files free of lines that ask the model to write out its reasoning.

Such a line can make a model refuse the task, on every model that a skill can run on.
"""
import re
import unittest

from support import REPO

PLUGIN_GLOB = "*/*/.claude-plugin/plugin.json"
REASONING_EXTRACTION = re.compile(
    r"show (?:me )?your (?:reasoning|thinking)"
    r"|explain your (?:reasoning|thinking)"
    r"|walk me through your (?:reasoning|thinking)"
    r"|write out your (?:reasoning|thinking)"
    r"|think(?:ing)? out loud"
    r"|chain[- ]of[- ]thought",
    re.IGNORECASE)


def phrase_hits(text):
    """Each line of the text that has a reasoning-extraction phrase, as (line number, phrase)."""
    return [(number, match.group(0)) for number, line in enumerate(text.splitlines(), 1)
            for match in REASONING_EXTRACTION.finditer(line)]


class PhraseHitsTests(unittest.TestCase):
    def test_finds_each_phrase(self):
        for line in ("Show your reasoning.", "Explain your thinking step by step.", "Think out loud first.",
                     "Use chain-of-thought.", "Use a chain of thought.", "Walk me through your reasoning.",
                     "Write out your thinking."):
            with self.subTest(line=line):
                self.assertEqual(len(phrase_hits(f"Intro.\n{line}\n")), 1)
                self.assertEqual(phrase_hits(f"Intro.\n{line}\n")[0][0], 2)

    def test_allows_a_short_explanation_or_a_summary(self):
        text = "Give a short explanation of the answer.\nSummarize the actions you took.\nBase your reasoning on the docs.\n"
        self.assertEqual(phrase_hits(text), [])


class PluginTextTest(unittest.TestCase):
    def test_no_reasoning_extraction_phrases(self):
        roots = sorted(path.parent.parent for path in REPO.glob(PLUGIN_GLOB))
        self.assertTrue(roots, f"No plugin manifest matches {PLUGIN_GLOB}.")
        failures = [f"{path.relative_to(REPO).as_posix()}:{number}: {phrase}"
                    for root in roots for path in sorted(root.rglob("*.md"))
                    for number, phrase in phrase_hits(path.read_text(encoding="utf-8"))]
        self.assertEqual(failures, [], "Ask for a short explanation or a summary of the actions instead. "
                                       "A request to write out the reasoning can make the model refuse.")


if __name__ == "__main__":
    unittest.main()
