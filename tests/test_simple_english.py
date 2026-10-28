"""Runs the simple-english linter on every tracked .md file of the repository.

The linter is evals/ste_lint.py of the simple-english plugin. The test looks for
it in this order:

1. The folder that the environment variable SIMPLE_ENGLISH_DIR names. This is
   the root of a SimpleEnglish checkout or of one cached plugin version.
2. The newest cached version under CLAUDE_CONFIG_DIR (default ~/.claude), in
   plugins/cache/simple-english/simple-english/.

If no linter is found, the test skips. In CI it fails.

The test fails on each hit that simple-english-baseline.json does not list.
It also fails on each baseline entry that has no hit. The "excluded" key of the
baseline lists folders, each with a reason. The test skips every file under such
a folder. An excluded folder with no tracked .md file fails the test. A baseline entry matches
by file, rule, and text, not by line, so that a line shift does not break it.
The value of an argument-hint line in the frontmatter and the closing "---"
of the frontmatter are not prose, so the test does not lint them.
"""
import json
import os
import re
import unittest
from collections import Counter
from pathlib import Path

from support import REPO, load_module, tool_missing, tracked_markdown_files

BASELINE = Path(__file__).resolve().parent / "simple-english-baseline.json"
CACHE = Path("plugins/cache/simple-english/simple-english")
FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
ARGUMENT_HINT = re.compile(r"^argument-hint:")


def find_linter_root():
    env = os.environ.get("SIMPLE_ENGLISH_DIR")
    if env:
        return Path(env)
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    roots = [p.parent.parent for p in (config / CACHE).glob("*/evals/ste_lint.py")]
    numbers = lambda p: [int(x) for x in re.findall(r"\d+", p.name)]
    return max(roots, key=numbers, default=None)


def prepare(text):
    """Blank the parts that are not prose, and flatten table rows, one output line per input line.

    The parts are fenced blocks, the value of an argument-hint line, and the
    closing "---" of the frontmatter. ste_lint pairs only triple-backtick fences, and it removes the newlines of a
    fence or a table, so its line numbers drift. This keeps them exact.
    """
    out, fence = [], None
    lines = text.split("\n")
    frontmatter = bool(lines) and lines[0].strip() == "---"
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if frontmatter:
            if i > 0 and line.strip() == "---":
                frontmatter = False
                out.append("")
            else:
                out.append("argument-hint:" if ARGUMENT_HINT.match(line) else line)
        elif fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and line.strip() == m.group(1):
                fence = None
            out.append("")
        elif m and not (m.group(1)[0] == "`" and "`" in line.strip()[len(m.group(1)):]):
            fence = m.group(1)
            out.append("")
        elif TABLE_RULE.match(line):
            out.append("")
        elif TABLE_ROW.match(line):
            out.append(". ".join(c.strip() for c in line.strip()[1:-1].split("|") if c.strip()) + ". ")
        else:
            out.append(line)
    return "\n".join(out)


def excluded_prefixes(baseline):
    return [e["path"] for e in baseline.get("excluded", [])]


def is_excluded(file, prefixes):
    return any(file.startswith(p) for p in prefixes)


def unused_prefixes(files, prefixes):
    """The excluded folders that no file in the list is under."""
    return [p for p in prefixes if not any(f.startswith(p) for f in files)]


def key(file, rule, text):
    return (file, rule, " ".join(text.split()))


class PrepareTests(unittest.TestCase):
    def test_indented_fence_in_a_list_is_blanked(self):
        text = "1. Run it:\n\n     ```bash\n     a; b\n     ```\n\nYou should go.\n"
        out = prepare(text).split("\n")
        self.assertEqual(len(out), len(text.split("\n")))
        self.assertEqual(out[2:5], ["", "", ""])
        self.assertEqual(out[6], "You should go.")

    def test_argument_hint_in_the_frontmatter_is_blanked(self):
        text = "---\ndescription: Do it.\nargument-hint: <task> [--a] [--b]\n---\n\nargument-hint: stays.\n"
        out = prepare(text).split("\n")
        self.assertEqual(len(out), len(text.split("\n")))
        self.assertEqual(out[1:4], ["description: Do it.", "argument-hint:", ""])
        self.assertEqual(out[5], "argument-hint: stays.")

    def test_line_that_starts_with_a_code_span_is_not_a_fence(self):
        text = "1. Run it:\n\n     ``` `x` ``` is code.\n\nYou should go.\n"
        self.assertEqual(prepare(text).split("\n")[4], "You should go.")


class ExclusionTests(unittest.TestCase):
    def test_a_file_under_an_excluded_folder_is_excluded(self):
        baseline = {"excluded": [{"path": "a/b/", "reason": "x"}]}
        prefixes = excluded_prefixes(baseline)
        self.assertTrue(is_excluded("a/b/c/SKILL.md", prefixes))
        self.assertFalse(is_excluded("a/bc/SKILL.md", prefixes))
        self.assertEqual(excluded_prefixes({"entries": []}), [])

    def test_an_excluded_folder_without_a_file_is_reported(self):
        files = ["a/b/one.md", "c/two.md"]
        self.assertEqual(unused_prefixes(files, ["a/b/", "d/"]), ["d/"])


class SimpleEnglishLintTest(unittest.TestCase):
    def test_hits_match_the_baseline(self):
        root = find_linter_root()
        if root is None or not (root / "evals" / "ste_lint.py").is_file():
            tool_missing(self, "simple-english linter not found. Set SIMPLE_ENGLISH_DIR to the root of a "
                               "SimpleEnglish checkout, or install the simple-english plugin.")
        lint = load_module("ste_lint", root / "evals" / "ste_lint.py")
        version = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        allowed = Counter(key(e["file"], e["rule"], e["text"]) for e in baseline["entries"])

        files = tracked_markdown_files()
        for e in baseline.get("excluded", []):
            self.assertTrue(e.get("path"), f"An excluded entry needs a path: {e}")
            self.assertTrue(e["path"].endswith("/"), f"The excluded folder {e['path']} must end with a slash.")
            self.assertTrue(e.get("reason"), f"The excluded folder {e['path']} needs a reason.")
        prefixes = excluded_prefixes(baseline)
        unused = unused_prefixes(files, prefixes)
        self.assertEqual(unused, [], "Excluded folders without a tracked .md file. Remove them from "
                         + BASELINE.name + ".")

        new = []
        for file in files:
            if is_excluded(file, prefixes):
                continue
            text = (REPO / file).read_text(encoding="utf-8")
            for hit in lint.lint_detail(prepare(text), "descriptive"):
                k = key(file, hit["category"], hit["text"])
                if allowed[k] > 0:
                    allowed[k] -= 1
                else:
                    new.append((file, hit))

        stale = [k for k, n in allowed.items() for _ in range(n)]
        problems = []
        if new:
            lines = [f"{f}:{h['line']}: {h['category']}: {' '.join(h['text'].split())}" for f, h in new]
            entries = [json.dumps({"file": f, "rule": h["category"], "text": " ".join(h["text"].split()),
                                   "reason": "TODO"}, ensure_ascii=False) for f, h in new]
            problems.append(f"New simple-english hits: {len(new)}\n" + "\n".join(lines)
                            + "\nFix each hit. Only for a valid exception, add an entry with a reason to "
                            + BASELINE.name + ":\n" + ",\n".join(entries))
        if stale:
            lines = [f"{f}: {r}: {t}" for f, r, t in stale]
            problems.append(f"Baseline entries without a hit: {len(stale)}\n" + "\n".join(lines)
                            + "\nRemove each entry from " + BASELINE.name + ".")
        if problems:
            note = "" if version == baseline["version"] else (
                f"\nThe baseline is for simple-english {baseline['version']}. This run used {version}.")
            self.fail(f"simple-english linter {version} at {root}:\n" + "\n\n".join(problems) + note)


if __name__ == "__main__":
    unittest.main()
