"""Tests for essentials/dev-essentials/skills/review-loop/scripts/group_diff.py.

Each test builds a git repository in a temporary folder, commits a change, and
runs the script as a child process, as the large-target mode of review-loop does.
"""
import os
import re
import shlex
import shutil
import sys
import unittest
from unittest import mock

from support import REPO, load_module, run_with_open_stdin, tool_missing
from testkit import ScratchCase, clean_env, git_init, run

SCRIPT = REPO / "essentials/dev-essentials/skills/review-loop/scripts/group_diff.py"
gd = load_module("group_diff", SCRIPT)
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

    def group(self, rng="HEAD~1..HEAD", code=0, repo=None, launch=("-I",), env=None):
        result = run([sys.executable, *launch, SCRIPT, "--repo", repo or self.repo, "--range", rng], env=env)
        self.assertResult(result, code)
        return result

    def areas(self, rng="HEAD~1..HEAD", **options):
        """The areas as {name: [(kind, added, deleted, path, old, mark), ...]}, in output order."""
        areas, name = {}, None
        for line in self.group(rng, **options).stdout.splitlines():
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
        self.assertIn(f"TOTAL files={len(names)} added={sum(range(1, 15)) + 1} deleted=1 areas=", out)

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

    def test_folder_with_exactly_ten_files_stays_one_area(self):
        for i in range(9):
            self.write(f"src/f{i}.py")
        self.write("src/lib/g.py")
        self.commit()
        self.assertEqual(list(self.areas()), ["src/"])

    def test_folder_with_exactly_800_lines_stays_one_area(self):
        self.write("src/api/a.py", lines=400)
        self.write("src/db/b.py", lines=400)
        self.commit()
        self.assertEqual(list(self.areas()), ["src/"])

    def test_folder_with_801_lines_splits(self):
        self.write("src/api/a.py", lines=401)
        self.write("src/db/b.py", lines=400)
        self.commit()
        self.assertEqual(list(self.areas()), ["src/api/", "src/db/"])

    def test_deleted_lines_count_for_the_line_limit(self):
        self.write("src/a/big.py", lines=500)
        self.commit("more")
        self.write("src/a/big.py", "".join(f"new {i}\n" for i in range(400)))
        self.write("src/b/x.py")
        self.commit()
        self.assertEqual(list(self.areas()), ["src/a/big.py", "src/b/"])

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

    def test_file_with_exactly_800_lines_stays_in_its_area(self):
        self.write("flat/edge.py", lines=800)
        self.write("flat/small.py")
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["flat/"])
        self.assertEqual(self.paths(areas["flat/"]), ["flat/edge.py", "flat/small.py"])

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

    def test_test_file_rule_knows_each_folder_name_and_each_name_form(self):
        tests = ["test/a.py", "src/Tests/a.cs", "web/__tests__/a.js", "src/test_a.py", "src/a_test.go",
                 "web/a.test.js", "web/a.spec.ts", "src/ATest.java", "src/A.Tests.cs"]
        others = ["src/contest/a.py", "src/latest.py", "src/attest_a.py", "src/tests.py", "src/a.tests.js"]
        for path in tests + others:
            self.assertEqual(gd.Change(path, None, 1, 0).is_test, path in tests, path)

    def test_total_line_and_area_lines_have_the_counts(self):
        self.write("app.py", lines=3)
        self.write("run.py", lines=2)
        self.write("src/a.py", lines=5)
        self.write("src/lib/b.py", lines=7)
        self.write("src/lib/c.py", lines=1)
        self.commit()
        lines = [line for line in self.group().stdout.splitlines() if not line.startswith("  ")]
        self.assertEqual(lines, ["TOTAL files=5 added=18 deleted=0 areas=2", "AREA 1 root files=2 lines=5",
                                 "AREA 2 src/ files=3 lines=13"])


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

    def test_prose_and_source_files_with_those_words_are_not_skipped(self):
        self.write("src/doc.md", "# Guide\n\nDo not edit the files in dist/ by hand.\n")
        self.write("src/tool.py", SCRIPT.read_bytes().decode("utf-8"))
        self.write("src/api.go", "// Code generated by protoc-gen-go. DO NOT EDIT.\n")
        self.write("src/list.md", "# Auto-generated files\n\n* Do not edit them by hand.\n")
        self.write("src/NOTES.MD", "* Do not edit this list.\n")
        self.write("src/more.markdown", "* Do not edit this list.\n")
        self.commit()
        areas = self.areas()
        self.assertEqual(list(areas), ["src/", "skipped"])
        self.assertEqual(self.paths(areas["src/"]),
                         ["src/NOTES.MD", "src/doc.md", "src/list.md", "src/more.markdown", "src/tool.py"])
        self.assertEqual(areas["skipped"][0][3:], ("src/api.go", None, "generated header"))

    def test_markdown_file_with_a_comment_header_is_skipped(self):
        self.write("docs/api.md", "<!-- This file is auto-generated. Do not edit. -->\n# API\n")
        self.commit()
        self.assertEqual(list(self.areas()), ["skipped"])

    def test_binary_file_with_a_header_text_is_not_skipped(self):
        (self.repo / "src").mkdir()
        (self.repo / "src/data.bin").write_bytes(b"# auto-generated\n\0\1\2")
        self.commit()
        self.assertEqual(self.areas()["src/"][0][:4], ("added", "bin", "bin", "src/data.bin"))

    def test_comment_forms_of_other_languages_are_skipped(self):
        self.write("src/a.c", "/*\n * This file is autogenerated by gen.py\n */\n")
        self.write("src/b.xml", '<?xml version="1.0"?>\n<!-- This file is auto-generated. -->\n')
        self.write("src/c.sql", "-- auto-generated schema\n")
        self.write("src/d.ini", "; do not edit\n")
        self.write("src/e.vb", "' <auto-generated/>\n")
        self.write("src/f.py", "VALUE = 1  # do not edit by hand\n")
        self.commit()
        areas = self.areas()
        self.assertEqual(self.paths(areas["src/"]), ["src/f.py"])
        self.assertEqual(sorted(self.paths(areas["skipped"])),
                         ["src/a.c", "src/b.xml", "src/c.sql", "src/d.ini", "src/e.vb"])

    def test_header_counts_only_in_the_first_ten_lines(self):
        filler = "x\n" * 9
        self.write("src/ten.py", filler + "# auto-generated\n")
        self.write("src/eleven.py", filler + "x\n# auto-generated\n")
        self.commit()
        self.assertEqual(self.paths(self.areas()["skipped"]), ["src/ten.py"])

    def test_header_of_a_deleted_file_counts(self):
        self.write("src/old.py", "# auto-generated\nx\n")
        self.commit("more")
        (self.repo / "src/old.py").unlink()
        self.commit()
        self.assertEqual(list(self.areas()), ["skipped"])

    def test_linguist_generated_set_to_true_is_skipped(self):
        self.write(".gitattributes", "gen/** linguist-generated=true\n")
        self.commit("attributes")
        self.write("gen/api.cs")
        self.commit()
        self.assertEqual(list(self.areas()), ["skipped"])

    def test_linguist_generated_is_found_from_a_subfolder(self):
        self.write(".gitattributes", "gen/** linguist-generated\n")
        self.write("sub/keep.txt")
        self.commit("attributes")
        self.write("gen/api.js")
        self.commit()
        areas = self.areas(repo=self.repo / "sub")
        self.assertEqual(list(areas), ["skipped"])
        self.assertEqual(self.paths(areas["skipped"]), ["gen/api.js"])

    def test_every_lock_file_name_is_skipped(self):
        names = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "poetry.lock",
                 "Gemfile.lock", "composer.lock", "packages.lock.json", "go.sum"]
        for name in names:
            self.write(f"locks/{name}")
        self.write("other/Yarn.Lock")
        self.commit()
        areas = self.areas()
        self.assertEqual(sorted(self.paths(areas["skipped"])), sorted(f"locks/{name}" for name in names))
        self.assertEqual(self.paths(areas["other/"]), ["other/Yarn.Lock"])

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

    def test_path_with_a_character_that_is_not_printable_is_shown_as_json(self):
        self.assertEqual(gd.show("a\tb.py"), '"a\\tb.py"')
        self.assertEqual(gd.show("a\x7fb.py"), '"a\\u007fb.py"')
        self.assertEqual(gd.show("a\u2028b.py"), '"a\\u2028b.py"')
        self.assertEqual(gd.show("a b\u00e9.py"), "a b\u00e9.py")

    def test_blob_that_git_does_not_have_is_left_out(self):
        with mock.patch.object(gd, "git", return_value=b"1111 missing\n2222 blob 3\nabc\n"):
            self.assertEqual(gd.read_blobs(".", ["1111", "2222"]), {"2222": b"abc"})

    def test_raw_records_set_the_kind_and_the_blob(self):
        old, new = "1" * 40, "2" * 40
        raw = (f":100644 120000 {old} {new} T\0link\0:100644 100644 {old} {new} C75\0src\0copy\0"
               f":100644 000000 {old} {'0' * 40} D\0gone\0:100644 100644 {old} {'0' * 40} M\0edit\0")
        changes = [gd.Change(path, None, 1, 1) for path in ("link", "copy", "gone", "edit", "not-in-raw")]
        with mock.patch.object(gd, "git", return_value=raw.encode("ascii")):
            gd.read_raw(".", "HEAD", changes)
        self.assertEqual([(c.kind, c.blob) for c in changes],
                         [("type-changed", new), ("copied", new), ("deleted", old), ("modified", None),
                          ("modified", None)])

    def test_non_ascii_paths_print_when_the_stream_is_ascii(self):
        self.write("docs/caf\u00e9.md")
        self.write("docs/\u0440\u0443\u043a.md")
        self.commit()
        env = clean_env(PYTHONIOENCODING="ascii")
        out = self.group(launch=(), env=env).stdout
        self.assertIn("docs/caf\u00e9.md", out)
        self.assertIn("docs/\u0440\u0443\u043a.md", out)

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

    def test_program_of_git_that_reads_input_does_not_block_the_script(self):
        self.write("src/a.py")
        self.commit()
        self.write("src/a.py", "y\n")
        reader = self.tmp / "read-input"
        reader.write_bytes(b"#!/bin/sh\ncat > /dev/null\n")
        os.chmod(reader, 0o755)
        self.git("config", "core.fsmonitor", shlex.quote(reader.as_posix()))
        result = run_with_open_stdin([sys.executable, "-I", SCRIPT, "--repo", self.repo, "--range", "HEAD"])
        self.git("config", "--unset", "core.fsmonitor")
        self.assertIsNotNone(result, "git waited for the input of the script")
        self.assertEqual(result[0], 0, result[2])
        self.assertIn("TOTAL files=1 ", result[1])


if __name__ == "__main__":
    unittest.main()
