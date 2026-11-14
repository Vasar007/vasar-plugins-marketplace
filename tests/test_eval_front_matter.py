"""
Parse the YAML of every eval case file and grader file with PyYAML, a real YAML parser.
The small parser of test_eval_cases.py accepts some text that is not valid YAML, and claude plugin eval
does not load a case with such text. CI installs the PyYAML version that .github/workflows/tests.yml names.
"""
import unittest
from pathlib import Path
from unittest import mock

from support import REPO
from test_eval_cases import EVALS, YamlError, find_case_folders, plugin_roots, split_frontmatter
from testkit import ScratchCase

try:
    import yaml
except ImportError:
    yaml = None

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "eval-front-matter" / "colon-in-plain-value.md"
NO_YAML = "PyYAML is not installed. Install the version that .github/workflows/tests.yml names."
NOT_A_MAPPING = "the YAML is not a mapping of keys to values"


def require_yaml(test):
    """
    Fail the test if PyYAML is not installed. A skip would hide the check.
    """
    if yaml is None:
        test.fail(NO_YAML)


def yaml_files(plugin_root):
    """
    The prompt.md, case.yaml, and graders/*.md files of each case folder of a plugin.
    """
    files = []
    for folder in find_case_folders(Path(plugin_root) / EVALS):
        files += [folder / name for name in ("prompt.md", "case.yaml") if (folder / name).is_file()]
        files += sorted((folder / "graders").glob("*.md"))
    return files


def yaml_error_text(exc):
    """
    The line and the problem of a PyYAML error, on one line.
    """
    mark, problem = getattr(exc, "problem_mark", None), getattr(exc, "problem", None)
    if mark is None or problem is None:
        return str(exc).splitlines()[0]
    return f"line {mark.line + 1}: {problem}"


def yaml_problem(path):
    """
    None if the YAML of the file parses to a mapping, else the reason.
    A line number in the reason counts from the first line of the file.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        try:
            lines, _body = split_frontmatter(text)
        except YamlError as exc:
            return str(exc)
        text = "\n" + "\n".join(lines)
    try:
        data = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:
        return yaml_error_text(exc)
    if not isinstance(data, dict):
        return NOT_A_MAPPING
    return None


def yaml_problems(files, base=REPO):
    """
    One 'path: reason' line for each file whose YAML does not parse. The path is relative to base.
    """
    problems = []
    for path in files:
        reason = yaml_problem(path)
        if reason:
            problems.append(f"{path.relative_to(base).as_posix()}: {reason}")
    return problems


class YamlScanTests(ScratchCase):
    """
    The scan on a plugin folder in a temporary folder.
    """

    def setUp(self):
        super().setUp()
        require_yaml(self)

    def write(self, relative, text):
        path = self.tmp / EVALS / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def scan(self):
        return yaml_problems(yaml_files(self.tmp), self.tmp)

    def test_the_fixture_with_a_colon_in_a_plain_value_fails_with_its_path(self):
        self.write("broken/prompt.md", FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(self.scan(), ["evals/broken/prompt.md: line 3: mapping values are not allowed here"])

    def test_a_broken_case_yaml_and_a_broken_grader_fail_with_their_paths(self):
        self.write("one/case.yaml", "name: one\ndescription: wait for the push: post no reply\n")
        self.write("one/graders/good.md", "---\ntype: regex\npattern: done\n---\nThe run says done.\n")
        self.write("one/graders/bad.md", "---\ntype: regex\npattern: [done\n---\nThe run says done.\n")
        self.assertEqual(self.scan(), [
            "evals/one/case.yaml: line 2: mapping values are not allowed here",
            "evals/one/graders/bad.md: line 3: expected ',' or ']', but got '<stream end>'",
        ])

    def test_front_matter_that_is_not_a_mapping_fails(self):
        self.write("one/prompt.md", "---\njust text\n---\nDo the task.\n")
        self.assertEqual(self.scan(), [f"evals/one/prompt.md: {NOT_A_MAPPING}"])

    def test_a_date_like_value_that_is_not_a_date_fails_with_its_path(self):
        self.write("one/prompt.md", "---\nname: one\ndescription: 2026-13-45\n---\nDo it.\n")
        self.assertEqual(self.scan(), ["evals/one/prompt.md: month must be in 1..12, not 13"])

    def test_a_quoted_value_with_a_colon_passes(self):
        self.write("one/prompt.md", '---\nname: one\ndescription: "wait for the push: post no reply"\n---\nDo it.\n')
        self.assertEqual(self.scan(), [])

    def test_a_machine_without_pyyaml_fails_with_the_install_hint(self):
        with mock.patch(f"{__name__}.yaml", None), self.assertRaises(AssertionError) as caught:
            require_yaml(self)
        self.assertIn(NO_YAML, str(caught.exception))


class RepositoryYamlTest(unittest.TestCase):
    """
    The scan on the case files and the grader files of every plugin.
    """

    def setUp(self):
        require_yaml(self)

    def test_every_case_file_and_grader_file_parses(self):
        files = [path for root in plugin_roots() for path in yaml_files(root)]
        self.assertTrue(files, "No eval case file found.")
        self.assertEqual(yaml_problems(files), [])


if __name__ == "__main__":
    unittest.main()
