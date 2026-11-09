"""Tests for skills/openbsd-style-docs/scripts/openbsd_lint.py of the doc-styles plugin."""
import json
import re
import shutil
import sys
import unittest

from support import REPO, load_module
from testkit import ScratchCase, clean_env, run

PLUGIN = REPO / "essentials/doc-styles"
SKILL_DIR = PLUGIN / "skills/openbsd-style-docs"
SCRIPT = SKILL_DIR / "scripts/openbsd_lint.py"
HOOKS_FILE = PLUGIN / "hooks/hooks.json"
EXCLUDE_VAR = "OPENBSD_STYLE_LINT_EXCLUDE"

lint_module = load_module("openbsd_lint", SCRIPT) if SCRIPT.is_file() else None

HEAD = "# probe\n\nprobe - print the text of a file\n\n"
DESCRIPTION = "## DESCRIPTION\n\nThe `probe` utility prints the text of a file.\n"
VALID_PAGE = HEAD + "## SYNOPSIS\n\n`probe` [`-v`] *file*\n\n" + DESCRIPTION + (
    "\nThe options are as follows:\n\n"
    "- `-c`\\\n  Count the lines.\n"
    "- `-v`\\\n  Print the version.\n"
)


def gold_readme():
    """The README block of references/examples.md, the complete example of the skill."""
    text = (SKILL_DIR / "references/examples.md").read_text(encoding="utf-8")
    start = text.index("## A complete README")
    fence = text.index("````markdown\n", start) + len("````markdown\n")
    return text[fence:text.index("\n````", fence) + 1]


def rules(text):
    """The rule ids of the hits in text, in line order."""
    return [rule for _, rule, _ in lint_module.lint(text)]


class LintCase(ScratchCase):
    def run_lint(self, text, *args):
        path = self.tmp / "page.md"
        path.write_bytes(text.encode("utf-8"))
        return run([sys.executable, "-I", SCRIPT, *args, path])

    def assertRules(self, text, *expected):
        self.assertEqual(rules(text), list(expected), text)


class GoldTests(LintCase):
    def test_gold_readme_is_found(self):
        self.assertIn("## DESCRIPTION", gold_readme())

    def test_gold_readme_has_no_hit(self):
        result = self.run_lint(gold_readme())
        self.assertResult(result, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_gold_readme_is_in_style(self):
        self.assertTrue(lint_module.in_style(gold_readme()))

    def test_valid_page(self):
        result = self.run_lint(VALID_PAGE)
        self.assertResult(result, 0)
        self.assertEqual(result.stdout + result.stderr, "")


class HeadingTests(LintCase):
    def test_mixed_case(self):
        text = HEAD + DESCRIPTION + "\n## Examples\n\nRun `probe`.\n"
        self.assertRules(text, "heading-case")

    def test_sentence_case_only(self):
        text = HEAD + "## Install\n\nRun `make`.\n\n## Usage\n\nRun `probe`.\n"
        self.assertRules(text)

    def test_canonical_order(self):
        text = HEAD + DESCRIPTION + "\n## SYNOPSIS\n\n`probe` *file*\n"
        self.assertRules(text, "section-order")

    def test_custom_section_before_description(self):
        text = HEAD + "## INSTALLATION\n\nRun `make`.\n\n" + DESCRIPTION
        self.assertRules(text, "section-order")

    def test_custom_section_after_description(self):
        text = HEAD + DESCRIPTION + "\n## INSTALLATION\n\nRun `make`.\n"
        self.assertRules(text)

    def test_empty_section(self):
        text = HEAD + DESCRIPTION + "\n## FILES\n\n## SEE ALSO\n\n`cat(1)`\n"
        self.assertRules(text, "empty-section")

    def test_empty_last_section(self):
        text = HEAD + DESCRIPTION + "\n## BUGS\n"
        self.assertRules(text, "empty-section")

    def test_code_block_is_content(self):
        text = HEAD + DESCRIPTION + "\n## EXAMPLES\n\n```sh\nprobe file\n```\n"
        self.assertRules(text)

    def test_code_span_in_a_custom_heading(self):
        text = HEAD + DESCRIPTION + "\n## `probe.conf` DIRECTIVES\n\nText.\n"
        self.assertRules(text)

    def test_heading_hint_keeps_code_spans(self):
        text = HEAD + DESCRIPTION + "\n## `probe.conf` directives\n\nText.\n"
        messages = [m for _, rule, m in lint_module.lint(text) if rule == "heading-case"]
        self.assertEqual(messages, ["write the heading in uppercase: `probe.conf` DIRECTIVES"])

    def test_hits_in_code_are_ignored(self):
        text = HEAD + DESCRIPTION + "\n```markdown\n## examples\n\n## FILES\n```\n"
        self.assertRules(text)


class NameLineTests(LintCase):
    def test_good_line(self):
        self.assertRules(HEAD + DESCRIPTION)

    def test_list_with_commas(self):
        self.assertRules("# `probe`\n\nprobe, `prb` - print the text of a file\n\n" + DESCRIPTION)

    def test_no_title(self):
        self.assertRules("probe - print the text of a file\n\n" + DESCRIPTION, "name-line")

    def test_no_name_line(self):
        self.assertRules("# probe\n\nThe probe utility prints text.\n\n" + DESCRIPTION, "name-line")

    def test_another_name(self):
        self.assertRules("# probe\n\nother - print the text of a file\n\n" + DESCRIPTION, "name-line")

    def test_article(self):
        self.assertRules("# probe\n\nprobe - a utility that prints text\n\n" + DESCRIPTION, "name-line")

    def test_uppercase_start(self):
        self.assertRules("# probe\n\nprobe - Print the text of a file\n\n" + DESCRIPTION, "name-line")

    def test_acronym_start(self):
        self.assertRules("# probe\n\nprobe - HTTP probe for a host\n\n" + DESCRIPTION)

    def test_final_period(self):
        self.assertRules("# probe\n\nprobe - print the text of a file.\n\n" + DESCRIPTION, "name-line")


class SortTests(LintCase):
    def options(self, *terms):
        return HEAD + DESCRIPTION + "\nThe options are as follows:\n\n" + "".join(
            "- `{}`\\\n  Do the thing.\n".format(term) for term in terms)

    def section(self, name, *terms):
        return HEAD + DESCRIPTION + "\n## {}\n\n".format(name) + "".join(
            "- `{}`\\\n  Text.\n".format(term) for term in terms)

    def test_sorted_options(self):
        self.assertRules(self.options("-1", "-A", "-a", "-B", "-b"))

    def test_unsorted_options(self):
        text = self.options("-v", "-c", "-k")
        hits = lint_module.lint(text)
        self.assertEqual([rule for _, rule, _ in hits], ["sort-order"])
        self.assertIn("-c, -k, -v", hits[0][2])

    def test_unsorted_environment(self):
        self.assertRules(self.section("ENVIRONMENT", "TMPDIR", "HOME"), "sort-order")

    def test_unsorted_files(self):
        self.assertRules(self.section("FILES", "/var/run/probe.pid", "/etc/probe.conf"), "sort-order")

    def test_unsorted_errors(self):
        self.assertRules(self.section("ERRORS", "[ENOENT]", "[EINVAL]"), "sort-order")

    def test_sorted_errors(self):
        self.assertRules(self.section("ERRORS", "[EINVAL]", "[ENOENT]"))

    def test_error_code_with_brackets_outside_the_code(self):
        text = HEAD + DESCRIPTION + "\n## ERRORS\n\n- [`ENOENT`]\\\n  Text.\n- [`EINVAL`]\\\n  Text.\n"
        self.assertRules(text, "sort-order")

    def test_tag_item_with_only_brackets(self):
        text = HEAD + DESCRIPTION + "\nThe notation is:\n\n- `[ ]` marks an optional part.\n- `[]` marks nothing.\n"
        self.assertRules(text)

    def test_tag_item_with_only_a_space(self):
        text = HEAD + DESCRIPTION + "\nThe notation is:\n\n- ` ` is a space.\n"
        self.assertRules(text)

    def test_equal_error_codes(self):
        self.assertRules(self.section("ERRORS", "[EINVAL]", "[EINVAL]", "[ENOENT]"))

    def test_subcommand_list(self):
        text = HEAD + DESCRIPTION + "\nThe commands are:\n\n- `start`\\\n  Start.\n- `add`\\\n  Add.\n"
        self.assertRules(text)

    def test_directive_list(self):
        text = HEAD + DESCRIPTION + "\n## CONFIGURATION\n\n- `Port`\\\n  Text.\n- `Host`\\\n  Text.\n"
        self.assertRules(text)

    def test_one_hit_for_a_list(self):
        self.assertRules(self.options("-d", "-c", "-b", "-a"), "sort-order")


class DefaultTests(LintCase):
    def option(self, text):
        return HEAD + DESCRIPTION + "\nThe options are as follows:\n\n- `-n` *count*\\\n  " + text + "\n"

    def test_own_sentence(self):
        self.assertRules(self.option("Set the number of lines. The default is 7."))

    def test_own_sentence_on_the_next_line(self):
        self.assertRules(self.option("Set the number of lines.\n  By default, 7 lines are printed."))

    def test_parenthesis(self):
        self.assertRules(self.option("Set the number of lines (default: 22)."), "default-sentence")

    def test_comma(self):
        self.assertRules(self.option("Set the number of lines, the default is 30."), "default-sentence")

    def test_which_defaults(self):
        self.assertRules(self.option("Set the number of lines, which defaults to 10."), "default-sentence")

    def test_word_default_as_a_noun(self):
        self.assertRules(self.option("Restore the default value."))

    def test_defaults_noun_with_a_colon(self):
        self.assertRules(self.option("Reset the settings to their defaults: colors and keys."))

    def test_defaults_to_opener(self):
        self.assertRules(self.option("Set the number of lines. Defaults to 7."))

    def test_if_not_specified_opener(self):
        self.assertRules(self.option("Set the number of lines. If not specified, probe defaults to 7."))

    def test_placeholder_before_the_default_sentence(self):
        text = HEAD + DESCRIPTION + "\nThe options are as follows:\n\n- `-n` *count*\\\n  By default, 7 lines are printed.\n"
        self.assertRules(text)

    def test_one_line_form_with_a_placeholder(self):
        text = HEAD + DESCRIPTION + "\nThe options are as follows:\n\n- `-n` *count*: The default is 7.\n"
        self.assertRules(text)

    def test_one_line_form_with_an_inline_default(self):
        text = HEAD + DESCRIPTION + "\nThe options are as follows:\n\n- `-n` *count*: Set the lines, the default is 7.\n"
        self.assertRules(text, "default-sentence")

    def test_bracket_term_form(self):
        text = HEAD + DESCRIPTION + "\n## ERRORS\n\n- [`EINVAL`]\\\n  The value is bad (default: 1).\n"
        self.assertRules(text, "default-sentence")


class WordTests(LintCase):
    def body(self, sentence):
        return HEAD + DESCRIPTION + "\n" + sentence + "\n"

    def test_each_word(self):
        for word in lint_module.WORDS:
            with self.subTest(word=word):
                self.assertRules(self.body("The tool is " + word + " fast."), "word-list")

    def test_each_phrase(self):
        for phrase in lint_module.PHRASES:
            with self.subTest(phrase=phrase):
                self.assertRules(self.body("The tool works " + phrase + "."), "word-list")

    def test_exclamation_mark(self):
        self.assertRules(self.body("The tool is fast!"), "word-list")

    def test_bold(self):
        self.assertRules(self.body("The tool is **fast**."), "word-list")

    def test_you(self):
        for word in ("you", "your", "yourself"):
            with self.subTest(word=word):
                self.assertRules(self.body("Then " + word + " run it."), "you")

    def test_you_in_a_link_target(self):
        self.assertRules(self.body("See the [guide](https://example.com/your-first-run) first."))

    def test_word_in_a_link_target(self):
        self.assertRules(self.body("See [guide](https://example.com/your-easy-start) first."))

    def test_words_in_a_bare_url(self):
        self.assertRules(self.body("See https://example.com/your-easy-start first."))

    def test_words_in_a_reference_definition(self):
        self.assertRules(self.body("See [guide][1].\n\n[1]: https://example.com/your-faq-easy"))

    def test_two_comments_on_one_line(self):
        self.assertRules(self.body("a <!-- x --> b <!-- just --> c"))

    def test_you_in_the_link_text(self):
        self.assertRules(self.body("See [your guide](https://example.com/guide) first."), "you")

    def test_comment_marker_in_inline_code(self):
        self.assertRules(self.body("Write `<!--` to open a comment.\n\nThe tool is just fast."), "word-list")

    def test_word_in_a_longer_word(self):
        self.assertRules(self.body("The justice and easiest cases stay."))

    def test_inline_code(self):
        self.assertRules(self.body("Run `just` or `easy!` or `you` or `**`."))

    def test_fenced_code(self):
        self.assertRules(self.body("```sh\njust run it!\n```\n\n~~~\nyou **just** go\n~~~"))

    def test_longer_fence(self):
        self.assertRules(self.body("````markdown\n```\njust\n```\n````"))

    def test_html_comment(self):
        self.assertRules(self.body("<!-- just you! -->\n\n<!--\nsimply\n-->"))

    def test_front_matter(self):
        self.assertRules("---\ntitle: just you!\n---\n" + HEAD + DESCRIPTION)

    def test_image_and_not_equal(self):
        self.assertRules(self.body("See ![image](a.png) and a != b."))

    def test_line_number(self):
        hits = lint_module.lint(self.body("The tool is just fast."))
        self.assertEqual([line for line, _, _ in hits], [9])


class CliTests(LintCase):
    def test_no_argument(self):
        result = run([sys.executable, "-I", SCRIPT])
        self.assertResult(result, 2)
        self.assertIn("Usage:", result.stderr)

    def test_tag_item_with_only_brackets(self):
        result = self.run_lint(HEAD + DESCRIPTION + "\nThe notation is:\n\n- `[ ]` marks an optional part.\n")
        self.assertResult(result, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_missing_file(self):
        self.assertResult(run([sys.executable, "-I", SCRIPT, self.tmp / "missing.md"]), 2, "missing.md")

    def test_hits(self):
        result = self.run_lint(HEAD + DESCRIPTION + "\nThe tool is just fast.\n")
        self.assertResult(result, 1, "page.md:9: word-list: ")

    def test_lints_a_file_outside_the_style(self):
        result = self.run_lint("# Notes\n\nIt is just a note.\n")
        self.assertResult(result, 1, "name-line")


class HookTests(LintCase):
    def hook(self, path, env=None, raw=None, tool="Write"):
        event = raw if raw is not None else json.dumps(
            {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": {"file_path": str(path)}})
        return run([sys.executable, "-I", SCRIPT, "--hook"], stdin=event, env=env)

    def write(self, name, text):
        path = self.tmp / name
        path.write_bytes(text.encode("utf-8"))
        return path

    def assertSilent(self, result):
        self.assertResult(result, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_bad_json(self):
        self.assertSilent(self.hook("", raw="not json"))

    def test_empty_input(self):
        self.assertSilent(self.hook("", raw=""))

    def test_other_extension(self):
        path = self.write("page.py", HEAD + DESCRIPTION + "\nThe tool is just fast.\n")
        self.assertSilent(self.hook(path))

    def test_missing_file(self):
        self.assertSilent(self.hook(self.tmp / "missing.md"))

    def test_plain_readme(self):
        path = self.write("README.md", "# Tool\n\nThis tool is just fast.\n")
        self.assertSilent(self.hook(path))

    def test_page_without_hits(self):
        self.assertSilent(self.hook(self.write("page.md", VALID_PAGE)))

    def test_page_with_hits(self):
        text = VALID_PAGE.replace("- `-c`", "- `-z`") + "\nThe tool is just fast.\n"
        result = self.hook(self.write("page.md", text))
        self.assertResult(result, 2, "openbsd-style-docs: page.md has 2 style hit(s).", "sort-order", "word-list",
                          "Fix each hit in the file, or keep it and give the reason in the reply.")
        self.assertEqual(result.stdout, "")

    def test_edit_event(self):
        path = self.write("page.md", HEAD + DESCRIPTION + "\nThe tool is just fast.\n")
        self.assertResult(self.hook(path, tool="Edit"), 2, "word-list")

    def test_report_form(self):
        result = self.hook(self.write("page.md", HEAD + DESCRIPTION + "\nThe tool is just fast.\n"))
        self.assertIn("\n  line 9, word-list: remove 'just', or give the reason in the reply\n", result.stderr)

    def test_report_is_capped(self):
        text = HEAD + DESCRIPTION + "\n" + "The tool is just fast.\n\n" * 14
        result = self.hook(self.write("page.md", text))
        self.assertResult(result, 2, "has 14 style hit(s).", "and 2 more hit(s).")
        self.assertEqual(result.stderr.count("word-list"), 12)

    def test_non_ascii_page(self):
        text = HEAD + DESCRIPTION + "\nCafé — the tool is just fast.\n"
        result = self.hook(self.write("page.md", text))
        self.assertResult(result, 2, "word-list")

    def test_exclude_everything(self):
        path = self.write("page.md", HEAD + DESCRIPTION + "\nThe tool is just fast.\n")
        self.assertSilent(self.hook(path, env=clean_env(**{EXCLUDE_VAR: "*"})))

    def test_exclude_pattern(self):
        path = self.write("page.md", HEAD + DESCRIPTION + "\nThe tool is just fast.\n")
        self.assertSilent(self.hook(path, env=clean_env(**{EXCLUDE_VAR: "*/page.md"})))

    def test_exclude_pattern_that_does_not_match(self):
        path = self.write("page.md", HEAD + DESCRIPTION + "\nThe tool is just fast.\n")
        result = self.hook(path, env=clean_env(**{EXCLUDE_VAR: "*/other.md"}))
        self.assertResult(result, 2, "word-list")

    def test_exclude_variable_is_unset(self):
        path = self.write("page.md", HEAD + DESCRIPTION + "\nThe tool is just fast.\n")
        result = self.hook(path, env=clean_env(drop=[EXCLUDE_VAR]))
        self.assertResult(result, 2, "word-list")


class InStyleTests(unittest.TestCase):
    def test_description_and_name_line(self):
        self.assertTrue(lint_module.in_style(HEAD + DESCRIPTION))

    def test_description_and_another_canonical_heading(self):
        self.assertTrue(lint_module.in_style("# Probe\n\n## SYNOPSIS\n\n`probe`\n\n" + DESCRIPTION))

    def test_description_only(self):
        self.assertFalse(lint_module.in_style("# Probe\n\n" + DESCRIPTION))

    def test_sentence_case_description(self):
        self.assertFalse(lint_module.in_style(HEAD + "## Description\n\nText.\n\n## Synopsis\n\n`probe`\n"))

    def test_no_description(self):
        self.assertFalse(lint_module.in_style(HEAD + "## SYNOPSIS\n\n`probe`\n"))

    def test_description_in_a_fence(self):
        self.assertFalse(lint_module.in_style(HEAD + "```\n## DESCRIPTION\n\n## FILES\n```\n"))


class SkillTextTests(unittest.TestCase):
    def test_every_word_is_named_in_sentence_rules(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        start = text.index("\n## Sentence rules\n")
        section = re.sub(r"\s+", " ", text[start:text.index("\n## ", start + 1)])
        for entry in lint_module.WORDS + lint_module.PHRASES:
            with self.subTest(entry=entry):
                self.assertIn(entry, section)


class HookFileTests(ScratchCase):
    def test_hook_file(self):
        config = json.loads(HOOKS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(list(config["hooks"]), ["PostToolUse"])
        groups = config["hooks"]["PostToolUse"]
        self.assertEqual([group["matcher"] for group in groups], ["Write|Edit"])
        commands = [hook for group in groups for hook in group["hooks"]]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["type"], "command")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/openbsd-style-docs/scripts/openbsd_lint.py", commands[0]["command"])
        self.assertTrue(commands[0]["command"].endswith("--hook"))

    def test_hook_exits_quietly_without_python3(self):
        shell = shutil.which("sh")
        if not shell:
            self.skipTest("no sh")
        command = json.loads(HOOKS_FILE.read_text(encoding="utf-8"))["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        empty = self.tmp / "empty"
        empty.mkdir()
        env = {"PATH": str(empty), "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
        result = run([shell, "-c", command], stdin="{}", env=env)
        self.assertResult(result, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
