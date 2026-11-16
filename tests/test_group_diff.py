"""Tests for essentials/dev-essentials/skills/review-loop/scripts/group_diff.py.

Each test builds a git repository in a temporary folder, commits a change, and
runs the script as a child process, as the large-target mode of review-loop does.
"""
import re
import shutil
import sys
import unittest

from support import REPO, tool_missing
from testkit import ScratchCase, git_init, run

SCRIPT = REPO / "essentials/dev-essentials/skills/review-loop/scripts/group_diff.py"
FILE = re.compile(r"^  (\S+) \+(\S+) -(\S+) (.+?)(?: <- (.+?))?(?: \[(.+)\])?$")


class GroupDiffCase(ScratchCase):
    def setUp(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        super().setUp()
        self.repo = git_init(self.tmp / "repo")
        self.write("README.txt", "base\n")
        self.commit("base")

    def git(self, *args):
        return run(["git", "-C", self.repo, *args], check=True).stdout

    def write(self, rel, text="x\n", lines=None):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if lines is not None:
            text = "".join(f"line {i}\n" for i in range(lines))
        path.write_bytes(text.encode("utf-8"))

    def commit(self, message="change"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def group(self, rng="HEAD~1..HEAD", code=0):
        result = run([sys.executable, "-I", SCRIPT, "--repo", self.repo, "--range", rng])
        self.assertResult(result, code)
        return result

    def areas(self, rng="HEAD~1..HEAD"):
        """The areas as {name: [(kind, added, deleted, path, old, mark), ...]}, in output order."""
        areas, name = {}, None
        for line in self.group(rng).stdout.splitlines():
            if line.startswith("AREA "):
                name = line.split(" ")[2]
                areas[name] = []
            elif line.startswith("  "):
                areas[name].append(FILE.match(line).groups())
        return areas

    def paths(self, area):
        return [entry[3] for entry in area]


class GroupingTests(GroupDiffCase):
    def test_small_change_has_one_area_per_top_folder_and_root(self):
        self.write("app.py")
        self.write("src/a.py")
        self.write("src/lib/b.py")
        self.write("docs/guide.md")
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["root", "docs/", "src/"])
        self.assertEqual(self.paths(areas["root"]), ["app.py"])
        self.assertEqual(self.paths(areas["src/"]), ["src/a.py", "src/lib/b.py"])

    def test_totals_and_paths_match_git(self):
        for i in range(14):
            self.write(f"src/m{i % 3}/f{i}.py", lines=i + 1)
        self.write("README.txt", "new\n")
        self.commit()
        out = self.group().stdout
        names = sorted(self.git("diff", "--name-only", "HEAD~1..HEAD").split())
        listed = sorted(m.group(4) for m in map(FILE.match, out.splitlines()) if m)
        self.assertEqual(listed, names)
        self.assertIn(f"TOTAL files={len(names)} added={sum(range(1, 15)) + 1} deleted=1", out)

    def test_folder_over_ten_files_splits_by_next_level(self):
        for i in range(6):
            self.write(f"src/api/f{i}.py")
            self.write(f"src/db/f{i}.py")
        self.write("src/main.py")
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["src/", "src/api/", "src/db/"])
        self.assertEqual(self.paths(areas["src/"]), ["src/main.py"])
        self.assertEqual(len(areas["src/api/"]), 6)

    def test_folder_over_800_lines_splits_by_next_level(self):
        self.write("src/api/a.py", lines=500)
        self.write("src/db/b.py", lines=500)
        self.commit()
        self.assertEqual(list(self.areas()), ["src/api/", "src/db/"])

    def test_split_goes_down_while_an_area_is_too_large(self):
        for i in range(11):
            self.write(f"pkg/core/deep/f{i}.py")
        self.write("pkg/other/x.py")
        self.commit()
        self.assertEqual(list(self.areas()), ["pkg/core/deep/", "pkg/other/"])

    def test_folder_with_no_next_level_stays_one_area(self):
        for i in range(12):
            self.write(f"flat/f{i:02}.py")
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["flat/"])
        self.assertEqual(len(areas["flat/"]), 12)

    def test_file_over_800_lines_is_its_own_area(self):
        self.write("flat/big.py", lines=900)
        self.write("flat/small.py")
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["flat/", "flat/big.py"])
        self.assertEqual(self.paths(areas["flat/"]), ["flat/small.py"])

    def test_root_files_are_one_area_named_root(self):
        self.write("a.txt")
        self.write("b.txt")
        self.commit()
        self.assertEqual(self.paths(self.areas()["root"]), ["a.txt", "b.txt"])

    def test_test_files_come_after_production_files(self):
        self.write("src/z_service.py")
        self.write("src/test_a.py")
        self.write("src/tests/helper.py")
        self.write("src/Thing.Tests.cs")
        self.commit()
        area = self.areas()["src/"]
        self.assertEqual(self.paths(area)[0], "src/z_service.py")
        self.assertEqual([entry[5] for entry in area], [None, "test", "test", "test"])


class SkippedTests(GroupDiffCase):
    def test_lock_generated_and_header_files_are_skipped(self):
        self.write(".gitattributes", "gen/** linguist-generated\n")
        self.commit("attributes")
        self.write("web/package-lock.json", lines=2000)
        self.write("gen/api.cs")
        self.write("src/Model.g.cs", "// <auto-generated>\nclass A {}\n")
        self.write("src/notes.py", "# DO NOT EDIT\n")
        self.write("src/real.py")
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["src/", "skipped"])
        skipped = {entry[3]: entry[5] for entry in areas["skipped"]}
        self.assertEqual(skipped, {"web/package-lock.json": "lock file", "gen/api.cs": "linguist-generated",
                                   "src/Model.g.cs": "generated header", "src/notes.py": "generated header"})

    def test_skipped_area_is_never_split(self):
        for i in range(12):
            self.write(f"m{i}/go.sum", lines=100)
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["skipped"])
        self.assertEqual(len(areas["skipped"]), 12)

    def test_header_of_the_working_tree_file_counts_for_a_working_tree_range(self):
        self.write("src/out.py", "x\n")
        self.commit()
        self.write("src/out.py", "# auto-generated\nx\n")
        self.assertEqual(list(self.areas("HEAD")), ["skipped"])


class KindTests(GroupDiffCase):
    def test_kinds_rename_binary_and_counts(self):
        self.write("src/old_name.py", lines=20)
        self.write("src/gone.py", lines=3)
        self.commit("more")
        self.git("mv", "src/old_name.py", "src/new_name.py")
        (self.repo / "src/gone.py").unlink()
        (self.repo / "src/logo.bin").write_bytes(bytes(range(256)))
        self.write("src/space name.py", "a\nb\n")
        self.commit()
        entries = {entry[3]: entry for entry in self.areas()["src/"]}
        self.assertEqual(entries["src/new_name.py"][:5], ("renamed", "0", "0", "src/new_name.py", "src/old_name.py"))
        self.assertEqual(entries["src/gone.py"][:3], ("deleted", "0", "3"))
        self.assertEqual(entries["src/logo.bin"][:3], ("added", "bin", "bin"))
        self.assertEqual(entries["src/space name.py"][:3], ("added", "2", "0"))

    def test_empty_diff_prints_no_area(self):
        out = self.group("HEAD..HEAD").stdout
        self.assertEqual(out.strip(), "TOTAL files=0 added=0 deleted=0 areas=0")


class UsageTests(GroupDiffCase):
    def test_unknown_range_is_a_usage_error(self):
        result = self.group("no-such-ref..HEAD", code=2)
        self.assertIn("error:", result.stderr)

    def test_range_that_looks_like_an_option_is_refused(self):
        result = run([sys.executable, "-I", SCRIPT, "--repo", self.repo, "--range=--output=x"])
        self.assertResult(result, 2, "must not start with '-'")
        self.assertFalse((self.repo / "x").exists())


if __name__ == "__main__":
    unittest.main()
