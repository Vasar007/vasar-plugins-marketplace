"""Runs the simple-english linter on every tracked .md file of the plugins.

The linter is evals/ste_lint.py of the simple-english plugin. The test looks for
it in this order:

1. The folder that the environment variable SIMPLE_ENGLISH_DIR names. This is
   the root of a SimpleEnglish checkout or of one cached plugin version.
2. The newest cached version under CLAUDE_CONFIG_DIR (default ~/.claude), in
   plugins/cache/simple-english/simple-english/.

If no linter is found, the test skips. In CI it fails.

The test fails on each hit that simple-english-baseline.json does not list.
A baseline entry matches by file, rule, and text, not by line, so that a
line shift does not break it.
"""
import json
import os
import re
import unittest
from collections import Counter
from pathlib import Path

from support import REPO, load_module, plugin_markdown_files, tool_missing

BASELINE = Path(__file__).resolve().parent / "simple-english-baseline.json"
CACHE = Path("plugins/cache/simple-english/simple-english")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")


def find_linter_root():
    env = os.environ.get("SIMPLE_ENGLISH_DIR")
    if env:
        return Path(env)
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    roots = [p.parent.parent for p in (config / CACHE).glob("*/evals/ste_lint.py")]
    numbers = lambda p: [int(x) for x in re.findall(r"\d+", p.name)]
    return max(roots, key=numbers, default=None)


def prepare(text):
    """Blank fenced blocks and flatten table rows, one output line per input line.

    ste_lint pairs only triple-backtick fences, and it removes the newlines of a
    fence or a table, so its line numbers drift. This keeps them exact.
    """
    out, fence = [], None
    for line in text.split("\n"):
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and line.strip() == m.group(1):
                fence = None
            out.append("")
        elif m:
            fence = m.group(1)
            out.append("")
        elif TABLE_RULE.match(line):
            out.append("")
        elif TABLE_ROW.match(line):
            out.append(". ".join(c.strip() for c in line.strip()[1:-1].split("|") if c.strip()) + ". ")
        else:
            out.append(line)
    return "\n".join(out)


def key(file, rule, text):
    return (file, rule, " ".join(text.split()))


class SimpleEnglishLintTest(unittest.TestCase):
    def test_no_new_hits(self):
        root = find_linter_root()
        if root is None or not (root / "evals" / "ste_lint.py").is_file():
            tool_missing(self, "simple-english linter not found. Set SIMPLE_ENGLISH_DIR to the root of a "
                               "SimpleEnglish checkout, or install the simple-english plugin.")
        lint = load_module("ste_lint", root / "evals" / "ste_lint.py")
        version = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        allowed = Counter(key(e["file"], e["rule"], e["text"]) for e in baseline["entries"])

        new = []
        for file in plugin_markdown_files():
            text = (REPO / file).read_text(encoding="utf-8")
            for hit in lint.lint_detail(prepare(text), "descriptive"):
                k = key(file, hit["category"], hit["text"])
                if allowed[k] > 0:
                    allowed[k] -= 1
                else:
                    new.append((file, hit))

        stale = [k for k, n in allowed.items() if n > 0]
        for file, rule, text in stale:
            print(f"NOTE: baseline entry without a hit: {file}: {rule}: {text}")
        if new:
            lines = [f"{f}:{h['line']}: {h['category']}: {' '.join(h['text'].split())}" for f, h in new]
            entries = [json.dumps({"file": f, "rule": h["category"], "text": " ".join(h["text"].split()),
                                   "reason": "TODO"}, ensure_ascii=False) for f, h in new]
            note = "" if version == baseline["version"] else (
                f"\nThe baseline is for simple-english {baseline['version']}. This run used {version}.")
            self.fail(f"{len(new)} new simple-english hits (linter {version} at {root}):\n"
                      + "\n".join(lines)
                      + "\nFix each hit. Only for a valid exception, add an entry with a reason to "
                      + BASELINE.name + ":\n" + ",\n".join(entries) + note)


if __name__ == "__main__":
    unittest.main()
