"""Tests for the text of the work modes: the skill work-modes and the gated units that point at it (issue #267).

The skill work-modes is the one place that defines the option --mode, the three modes, the hard stops, and the
old spellings. These tests pin its main sentences, the pointer and the gate table header of each gated unit, and
the absence of the old mode flags and of the old copies of the common block in every other file.
"""
import re
import unittest

from support import REPO

PLUGIN = REPO / "essentials/dev-essentials"
WORK_MODES = PLUGIN / "skills/work-modes/SKILL.md"
POINTER = "load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the three modes"
HEADER = "| Gate | Partial (the default) | Interactive | Full |"
# The gated units with a gate table. process-pr-comments is gated too, and its section has buckets, not a table.
TABLE_UNITS = (
    "skills/feature-pipeline/SKILL.md",
    "skills/research-implement-review-report/SKILL.md",
    "commands/implement-task.md",
    "skills/implement-batch/SKILL.md",
    "skills/review-loop/SKILL.md",
    "commands/implement.md",
    "commands/opsx-implement.md",
    "skills/optimize-skill/SKILL.md",
    "skills/bug-hunt/SKILL.md",
    "skills/trim-artifacts/SKILL.md",
    "skills/git-worktree-management/SKILL.md",
    "skills/promote-conventions/SKILL.md",
    "commands/save-context.md",
)
PPC = "skills/process-pr-comments/SKILL.md"
OLD_FLAG = re.compile(r"(?<![\w-])--(?:interactive|autonomous|merge)(?![\w-])")
OLD_WORD = re.compile(r"`autonomous`")
COMMON_BLOCK = ("These rules apply in every mode:", "removes stops. It adds no steps.",
                "The user picks one with a flag: the default (no flag)")
# Lines that keep an old flag on purpose, as (path, count). The body of git-worktree-management changes after the
# task that rewrites its workflows merges, so that the two branches do not conflict. Remove the entry then.
KNOWN_OLD_FLAGS = {"essentials/dev-essentials/skills/git-worktree-management/SKILL.md": 14}


def read(path):
    return path.read_text(encoding="utf-8")


def autonomy(text):
    start = text.index("## Autonomy\n")
    end = text.find("\n## ", start + 1)
    return text[start:] if end < 0 else text[start:end]


def text_files():
    """Each Markdown file of each plugin, each eval prompt, the docs pages, and the root README, but work-modes."""
    files = [p for base in ("essentials", "dotnet", "knowledge") for p in (REPO / base).rglob("*.md")
             if "/graders/" not in p.as_posix() and "/results/" not in p.as_posix()]
    files += sorted((REPO / "docs").glob("*.md")) + [REPO / "README.md"]
    return [p for p in files if p != WORK_MODES and "/mocks/" not in p.as_posix()]


class WorkModesSkillTests(unittest.TestCase):
    def setUp(self):
        self.text = read(WORK_MODES)

    def test_only_claude_loads_the_skill(self):
        head = self.text.split("\n---\n", 1)[0]
        self.assertIn("\nname: work-modes\n", head)
        self.assertIn("\nuser-invocable: false", head)
        self.assertNotIn("disable-model-invocation", head)

    def test_the_skill_defines_the_option_the_default_and_the_end_of_each_mode(self):
        for sentence in (
                "The user picks the mode with `--mode interactive`, `--mode partial`, or `--mode full`. With no `--mode`, the mode is partial.",
                "- `feature-pipeline`: the merge of the pull request, after the gate of `dev-essentials:merge-pr`.",
                "It never merges, because the reviewers of the pull request approve it first.",
                "In the partial mode, a user who wants a stop after the plan writes \"stop after the plan\" in the request, or uses `--mode interactive`.",
                "Only the user picks the full mode, in the request of this session",
                "Such a rule can pick the interactive mode or the partial mode.",
                "In the full mode, ask only the questions of stop 6 and the questions that the gate table keeps.",
                "When a workflow runs another workflow, it passes its `--mode` on, unless its own text names an exception."):
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, self.text)

    def test_the_hard_stops_come_before_the_rules_for_every_mode(self):
        stops = self.text.index("## Hard stops")
        self.assertLess(self.text.index("## The three modes"), stops)
        self.assertLess(stops, self.text.index("## Rules for every mode"))
        for number in range(1, 8):
            with self.subTest(stop=number):
                self.assertIn(f"\n{number}. ", self.text[stops:])

    def test_the_old_spellings_keep_their_behavior(self):
        old = self.text[self.text.index("## Old spellings"):]
        self.assertIn("- `--interactive`, or the word `interactive` of `process-pr-comments`: `--mode interactive`.", old)
        self.assertIn("with no `--merge`: `--mode full`, with no approval of a merge. The run does not stop, and it does not merge.", old)
        self.assertIn("- `--autonomous --merge`: `--mode full`.", old)


class GatedUnitTests(unittest.TestCase):
    def test_each_gated_unit_points_at_the_skill_and_names_the_three_modes(self):
        for rel in TABLE_UNITS:
            with self.subTest(unit=rel):
                section = autonomy(read(PLUGIN / rel))
                self.assertIn(POINTER, section)
                self.assertIn(HEADER, section)
        self.assertIn(POINTER, autonomy(read(PLUGIN / PPC)))

    def test_no_file_keeps_a_copy_of_the_common_block(self):
        for path in text_files():
            text = read(path)
            for phrase in COMMON_BLOCK:
                with self.subTest(file=path.relative_to(REPO).as_posix(), phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_no_file_outside_work_modes_names_an_old_mode_flag(self):
        for path in text_files():
            rel = path.relative_to(REPO).as_posix()
            with self.subTest(file=rel):
                count = len(OLD_FLAG.findall(read(path))) + len(OLD_WORD.findall(read(path)))
                self.assertEqual(count, KNOWN_OLD_FLAGS.get(rel, 0))

    def test_the_old_flag_pattern_finds_the_flags_and_skips_other_options(self):
        self.assertEqual(OLD_FLAG.findall("--interactive, --autonomous --merge."), ["--interactive", "--autonomous", "--merge"])
        self.assertEqual(OLD_FLAG.findall("git diff --merge-base origin/main --no-merge x--merge"), [])


class FullModeEndTests(unittest.TestCase):
    def test_the_full_mode_asks_no_save_context_question(self):
        rirr = read(PLUGIN / "skills/research-implement-review-report/SKILL.md")
        self.assertIn("| Keep the files and the branches, and list them in the report |", autonomy(rirr))
        self.assertIn("In the full mode, ask no question, and list the kept files and branches in the report.", rirr)
        task = read(PLUGIN / "commands/implement-task.md")
        self.assertIn("| Keep the files and the branches, and list them in the report |", autonomy(task))
        self.assertIn("If it does, ask its one Step 6 question after the report. In the full mode, ask no question.", task)

    def test_the_pipeline_ends_with_a_report_for_blocking_issues_in_the_full_mode(self):
        skill = read(PLUGIN / "skills/feature-pipeline/SKILL.md")
        self.assertIn("In the full mode, write the gate content and the blocking issues to the final report, and end the run.", skill)
        self.assertIn("So the run pushes nothing, and the worktree and the artifacts stay.", skill)

    def test_the_full_mode_creates_an_out_of_scope_issue_with_no_question(self):
        folder = PLUGIN / "skills/process-pr-comments"
        self.assertIn("3. Else, in the full mode, ask no question.", read(folder / "references/tag-actions.md"))
        skill = read(folder / "SKILL.md")
        self.assertIn("If it finds none, ask no question, and create the new issue", skill)
        self.assertIn("Two questions still stop in the full mode.", skill)
        self.assertNotIn("Three questions", skill)
        self.assertIn("| `--mode` | `interactive`, `partial`, `full` | `partial` |", read(folder / "references/parameters.md"))


if __name__ == "__main__":
    unittest.main()
