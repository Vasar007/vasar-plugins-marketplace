"""Static checks of the `claude plugin eval` cases of every plugin. The tests call no model.

A case folder is a folder under <plugin>/evals/ that holds prompt.md or case.yaml.
The checks follow the eval suite reference of the Claude Code docs: the keys of
prompt.md and case.yaml, the grader types and their options, and the plugins
and scaffold fields. A small parser reads the subset of YAML that the cases use:
block mappings, block lists of scalars, quoted and plain scalars, and inline
lists and maps. Block scalars (| and >) and anchors are not supported.
"""
import json
import posixpath
import re
import shutil
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from support import REPO, tool_missing
from testkit import ScratchCase, git_init, run

PLUGIN_GLOB = "*/*/.claude-plugin/plugin.json"
EVALS = "evals"
NOT_CASE_FOLDERS = {"results", "_lib", "mocks"}
ROUTE_PREFIX = "route-"
ROUTE_TAG = "route"
MAX_TURNS = 200
MAX_SECONDS = 3600
SCAFFOLD_SHEBANG = "#!/usr/bin/env bash"
SCAFFOLD_STRICT = "set -euo pipefail"
EXECUTABLE_MODE = "100755"
LINK_MODE = "120000"
LIBRARY_SOURCE = "essentials/dev-essentials"

PROMPT_KEYS = {"schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome", "model",
               "max_turns", "timeout_seconds", "allowed_tools", "append_system_prompt", "env"}
EXECUTION_KEYS = {"prompt", "model", "max_turns", "timeout_seconds", "allowed_tools", "append_system_prompt", "env"}
CASE_YAML_KEYS = {"schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome",
                  "context", "execution"}
CONTEXT_KEYS = {"scaffold_script", "history_file", "add_dirs"}
GRADER_COMMON_KEYS = {"type", "weight", "arm"}
GRADER_OPTIONS = {
    "regex": {"pattern", "flags", "match", "target"},
    "tool_used": {"tool", "input_match", "min", "max"},
    "tool_order": {"before", "after"},
    "file_exists": {"path", "exists"},
    "llm": {"criteria", "focus"},
    "baseline": {"baseline_file", "criteria"},
}
GRADER_REQUIRED = {"regex": {"pattern"}, "tool_used": {"tool"}, "tool_order": {"before", "after"},
                   "file_exists": {"path"}, "llm": set(), "baseline": {"baseline_file"}}
ARMS = {"with-only", "both"}
TARGETS = {"last_message", "trace", "files", "mock_calls"}
MATCH_VALUE = re.compile(r"not_contains|count:\d+")
REGEX_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}
IGNORED_REGEX_FLAGS = set("gd")
# The CLI takes these flags too, but Python cannot apply them, so a sample test would give another verdict than a run.
REFUSED_REGEX_FLAGS = {
    "y": "the flag y matches only at the start of the text, so wrap the pattern in ^(?:...) and leave out the flag m",
    "u": "Python cannot check a pattern with the flag u, because the flag changes the syntax, so leave out the flag u",
    "v": "Python cannot check a pattern with the flag v, so leave out the flag v",
}

# Plugins whose eval runs load a .deps copy of a plugin that plugin.json does not declare.
# compare_versions.py makes the copy with --extra-dep. The key is the plugin folder name.
EVAL_ONLY_DEPS = {"doc-styles": {"dev-essentials"}}

# compare_versions.py copies each folder here into <plugin>/eval-stubs/ of its plugin copy.
STUBS = REPO / "tests" / "evals" / "stubs"

PAIR_FOLDER = "style-compare"
PAIR_ARMS = ("openbsd", "simple-english")
PAIR_KEYS_THAT_DIFFER = {"name", "tags", "plugins"}
PAIR_GRADERS_THAT_DIFFER = {"loaded-style"}
PAIR_SKILLS = {"openbsd": "openbsd-style-docs", "simple-english": "simple-english"}
# The one allowed difference in a prompt text: the docs prompts (ids that start with d) of the first arm name the style.
PAIR_STYLE_PHRASE = "In the OpenBSD man-page style, "
PAIR_STYLE_PHRASE_ID_PREFIX = "d"

LIBRARY_COPIES = {
    "git-fixture.sh": ["essentials/dev-essentials", "dotnet/dotnet-backend-dev"],
    "dotnet-fixture.sh": ["essentials/dev-essentials", "dotnet/dotnet-backend-dev"],
}


class YamlError(ValueError):
    """Text that the small YAML parser cannot read."""


def plain_value(text):
    if text in ("", "~", "null"):
        return None
    if text in ("true", "false"):
        return text == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


class Flow:
    """Reads one value of the flow style: a quoted string, a plain scalar, [a, b], or { k: v }."""

    ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "/": "/", " ": " "}

    def __init__(self, text):
        self.s, self.i = text, 0

    def peek(self):
        return self.s[self.i:self.i + 1]

    def skip(self):
        while self.peek() in (" ", "\t") and self.peek():
            self.i += 1

    def value(self):
        self.skip()
        char = self.peek()
        if not char:
            raise YamlError("a value is missing")
        if char == "[":
            return self.sequence()
        if char == "{":
            return self.mapping()
        if char in "\"'":
            return self.quoted()
        return self.plain()

    def plain(self):
        start = self.i
        while self.peek() and self.peek() not in ",]}":
            self.i += 1
        return plain_value(self.s[start:self.i].strip())

    def quoted(self):
        quote = self.peek()
        self.i += 1
        out = []
        while self.peek():
            char = self.peek()
            if quote == "'" and char == "'":
                if self.s[self.i + 1:self.i + 2] == "'":
                    out.append("'")
                    self.i += 2
                    continue
                self.i += 1
                return "".join(out)
            if quote == '"' and char == '"':
                self.i += 1
                return "".join(out)
            if quote == '"' and char == "\\":
                self.i += 1
                out.append(self.escape())
                continue
            out.append(char)
            self.i += 1
        raise YamlError("a quoted string is not closed")

    def escape(self):
        char = self.peek()
        self.i += 1
        if char in self.ESCAPES:
            return self.ESCAPES[char]
        width = {"x": 2, "u": 4, "U": 8}.get(char)
        digits = self.s[self.i:self.i + (width or 0)]
        if not width or not re.fullmatch(r"[0-9A-Fa-f]{%d}" % width, digits):
            raise YamlError(f"the escape \\{char} is not valid in a double-quoted string")
        self.i += width
        return chr(int(digits, 16))

    def sequence(self):
        self.i += 1
        result = []
        while True:
            self.skip()
            if self.peek() == "]":
                self.i += 1
                return result
            result.append(self.value())
            self.skip()
            if self.peek() == ",":
                self.i += 1
            elif self.peek() != "]":
                raise YamlError("a list needs a comma or a closing bracket")

    def mapping(self):
        self.i += 1
        result = {}
        while True:
            self.skip()
            if self.peek() == "}":
                self.i += 1
                return result
            if self.peek() in ("'", '"'):
                key = self.quoted()
            else:
                start = self.i
                while self.peek() and self.peek() not in ":,}":
                    self.i += 1
                key = self.s[start:self.i].strip()
            self.skip()
            if self.peek() != ":":
                raise YamlError(f"the key {key!r} needs a colon")
            self.i += 1
            result[key] = self.value()
            self.skip()
            if self.peek() == ",":
                self.i += 1
            elif self.peek() != "}":
                raise YamlError("a map needs a comma or a closing brace")

    def finish(self):
        self.skip()
        if self.peek() and not self.s[self.i:].startswith("#"):
            raise YamlError(f"unexpected text after the value: {self.s[self.i:]!r}")


def parse_value(text):
    """One value after `key:`. A plain scalar ends at a comment that starts with ' #'."""
    text = text.strip()
    if text[:1] in ("[", "{", '"', "'"):
        flow = Flow(text)
        value = flow.value()
        flow.finish()
        return value
    if text[:1] in ("|", ">", "&", "*", "!"):
        raise YamlError(f"the value {text!r} is not supported by this parser")
    return plain_value(re.split(r"\s+#", text, maxsplit=1)[0].strip())


KEY_LINE = re.compile(r"([A-Za-z0-9_.-]+):(?:\s+(.*))?")


def parse_block(lines):
    """Read the lines of a block mapping into a dict. Blank lines and comment lines are skipped."""
    entries = []
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line[:len(line) - len(line.lstrip())]:
            raise YamlError(f"line {number}: a tab is not allowed in the indent")
        entries.append((len(line) - len(line.lstrip(" ")), line.strip(), number))
    if not entries:
        return {}
    result, position = read_mapping(entries, 0, entries[0][0])
    if position < len(entries):
        raise YamlError(f"line {entries[position][2]}: unexpected indent")
    return result


def read_mapping(entries, position, indent):
    result = {}
    while position < len(entries):
        entry_indent, text, number = entries[position]
        if entry_indent < indent:
            break
        if entry_indent > indent:
            raise YamlError(f"line {number}: unexpected indent")
        match = KEY_LINE.fullmatch(text)
        if not match:
            raise YamlError(f"line {number}: cannot read {text!r} as 'key: value'")
        key, rest = match.group(1), (match.group(2) or "").strip()
        if key in result:
            raise YamlError(f"line {number}: the key {key} appears twice")
        position += 1
        if rest and not rest.startswith("#"):
            result[key] = parse_value(rest)
            continue
        following = entries[position] if position < len(entries) else None
        if following and following[1].startswith("- ") and following[0] >= indent:
            result[key], position = read_list(entries, position, following[0])
        elif following and following[0] > indent:
            result[key], position = read_mapping(entries, position, following[0])
        else:
            result[key] = None
    return result, position


def read_list(entries, position, indent):
    result = []
    while position < len(entries) and entries[position][0] == indent and entries[position][1].startswith("- "):
        result.append(parse_value(entries[position][1][2:]))
        position += 1
    return result, position


def split_frontmatter(text):
    """Return (frontmatter lines, body) of a Markdown file. Raise YamlError if there is no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise YamlError("the file does not start with a frontmatter line '---'")
    for number in range(1, len(lines)):
        if lines[number].strip() == "---":
            return lines[1:number], "\n".join(lines[number + 1:])
    raise YamlError("the frontmatter has no closing line '---'")


class Case:
    """One case folder with the files that the static checks read."""

    def __init__(self, path, plugin_root):
        self.path = Path(path)
        self.plugin_root = Path(plugin_root)
        self.errors = []
        self.prompt, self.prompt_body, self.case_yaml, self.graders = {}, "", None, {}
        self.has_prompt = (self.path / "prompt.md").is_file()
        self.has_case_yaml = (self.path / "case.yaml").is_file()
        if self.has_prompt:
            try:
                lines, self.prompt_body = split_frontmatter((self.path / "prompt.md").read_text(encoding="utf-8"))
                self.prompt = parse_block(lines)
            except YamlError as exc:
                self.errors.append(f"{self.label}/prompt.md: {exc}")
        if self.has_case_yaml:
            try:
                self.case_yaml = parse_block((self.path / "case.yaml").read_text(encoding="utf-8").splitlines())
            except YamlError as exc:
                self.errors.append(f"{self.label}/case.yaml: {exc}")
        for grader in sorted((self.path / "graders").glob("*.md")):
            try:
                lines, body = split_frontmatter(grader.read_text(encoding="utf-8"))
                self.graders[grader.stem] = (parse_block(lines), body)
            except YamlError as exc:
                self.errors.append(f"{self.label}/graders/{grader.name}: {exc}")

    @property
    def label(self):
        try:
            return self.path.relative_to(REPO).as_posix()
        except ValueError:
            return self.path.as_posix()

    def field(self, key):
        """A case field. The frontmatter of prompt.md overrides case.yaml."""
        if key in self.prompt:
            return self.prompt[key]
        return (self.case_yaml or {}).get(key)

    @property
    def name(self):
        return self.field("name") or self.path.name

    @property
    def tags(self):
        value = self.field("tags")
        return value if isinstance(value, list) else []


def find_case_folders(evals):
    """The case folders under an eval folder, as sorted paths."""
    found = []

    def walk(folder):
        if (folder / "prompt.md").is_file() or (folder / "case.yaml").is_file():
            found.append(folder)
            return
        for child in sorted(folder.iterdir()):
            if child.is_dir() and child.name not in NOT_CASE_FOLDERS and not child.name.startswith("."):
                walk(child)

    if evals.is_dir():
        walk(evals)
    return found


def load_cases(plugin_root):
    return [Case(folder, plugin_root) for folder in find_case_folders(Path(plugin_root) / EVALS)]


def plugin_roots(repo=REPO):
    return sorted(path.parent.parent for path in Path(repo).glob(PLUGIN_GLOB))


def duplicate_name_problems(cases):
    """Case names that appear twice in one plugin."""
    seen, problems = {}, []
    for case in cases:
        key = (case.plugin_root, case.name)
        if key in seen:
            problems.append(f"{case.label}: the name {case.name} is also used by {seen[key]}")
        seen[key] = case.label
    return problems


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def unknown_keys(where, data, allowed):
    return [f"{where}: unknown key {key}" for key in data if key not in allowed]


def key_problems(case):
    """Unknown keys and limits in prompt.md and case.yaml."""
    problems = list(case.errors)
    if case.has_prompt:
        problems += unknown_keys(f"{case.label}/prompt.md", case.prompt, PROMPT_KEYS)
    if case.case_yaml is not None:
        where = f"{case.label}/case.yaml"
        problems += unknown_keys(where, case.case_yaml, CASE_YAML_KEYS)
        if "graders" in case.case_yaml:
            problems.append(f"{where}: put the graders in graders/*.md, because this parser reads no graders list")
        context, execution = case.case_yaml.get("context") or {}, case.case_yaml.get("execution") or {}
        if not isinstance(context, dict) or not isinstance(execution, dict):
            problems.append(f"{where}: context and execution must be mappings")
        else:
            problems += unknown_keys(f"{where} context", context, CONTEXT_KEYS)
            problems += unknown_keys(f"{where} execution", execution, EXECUTION_KEYS)
    limits = [(f"{case.label}/prompt.md", case.prompt)]
    if case.case_yaml is not None and isinstance(case.case_yaml.get("execution"), dict):
        limits.append((f"{case.label}/case.yaml execution", case.case_yaml["execution"]))
    for where, data in limits:
        for key, top in (("max_turns", MAX_TURNS), ("timeout_seconds", MAX_SECONDS)):
            value = data.get(key)
            if value is not None and not (isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= top):
                problems.append(f"{where}: {key} must be a whole number from 1 to {top}, but it is {value!r}")
    return problems


def regex_problems(where, key, pattern, flags=""):
    if not isinstance(pattern, str):
        return [f"{where}: {key} must be a string"]
    refused = [f"{where}: {REFUSED_REGEX_FLAGS[f]}" for f in sorted(set(flags) & REFUSED_REGEX_FLAGS.keys())]
    if refused:
        return refused
    bad = [f for f in flags if f not in REGEX_FLAGS and f not in IGNORED_REGEX_FLAGS]
    if bad:
        return [f"{where}: the regex flags {''.join(bad)} are not known"]
    try:
        re.compile(pattern, sum(REGEX_FLAGS.get(f, 0) for f in flags))
    except re.error as exc:
        return [f"{where}: {key} is not a valid regex: {exc}"]
    return []


def target_problems(where, key, value):
    if isinstance(value, str) and value in TARGETS:
        return []
    if isinstance(value, dict) and value.get("source") == "file" and isinstance(value.get("path"), str) \
            and set(value) == {"source", "path"}:
        return []
    return [f"{where}: {key} must be one of {sorted(TARGETS)} or a map with source: file and a path"]


def step_problems(where, key, value):
    if isinstance(value, str):
        return []
    if isinstance(value, dict) and set(value) <= {"tool", "input_match"} and isinstance(value.get("tool"), str):
        return regex_problems(where, f"{key} input_match", value["input_match"]) if "input_match" in value else []
    return [f"{where}: {key} must be a tool name or a map with tool and input_match"]


def one_grader_problems(case, name, meta, body):
    where = f"{case.label}/graders/{name}.md"
    kind = meta.get("type")
    if kind not in GRADER_OPTIONS:
        return [f"{where}: type must be one of {sorted(GRADER_OPTIONS)}, but it is {kind!r}"]
    problems = unknown_keys(where, meta, GRADER_COMMON_KEYS | GRADER_OPTIONS[kind])
    problems += [f"{where}: a {kind} grader needs {key}" for key in sorted(GRADER_REQUIRED[kind] - set(meta))]
    if "weight" in meta and not (is_number(meta["weight"]) and meta["weight"] > 0):
        problems.append(f"{where}: weight must be a positive number")
    if "arm" in meta and meta["arm"] not in ARMS:
        problems.append(f"{where}: arm must be one of {sorted(ARMS)}")
    if kind == "regex":
        flags = meta.get("flags", "")
        problems += regex_problems(where, "pattern", meta.get("pattern"), flags if isinstance(flags, str) else "")
        if not isinstance(flags, str):
            problems.append(f"{where}: flags must be a string")
        if "match" in meta and not (isinstance(meta["match"], str) and MATCH_VALUE.fullmatch(meta["match"])):
            problems.append(f"{where}: match must be not_contains or count:N")
        if "target" in meta:
            problems += target_problems(where, "target", meta["target"])
    elif kind == "tool_used":
        if not isinstance(meta.get("tool"), str):
            problems.append(f"{where}: tool must be a tool name")
        if "input_match" in meta:
            problems += regex_problems(where, "input_match", meta["input_match"])
        counts = {key: meta[key] for key in ("min", "max") if key in meta}
        for key, value in counts.items():
            if not (isinstance(value, int) and not isinstance(value, bool) and value >= 0):
                problems.append(f"{where}: {key} must be a whole number of 0 or more")
        if len(counts) == 2 and all(isinstance(v, int) for v in counts.values()) and counts["min"] > counts["max"]:
            problems.append(f"{where}: min is above max")
    elif kind == "tool_order":
        for key in ("before", "after"):
            if key in meta:
                problems += step_problems(where, key, meta[key])
    elif kind == "file_exists":
        if not isinstance(meta.get("path"), str):
            problems.append(f"{where}: path must be a glob string")
        if "exists" in meta and not isinstance(meta["exists"], bool):
            problems.append(f"{where}: exists must be true or false")
    else:
        if "focus" in meta:
            problems += target_problems(where, "focus", meta["focus"])
        if kind == "llm" and not (body.strip() or meta.get("criteria")):
            problems.append(f"{where}: an llm grader needs a rubric in the file body or in criteria")
        if kind == "baseline" and isinstance(meta.get("baseline_file"), str) \
                and not (case.path / meta["baseline_file"]).is_file():
            problems.append(f"{where}: baseline_file {meta['baseline_file']} does not exist")
    return problems


def grader_problems(case):
    """A case needs a grader, and each grader needs a documented type with only the options of that type."""
    if not case.graders:
        return [f"{case.label}: the case has no grader in graders/*.md"]
    return [p for name, (meta, body) in case.graders.items() for p in one_grader_problems(case, name, meta, body)]


def route_problems(case):
    """A case with a route grader needs the tag route, so that a run can pick the route cases."""
    routes = [name for name in case.graders if name.startswith(ROUTE_PREFIX)]
    if routes and ROUTE_TAG not in case.tags:
        return [f"{case.label}: the route graders {', '.join(routes)} need the tag {ROUTE_TAG}"]
    return []


def dependency_names(plugin_root):
    """The plugin names in `dependencies` of the manifest of a plugin."""
    try:
        entries = json.loads((Path(plugin_root) / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    names = set()
    for entry in entries.get("dependencies") or []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if isinstance(name, str):
            names.add(name.partition("@")[0])
    return names


def in_own_case_subfolder(target, case_dir):
    """True if target is below the case folder, and is not the graders or mocks folder or inside them."""
    if target == case_dir or not target.is_relative_to(case_dir):
        return False
    return not any(target.is_relative_to(case_dir / name) for name in ("graders", "mocks"))


def plugin_entry_problems(case, stubs=STUBS):
    """Each entry of `plugins` must be a plugin folder. A .deps copy of a declared dependency also counts.

    A .deps copy of a plugin in EVAL_ONLY_DEPS for this plugin counts too.
    An eval-stubs/<name> entry counts when tests/evals/stubs/<name> is a plugin folder.

    claude plugin eval refuses a plugin in the eval folder unless the plugin sits in its own subfolder of the case.
    """
    entries = case.field("plugins")
    if entries is None:
        return []
    if not isinstance(entries, list) or not all(isinstance(e, str) for e in entries):
        return [f"{case.label}: plugins must be a list of strings"]
    problems = []
    evals = (case.plugin_root / EVALS).resolve()
    case_dir = case.path.resolve()
    for entry in entries:
        target = (case.path / entry).resolve()
        if target != evals and target.is_relative_to(evals) and not in_own_case_subfolder(target, case_dir):
            problems.append(f"{case.label}: the plugins entry {entry} is in {EVALS}/ but not in its own subfolder "
                            f"of the case, so claude plugin eval refuses it. Move the plugin out of {EVALS}/")
            continue
        if (target / ".claude-plugin" / "plugin.json").is_file():
            continue
        if target.parent == (case.plugin_root / "eval-stubs").resolve() and (stubs / target.name / ".claude-plugin" / "plugin.json").is_file():
            continue
        deps = (case.plugin_root / ".deps").resolve()
        allowed = dependency_names(case.plugin_root) | EVAL_ONLY_DEPS.get(case.plugin_root.name, set())
        if target.parent == deps and target.name in allowed:
            continue
        problems.append(f"{case.label}: the plugins entry {entry} is not a plugin folder, and it is not a .deps copy "
                        f"of a dependency of the plugin or of an eval-only dependency in EVAL_ONLY_DEPS, "
                        f"and it is not a stand-in in tests/evals/stubs")
    return problems


def without_style_phrase(pair_id, body):
    """The prompt text of the first arm, without the style phrase that a docs case may start with."""
    body = body.strip()
    if pair_id.startswith(PAIR_STYLE_PHRASE_ID_PREFIX) and body.startswith(PAIR_STYLE_PHRASE):
        rest = body[len(PAIR_STYLE_PHRASE):]
        return rest[:1].upper() + rest[1:]
    return body


def pair_problems(cases):
    """The two arms of a style comparison must differ in the style only.

    A pair is <PAIR_FOLDER>/<arm>/<id> for each arm in PAIR_ARMS. The prompt text, the other frontmatter keys, and
    the graders must be equal, except the keys in PAIR_KEYS_THAT_DIFFER and the graders in PAIR_GRADERS_THAT_DIFFER.
    Each arm must have the graders in PAIR_GRADERS_THAT_DIFFER, and the loaded-style grader must name the skill of its arm.
    The first arm must start the prompt text of a docs case with PAIR_STYLE_PHRASE. That phrase is the only allowed difference.
    In the first arm, the loaded-style grader of a case that is not a docs case must have min 0 and max 0.
    """
    groups = {}
    for case in cases:
        parts = case.path.parts
        if PAIR_FOLDER not in parts:
            continue
        rest = parts[len(parts) - parts[::-1].index(PAIR_FOLDER):]
        if len(rest) == 2 and rest[0] in PAIR_ARMS:
            groups.setdefault((str(case.plugin_root), rest[1]), {})[rest[0]] = case
    problems = []
    for (root, pair_id), arms in sorted(groups.items()):
        missing = [arm for arm in PAIR_ARMS if arm not in arms]
        if missing:
            problems.append(f"{PAIR_FOLDER}/{pair_id}: the arm {', '.join(missing)} is missing")
            continue
        first, second = (arms[arm] for arm in PAIR_ARMS)
        where = f"{first.label} and {second.label}"
        if without_style_phrase(pair_id, first.prompt_body) != second.prompt_body.strip():
            problems.append(f"{where}: the prompt text differs")
        keys = [{k: v for k, v in case.prompt.items() if k not in PAIR_KEYS_THAT_DIFFER} for case in (first, second)]
        if keys[0] != keys[1]:
            problems.append(f"{where}: the frontmatter differs in a key other than "
                            f"{', '.join(sorted(PAIR_KEYS_THAT_DIFFER))}")
        graders = [{n: g for n, g in case.graders.items() if n not in PAIR_GRADERS_THAT_DIFFER}
                   for case in (first, second)]
        if graders[0] != graders[1]:
            different = sorted(n for n in set(graders[0]) | set(graders[1]) if graders[0].get(n) != graders[1].get(n))
            problems.append(f"{where}: the graders differ: {', '.join(different)}")
        for arm, case in zip(PAIR_ARMS, (first, second)):
            for name in sorted(PAIR_GRADERS_THAT_DIFFER - set(case.graders)):
                problems.append(f"{case.label}: the arm needs the grader {name}")
            loaded = case.graders.get("loaded-style")
            if loaded and f'{PAIR_SKILLS[arm]}"' not in str(loaded[0].get("input_match", "")):
                problems.append(f"{case.label}: the input_match of the grader loaded-style must name the skill "
                                f"{PAIR_SKILLS[arm]}")
        is_docs_case = pair_id.startswith(PAIR_STYLE_PHRASE_ID_PREFIX)
        if is_docs_case and not first.prompt_body.strip().startswith(PAIR_STYLE_PHRASE):
            problems.append(f"{first.label}: the prompt text of a docs case must start with {PAIR_STYLE_PHRASE!r}, "
                            f"or the skill of the arm does not load")
        loaded = first.graders.get("loaded-style")
        if loaded and not is_docs_case and (loaded[0].get("min"), loaded[0].get("max")) != (0, 0):
            problems.append(f"{first.label}: the grader loaded-style of a case that is not a docs case must have "
                            f"min: 0 and max: 0, because the skill must not load")
    return problems


def scaffold_problems(case, modes):
    """The case.yaml of a fixture case, and the scaffold script that it names. Modes maps a path to its git mode."""
    if case.case_yaml is None:
        return []
    where = f"{case.label}/case.yaml"
    problems = []
    if case.case_yaml.get("schema_version") != "1.1":
        problems.append(f'{where}: schema_version must be the string "1.1"')
    if case.case_yaml.get("name") != case.path.name:
        problems.append(f"{where}: name {case.case_yaml.get('name')!r} must equal the folder name {case.path.name}")
    script = (case.case_yaml.get("context") or {}).get("scaffold_script") if isinstance(
        case.case_yaml.get("context"), dict) else None
    if script is None:
        return problems
    path = case.path / script
    if not isinstance(script, str) or not path.is_file():
        return problems + [f"{where}: the scaffold_script {script} does not exist"]
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    head = [line for line in text.splitlines()[:6]]
    if not head or head[0] != SCAFFOLD_SHEBANG:
        problems.append(f"{case.label}/{script}: the first line must be {SCAFFOLD_SHEBANG}")
    if SCAFFOLD_STRICT not in head:
        problems.append(f"{case.label}/{script}: the script must start with {SCAFFOLD_STRICT}")
    if b"\r" in data:
        problems.append(f"{case.label}/{script}: the script has a CR character, but it needs LF line ends only")
    mode = modes.get(f"{case.label}/{script}")
    if mode != EXECUTABLE_MODE:
        problems.append(f"{case.label}/{script}: the git mode is {mode}, but it must be {EXECUTABLE_MODE}. "
                        f"Run: git add --chmod=+x {case.label}/{script}")
    return problems


def copy_problems(repo=REPO):
    """The shared fixture libraries must exist in every plugin that needs them, with equal bytes."""
    problems = []
    for name, roots in LIBRARY_COPIES.items():
        copies = {}
        for root in roots:
            path = Path(repo) / root / EVALS / "_lib" / name
            if path.is_file():
                copies[root] = path.read_bytes()
            else:
                problems.append(f"{root}/{EVALS}/_lib/{name} does not exist")
        if len(set(copies.values())) > 1:
            problems.append(f"the copies of {name} differ: {', '.join(sorted(copies))}")
    return problems


def link_target(path, repo=REPO):
    """The repo path that the git symlink at path names, read from the index, so a checkout with no links works too."""
    text = run(["git", "-C", repo, "cat-file", "blob", f":{path}"], check=True).stdout
    return posixpath.normpath(posixpath.join(posixpath.dirname(path), text))


def link_problems(modes, repo=REPO):
    """Each shared library outside dev-essentials must be a git symlink to the file of the same name in dev-essentials."""
    problems = []
    for name, roots in LIBRARY_COPIES.items():
        source = f"{LIBRARY_SOURCE}/{EVALS}/_lib/{name}"
        for root in roots:
            if root == LIBRARY_SOURCE:
                continue
            path = f"{root}/{EVALS}/_lib/{name}"
            if modes.get(path) != LINK_MODE:
                problems.append(f"{path}: the git mode is {modes.get(path)}, but it must be {LINK_MODE}, a link to {source}")
            elif link_target(path, repo) != source:
                problems.append(f"{path}: the link names {link_target(path, repo)}, but it must name {source}")
            elif not (Path(repo) / path).is_symlink():
                problems.append(f"{path}: git checked out the link as a plain file. Run: git config core.symlinks true, "
                                f"turn on the Developer Mode of Windows, then run: git checkout -- {path}")
    return problems


def blob_id(content):
    """The git blob id of the bytes, as `git hash-object --stdin` prints it."""
    done = run(["git", "hash-object", "--stdin"], stdin=content, check=True, text=False)
    return done.stdout.decode().strip()


def blob_path(content):
    """The path of a loose object for the bytes, as a grader of a case writes it."""
    blob = blob_id(content)
    return f".git/objects/{blob[:2]}/{blob[2:]}"


SCRATCH_ASSIGNMENT = re.compile(r"^SCRATCH_CONTENT='([^']*)'$", re.MULTILINE)


def scratch_problems(case):
    """The `scratch-not-staged` grader of the untracked-file case must name the blob of the scaffold content.

    The scaffold holds the content in one line, SCRATCH_CONTENT='...', and writes it with printf '%s'.
    """
    scaffold = case.path / "scaffold.sh"
    grader = case.graders.get("scratch-not-staged")
    if grader is None or not scaffold.is_file():
        return [f"{case.label}: the case needs scaffold.sh and the grader scratch-not-staged"]
    match = SCRATCH_ASSIGNMENT.search(scaffold.read_text(encoding="utf-8"))
    if not match:
        return [f"{case.label}/scaffold.sh: no line SCRATCH_CONTENT='...' found"]
    expected = blob_path(match.group(1).encode())
    actual = (grader[0].get("path") or "").replace("\\", "/")
    if actual != expected:
        return [f"{case.label}/graders/scratch-not-staged.md: path is {actual}, but the content gives {expected}"]
    return []


def tracked_modes(repo=REPO):
    """Map each tracked path to its git mode, from the index."""
    out = run(["git", "-C", repo, "ls-files", "-s", "-z"], check=True, text=False).stdout
    modes = {}
    for entry in out.decode("utf-8", errors="replace").split("\0"):
        meta, _, path = entry.partition("\t")
        if path:
            modes[path] = meta.split()[0]
    return modes


def shell_file_problems(modes, repo=REPO, bash=None):
    """Each tracked .sh file under an eval folder: LF only, executable in the index, and valid Bash syntax.

    A git symlink is accepted only in an evals/_lib folder, to an executable .sh file in an evals/_lib folder.
    The loop checks the target under its own path.
    """
    lib = f"/{EVALS}/_lib/"
    problems = []
    for path, mode in sorted(modes.items()):
        if not (path.endswith(".sh") and f"/{EVALS}/" in path):
            continue
        if mode == LINK_MODE:
            target = link_target(path, repo)
            if lib not in path or lib not in target or modes.get(target) != EXECUTABLE_MODE:
                problems.append(f"{path}: a link must sit in an {EVALS}/_lib folder and name an executable .sh file "
                                f"in an {EVALS}/_lib folder, but it names {target}")
            continue
        if not (Path(repo) / path).is_file():
            continue
        data = (Path(repo) / path).read_bytes()
        if b"\r" in data:
            problems.append(f"{path}: the file has a CR character, but it needs LF line ends only")
        if mode != EXECUTABLE_MODE:
            problems.append(f"{path}: the git mode is {mode}, but it must be {EXECUTABLE_MODE}")
        if bash:
            done = run([bash, "-n"], stdin=data, text=False)
            if done.returncode != 0:
                problems.append(f"{path}: bash -n failed: {done.stderr.decode(errors='replace').strip()}")
    return problems


class ParserTests(unittest.TestCase):
    def test_scalars(self):
        self.assertEqual(parse_value("5"), 5)
        self.assertEqual(parse_value("-2"), -2)
        self.assertEqual(parse_value("0.5"), 0.5)
        self.assertIs(parse_value("true"), True)
        self.assertIs(parse_value("false"), False)
        self.assertIsNone(parse_value("null"))
        self.assertEqual(parse_value("some text # a comment"), "some text")
        self.assertEqual(parse_value("not_contains"), "not_contains")

    def test_quoted_strings(self):
        self.assertEqual(parse_value("'it''s'"), "it's")
        self.assertEqual(parse_value(r"'\tcommit: (?!fixture:)'"), r"\tcommit: (?!fixture:)")
        self.assertEqual(parse_value('"count:2"'), "count:2")
        self.assertEqual(parse_value(r'"a\x60b\n"'), "a`b\n")
        self.assertEqual(parse_value("'a' # note"), "a")
        with self.assertRaises(YamlError):
            parse_value(r'"\d"')
        with self.assertRaises(YamlError):
            parse_value("'open")

    def test_inline_lists_and_maps(self):
        self.assertEqual(parse_value("[Skill, Read, Glob]"), ["Skill", "Read", "Glob"])
        self.assertEqual(parse_value('["../..", "../../_stubs/github"]'), ["../..", "../../_stubs/github"])
        self.assertEqual(parse_value("[]"), [])
        self.assertEqual(parse_value("{ source: file, path: .git/logs/HEAD }"),
                         {"source": "file", "path": ".git/logs/HEAD"})
        self.assertEqual(parse_value("{ tool: Bash, input_match: 'git commit' }"),
                         {"tool": "Bash", "input_match": "git commit"})
        with self.assertRaises(YamlError):
            parse_value("[a, b")
        with self.assertRaises(YamlError):
            parse_value("[a] extra")

    def test_unsupported_values(self):
        for text in ("|", ">", "&anchor x", "*alias"):
            with self.subTest(text=text), self.assertRaises(YamlError):
                parse_value(text)

    def test_block_mapping_with_nesting_and_lists(self):
        lines = ['schema_version: "1.1"', "name: demo", "tags: [a, b]", "context:", "  scaffold_script: scaffold.sh",
                 "  add_dirs:", "    - resources", "    - more", "# comment", "", "runs: 3"]
        self.assertEqual(parse_block(lines), {"schema_version": "1.1", "name": "demo", "tags": ["a", "b"],
                                              "context": {"scaffold_script": "scaffold.sh",
                                                          "add_dirs": ["resources", "more"]}, "runs": 3})

    def test_block_mapping_errors(self):
        for lines in (["a: 1", "a: 2"], ["a: 1", "  b: 2"], ["just text"], ["\ta: 1"]):
            with self.subTest(lines=lines), self.assertRaises(YamlError):
                parse_block(lines)

    def test_frontmatter(self):
        lines, body = split_frontmatter("---\ntype: regex\n---\nBody line.\n")
        self.assertEqual((lines, body), (["type: regex"], "Body line."))
        for text in ("no frontmatter\n", "---\ntype: regex\n"):
            with self.subTest(text=text), self.assertRaises(YamlError):
                split_frontmatter(text)

    def test_blob_path_of_known_content(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        self.assertEqual(blob_id(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(blob_path(b"hello\n"), ".git/objects/ce/013625030ba8dba906f756967f9e9ca394464a")


class CaseFiles(ScratchCase):
    """Helpers that build a plugin with cases in a temporary folder."""

    def setUp(self):
        super().setUp()
        self.plugin = self.tmp / "group" / "demo"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "demo", "version": "1.0.0", "dependencies": ["helper"]}), encoding="utf-8")

    def write(self, relative, text, plugin=None):
        path = (plugin or self.plugin) / EVALS / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def case(self, name="demo-case", prompt="---\ntags: [demo]\n---\nDo it.\n", graders=None, extra=None):
        self.write(f"{name}/prompt.md", prompt)
        for grader, text in (graders if graders is not None else {"ok": "---\ntype: regex\npattern: ok\n---\n"}).items():
            self.write(f"{name}/graders/{grader}.md", text)
        for relative, text in (extra or {}).items():
            self.write(f"{name}/{relative}", text)
        return Case(self.plugin / EVALS / name, self.plugin)


class DiscoveryTests(CaseFiles):
    def test_finds_cases_in_nested_folders_and_skips_support_folders(self):
        self.case("group-a/first")
        self.case("second")
        self.write("_lib/helper.sh", "echo hi\n")
        self.write("_stubs/github/note.txt", "x")
        self.write("results/run/prompt.md", "x")
        self.write("mocks/server/tool.md", "x")
        names = [folder.name for folder in find_case_folders(self.plugin / EVALS)]
        self.assertEqual(names, ["first", "second"])

    def test_a_case_with_only_a_case_yaml_is_a_case(self):
        self.write("fixture-case/case.yaml", 'schema_version: "1.1"\nname: fixture-case\n')
        self.assertEqual([f.name for f in find_case_folders(self.plugin / EVALS)], ["fixture-case"])


class CaseCheckTests(CaseFiles):
    def test_a_good_case_has_no_problem(self):
        case = self.case(prompt="---\nmax_turns: 200\ntimeout_seconds: 3600\ntags: [demo]\n---\nDo it.\n")
        for check in (key_problems, grader_problems, route_problems, plugin_entry_problems):
            self.assertEqual(check(case), [], check.__name__)

    def test_unique_names(self):
        self.case("one/same")
        self.case("two/same")
        problems = duplicate_name_problems(load_cases(self.plugin))
        self.assertEqual(len(problems), 1)
        self.assertIn("the name same is also used by", problems[0])

    def test_name_in_the_frontmatter_counts_as_the_case_name(self):
        self.case("one/first", prompt="---\nname: shared\n---\nDo it.\n")
        self.case("two/second", prompt="---\nname: shared\n---\nDo it.\n")
        self.assertEqual(len(duplicate_name_problems(load_cases(self.plugin))), 1)

    def test_unknown_key_in_prompt_md(self):
        problems = key_problems(self.case(prompt="---\nbad_key: 1\n---\nDo it.\n"))
        self.assertEqual(len(problems), 1)
        self.assertIn("unknown key bad_key", problems[0])

    def test_limits_above_the_maximum(self):
        problems = key_problems(self.case(prompt="---\nmax_turns: 201\ntimeout_seconds: 3601\n---\nDo it.\n"))
        self.assertEqual(len(problems), 2)

    def test_a_copy_of_a_real_case_with_a_bad_key_fails(self):
        real = next((c for plugin in plugin_roots() for c in load_cases(plugin) if c.has_prompt), None)
        if real is None:
            self.skipTest("the repository has no case yet")
        copy = self.plugin / EVALS / "copy"
        shutil.copytree(real.path, copy)
        prompt = copy / "prompt.md"
        text = prompt.read_text(encoding="utf-8").replace("---", "---\nbad_key: 1", 1)
        prompt.write_text(text, encoding="utf-8")
        case = Case(copy, self.plugin)
        self.assertEqual(Case(real.path, real.plugin_root).errors, [])
        self.assertTrue(any("unknown key bad_key" in p for p in key_problems(case)), key_problems(case))

    def test_case_without_grader(self):
        self.assertEqual(len(grader_problems(self.case(graders={}))), 1)

    def test_grader_problems(self):
        bad = {
            "no-type": "---\npattern: a\n---\n",
            "wrong-type": "---\ntype: script\n---\n",
            "wrong-option": "---\ntype: regex\npattern: a\ninput_match: b\n---\n",
            "missing-pattern": "---\ntype: regex\n---\n",
            "bad-regex": "---\ntype: regex\npattern: '('\n---\n",
            "bad-flag": "---\ntype: regex\npattern: a\nflags: q\n---\n",
            "sticky-flag": "---\ntype: regex\npattern: a\nflags: y\n---\n",
            "bad-match": "---\ntype: regex\npattern: a\nmatch: never\n---\n",
            "bad-target": "---\ntype: regex\npattern: a\ntarget: stdout\n---\n",
            "bad-weight": "---\ntype: regex\npattern: a\nweight: 0\n---\n",
            "bad-arm": "---\ntype: regex\npattern: a\narm: none\n---\n",
            "min-above-max": "---\ntype: tool_used\ntool: Agent\nmin: 2\nmax: 1\n---\n",
            "missing-tool": "---\ntype: tool_used\n---\n",
            "bad-exists": "---\ntype: file_exists\npath: a.txt\nexists: no\n---\n",
            "empty-llm": "---\ntype: llm\n---\n",
            "missing-baseline": "---\ntype: baseline\nbaseline_file: none.jsonl\n---\n",
            "half-order": "---\ntype: tool_order\nbefore: Read\n---\n",
        }
        case = self.case(graders=bad)
        problems = grader_problems(case)
        for name in bad:
            with self.subTest(grader=name):
                self.assertTrue(any(f"graders/{name}.md" in p for p in problems), problems)

    def test_a_flag_that_python_cannot_apply_is_refused(self):
        self.assertEqual(regex_problems("g.md", "pattern", "a", "my"),
                         ["g.md: the flag y matches only at the start of the text, so wrap the pattern in ^(?:...) and "
                          "leave out the flag m"])
        self.assertEqual(regex_problems("g.md", "pattern", "a", "v"),
                         ["g.md: Python cannot check a pattern with the flag v, so leave out the flag v"])
        self.assertEqual(regex_problems("g.md", "pattern", "a", "u"),
                         ["g.md: Python cannot check a pattern with the flag u, because the flag changes the syntax, so "
                          "leave out the flag u"])
        self.assertEqual(regex_problems("g.md", "pattern", "a", "gimsd"), [])

    def test_good_graders_of_every_type(self):
        good = {
            "regex": "---\ntype: regex\npattern: 'a'\nflags: i\nmatch: \"count:2\"\n"
                     "target: { source: file, path: src/a.py }\n---\n",
            "not-contains": "---\ntype: regex\npattern: 'a'\nmatch: not_contains\ntarget: mock_calls\n---\n",
            "used": "---\ntype: tool_used\ntool: Skill\ninput_match: '\"skill\"\\s*:\\s*\"x\"'\nmin: 0\nmax: 0\n---\n",
            "order": "---\ntype: tool_order\nbefore: Read\nafter: { tool: Edit, input_match: a }\nweight: 2\n---\n",
            "exists": "---\ntype: file_exists\npath: '.remote/**'\nexists: false\narm: both\n---\n",
            "judge": "---\ntype: llm\nfocus: trace\n---\nPASS if good.\n",
        }
        self.assertEqual(grader_problems(self.case(graders=good)), [])

    def test_route_grader_needs_the_route_tag(self):
        graders = {"route-skill-fired": "---\ntype: tool_used\ntool: Skill\n---\n"}
        self.assertEqual(len(route_problems(self.case(graders=graders))), 1)
        tagged = self.case("tagged", prompt="---\ntags: [demo, route]\n---\nDo it.\n", graders=graders)
        self.assertEqual(route_problems(tagged), [])

    def test_plugins_entries(self):
        helper = self.tmp / "other" / "helper"
        (helper / ".claude-plugin").mkdir(parents=True)
        (helper / ".claude-plugin" / "plugin.json").write_text('{"name": "helper"}', encoding="utf-8")
        for stub in (self.tmp / "stubs" / "github", self.plugin / EVALS / "probes" / "own" / "github-stub"):
            (stub / ".claude-plugin").mkdir(parents=True)
            (stub / ".claude-plugin" / "plugin.json").write_text('{"name": "github"}', encoding="utf-8")
        entries = '["../../..", "../../../eval-stubs/github", "../../../.deps/helper"]'
        good = self.case("probes/good", prompt=f"---\nplugins: {entries}\n---\nx\n")
        stubs = self.tmp / "stubs"
        self.assertEqual(plugin_entry_problems(good, stubs=stubs), [])
        own = self.case("probes/own", prompt='---\nplugins: ["../../..", "github-stub"]\n---\nx\n')
        self.assertEqual(plugin_entry_problems(own, stubs=stubs), [])
        entries = '["../../..", "../../../eval-stubs/missing", "../../../.deps/unknown"]'
        bad = self.case("probes/bad", prompt=f"---\nplugins: {entries}\n---\nx\n")
        self.assertEqual(len(plugin_entry_problems(bad, stubs=stubs)), 2)

    def test_plugins_entry_allows_a_deps_copy_of_an_eval_only_dependency(self):
        entries = '["../../..", "../../../.deps/extra"]'
        case = self.case("probes/extra", prompt=f"---\nplugins: {entries}\n---\nx\n")
        self.assertEqual(len(plugin_entry_problems(case)), 1)
        with mock.patch.dict(EVAL_ONLY_DEPS, {self.plugin.name: {"extra"}}):
            self.assertEqual(plugin_entry_problems(case), [])

    def test_plugins_entry_with_an_unlisted_deps_copy_still_fails(self):
        entries = '["../../..", "../../../.deps/other"]'
        case = self.case("probes/other", prompt=f"---\nplugins: {entries}\n---\nx\n")
        with mock.patch.dict(EVAL_ONLY_DEPS, {self.plugin.name: {"extra"}, "elsewhere": {"other"}}):
            problems = plugin_entry_problems(case)
        self.assertEqual(len(problems), 1)
        self.assertIn("EVAL_ONLY_DEPS", problems[0])

    def test_plugins_entry_in_the_eval_folder_must_be_in_its_own_case_subfolder(self):
        stub = self.plugin / EVALS / "_stubs" / "github" / ".claude-plugin"
        stub.mkdir(parents=True)
        (stub / "plugin.json").write_text('{"name": "github"}', encoding="utf-8")
        for entries in ('["../../_stubs/github"]', '["."]', '["graders"]', '["mocks/github"]'):
            with self.subTest(entries=entries):
                case = self.case("probes/demo", prompt=f"---\nplugins: {entries}\n---\nx\n")
                problems = plugin_entry_problems(case)
                self.assertTrue(any("refuses it" in problem for problem in problems), problems)

    def scaffold_case(self, yaml, script="#!/usr/bin/env bash\nset -euo pipefail\n", name="fixture-case"):
        extra = {"case.yaml": yaml}
        if script is not None:
            extra["scaffold.sh"] = script
        return self.case(name, extra=extra)

    GOOD_YAML = 'schema_version: "1.1"\nname: fixture-case\ncontext:\n  scaffold_script: scaffold.sh\n'

    def test_scaffold_checks_pass_for_a_good_case(self):
        case = self.scaffold_case(self.GOOD_YAML)
        modes = {f"{case.label}/scaffold.sh": EXECUTABLE_MODE}
        self.assertEqual(scaffold_problems(case, modes), [])

    def test_scaffold_checks_find_each_problem(self):
        modes = lambda case: {f"{case.label}/scaffold.sh": "100644"}
        cases = {
            "version": self.scaffold_case(self.GOOD_YAML.replace("1.1", "1.0"), name="c1"),
            "name": self.scaffold_case(self.GOOD_YAML.replace("name: fixture-case", "name: other"), name="c2"),
            "shebang": self.scaffold_case(self.GOOD_YAML, script="#!/bin/sh\nset -euo pipefail\n", name="c3"),
            "strict": self.scaffold_case(self.GOOD_YAML, script="#!/usr/bin/env bash\necho hi\n", name="c4"),
            "crlf": self.scaffold_case(self.GOOD_YAML, script="#!/usr/bin/env bash\r\nset -euo pipefail\r\n",
                                       name="c5"),
            "missing": self.scaffold_case(self.GOOD_YAML, script=None, name="c6"),
        }
        for label, case in cases.items():
            with self.subTest(problem=label):
                self.assertTrue(scaffold_problems(case, modes(case)), label)
        mode_problems = scaffold_problems(cases["version"], modes(cases["version"]))
        self.assertTrue(any("git mode is 100644" in p for p in mode_problems), mode_problems)

    def test_copies_must_be_equal(self):
        for root in ("essentials/dev-essentials", "dotnet/dotnet-backend-dev"):
            for name in LIBRARY_COPIES:
                if root in LIBRARY_COPIES[name]:
                    self.write(f"_lib/{name}", "same\n", plugin=self.tmp / root)
        self.assertEqual(copy_problems(self.tmp), [])
        self.write("_lib/git-fixture.sh", "different\n", plugin=self.tmp / "dotnet/dotnet-backend-dev")
        self.assertEqual(len(copy_problems(self.tmp)), 1)

    GOOD_LINK = "../../../../essentials/dev-essentials/evals/_lib/git-fixture.sh"

    def link_repo(self, target_text, link="dotnet/dotnet-backend-dev/evals/_lib/git-fixture.sh"):
        """A git repository in self.tmp with the dev-essentials libraries, and one link that only the index holds."""
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        git_init(self.tmp)
        for name in LIBRARY_COPIES:
            source = self.tmp / LIBRARY_SOURCE / EVALS / "_lib" / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"#!/usr/bin/env bash\necho hi\n")
            run(["git", "-C", self.tmp, "add", "--chmod=+x", source.relative_to(self.tmp).as_posix()], check=True)
        blob = run(["git", "-C", self.tmp, "hash-object", "-w", "--stdin"], stdin=target_text, check=True).stdout.strip()
        run(["git", "-C", self.tmp, "update-index", "--add", "--cacheinfo", f"{LINK_MODE},{blob},{link}"], check=True)
        return tracked_modes(self.tmp)

    def test_link_problems_name_a_plain_file_and_a_link_that_is_not_on_disk(self):
        modes = self.link_repo(self.GOOD_LINK)
        problems = link_problems(modes, self.tmp)
        self.assertTrue(any("dotnet-fixture.sh: the git mode is None, but it must be 120000" in p for p in problems), problems)
        self.assertTrue(any("git-fixture.sh: git checked out the link as a plain file" in p for p in problems), problems)
        self.assertEqual(shell_file_problems(modes, self.tmp), [])

    def test_a_link_to_another_file_or_outside_a_lib_folder_is_a_problem(self):
        modes = self.link_repo("../../../../essentials/dev-essentials/evals/_lib/dotnet-fixture.sh")
        self.assertTrue(any("the link names essentials/dev-essentials/evals/_lib/dotnet-fixture.sh" in p
                            for p in link_problems(modes, self.tmp)))
        modes = self.link_repo(self.GOOD_LINK, link="dotnet/dotnet-backend-dev/evals/demo/scaffold.sh")
        problems = shell_file_problems(modes, self.tmp)
        self.assertTrue(any("demo/scaffold.sh: a link must sit in an evals/_lib folder" in p for p in problems), problems)

    def test_shell_file_problems(self):
        good = self.write("_lib/good.sh", "#!/usr/bin/env bash\necho hi\n")
        bad = self.write("_lib/bad.sh", "if then\r\n")
        modes = {path.relative_to(self.tmp).as_posix(): mode
                 for path, mode in ((good, EXECUTABLE_MODE), (bad, "100644"))}
        bash = shutil.which("bash")
        problems = shell_file_problems(modes, self.tmp, bash)
        self.assertFalse(any("good.sh" in p for p in problems), problems)
        self.assertTrue(any("bad.sh" in p and "CR character" in p for p in problems), problems)
        self.assertTrue(any("bad.sh" in p and "git mode" in p for p in problems), problems)
        if bash:
            self.assertTrue(any("bad.sh" in p and "bash -n" in p for p in problems), problems)


class PairTests(CaseFiles):
    PROMPT = "---\nname: {name}\ntags: [{tag}]\nappend_system_prompt: {rule}\n{extra}---\nWrite the file.\n"
    OK = "---\ntype: regex\npattern: ok\n---\n"
    LOADED = "---\ntype: tool_used\ntool: Skill\ninput_match: '\"skill\"\\s*:\\s*\"{skill}\"'\n---\n"

    LOADED_NEVER = LOADED.replace("\n---\n", "\nmin: 0\nmax: 0\n---\n")

    def pair(self, text="Write the file.", extra="", second_graders=None, drop_second=False,
             first_text=None, pair_id="d1", second_rule="one", first_loaded=None):
        is_docs_case = pair_id.startswith(PAIR_STYLE_PHRASE_ID_PREFIX)
        if first_text is None:
            first_text = "In the OpenBSD man-page style, write the file." if is_docs_case else "Write the file."
        if first_loaded is None:
            first_loaded = self.LOADED if is_docs_case else self.LOADED_NEVER
        graders = {"acc": self.OK, "loaded-style": first_loaded.format(skill="openbsd-style-docs")}
        first = self.PROMPT.format(name="a", tag="x", rule="one", extra="").replace("Write the file.", first_text)
        self.case(f"{PAIR_FOLDER}/openbsd/{pair_id}", prompt=first, graders=graders)
        if not drop_second:
            second = self.PROMPT.format(name="b", tag="y", rule=second_rule, extra=extra)
            second = second.replace("Write the file.", text)
            if second_graders is None:
                second_graders = {"acc": self.OK, "loaded-style": self.LOADED.format(skill="simple-english")}
            self.case(f"{PAIR_FOLDER}/simple-english/{pair_id}", prompt=second, graders=second_graders)
        return pair_problems(load_cases(self.plugin))

    def test_arms_that_differ_in_the_style_only_pass(self):
        self.assertEqual(self.pair(), [])

    def test_a_different_prompt_text_fails(self):
        problems = self.pair(text="Write the page.")
        self.assertEqual(len(problems), 1)
        self.assertIn("the prompt text differs", problems[0])

    def test_the_style_phrase_is_allowed_in_a_docs_prompt_of_the_first_arm(self):
        self.assertEqual(self.pair(first_text="In the OpenBSD man-page style, write the file."), [])

    def test_a_second_difference_next_to_the_style_phrase_fails(self):
        problems = self.pair(first_text="In the OpenBSD man-page style, write the page.")
        self.assertEqual(len(problems), 1)
        self.assertIn("the prompt text differs", problems[0])

    def test_the_style_phrase_fails_in_a_case_that_is_not_a_docs_case(self):
        problems = self.pair(first_text="In the OpenBSD man-page style, write the file.", pair_id="a1")
        self.assertEqual(len(problems), 1)
        self.assertIn("the prompt text differs", problems[0])

    def test_a_docs_prompt_of_the_first_arm_needs_the_style_phrase(self):
        problems = self.pair(first_text="Write the file.")
        self.assertEqual(len(problems), 1)
        self.assertIn("must start with", problems[0])

    def test_a_loaded_style_grader_of_a_non_docs_case_needs_min_and_max_zero(self):
        for missing in ("max: 0\n", "min: 0\n"):
            loaded = self.LOADED_NEVER.replace(missing, "")
            problems = self.pair(pair_id="a1", first_loaded=loaded)
            self.assertEqual(len(problems), 1, missing)
            self.assertIn("min: 0 and max: 0", problems[0])

    def test_the_style_phrase_fails_in_the_second_arm(self):
        problems = self.pair(text="In the OpenBSD man-page style, write the file.")
        self.assertEqual(len(problems), 1)
        self.assertIn("the prompt text differs", problems[0])

    def test_a_different_system_prompt_fails(self):
        problems = self.pair(second_rule="two")
        self.assertEqual(len(problems), 1)
        self.assertIn("the frontmatter differs", problems[0])

    def test_a_loaded_style_grader_must_name_the_skill_of_its_arm(self):
        wrong = self.LOADED.format(skill="openbsd-style-docs")
        problems = self.pair(second_graders={"acc": self.OK, "loaded-style": wrong})
        self.assertEqual(len(problems), 1)
        self.assertIn("must name the skill simple-english", problems[0])

    def test_a_different_frontmatter_key_fails(self):
        problems = self.pair(extra="max_turns: 5\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("the frontmatter differs", problems[0])

    def test_a_different_grader_fails(self):
        problems = self.pair(second_graders={"acc": "---\ntype: regex\npattern: other\n---\n",
                                             "loaded-style": self.LOADED.format(skill="simple-english")})
        self.assertEqual(len(problems), 1)
        self.assertIn("the graders differ: acc", problems[0])

    def test_a_missing_arm_fails(self):
        problems = self.pair(drop_second=True)
        self.assertEqual(len(problems), 1)
        self.assertIn("the arm simple-english is missing", problems[0])

    def test_an_arm_needs_the_loaded_style_grader(self):
        problems = self.pair(second_graders={"acc": self.OK})
        self.assertEqual(len(problems), 1)
        self.assertIn("the arm needs the grader loaded-style", problems[0])


class ScratchTests(CaseFiles):
    def make(self, content, path):
        self.case("fp-e2", graders={"scratch-not-staged": f"---\ntype: file_exists\npath: {path}\nexists: false\n---\n"},
                  extra={"scaffold.sh": f"#!/usr/bin/env bash\nSCRATCH_CONTENT='{content}'\n"})
        return Case(self.plugin / EVALS / "fp-e2", self.plugin)

    def test_blob_path_must_match_the_scaffold_content(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        self.assertEqual(scratch_problems(self.make("hello", blob_path(b"hello"))), [])
        self.assertEqual(len(scratch_problems(self.make("hello", blob_path(b"other")))), 1)


class RepositoryCasesTest(unittest.TestCase):
    """The checks on the real cases of the repository."""

    @classmethod
    def setUpClass(cls):
        cls.roots = plugin_roots()
        cls.cases = [case for root in cls.roots for case in load_cases(root)]

    def collect(self, check):
        return [problem for case in self.cases for problem in check(case)]

    def test_the_repository_has_plugins_and_cases(self):
        self.assertTrue(self.roots, f"No plugin manifest matches {PLUGIN_GLOB}.")
        self.assertTrue(self.cases, "No eval case found.")

    def test_case_names_are_unique_in_each_plugin(self):
        self.assertEqual(duplicate_name_problems(self.cases), [])

    def test_prompt_keys_and_limits(self):
        self.assertEqual(self.collect(key_problems), [])

    def test_graders(self):
        self.assertEqual(self.collect(grader_problems), [])

    def test_route_graders_have_the_route_tag(self):
        self.assertEqual(self.collect(route_problems), [])

    def test_plugins_entries_resolve(self):
        self.assertEqual(self.collect(plugin_entry_problems), [])

    def test_case_yaml_and_scaffold_scripts(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        modes = tracked_modes()
        self.assertEqual([p for case in self.cases for p in scaffold_problems(case, modes)], [])

    def test_shell_files_are_lf_executable_and_valid(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        bash = shutil.which("bash")
        if bash is None:
            tool_missing(self, "bash not found")
        self.assertEqual(shell_file_problems(tracked_modes(), REPO, bash), [])

    def test_fixture_libraries_have_equal_copies(self):
        self.assertEqual(copy_problems(), [])

    def test_shared_libraries_of_dotnet_backend_dev_are_links(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        self.assertEqual(link_problems(tracked_modes()), [])

    def test_style_compare_arms_differ_in_the_style_only(self):
        self.assertEqual(pair_problems(self.cases), [])

    def test_untracked_file_case_names_the_blob_of_its_scratch_file(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        found = [case for case in self.cases if case.name == "fp-e2-untracked-file"]
        if not found:
            self.skipTest("the case fp-e2-untracked-file does not exist yet")
        self.assertEqual([p for case in found for p in scratch_problems(case)], [])


FP_ROOT = REPO / "essentials" / "dev-essentials"
FP_STAGES = FP_ROOT / "skills" / "feature-pipeline" / "stages"
# For each caught-* grader: the path of the planted defect and a sentence with a keyword of the grader.
FP_CAUGHT = {
    "caught-sql": ("src/Inventory/StockQuery.cs", "SQL injection through string concatenation"),
    "caught-bound": ("src/Inventory/StockQuery.cs", "The loop bound uses <= skus.Length, an off-by-one"),
    "caught-key": ("src/Inventory/InventoryOptions.cs", "Hard-coded API key in the options class"),
    "caught-query-in-loop": ("src/Inventory/StockQuery.cs", "N+1: one query for each sku in the loop"),
    "caught-duplicate": ("src/Inventory/StockQuery.cs", "Duplicates SkuFormatter.Normalize"),
    "caught-review-rule": ("src/Inventory/StockQuery.cs", "Missing XML doc comment (REVIEW.md rule)"),
    "caught-typosquat": ("Directory.Packages.props", "Likely typosquat of the Newtonsoft.Json package"),
    "caught-auth": ("src/Inventory/AccessPolicy.cs", "A null user bypasses the check"),
}
FP_SEEDED_CASE = FP_ROOT / "evals" / "feature-pipeline" / "fp-e1-seeded-defects"
# For each caught-* grader of fp-e1-seeded-defects: a line of a Stage 1 reply that names the defect.
FP_QUESTION_LINES = {
    "caught-sql": "1. **SQL injection:** `FindQuantity` builds the SQL by joining the raw `sku` into the query text.",
    "caught-bound": ("2. **Off-by-one:** `FindQuantities` loops with `i <= skus.Length`, "
                     "so it throws `IndexOutOfRangeException` on every call."),
    "caught-duplicate": "3. **Duplicate code.** `CleanSku` repeats `SkuFormatter.Normalize` but without the null check.",
    "caught-review-rule": ("4. **Review rule broken.** No public member has an XML doc comment. "
                           "`REVIEW.md` requires one on each public method."),
    "caught-query-in-loop": ("5. **One query per sku:** `FindQuantities` runs a separate query for each sku "
                             "and ignores `ISqlRunner.QueryMany`."),
    "caught-key": "6. **Hard-coded secret.** `ApiKey = \"inv-key-0042-local\"` would sit in source and in git history.",
    "caught-typosquat": ("7. **Misspelled package name.** `Newtonsoft.Jsonn` (two n's) is not the real package. "
                         "It looks like a typosquatting name."),
}
FP_QUESTION_BLOCK = ("QUESTIONS:\n1. How should `StockQuery.cs` be handled?\n"
                     "   Options: add it as written / fix it. Recommended: fix it.\n")
FP_QUESTION_TEMPLATE = ("QUESTIONS:\n1. <question>\n   Options: <option 1> / <option 2> / <option 3>. "
                        "Recommended: <option>.\n2. <question>\n")
# For each caught-* grader: the seeded name on one line and the defect word on the next line.
FP_SPLIT_LINES = {
    "caught-sql": "1. **SQL injection** is possible in the new code.\n   The method is `FindQuantity`.",
    "caught-bound": "2. **Off-by-one** in the new loop.\n   The method is `FindQuantities`.",
    "caught-duplicate": "3. **Duplicate code** in the new class.\n   The method is `CleanSku`.",
    "caught-review-rule": "4. No public member has an XML doc comment.\n   The rule file is `REVIEW.md`.",
    "caught-query-in-loop": "5. One query per sku in the new loop.\n   The method is `FindQuantities`.",
    "caught-key": "6. **Hard-coded secret** in the options.\n   The property is `ApiKey`.",
    "caught-typosquat": "7. **Misspelled package name** in the props file.\n   The id is `Newtonsoft.Jsonn`.",
}
# For each caught-* grader: text that says that the defect is not in the diff.
FP_NOT_PRESENT = {
    "caught-bound": ("The off-by-one loop of the issue code (`i <= skus.Length`) is also gone. "
                     "`FindQuantities` now uses LINQ."),
    "caught-key": ("- **Hard-coded API key (issue code: `= \"inv-key-0042-local\"`):** not present. "
                   "`InventoryOptions.cs:13` defaults `ApiKey` to `string.Empty`."),
    "caught-typosquat": ("- **Likely typosquat `Newtonsoft.Jsonn` 13.0.3:** not present. "
                         "`Directory.Packages.props` is unchanged."),
    "caught-sql": "The unsafe parts of the issue are not in the diff: no string-concatenated SQL in `FindQuantity`.",
    "caught-duplicate": "`CleanSku` is not a duplicate any more. It calls `SkuFormatter.Normalize`.",
    "caught-review-rule": "No public member is without an XML doc comment, so the `REVIEW.md` rule holds.",
    "caught-query-in-loop": "`FindQuantities` no longer runs one query per sku.",
}
# A stop of the master before Stage 1. It names each defect and asks the user, but no stage ran.
FP_STOP_MESSAGE = ("I stopped before Stage 1.\n\n" + "\n".join(FP_QUESTION_LINES.values())
                   + "\n\nI need your answers first.\n\n" + FP_QUESTION_BLOCK)
# For each fixed-* grader: the file that it reads after the run.
FP_FIXED = {
    "fixed-bound": "src/Inventory/StockQuery.cs",
    "fixed-sql": "src/Inventory/StockQuery.cs",
    "fixed-key": "src/Inventory/InventoryOptions.cs",
    "fixed-typosquat": "Directory.Packages.props",
}


def trace_form(text):
    """The text as it appears in the trace: a JSON string with escaped line ends, quotes, and dashes."""
    return json.dumps(text)[1:-1]


def trace_record(record):
    """One record of the trace: compact JSON on one line, as the eval runner writes it."""
    return json.dumps(record, separators=(",", ":"))


def stage_reply(text):
    """The record that ends a stage subagent: a task notification with the final reply and then a usage object."""
    return trace_record({"type": "system", "subtype": "task_notification", "task_id": "a1",
                         "tool_use_id": "toolu_1", "status": "completed", "summary": text,
                         "usage": {"total_tokens": 1}})


def agent_result(reply, prompt="The brief of the stage."):
    """The result of an Agent call. It holds the brief of the master and the final reply of the subagent."""
    return trace_record({
        "type": "user",
        "message": {"role": "user", "content": [
            {"tool_use_id": "toolu_1", "type": "tool_result", "content": [{"type": "text", "text": reply}]},
        ]},
        "parent_tool_use_id": None,
        "tool_use_result": {"status": "completed", "prompt": prompt, "agentId": "a1",
                            "agentType": "general-purpose", "content": [{"type": "text", "text": reply}]},
    })


def master_records(text):
    """The records that hold text of the master agent, and the record of the subagent prompt."""
    return {
        "Agent call": trace_record({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Agent", "input": {"description": "Stage 1", "prompt": text}},
        ]}}),
        "task start": trace_record({"type": "system", "subtype": "task_started", "task_id": "a1", "prompt": text}),
        "subagent prompt": trace_record({"type": "user", "message": {"content": [{"type": "text", "text": text}]},
                                         "parent_tool_use_id": "toolu_1"}),
        "message": trace_record({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}),
        "result": trace_record({"type": "result", "subtype": "success", "result": text}),
    }


class FeaturePipelineGraderTests(unittest.TestCase):
    """The caught-* graders read a review entry or a line of a stage question reply in the trace.

    The fixed-* graders read one file after the run, and they fail if the planted defect is still in it.
    """

    @classmethod
    def setUpClass(cls):
        cls.graders, cls.meta = {}, {}
        for case in load_cases(FP_ROOT):
            if case.name.startswith("fp-e1-"):
                for name, (meta, _body) in case.graders.items():
                    if name.startswith(("caught-", "fixed-")) or name == "no-blocking":
                        flags = sum(REGEX_FLAGS.get(f, 0) for f in meta.get("flags", ""))
                        cls.graders[name] = re.compile(meta["pattern"], flags)
                        cls.meta[name] = meta

    def test_every_planted_defect_has_a_grader(self):
        self.assertEqual(sorted(n for n in self.graders if n.startswith("caught-")), sorted(FP_CAUGHT))
        self.assertEqual(sorted(n for n in self.graders if n.startswith("fixed-")), sorted(FP_FIXED))

    @staticmethod
    def entries(path, sentence):
        return {
            "review": f"- [ ] [correctness] {sentence} — `{path}:26` (confidence: high)\n  - Fix: change it",
            "security": (f"- [ ] **[HIGH]** Weak code — `{path}:26` (confidence: 0.9)\n"
                         f"  - **Description:** {sentence}\n  - **Exploit scenario:** an attacker sends input"),
            "keyword first": f"- [ ] **[MEDIUM]** {sentence} — `./{path}:26` (confidence: 0.6)",
        }

    def test_each_pattern_matches_an_entry_of_each_stage(self):
        for name, (path, sentence) in FP_CAUGHT.items():
            for kind, entry in self.entries(path, sentence).items():
                with self.subTest(grader=name, entry=kind):
                    text = trace_form(f"## Warnings\n{entry}\n\n## Suggestions\n")
                    self.assertRegex(text, self.graders[name])

    def test_a_keyword_in_another_entry_or_another_file_does_not_match(self):
        other = "src/Inventory/Elsewhere.cs"
        for name, (path, sentence) in FP_CAUGHT.items():
            cases = {
                "keyword in another file": f"- [ ] [correctness] {sentence} — `{other}:3` (confidence: high)",
                "path in another entry": (f"- [ ] [correctness] Plain issue — `{path}:3` (confidence: high)\n"
                                          f"- [ ] [correctness] {sentence} — `{other}:9` (confidence: high)"),
                "no confidence": f"- [ ] {sentence} — `{path}:26`",
                "no line number": f"- [ ] [correctness] {sentence} — `{path}` (confidence: high)",
            }
            for kind, entry in cases.items():
                with self.subTest(grader=name, entry=kind):
                    self.assertNotRegex(trace_form(entry), self.graders[name])

    def test_a_reuse_entry_needs_the_new_code_path(self):
        existing = ("- [ ] [reuse] `CleanSku` repeats the logic of `SkuFormatter.Normalize` "
                    "— `src/Inventory/SkuFormatter.cs:7` (confidence: high)\n  - Fix: call SkuFormatter.Normalize")
        fixed = ("- [ ] [reuse] `CleanSku` repeats the logic of `SkuFormatter.Normalize` "
                 "— `src/Inventory/StockQuery.cs:29` (confidence: high)\n"
                 "  - Fix: call SkuFormatter.Normalize (`src/Inventory/SkuFormatter.cs:7`)")
        pattern = self.graders["caught-duplicate"]
        self.assertNotRegex(trace_form(existing), pattern)
        self.assertRegex(trace_form(fixed), pattern)

    def test_a_summary_after_the_last_entry_does_not_match(self):
        other = "src/Inventory/Elsewhere.cs"
        for name, (path, sentence) in FP_CAUGHT.items():
            text = (f"## Warnings\n- [ ] [correctness] Plain issue — `{other}:3` (confidence: high)\n\n"
                    f"## Summary\n{sentence} at `{path}:26` (confidence: high)\n")
            with self.subTest(grader=name):
                self.assertNotRegex(trace_form(text), self.graders[name])

    def test_the_stage_templates_and_a_spec_checkbox_do_not_match(self):
        texts = {"spec": "- [ ] Reject a bad sku in src/Inventory/StockQuery.cs:12 to stop SQL injection and N+1 calls"}
        for stage in ("review.md", "security-review.md"):
            text = (FP_STAGES / stage).read_text(encoding="utf-8")
            texts[stage] = text
            for number, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith("- [ ]"):
                    texts[f"{stage}:{number}"] = line
        for name in FP_CAUGHT:
            for source, text in texts.items():
                with self.subTest(grader=name, source=source):
                    self.assertNotRegex(trace_form(text), self.graders[name])

    def test_a_stage_reply_names_each_seeded_defect(self):
        for name, line in FP_QUESTION_LINES.items():
            reply = f"Problems in the code of the issue:\n{line}\n\n{FP_QUESTION_BLOCK}"
            texts = {
                "line before the block": stage_reply(reply),
                "line in the first item": stage_reply(f"QUESTIONS:\n{line}\n   Options: a / b. Recommended: b.\n"),
                "line after the block": stage_reply(f"{FP_QUESTION_BLOCK}{line}\n   Options: a / b. Recommended: b.\n"),
                "result of the Agent call": agent_result(reply),
            }
            for kind, text in texts.items():
                with self.subTest(grader=name, text=kind):
                    self.assertRegex(text, self.graders[name])

    def test_a_defect_line_outside_a_question_reply_does_not_match(self):
        for name, line in FP_QUESTION_LINES.items():
            texts = {
                "line alone": stage_reply(line),
                "no recommended option": stage_reply(f"{line}\n\nQUESTIONS:\n1. How?\n"),
                "only the template": stage_reply(f"{line}\n\n{FP_QUESTION_TEMPLATE}"),
                "marker inside a sentence": stage_reply(
                    f"{line}\n\nThese are my questions:\n1. How? Recommended: fix it.\n"
                ),
                "block in another record": stage_reply(line) + "\n" + stage_reply(FP_QUESTION_BLOCK),
                "name and word on two lines": stage_reply(
                    f"QUESTIONS:\n{FP_SPLIT_LINES[name]}\n   Options: a / b. Recommended: b.\n"
                ),
                "line in the brief of the Agent call": agent_result(
                    FP_QUESTION_BLOCK, prompt=f"{line}\n\n{FP_QUESTION_TEMPLATE}"
                ),
                "template after a blank line": stage_reply(
                    line + "\n\n" + FP_QUESTION_TEMPLATE.replace("QUESTIONS:\n", "QUESTIONS:\n\n")
                ),
                "command of a Bash notification": trace_record({
                    "type": "system", "subtype": "task_notification", "task_id": "b1", "status": "completed",
                    "summary": f"cat > notes.md <<'X'\n{line}\n{FP_QUESTION_BLOCK}X",
                }),
                "line in a string after the reply": trace_record({"type": "user", "tool_use_result": {
                    "agentType": "general-purpose", "content": [{"type": "text", "text": FP_QUESTION_BLOCK}],
                    "prompt": line,
                }}),
            }
            for other, other_line in FP_QUESTION_LINES.items():
                if other != name:
                    texts[f"line of {other}"] = stage_reply(f"{other_line}\n\n{FP_QUESTION_BLOCK}")
            for kind, text in texts.items():
                with self.subTest(grader=name, text=kind):
                    self.assertNotRegex(text, self.graders[name])

    def test_text_of_the_master_does_not_match(self):
        stage = (FP_STAGES / "requirements.md").read_text(encoding="utf-8")
        note = "\n".join(FP_QUESTION_LINES.values())
        texts = {}
        for kind, text in master_records(f"{note}\n\n{stage}").items():
            texts[f"note and stage text, {kind}"] = text
        for kind, text in master_records(f"<clarifications>\n{note}\n</clarifications>\n\n{stage}").items():
            texts[f"clarifications, {kind}"] = text
        for kind, text in master_records(FP_STOP_MESSAGE).items():
            texts[f"stop message, {kind}"] = text
        for name in FP_QUESTION_LINES:
            for source, text in texts.items():
                with self.subTest(grader=name, source=source):
                    self.assertNotRegex(text, self.graders[name])

    def test_the_issue_the_skill_and_a_not_present_report_do_not_match(self):
        get_json = (FP_SEEDED_CASE / "mocks" / "github" / "fixtures" / "get.json").read_text(encoding="utf-8")
        body = json.loads(get_json)["body"]
        texts = {
            "mock answer": trace_form(get_json),
            "mock answer in a tool result": trace_form(json.dumps({"text": get_json})),
            "issue body": trace_form(body),
            "issue body and template in a stage reply": stage_reply(f"{body}\n\n{FP_QUESTION_TEMPLATE}"),
            "issue body and block in a stage reply": stage_reply(f"{body}\n\n{FP_QUESTION_BLOCK}"),
        }
        skill = FP_ROOT / "skills" / "feature-pipeline"
        for path in sorted(skill.rglob("*.md")):
            texts[path.relative_to(skill).as_posix()] = trace_form(path.read_text(encoding="utf-8"))
        for defect, report in FP_NOT_PRESENT.items():
            content = f"{report}\n\n{FP_QUESTION_BLOCK}"
            write = {"type": "tool_use", "name": "Write",
                     "input": {"file_path": ".pipeline/811/security-review.md", "content": content}}
            review = {"type": "assistant", "message": {"content": [write]}}
            texts[f"not present, {defect}, review file"] = trace_record(review)
            texts[f"not present, {defect}, message"] = master_records(content)["message"]
        for name in FP_QUESTION_LINES:
            for source, text in texts.items():
                with self.subTest(grader=name, source=source):
                    self.assertNotRegex(text, self.graders[name])

    def test_a_review_entry_about_another_problem_does_not_match(self):
        entries = {
            "caught-query-in-loop": (
                "- [ ] [correctness] The code looks up the `QueryMany` results by the normalized sku. "
                "— `src/Inventory/StockQuery.cs:44` (confidence: low)",
                "- [ ] [performance] `FindQuantities` sends all skus in one call. The spec asks for exactly one "
                "round trip. — `src/Inventory/StockQuery.cs:61` (confidence: low)",
            ),
            "caught-duplicate": (
                "- [ ] [reuse] `QuantitySql` is copied from `StockService.QuantitySql`. `FindQuantity` is also "
                "the same as `StockService.GetQuantity`. — `src/Inventory/StockQuery.cs:14` (confidence: low)",
                "- [ ] [reuse] `StockQuery.FindQuantity` is the same code as `StockService.GetQuantity`. "
                "— `src/Inventory/StockQuery.cs:8` (confidence: low)",
                "- [ ] [correctness] `CleanSku` throws a NullReferenceException for a null sku "
                "— `src/Inventory/StockQuery.cs:31` (confidence: high)",
                "- [ ] [compliance] `CleanSku` has no XML doc comment "
                "— `src/Inventory/StockQuery.cs:29` (confidence: high)",
            ),
        }
        for name, texts in entries.items():
            for text in texts:
                with self.subTest(grader=name, text=text):
                    self.assertNotRegex(trace_form(text), self.graders[name])

    def test_a_review_entry_that_reports_no_defect_does_not_match(self):
        entries = {
            "caught-review-rule": (
                "- [ ] [compliance] The new XML docs have only `<summary>`. They have no `<param>` tags. "
                "This meets REVIEW.md, so it does not break a repo rule. — `src/Inventory/StockQuery.cs:3` "
                "(confidence: medium)",
                "- [ ] [compliance] The members have only a `<summary>`. The REVIEW.md rule (\"Each public method "
                "has an XML doc comment.\") is met. — `src/Inventory/StockQuery.cs:16` (confidence: medium)",
                "- [ ] [compliance] No public member is without an XML doc comment, so the `REVIEW.md` rule holds. "
                "\u2014 `src/Inventory/StockQuery.cs:3` (confidence: low)",
            ),
            "caught-sql": (
                "- [ ] **[LOW]** Batch query safety — `src/Inventory/StockQuery.cs:8` (confidence: 0.2)\n"
                "  - **Description:** The skus go to `QueryMany` as a list, so the diff itself has no injection.",
                "- [ ] **[LOW]** Query text — `src/Inventory/StockQuery.cs:8` (confidence: 0.2)\n"
                "  - **Description:** The SQL is a constant, so it is not open to SQL injection.",
            ),
        }
        for name, texts in entries.items():
            for text in texts:
                with self.subTest(grader=name, text=text):
                    self.assertNotRegex(trace_form(text), self.graders[name])

    def test_a_review_entry_in_another_word_order_matches(self):
        entries = {
            "caught-duplicate": (
                "- [ ] [reuse] The logic of `SkuFormatter.Normalize` is duplicated here "
                "— `src/Inventory/StockQuery.cs:29` (confidence: high)",
            ),
            "caught-review-rule": (
                "- [ ] [compliance] `CleanSku` has no XML doc comment, which REVIEW.md requires "
                "— `src/Inventory/StockQuery.cs:29` (confidence: high)",
                "- [ ] [compliance] REVIEW.md asks for an XML doc comment on each public method of "
                "`StockQuery.cs`, and `FindQuantity` has none — `src/Inventory/StockQuery.cs:12` (confidence: high)",
            ),
            "caught-sql": (
                "- [ ] **[HIGH]** SQL injection — `src/Inventory/StockQuery.cs:14` (confidence: 0.9)\n"
                "  - **Description:** `FindQuantity` joins the raw sku into the SQL text. It is not parameterized.",
                "- [ ] **[HIGH]** SQL injection in `FindQuantity` \u2014 `src/Inventory/StockQuery.cs:14` (confidence: 0.9)\n"
                "  - **Description:** `FindQuantity` joins the raw sku into the SQL text.\n"
                "  - **Recommendation:** Bind the sku as a parameter (`@sku`), so that there is no injection path.",
            ),
        }
        for name, texts in entries.items():
            for text in texts:
                with self.subTest(grader=name, text=text):
                    self.assertRegex(trace_form(text), self.graders[name])

    def test_each_outcome_grader_reads_its_file(self):
        for name, path in FP_FIXED.items():
            with self.subTest(grader=name):
                self.assertEqual(self.meta[name].get("match"), "not_contains")
                self.assertEqual(self.meta[name].get("target"), {"source": "file", "path": path})

    def test_each_outcome_grader_finds_the_dictated_defect_and_not_its_fix(self):
        get_json = (FP_SEEDED_CASE / "mocks" / "github" / "fixtures" / "get.json").read_text(encoding="utf-8")
        body = json.loads(get_json)["body"]
        query, key = re.findall(r"```csharp\n(.*?)```", body, re.S)
        package = re.search(r"```xml\n(.*?)```", body, re.S).group(1)
        options = "public sealed class InventoryOptions\n{\n    public int LowStockThreshold { get; init; } = 5;\n}\n"
        props = '<ItemGroup>\n  <PackageVersion Include="NUnit" Version="4.4.0" />\n</ItemGroup>\n'
        samples = {
            "fixed-bound": (query, query.replace("i <= skus.Length", "i < skus.Length"),
                            "if (count <= skus.Length)\n{\n}\n"),
            "fixed-sql": (query, query.replace("'\" + sku + \"'\"", "@sku\""),
                          'throw new ArgumentException("Unknown sku " + sku);\n'),
            "fixed-key": (options + key, options + key.replace('"inv-key-0042-local"', "string.Empty"), options),
            "fixed-typosquat": (props + package, props + package.replace("Jsonn", "Json"), props),
        }
        for name, (defect, fixed, other) in samples.items():
            with self.subTest(grader=name):
                self.assertNotEqual(defect, fixed)
                self.assertRegex(defect, self.graders[name])
                self.assertNotRegex(fixed, self.graders[name])
                self.assertNotRegex(other, self.graders[name])

    def test_each_outcome_grader_reads_other_forms_of_the_code(self):
        samples = {
            "fixed-sql": (
                ("var text = $\"SELECT quantity FROM stock WHERE sku = '{sku}'\";\n",
                 "var text = string.Format(\"SELECT quantity FROM stock WHERE sku = '{0}'\", sku);\n",
                 "var text = \"select quantity from stock where sku = '\" + sku + \"'\";\n"),
                ("throw new ArgumentException(\"Unknown sku '\" + sku + \"'\");\n",
                 "throw new ArgumentException($\"Unknown sku '{sku}'\");\n",
                 "var text = \"select quantity from stock where sku = @sku\";\n"),
            ),
            "fixed-bound": (
                ("while (i <= skus.Length)\n{\n    i++;\n}\n",),
                ("for (var i = 0; i <= skus.Length - 1; i++)\n{\n}\n",),
            ),
        }
        for name, (defects, clean) in samples.items():
            for text in defects:
                with self.subTest(grader=name, text=text):
                    self.assertRegex(text, self.graders[name])
            for text in clean:
                with self.subTest(grader=name, text=text):
                    self.assertNotRegex(text, self.graders[name])

    def test_no_blocking_finds_a_real_entry_and_skips_the_templates(self):
        pattern = self.graders["no-blocking"]
        real = "## Blocking Issues\n- [ ] [correctness] Bug — `src/A.cs:3` (confidence: high)\n\n## Warnings\n"
        real_security = "## Blocking Issues\n\n- [ ] **[HIGH]** Bug — `src/A.cs:3` (confidence: 0.9)\n"
        self.assertRegex(trace_form(real), pattern)
        self.assertRegex(trace_form(real_security), pattern)
        templates = (
            "## Blocking Issues\n- [ ] <description> — `file:line` (confidence: high)",
            "## Blocking Issues\n- [ ] [<lens>] <description> — `file:line`",
            "## Blocking Issues\n- [ ] **[HIGH]** <title> — `file:line` (confidence: X.X)",
            "## Blocking Issues\n\n## Warnings\n",
            "## Blocking Issues\n- None\n",
        )
        for text in templates:
            with self.subTest(text=text):
                self.assertNotRegex(trace_form(text), pattern)
        for stage in ("review.md", "security-review.md"):
            with self.subTest(stage=stage):
                self.assertNotRegex(trace_form((FP_STAGES / stage).read_text(encoding="utf-8")), pattern)


OBSD_ROOT = REPO / "essentials" / "doc-styles"
OBSD_PROBE = OBSD_ROOT / "evals" / "probes" / "probe-obsd-lint-hook"
OBSD_LINT = OBSD_ROOT / "skills" / "openbsd-style-docs" / "scripts" / "openbsd_lint.py"
CLAUDE_CODE_PREFIX = 'PostToolUse:Write hook blocking error from command: "command hook 3": [command hook 3]: '


class ObsdLintHookProbeGraderTests(ScratchCase):
    """The graders of probe-obsd-lint-hook match the message of the real lint hook, and nothing that a run with no hook prints."""

    def setUp(self):
        super().setUp()
        case = Case(OBSD_PROBE, OBSD_ROOT)
        self.assertEqual(case.errors, [])
        self.assertEqual(sorted(case.graders), ["hook-hit-quoted", "lint-hook-ran"])
        self.patterns = {}
        for name, (meta, _body) in case.graders.items():
            self.assertEqual(meta["type"], "regex", name)
            self.assertEqual(meta.get("target", "last_message"), "last_message", name)
            self.assertNotIn("match", meta, name)
            flags = sum(REGEX_FLAGS.get(f, 0) for f in meta.get("flags", ""))
            self.patterns[name] = re.compile(meta["pattern"], flags)
        body = case.prompt_body
        start = body.index("```markdown\n") + len("```markdown\n")
        self.probe = self.tmp / "probe.md"
        self.probe.write_bytes((body[start:body.index("\n```", start)] + "\n").encode("utf-8"))

    def hook_stderr(self):
        event = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Write",
                            "tool_input": {"file_path": str(self.probe)}})
        result = run([sys.executable, "-I", OBSD_LINT, "--hook"], stdin=event)
        self.assertResult(result, 2)
        self.assertEqual(result.stdout, "")
        return result.stderr

    def test_both_patterns_match_the_hook_message_with_and_without_the_prefix(self):
        message = self.hook_stderr()
        replies = {
            "bare": f"```text\n{message}```\n",
            "with prefix": f"```text\n{CLAUDE_CODE_PREFIX}{message}```\n",
        }
        for name, pattern in self.patterns.items():
            for kind, reply in replies.items():
                with self.subTest(grader=name, reply=kind):
                    self.assertRegex(reply, pattern)

    def test_neither_pattern_matches_a_run_with_no_hook(self):
        file_mode = run([sys.executable, "-I", OBSD_LINT, self.probe])
        self.assertResult(file_mode, 1)
        replies = {"no hook answer": "No hook message.", "file mode output": file_mode.stdout}
        for name, pattern in self.patterns.items():
            for kind, reply in replies.items():
                with self.subTest(grader=name, reply=kind):
                    self.assertNotRegex(reply, pattern)


SE_STUB = STUBS / "simple-english"
SE_PROBE = OBSD_ROOT / "evals" / "probes" / "probe-se-lint-hook"
SE_HOOK = SE_STUB / "src" / "hooks" / "lint_hook.py"
SE_LINT = SE_STUB / "evals" / "ste_lint.py"


class SeLintHookProbeGraderTests(ScratchCase):
    """The graders of probe-se-lint-hook match the message of the stand-in lint hook, and nothing that a run with no hook prints."""

    def setUp(self):
        super().setUp()
        case = Case(SE_PROBE, OBSD_ROOT)
        self.assertEqual(case.errors, [])
        self.assertEqual(sorted(case.graders), ["hook-hit-quoted", "lint-hook-ran"])
        self.patterns = {}
        for name, (meta, _body) in case.graders.items():
            self.assertEqual(meta["type"], "regex", name)
            self.assertEqual(meta.get("target", "last_message"), "last_message", name)
            self.assertNotIn("match", meta, name)
            flags = sum(REGEX_FLAGS.get(f, 0) for f in meta.get("flags", ""))
            # In hook-hit-quoted, the class [l] hides the plain word from the linter. The match is the same.
            self.patterns[name] = re.compile(meta["pattern"], flags)
        body = self.prompt_body = case.prompt_body
        start = body.index("```text\n") + len("```text\n")
        self.probe = self.tmp / "probe.md"
        self.probe.write_bytes((body[start:body.index("\n```", start)] + "\n").encode("utf-8"))

    def hook_stderr(self):
        event = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Write",
                            "tool_input": {"file_path": str(self.probe)}})
        result = run([sys.executable, "-I", SE_HOOK], stdin=event)
        self.assertResult(result, 2)
        self.assertEqual(result.stdout, "")
        return result.stderr

    def test_both_patterns_match_the_hook_message_with_and_without_the_prefix(self):
        message = self.hook_stderr()
        replies = {
            "bare": f"```text\n{message}```\n",
            "with prefix": f"```text\n{CLAUDE_CODE_PREFIX}{message}```\n",
        }
        for name, pattern in self.patterns.items():
            for kind, reply in replies.items():
                with self.subTest(grader=name, reply=kind):
                    self.assertRegex(reply, pattern)

    def test_neither_pattern_matches_a_run_with_no_hook(self):
        linter = run([sys.executable, "-I", SE_LINT, self.probe])
        self.assertResult(linter, 0, '"banned_modal": 1')
        file_text = self.probe.read_text(encoding="utf-8")
        replies = {
            "no hook answer": "No hook message.",
            "line 1 and no hook answer": "The modal on line 1 is a hit. No hook message.",
            "linter output": linter.stdout,
            "prompt": self.prompt_body,
            "file content and no hook answer": f"I wrote probe.md:\n\n```text\n{file_text}```\n\nNo hook message.",
        }
        for name, pattern in self.patterns.items():
            for kind, reply in replies.items():
                with self.subTest(grader=name, reply=kind):
                    self.assertNotRegex(reply, pattern)


TBC_CASES = ("so-rename-small", "so-rename-large", "so-two-fixes", "rl-null-guard", "rl-off-by-one",
             "rl-unbounded-query", "rirr-retry-limit")


def trace_bash(command):
    return f'{{"type":"tool_use","id":"t","name":"Bash","input":{{"command":"{trace_form(command)}"}}}}'


def trace_edit(path, tool="Edit"):
    return f'{{"type":"tool_use","id":"t","name":"{tool}","input":{{"replace_all":false,"file_path":"{path}","old_string":"a"}}}}'


def trace_write(path):
    return f'{{"type":"tool_use","id":"t","name":"Write","input":{{"file_path":"{path}","content":"x"}}}}'


def trace_result(text):
    return f'{{"type":"tool_result","content":"{trace_form(text)}"}}'


class TestsBeforeCommitGraderTests(unittest.TestCase):
    """The grader tests-before-commit needs a test run, then a commit, with no edit of a .py file between them."""

    TEST_RUN = trace_bash("cd /w && python3 -m unittest discover -s tests 2>&1 | tail -5")
    COMMIT = trace_bash('git -C "/x y" commit -q -m "Rename"')

    @classmethod
    def setUpClass(cls):
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        cls.patterns = {name: cases[name].graders["tests-before-commit"][0]["pattern"] for name in TBC_CASES}

    def matches(self, *records):
        return re.search(next(iter(self.patterns.values())), "\n".join(records)) is not None

    def test_every_case_has_the_same_pattern_and_the_trace_target(self):
        self.assertEqual(len(set(self.patterns.values())), 1)
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        for name in TBC_CASES:
            with self.subTest(case=name):
                self.assertEqual(cases[name].graders["tests-before-commit"][0]["target"], "trace")

    def test_a_test_run_before_a_commit_matches(self):
        edit = trace_edit("app/a.py")
        runs = {
            "test and commit": [self.TEST_RUN, trace_result("OK"), self.COMMIT],
            "a Markdown write between them": [self.TEST_RUN, trace_write("Notes/Reviews/c-1.md"), self.COMMIT],
            "an edit before the test": [edit, self.TEST_RUN, trace_bash("git add -A"), self.COMMIT],
            "one shell command": [trace_bash("python3 -m unittest discover -s tests && git add a.py && git commit -m x")],
            "a later test and commit": [self.TEST_RUN, edit, self.COMMIT, self.TEST_RUN, self.COMMIT],
            "a commit on a new line of the command": [self.TEST_RUN, trace_bash('python3 -c "import app"\ngit commit -q -m x')],
        }
        for name, records in runs.items():
            with self.subTest(run=name):
                self.assertTrue(self.matches(*records))

    def test_other_orders_do_not_match(self):
        runs = {
            "commit and then test": [self.COMMIT, self.TEST_RUN],
            "commit only": [self.COMMIT],
            "unittest in the message of a commit": [trace_bash('git commit -m "run unittest later"')],
            "an Edit of a .py file between them": [self.TEST_RUN, trace_edit("app/a.py"), self.COMMIT],
            "a MultiEdit of a .py file between them": [self.TEST_RUN, trace_edit("app/a.py", "MultiEdit"), self.COMMIT],
            "a Write of a .py file between them": [self.TEST_RUN, trace_write("app/b.py"), self.COMMIT],
            "the word commit in a tool result": [self.TEST_RUN, trace_result("nothing to commit, use git add")],
        }
        for name, records in runs.items():
            with self.subTest(run=name):
                self.assertFalse(self.matches(*records))

    def test_the_untested_commit_grader_finds_an_edit_then_a_commit(self):
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        pattern = cases["so-two-fixes"].graders["untested-commit"][0]["pattern"]
        edit = trace_edit("app/a.py")
        bad = {
            "edit and commit": [edit, self.COMMIT],
            "a later test and commit": [self.TEST_RUN, edit, self.COMMIT, self.TEST_RUN, self.COMMIT],
            "a sed edit, then a commit": [self.TEST_RUN, trace_bash("sed -i 's/= 5/= 3/' config/settings.py"), self.COMMIT],
            "a heredoc edit and a commit in one command": [
                self.TEST_RUN, trace_bash("cat > config/settings.py <<'EOF'\nHTTP_RETRY_LIMIT = 3\nEOF\ngit commit -q -am a")],
            "the word unittest in a sed script": [
                self.TEST_RUN, trace_bash("sed -i 's/import unittest/import pytest/' tests/test_a.py"), self.COMMIT],
        }
        good = {
            "test and commit": [self.TEST_RUN, self.COMMIT],
            "an edit before the test": [edit, self.TEST_RUN, self.COMMIT],
            "one shell command": [edit, trace_bash("python3 -m unittest discover -s tests && git commit -m x")],
            "a sed edit and a test in one command": [
                trace_bash("sed -i 's/= 5/= 3/' config/settings.py && python3 -m unittest discover -s tests"), self.COMMIT],
            "a sed read of a .py file": [self.TEST_RUN, trace_bash("sed -n '1,20p' app/a.py"), self.COMMIT],
            "a sed edit, a test, and a commit in one command": [
                trace_bash("sed -i 's|a|b|' app/billing.py; python3 -m unittest discover -s tests; git add app/billing.py && git commit -m x")],
            "a plain sed edit, a test, and a commit in one command": [
                trace_bash("sed -i 's/a/b/' app/billing.py; python3 -m unittest discover -s tests; git add app/billing.py && git commit -m x")],
            "a sed edit of a Markdown file, then a sed read of a .py file": [
                self.TEST_RUN, trace_bash("sed -i 's/a;b/c/' README.md && sed -n '1,5p' app/a.py"), self.COMMIT],
            "a sed edit of a Markdown file, then a read of a .py file on a new line": [
                self.TEST_RUN, trace_bash("sed -i 's/a/b/' README.md\ngrep -n x app/a.py"), self.COMMIT],
        }
        for name, records in {**bad, **good}.items():
            with self.subTest(run=name):
                self.assertEqual(re.search(pattern, "\n".join(records)) is not None, name in bad)

    def test_the_untested_commit_grader_keeps_its_known_limits(self):
        """docs/evals.md names these wrong verdicts. A pattern change that fixes one also changes the docs."""
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        pattern = cases["so-two-fixes"].graders["untested-commit"][0]["pattern"]
        runs = {
            "a bad run passes: xargs sed": ("git ls-files '*.py' | xargs sed -i 's/a/b/'", False),
            "a bad run passes: the paths in a variable": ('sed -i "s/a/b/" $FILES', False),
            "a bad run passes: sed -Ei": ("sed -Ei 's/a/b/' app/a.py", False),
            "a bad run passes: a script over two lines": ("sed -i '/a/{\ns/a/b/\n}' app/a.py", False),
            "a bad run passes: find -exec sed": ("find app -name '*.py' -exec sed -i 's/a/b/' {} +", False),
            "a bad run passes: sed on the second line": ("cd /w\nsed -i 's/a/b/' app/a.py", False),
            "a bad run passes: a semicolon in a quoted sed script": ("sed -i 's/a;b/c/' app/a.py", False),
            "a bad run passes: a bar as the sed delimiter": ("sed -i 's|a|b|' app/billing.py", False),
            "a bad run passes: an ampersand in a quoted perl script": ("perl -pi -e 's/a&b/c/' app/a.py", False),
        }
        for name, (command, expected) in runs.items():
            with self.subTest(run=name):
                trace = "\n".join([self.TEST_RUN, trace_bash(command), self.COMMIT])
                self.assertEqual(re.search(pattern, trace) is not None, expected)

    def test_the_untested_commit_grader_is_fast_on_many_sed_edits(self):
        """The grader needs less than 2 seconds for a command with 4000 sed edits or 4000 -e scripts."""
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        pattern = re.compile(cases["so-two-fixes"].graders["untested-commit"][0]["pattern"])
        inputs = {
            "4000 sed edits joined by &&": "sed -i 's/a;b/c/' x.md && " * 4000,
            "4000 sed scripts in one command": "sed -i " + "-e 's/a/b/' " * 4000 + "notes.md",
        }
        for name, command in inputs.items():
            with self.subTest(input=name):
                trace = "\n".join([self.TEST_RUN, trace_bash(command)])
                start = time.perf_counter()
                self.assertIsNone(pattern.search(trace))
                self.assertLess(time.perf_counter() - start, 2.0)

    def test_every_case_has_the_same_untested_commit_grader(self):
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        graders = [cases[name].graders["untested-commit"][0] for name in TBC_CASES]
        self.assertEqual(len({grader["pattern"] for grader in graders}), 1)
        for name, grader in zip(TBC_CASES, graders):
            with self.subTest(case=name):
                self.assertEqual((grader.get("target"), grader.get("match")), ("trace", "not_contains"))


class RouteReportedGraderTests(unittest.TestCase):
    """The graders route-reported accept a Route line that names a delegation test, the main loop, or a label of Rule 1."""

    SO_CASES = ("so-lookup", "so-rename-large", "so-rename-small", "so-two-fixes")
    LABEL_LINES = {
        "a workflow dispatch": "Route: stage 2 (workflow).",
        "a stronger model": "Route: plan (stronger model).",
        "a Rule 4 dispatch": "Route: PR threads (outside system).",
    }

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(FP_ROOT)}

    def matches(self, name, reply):
        grader = self.cases[name].graders["route-reported"][0]
        flags = re.I if "i" in grader.get("flags", "") else 0
        return re.search(grader["pattern"], reply, flags) is not None

    def test_the_route_line_may_name_the_reviewer_or_the_main_session(self):
        runs = {
            "a reviewer and the main session": ("Route: research and the edit in the main session; one Opus reviewer subagent.", True),
            "a reviewer subagent only": ("Route: one reviewer subagent (Opus); all other work in the main session.", True),
            "the main loop": ("Route: research, plan and tests ran in the main loop.", True),
            "no Route line": ("The retry limit is now 3.", False),
            "a Route line with no reason": ("Route: n/a", False),
            "the colon on another line": ("Route\nreviewer", False),
        }
        for name, (reply, expected) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(self.matches("rirr-retry-limit", reply), expected)

    def test_every_so_case_has_the_same_route_reported_grader(self):
        graders = [self.cases[name].graders["route-reported"][0] for name in self.SO_CASES]
        self.assertEqual(len({grader["pattern"] for grader in graders}), 1)
        for name, grader in zip(self.SO_CASES, graders):
            with self.subTest(case=name):
                self.assertEqual((grader.get("target"), grader.get("flags")), ("last_message", "i"))

    def test_the_so_grader_accepts_each_test_and_each_label(self):
        runs = {
            "the main loop": ("Route: main loop", True),
            "two tests": ("Route: code search (context), two fixes (parallel work)", True),
            "a review": ("Route: review of the diff (independent view)", True),
            "read-only tools": ("Route: audit (tool isolation)", True),
            **{name: (line, True) for name, line in self.LABEL_LINES.items()},
            "no Route line": ("The retry limit is now 3.", False),
            "a Route line with no reason": ("Route: one subagent", False),
            "a reason that is no label": ("Route: plan (a better model)", False),
            "a label with no Route line": ("Stage 2 ran in the workflow (stronger model).", False),
            "the colon on another line": ("Route\nworkflow", False),
            "a longer word": ("Route: stage 2 (workflows)", False),
        }
        for name, (reply, expected) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(self.matches("so-lookup", reply), expected)

    def test_the_rirr_grader_accepts_each_label(self):
        for name, line in self.LABEL_LINES.items():
            with self.subTest(run=name):
                self.assertTrue(self.matches("rirr-retry-limit", line))


DOTNET_ROOT = REPO / "dotnet" / "dotnet-backend-dev"


def bash_input(command):
    """The JSON text of the input of a Bash call, as a tool_used grader reads it."""
    return json.dumps({"command": command, "description": "Run it"}, separators=(",", ":"), ensure_ascii=False)


class RoutePlainDotnetGraderTests(unittest.TestCase):
    """The graders route-plain-dotnet count a dotnet build or dotnet test command with no -m:1 at the start of a command."""

    @classmethod
    def setUpClass(cls):
        cls.graders = {case.label: case.graders["route-plain-dotnet"][0] for root in (FP_ROOT, DOTNET_ROOT)
                       for case in load_cases(root) if "route-plain-dotnet" in case.graders}
        cls.pattern = re.compile(next(iter(cls.graders.values()))["input_match"])

    def check(self, runs):
        for name, (command, expected) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(self.pattern.search(bash_input(command)) is not None, expected)

    def test_every_dotnet_case_has_the_same_grader(self):
        self.assertEqual(len(self.graders), 12)
        self.assertEqual(len({grader["input_match"] for grader in self.graders.values()}), 1)
        for label, grader in self.graders.items():
            with self.subTest(case=label):
                self.assertEqual((grader["type"], grader["tool"], grader["min"], grader["max"]), ("tool_used", "Bash", 0, 0))

    def test_a_plain_call_counts(self):
        self.check({
            "a plain build": ("dotnet build Inventory.sln", True),
            "a quoted filter": ('dotnet test Inventory.sln --filter "Category=Unit|Category=Fast"', True),
            "after cd and &&": ('cd "/x y" && dotnet build Inventory.sln', True),
            "on the second line": ("git status\ndotnet test Inventory.sln", True),
            "indented in an if block": ("if true; then\n  dotnet test Inventory.sln\nfi", True),
            "after timeout": ("timeout 300 dotnet test Inventory.sln 2>&1 | tail -15", True),
            "after timeout with an option": ("timeout --signal=KILL 300 dotnet test Inventory.sln", True),
            "after if !": ("if ! dotnet build Inventory.sln; then echo failed; fi", True),
            "in a command substitution": ("out=$(dotnet test Inventory.sln 2>&1)", True),
            "after an assignment": ("DOTNET_NOLOGO=1 dotnet build Inventory.sln", True),
            "after env": ("env DOTNET_NOLOGO=1 dotnet test Inventory.sln", True),
            "after time": ("time dotnet build Inventory.sln", True),
            "in a loop": ("for p in a b; do dotnet test $p; done", True),
            "in a subshell": ("(cd src && dotnet build)", True),
            "in braces": ("{ dotnet build Inventory.sln; } 2>&1", True),
            "after a pipe": ("echo x | dotnet test Inventory.sln", True),
            "indented with a tab": ("if true; then\n\tdotnet test Inventory.sln\nfi", True),
            "after an assignment with a double-quoted value": ('DOTNET_CLI_HOME="$HOME" dotnet build Inventory.sln', True),
            "after env with a double-quoted value": ('env DOTNET_NOLOGO="1" dotnet test Inventory.sln', True),
            "with -m:2": ("dotnet build Inventory.sln -m:2", True),
            "a plain test after a build with -m:1": ("dotnet build Inventory.sln -m:1; dotnet test Inventory.sln", True),
        })

    def test_a_call_with_one_process_and_text_do_not_count(self):
        self.check({
            "-m:1": ("dotnet build Inventory.sln -m:1", False),
            "-maxcpucount:1": ("dotnet test Inventory.sln -maxcpucount:1", False),
            "-m 1": ("dotnet build Inventory.sln -m 1", False),
            "-m=1": ("dotnet test Inventory.sln -m=1 2>&1 | tail -5", False),
            "two calls with -m:1": ("cd /w && dotnet build Inventory.sln -m:1 2>&1 | tail -3; echo exit=$?; "
                                    "dotnet test Inventory.sln -m:1 --filter X", False),
            "build-server": ("dotnet build-server shutdown", False),
            "restore": ("dotnet restore Inventory.sln", False),
            "a prompt script in a heredoc": (
                "cat > $TMPDIR/fp/compose.py <<'EOF'\nparts.append('<machine-constraint>\\nOn this machine, MSBuild can use only "
                "one process. Pass `-m:1` to every `dotnet build` and `dotnet test` command you run.')\nEOF", False),
            "a review file in a heredoc": (
                "cat > .pipeline/821/review.md <<'EOF'\n## Suggestions\n- I did not run a separate `dotnet build`, so I have "
                "no `0 Warning(s)` line.\nEOF", False),
            "an echo text in a heredoc": (
                "cat > $TMPDIR/compose.sh <<'EOF'\necho 'Machine constraint from the user: Pass -m:1 to EVERY dotnet build and "
                "dotnet test command.'\nEOF", False),
            "a commit message": ('git commit -m "Pass -m:1 to dotnet build"', False),
            "a search for the text": ("grep -rn 'dotnet build' .claude", False),
        })

    def test_the_grader_keeps_its_known_limits(self):
        """docs/evals.md names these wrong verdicts. A pattern change that fixes one also changes the docs."""
        self.check({
            "a plain call is missed: bash -c": ('bash -c "dotnet build Inventory.sln"', False),
            "a plain call is missed: another word before it": ("nice dotnet build Inventory.sln", False),
            "a plain call is missed: a timeout option with a value": ("timeout -k 5 300 dotnet build Inventory.sln", False),
            "a plain call is missed: a space in an assignment value": ('X="a b" dotnet build Inventory.sln', False),
            "a plain call is missed: a pipe in an assignment value": ("F='A|B' dotnet test Inventory.sln", False),
            "a plain call is missed: an ampersand in an assignment value": ("F='A&B' dotnet test Inventory.sln", False),
            "a plain call is missed: a semicolon in an assignment value": ("F='A;B' dotnet test Inventory.sln", False),
            "a plain call is missed: a path before dotnet": ("$HOME/.dotnet/dotnet build Inventory.sln", False),
            "a plain call is missed: a call in backticks": ("out=`dotnet test Inventory.sln`", False),
            "a plain call is missed: -m:1 of a later command": (
                "dotnet build Inventory.sln && dotnet test Inventory.sln -m:1", False),
            "text counts: a heredoc line that starts with the command": (
                "cat > notes.md <<'EOF'\nRun this:\ndotnet build Inventory.sln\nEOF", True),
            "text counts: quoted text after a semicolon": ("echo 'Build first; dotnet build is slow.'", True),
        })

    def test_the_grader_is_fast_on_long_commands(self):
        """The grader needs less than 2 seconds for a command with 4000 assignments, 4000 timeout options, 16000 joined assignments, or 4000 echo texts with -m:1."""
        inputs = {
            "4000 assignments": "X=1 " * 4000 + "echo",
            "4000 timeout options": "timeout " + "-k " * 4000 + "echo",
            "16000 assignments joined by semicolons": "X=a\x3b" * 16000 + " echo",
            "4000 echo texts that name the command": "echo 'a; dotnet build -m:1 is slow'; " * 4000,
        }
        for name, command in inputs.items():
            with self.subTest(input=name):
                start = time.perf_counter()
                self.assertIsNone(self.pattern.search(bash_input(command)))
                self.assertLess(time.perf_counter() - start, 2.0)


class PrCreatedGraderTests(unittest.TestCase):
    """The grader pr-created of fp-e2-untracked-file reads only the tool field of each mocked call.

    A line has the form of the mock_calls text of an eval run: the full tool name, the input, the output, and the verdict.
    """

    @staticmethod
    def call(tool, tool_input, output="{}"):
        return json.dumps({"tool": "mcp__plugin_github_github__" + tool, "input": tool_input, "output": output,
                           "verdict": "ok"}, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def setUpClass(cls):
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        cls.meta = cases["fp-e2-untracked-file"].graders["pr-created"][0]

    def test_only_a_call_of_the_pr_tool_passes(self):
        self.assertEqual((self.meta["target"], self.meta.get("match", "contains")), ("mock_calls", "contains"))
        read = self.call("issue_read", {"method": "get", "owner": "example-org", "repo": "inventory", "issue_number": 821})
        comment = self.call("add_issue_comment", {"issue_number": 821, "body": "Stage 9 started."})
        pr = self.call("create_pull_request", {"owner": "example-org", "repo": "inventory", "base": "main",
                                               "head": "work/untracked-file", "title": "Reject a blank SKU"}, '{"number": 77}')
        runs = {
            "the PR call": ([read, comment, pr], True),
            "a comment names the tool": ([read, self.call("add_issue_comment", {"body": "Next: call create_pull_request."})], False),
            "a comment quotes a call line": ([read, self.call("add_issue_comment", {"body": '{"tool":"create_pull_request"}'})],
                                             False),
            "a read answer names the tool": ([self.call("issue_read", {"issue_number": 821}, "Use create_pull_request."), comment],
                                             False),
            "another tool whose name starts with the PR tool": ([read, self.call("create_pull_request_with_copilot", {})], False),
            "no mocked call": ([], False),
        }
        for name, (calls, expected) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(re.search(self.meta["pattern"], "\n".join(calls)) is not None, expected)


class PrBodyFormGraderTests(unittest.TestCase):
    """The graders of fp-e2-untracked-file for the PR body in the form of compose-pr (issue #203).

    A line has the form of the mock_calls text of an eval run: the full tool name, the input, the output, and the verdict.
    """

    FORM = ("## What\nReject a blank sku.\n\n## Why\nA blank sku reached the database.\n\n"
            "## Changes\n- **SkuFormatter**: throws for a blank sku.\n\n## Testing\nUnit tests.\n\nCloses #821.")

    @staticmethod
    def call(tool, tool_input, output="{}"):
        return json.dumps({"tool": "mcp__plugin_github_github__" + tool, "input": tool_input, "output": output,
                           "verdict": "ok"}, separators=(",", ":"), ensure_ascii=False)

    def pr(self, body, **fields):
        return self.call("create_pull_request", {"owner": "example-org", "repo": "inventory", "base": "main",
                                                 "head": "work/untracked-file", "title": "Reject a blank sku",
                                                 "body": body, **fields}, '{"number": 77}')

    @classmethod
    def setUpClass(cls):
        cls.graders = {case.name: case for case in load_cases(FP_ROOT)}["fp-e2-untracked-file"].graders

    def test_only_a_pr_body_in_the_form_of_compose_pr_passes(self):
        meta = self.graders["pr-body-form"][0]
        self.assertEqual((meta["target"], meta.get("match", "contains")), ("mock_calls", "contains"))
        free = self.pr("Free text.\n\nCloses #821.")
        runs = {
            "the form": ([self.pr(self.FORM)], True),
            "the body before the other fields": ([self.call("create_pull_request", {"body": self.FORM})], True),
            "a closing line before What": ([self.pr("Closes #821.\n\n" + self.FORM)], True),
            "no Testing section": ([self.pr("## What\nx\n\n## Why\ny\n\n## Changes\n- z\n")], True),
            "Why before What": ([self.pr("## Why\ny\n\n## What\nx\n\n## Changes\n- z\n")], False),
            "a Summary section first": ([self.pr("## Summary\ns\n\n" + self.FORM)], False),
            "a title first": ([self.pr("# Reject a blank sku\n\n" + self.FORM)], False),
            "a heading between What and Why": ([self.pr("## What\nx\n\n### Detail\nd\n\n## Why\ny\n\n## Changes\n- z\n")],
                                               False),
            "a section between Why and Changes": ([self.pr("## What\nx\n\n## Why\ny\n\n## Tests\nt\n\n## Changes\n- z\n")],
                                                  False),
            "third-level headings": ([self.pr("### What\nx\n\n### Why\ny\n\n### Changes\n- z\n")], False),
            "Why in the middle of a line": ([self.pr("## What\nx ## Why\ny\n\n## Changes\n- z\n")], False),
            "Changes in the middle of a line": ([self.pr("## What\nx\n\n## Why\ny ## Changes\n- z\n")], False),
            "no Changes section": ([self.pr("## What\nx\n\n## Why\ny\n")], False),
            "the form in a comment only": ([self.call("add_issue_comment", {"issue_number": 821, "body": self.FORM}), free],
                                           False),
            "the form in a read answer only": ([self.call("issue_read", {"issue_number": 821}, json.dumps({"body": self.FORM})),
                                                free], False),
            "the form in a comment after the PR call": ([free, self.call("add_issue_comment", {"issue_number": 821, "body": self.FORM})], False),
            "a Summary section after a closing line": ([self.pr("Closes #821.\n\n## Summary\ns\n\n" + self.FORM)], False),
            "a line that starts with an issue number": ([self.pr("## What\nReject a blank sku.\n#821 asked for it.\n\n## Why\ny\n\n## Changes\n- z\n")], True),
            "a first line that starts with an issue number": ([self.pr("#821 asked for it.\n\n" + self.FORM)], True),
            "a line before What that starts with an issue number": ([self.pr("Closes #821.\n#821 asked for it.\n\n" + self.FORM)], True),
            "a line in Why that starts with an issue number": ([self.pr("## What\nx\n\n## Why\ny\n#821 asked for it.\n\n## Changes\n- z\n")], True),
            "the form in the title only": ([self.pr("Free text.", title=self.FORM)], False),
            "no mocked call": ([], False),
        }
        for name, (calls, expected) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(re.search(meta["pattern"], "\n".join(calls)) is not None, expected)

    def test_the_length_grader_passes_only_a_body_of_at_most_1000_characters(self):
        meta = self.graders["pr-body-length"][0]
        self.assertEqual((meta["target"], meta.get("match", "contains")), ("mock_calls", "contains"))
        self.assertIsNotNone(re.search(meta["pattern"], self.pr("## What\n" + "a" * 992)))
        self.assertIsNone(re.search(meta["pattern"], self.pr("## What\n" + "a" * 993)))
        comment = self.call("add_issue_comment", {"issue_number": 821, "body": "Opened the PR."})
        self.assertIsNone(re.search(meta["pattern"], self.pr("## What\n" + "a" * 993) + "\n" + comment))

    def test_the_draft_grader_names_the_draft_file_of_compose_pr(self):
        meta = self.graders["pr-draft-not-saved"][0]
        self.assertEqual((meta["type"], meta["path"], meta["exists"]),
                         ("file_exists", "Notes/PRs/PR-work-untracked-file.md", False))

    def test_the_stage_names_the_step_of_compose_pr_that_has_the_form(self):
        skill = (FP_ROOT / "skills" / "compose-pr" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("### 5. Generate PR Description", skill)
        self.assertRegex(skill, r"`{3}md\n## What\n[^\n]*\n\n## Why\n[^\n]*\n\n## Changes\n")
        stage = (FP_STAGES / "finalization.md").read_text(encoding="utf-8")
        self.assertIn('"5. Generate PR Description"', stage)


class ForkHeadMockTests(unittest.TestCase):
    """The mock of the PR call guards head: the bare branch with no fork, and <fork owner>:<branch> for a fork (issue #225).

    A call that breaks the expect block of a mock ends the eval run with the score 0.
    """

    # The case, its work branch, and the fork owner of its project context.
    CASES = {"fp-e2-untracked-file": ("work/untracked-file", None), "fp-e2-fork-pr": ("work/fork-pr", "eval-user")}

    @staticmethod
    def case_file(case, *parts):
        return (FP_ROOT / EVALS / "feature-pipeline" / case).joinpath(*parts).read_text(encoding="utf-8")

    def test_the_mock_expects_the_head_that_the_project_context_gives(self):
        for case, (branch, owner) in self.CASES.items():
            with self.subTest(case=case):
                lines, _body = split_frontmatter(self.case_file(case, "mocks", "github", "create_pull_request.md"))
                expect = parse_block(lines)["expect"]
                self.assertEqual((expect["owner"], expect["repo"], expect["base"]), ("example-org", "inventory", "main"))
                self.assertEqual(expect["head"], f"{owner}:{branch}" if owner else branch)
                scaffold = self.case_file(case, "scaffold.sh")
                self.assertIn(f"git checkout -q -b {branch}\n", scaffold)
                if owner:
                    self.assertIn(f"fork owner `{owner}`", scaffold)
                else:
                    self.assertNotIn("fork owner", scaffold)

    def test_the_stage_and_the_template_name_the_fork_owner(self):
        stage = (FP_STAGES / "finalization.md").read_text(encoding="utf-8")
        self.assertIn("pass `<fork owner>:<branch>`", stage)
        self.assertIn("Without a fork owner, pass the bare branch.", stage)
        template = (FP_ROOT / "skills" / "feature-pipeline" / "project-context.template.md").read_text(encoding="utf-8")
        self.assertIn("fork owner `my-user`", template)


# The start of a mock_calls pattern: the tool field, with or without the prefix of the server.
MOCK_CALL_FIELD = '"tool":"(?:[\\w-]*__)?'
# The field, then one tool name or a group (?:a|b) of names, then the closing quote. A name can end with \w*.
BOUND_TOOL_FIELD = re.compile(re.escape(MOCK_CALL_FIELD) + r'(?:\w+|\(\?:\w+(?:\\w\*)?(?:\|\w+(?:\\w\*)?)*\))"')
# The only piece that can join two tool fields across lines: a grader of the order of two calls.
CALL_ORDER_SPANS = {r"[\s\S]*", r"[\s\S]*?"}
# The escapes that also match a line end, outside a negated class.
LINE_END_ESCAPES = {"\\n", "\\s", "\\W", "\\D"}


def alternatives(pattern):
    """The parts of a pattern between the | signs that are outside each group and each class."""
    parts, start, depth, index, in_class = [], 0, 0, 0, False
    while index < len(pattern):
        char = pattern[index]
        if char == "\\":
            index += 2
            continue
        if in_class:
            in_class = char != "]"
        elif char == "[":
            in_class = True
        elif char in "()":
            depth += 1 if char == "(" else -1
        elif char == "|" and depth == 0:
            parts.append(pattern[start:index])
            start = index + 1
        index += 1
    return parts + [pattern[start:]]


def crosses_line_end(piece):
    """True if the piece holds \\n, \\s, \\W, or \\D outside a negated class, or a negated class without \\n."""
    index = 0
    while index < len(piece):
        if piece[index] == "\\":
            if piece[index:index + 2] in LINE_END_ESCAPES:
                return True
            index += 2
        elif piece[index] == "[":
            items, index = [], index + 1
            while index < len(piece) and piece[index] != "]":
                step = 2 if piece[index] == "\\" else 1
                items.append(piece[index:index + step])
                index += step
            index += 1
            if items[:1] == ["^"]:
                if "\\n" not in items:
                    return True
            elif LINE_END_ESCAPES & set(items):
                return True
        else:
            index += 1
    return False


def mocked_tools(repo=REPO):
    """The names of the mocked tools: the file names of mocks/<server>/<tool>.md in the eval folders of all plugins."""
    return {path.stem for root in plugin_roots(repo) for path in (root / EVALS).glob("**/mocks/*/*.md")}


def mock_calls_problems(case, tools):
    """A regex grader on mock_calls reads a tool name only in the tool field, and it reads the input of that call line only.

    Each piece after a tool field must not cross a line end, except a [\\s\\S]* that ends at the next tool field.
    """
    problems = []
    for name, (meta, _body) in sorted(case.graders.items()):
        if meta.get("type") != "regex" or meta.get("target") != "mock_calls":
            continue
        where = f"{case.label}/graders/{name}.md"
        for pattern in alternatives(str(meta.get("pattern", ""))):
            if not BOUND_TOOL_FIELD.match(pattern):
                problems.append(f"{where}: the pattern {pattern} does not start with {MOCK_CALL_FIELD}<tool>\"")
                continue
            pieces = BOUND_TOOL_FIELD.split(pattern)[1:]
            # An escape such as \b or \W before a name is not a letter of a word.
            words = [re.sub(r"\\.", " ", piece) for piece in pieces]
            named = sorted(tool for tool in tools if any(
                re.search(rf"(?<![A-Za-z0-9]){re.escape(tool)}(?![A-Za-z0-9_])", word) for word in words))
            if named:
                problems.append(f"{where}: the pattern names {', '.join(named)} outside the tool field")
            for index, piece in enumerate(pieces):
                if index < len(pieces) - 1 and piece in CALL_ORDER_SPANS:
                    continue
                if crosses_line_end(piece):
                    problems.append(f"{where}: the piece {piece} can cross the end of a call line")
        if "s" in str(meta.get("flags", "")):
            problems.append(f"{where}: the flag s lets . cross the end of a call line")
    return problems


class MockCallsGraderTests(unittest.TestCase):
    """Each regex grader on mock_calls reads a tool name only in the tool field of a call line (issue #189).

    A line has the form of the mock_calls text of an eval run: the full tool name, the input, the output, and the verdict.
    """

    SOURCE = "Source: https://github.com/example-org/pager/pull/42#discussion_r9103"

    @classmethod
    def setUpClass(cls):
        cls.all_cases = [case for root in plugin_roots() for case in load_cases(root)]
        cls.cases = {case.name: case for case in load_cases(FP_ROOT)}
        cls.tools = mocked_tools()

    @staticmethod
    def call(tool, tool_input, output="{}"):
        return json.dumps({"tool": "mcp__plugin_github_github__" + tool, "input": tool_input, "output": output,
                           "verdict": "ok"}, separators=(",", ":"), ensure_ascii=False)

    def passes(self, case, grader, calls):
        meta = self.cases[case].graders[grader][0]
        self.assertEqual(meta.get("target"), "mock_calls")
        found = sum(1 for _ in re.finditer(meta["pattern"], "\n".join(calls)))
        match = meta.get("match", "contains")
        if match == "not_contains":
            return found == 0
        if match.startswith("count:"):
            return found == int(match[len("count:"):])
        return found > 0

    def check(self, case, grader, runs):
        for name, (calls, expected) in runs.items():
            with self.subTest(grader=grader, run=name):
                self.assertEqual(self.passes(case, grader, calls), expected)

    def test_each_mock_calls_grader_of_the_repository_reads_the_tool_field(self):
        self.assertIn("issue_write", self.tools)
        graders = [name for case in self.all_cases for name, (meta, _body) in case.graders.items()
                   if meta.get("type") == "regex" and meta.get("target") == "mock_calls"]
        self.assertTrue(graders, "No regex grader on mock_calls found.")
        self.assertEqual([problem for case in self.all_cases for problem in mock_calls_problems(case, self.tools)], [])

    def test_the_check_finds_each_bad_form(self):
        tools = {"issue_write", "issue_read", "get_label", "add_reply_to_pull_request_comment"}
        reply = MOCK_CALL_FIELD + 'add_reply_to_pull_request_comment"'
        issue = MOCK_CALL_FIELD + 'issue_write"'
        forms = {
            "a bare tool name": ("issue_write", "does not start with"),
            "a field with \\w* only": ('"tool":"\\w*issue_write"', "does not start with"),
            "a bare method": ("resolve_thread", "does not start with"),
            "a second tool with no field": (issue + "[^\\n]*issue_read", "names issue_read outside"),
            "a span across lines": (reply + "[\\s\\S]{0,400}AI", "can cross the end"),
            "a negated class without the line end": (issue + "[^\\n]*labels[^\\]]*feature", "can cross the end"),
            "an order of two calls with an unbound end": (reply + "[\\s\\S]*issue_write", "names issue_write outside"),
            "an order span at the end": (issue + "[\\s\\S]*", "can cross the end"),
            "the flag s": (issue + ".*AI", "the flag s"),
            "a bare method after a bar": (issue + "|resolve_thread", "does not start with"),
            "a class [\\w\\W]": (reply + "[\\w\\W]{0,400}AI", "can cross the end"),
            "a line end": (reply + "[^\\n]*\\n[^\\n]*AI", "can cross the end"),
            "a tool name after \\b": (reply + "[^\\n]*\\bissue_read\\b", "names issue_read outside"),
            "a class [\\d\\D]": (reply + "[\\d\\D]{0,400}AI", "can cross the end"),
            "a class with a line end": (reply + "[^\\n]*[ \\n]AI", "can cross the end"),
            "a bare \\s": (issue + "[^\\n]*\\s[^\\n]*AI", "can cross the end"),
            "a bare \\D": (reply + "[^\\n]*?commentId\\D*9102", "can cross the end"),
            "a right call": (issue, None),
            "a right bar between two calls": (issue + "|" + reply, None),
            "a right method get_labels": (MOCK_CALL_FIELD + 'issue_read"[^\\n]*?"method":"get_labels"', None),
            "a right escaped line end in a body": (issue + "[^\\n]*Analysis\\\\n", None),
            "a right escaped bar": (issue + "[^\\n]*\\|AI", None),
            "a right bar in a class": (issue + "[^\\n]*[a|b]AI", None),
            "a right name with more after an underscore": (MOCK_CALL_FIELD + 'issue_read"[^\\n]*?get_label_names', None),
            "a right word that ends with a tool name": (issue + "[^\\n]*?budget_label", None),
            "a right group of names": (MOCK_CALL_FIELD + '(?:issue_write|create_\\w*)"', None),
            "a right input": (reply + '[^\\n]{0,400}?commentId[^\\w\\n]{1,4}9102\\b', None),
            "a right order of two calls": (reply + "[\\s\\S]*" + issue, None),
        }
        for name, (pattern, expected) in forms.items():
            with self.subTest(form=name):
                meta = {"type": "regex", "target": "mock_calls", "pattern": pattern}
                if name == "the flag s":
                    meta["flags"] = "s"
                problems = mock_calls_problems(SimpleNamespace(label="case", graders={"g": (meta, "")}), tools)
                if expected is None:
                    self.assertEqual(problems, [])
                else:
                    self.assertTrue(any(expected in problem for problem in problems), problems)
        trace = {"type": "regex", "target": "trace", "pattern": "issue_write"}
        self.assertEqual(mock_calls_problems(SimpleNamespace(label="case", graders={"g": (trace, "")}), tools), [])

    def test_a_field_grader_needs_the_tool_with_its_full_name(self):
        right = self.call("issue_write", {"method": "create", "title": "Add an index", "body": self.SOURCE})
        self.check("ppc-open-items-answered", "issue-source", {
            "the create call": ([right], True),
            "a call of sub_issue_write": ([self.call("sub_issue_write", {"method": "add", "body": self.SOURCE})], False),
        })
        body = {"method": "create", "title": "Add an index", "body": "Needs labels [see the read-back"}
        read = self.call("issue_read", {"method": "get", "issue_number": 77}, '{"labels": [{"name": "feature"}]}')
        self.check("cmp-issue-create", "label-kept", {
            "the label in the create call": ([self.call("issue_write", {**body, "labels": ["feature"]}), read], True),
            "a bracket in the body, the label only in the read-back": ([self.call("issue_write", body), read], False),
        })

    def test_a_call_grader_ignores_the_name_in_another_call(self):
        read = self.call("pull_request_read", {"method": "get_review_comments"}, "Run search_issues first.")
        self.check("ppc-gated-threads", "searched", {
            "the search call": ([self.call("search_issues", {"query": "repo:example-org/pager index"})], True),
            "the name in a read answer": ([read], False),
        })

    def test_a_no_call_grader_ignores_the_name_in_another_call(self):
        read = self.call("pull_request_read", {"method": "get"}, "Answer with add_reply_to_pull_request_comment.")
        self.check("ppc-tofix-default", "reply-waits", {
            "the name in a read answer": ([read], True),
            "the reply call": ([read, self.call("add_reply_to_pull_request_comment", {"commentId": 9101})], False),
        })
        search = self.call("search_issues", {"query": "create_issue issue_write add_issue_comment"}, "No issue_write.")
        self.check("bh-github-known", "no-github-write", {
            "the names in a search": ([search], True),
            "an issue": ([search, self.call("issue_write", {"method": "create", "title": "Fix the cache"})], False),
            "a comment": ([search, self.call("add_issue_comment", {"issue_number": 17, "body": "Same cause."})], False),
        })

    def test_a_count_grader_counts_the_calls_only(self):
        def reply(comment, body):
            return self.call("add_reply_to_pull_request_comment", {"commentId": comment, "body": body})
        issue = self.call("issue_write", {"method": "create", "body": "Then add_reply_to_pull_request_comment."})
        self.check("ppc-open-items-answered", "two-replies", {
            "two replies and the name in an issue": ([issue, reply(9102, "a"), reply(9103, "b")], True),
            "three replies": ([reply(9102, "a"), reply(9103, "b"), reply(9104, "c")], False),
        })

    def test_an_order_grader_binds_both_calls(self):
        issue = self.call("issue_write", {"method": "create", "title": "Add an index"}, '{"number": 77}')
        reply = self.call("add_reply_to_pull_request_comment", {"commentId": 9103, "body": "Made with issue_write: #77."})
        self.check("ppc-open-items-answered", "issue-before-batch", {
            "the issue first, the reply names the tool": ([issue, reply], True),
            "the reply first": ([reply, issue], False),
        })
        write = self.call("issue_write", {"method": "create", "body": "Then issue_read."})
        self.check("cmp-issue-create", "read-back", {
            "the read call after the create call": ([write, self.call("issue_read", {"issue_number": 77})], True),
            "the name in the create call only": ([write], False),
        })

    def test_an_input_grader_reads_the_line_of_its_call(self):
        draft = self.call("pull_request_read", {"method": "get"}, "Then resolve_thread.")
        resolve = self.call("pull_request_review_write", {"method": "resolve_thread", "threadId": "PRRT_1"})
        self.check("ppc-tofix-default", "no-resolve", {
            "the method in a read answer": ([draft], True),
            "a pending review": ([draft, self.call("pull_request_review_write", {"method": "create"})], True),
            "a resolve": ([draft, resolve], False),
        })
        untagged = self.call("add_reply_to_pull_request_comment", {"commentId": 9101, "body": "Fixed."})
        self.check("ppc-autonomous-push", "replied", {
            "the tag in the reply": ([self.call("add_reply_to_pull_request_comment", {"body": "**[AI]** Fixed."})], True),
            "the tag only in the next call": ([untagged, self.call("issue_write", {"body": "**[AI]** note"})], False),
        })
        self.check("ppc-open-items-answered", "question-replied", {
            "the reply on the thread": ([self.call("add_reply_to_pull_request_comment", {"commentId": 9102})], True),
            "the id only in the next call": ([untagged, self.call("issue_read", {"commentId": 9102})], False),
        })


class PpcOpenItemsGraderTests(unittest.TestCase):
    """The graders of ppc-open-items-answered read the mocked calls, one JSON line for each call.

    A line has the form of the mock_calls text of an eval run: the full tool name, the input, the output, and the verdict.
    """

    CASE = "ppc-open-items-answered"
    SOURCE = "Source: https://github.com/example-org/pager/pull/42#discussion_r9103"

    @classmethod
    def setUpClass(cls):
        cls.graders = {case.name: case for case in load_cases(FP_ROOT)}[cls.CASE].graders

    @staticmethod
    def call(tool, **fields):
        call = {"tool": "mcp__plugin_github_github__" + tool, "input": fields, "output": "{}", "verdict": "ok"}
        return json.dumps(call, separators=(",", ":"))

    def right_run(self):
        return [
            self.call("search_issues", query="Add an index on the customer column"),
            self.call("issue_write", method="create", title="Add an index", body="## Current State Analysis\n\n" + self.SOURCE),
            self.call("issue_read", method="get", issue_number=77),
            self.call("add_reply_to_pull_request_comment", commentId=9102, body="**[AI]** The check comes first."),
            self.call("add_reply_to_pull_request_comment", commentId=9103, body="**[AI]** Tracked as issue #77: Add an index."),
        ]

    def passes(self, grader, calls):
        meta = self.graders[grader][0]
        self.assertEqual(meta.get("target"), "mock_calls")
        found = sum(1 for _ in re.finditer(meta["pattern"], "\n".join(calls)))
        match = meta.get("match", "contains")
        if match == "not_contains":
            return found == 0
        if match.startswith("count:"):
            return found == int(match[len("count:"):])
        return found > 0

    def test_a_right_run_passes_each_grader_of_the_mocked_calls(self):
        names = [name for name, graders in self.graders.items() if graders[0].get("target") == "mock_calls"]
        self.assertEqual(len(names), 8)
        for name in names:
            with self.subTest(grader=name):
                self.assertTrue(self.passes(name, self.right_run()))

    def test_each_wrong_run_fails_its_grader(self):
        search, issue, read, question, tracked = self.right_run()
        no_source = self.call("issue_write", method="create", title="Add an index", body="## Current State Analysis")
        runs = {
            "the source line only in the search query": ("issue-source", [self.call("search_issues", query=self.SOURCE), no_source, read]),
            "no issue": ("issue-created", [search, question]),
            "a reply before the issue": ("issue-before-batch", [search, question, issue, read, tracked]),
            "a resolve of a thread": ("no-resolve", [*self.right_run(), self.call("pull_request_review_write", method="resolve_thread")]),
            "one reply": ("two-replies", [search, issue, read, tracked]),
            "three replies": ("two-replies", [*self.right_run(), question]),
            "no reply on the question thread": ("question-replied", [search, issue, read, tracked]),
            "a reply that names no issue": ("reply-names-issue", [search, issue, read, question,
                                                                  self.call("add_reply_to_pull_request_comment", commentId=9103, body="Noted.")]),
            "no search": ("searched", [issue, read, question, tracked]),
        }
        for name, (grader, calls) in runs.items():
            with self.subTest(run=name):
                self.assertFalse(self.passes(grader, calls))


class PpcQuestionGraderTests(unittest.TestCase):
    """Two graders of the process-pr-comments suite read a question of the last message in more than one wording."""

    CREATE_QUESTION = '**Create issue "Add an index on the customer column"?** (yes / edit / skip)'
    DRAFT = "> **[AI]** **[[T#9102](https://example.com/pull/42#discussion_r9102)]**\n>\n> The check comes first.\n\n"

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(FP_ROOT)}

    def matches(self, case, grader, reply):
        meta = self.cases[case].graders[grader][0]
        self.assertEqual(meta.get("target"), "last_message")
        flags = re.I if "i" in meta.get("flags", "") else 0
        return re.search(meta["pattern"], reply, flags) is not None

    def test_asks_create_needs_an_empty_search_and_a_create_question(self):
        draft = "- **Body:** the lookup scans the whole table.\n" * 20
        runs = {
            "found none": ("I searched the repository for an existing issue and found none.\n\n" + self.CREATE_QUESTION, True),
            "found none, with the draft between": ("I searched for an existing issue and found none, though that search "
                                                   "can miss one.\n\n" + draft + "\n**Create this issue?**", True),
            "none found": ("Issue search: none found.\n\nShould I create the issue?", True),
            "found nothing": ("The issue search found nothing that tracks this.\n\n" + self.CREATE_QUESTION, True),
            "neither search found one": ("I searched twice. Neither search found one.\n\n**Create this issue?**", True),
            "could not find": ("I could not find an existing issue.\n\n" + self.CREATE_QUESTION, True),
            "zero results": ("The issue search returned zero results.\n\n" + self.CREATE_QUESTION, True),
            "came back empty": ("The issue search came back empty.\n\nShould I create the issue?", True),
            "a long quoted title before the word issue": ("I searched and found no existing issue.\n\n"
                                                          'Create "Add index on customer column of orders table" as a new '
                                                          "issue?", True),
            "a ticket": ("I searched and found no existing issue.\n\nShould I open a tracking ticket for this?", True),
            "neither search found a matching issue": ("Neither search found a matching issue.\n\n**Create this issue?**", True),
            "neither names two found issues": ("Neither of the two issues I found tracks the paging change.\n\n"
                                               "Should I create one for the index?", False),
            "neither found existing issues": ("Neither search found existing issues.\n\n" + self.CREATE_QUESTION, True),
            "neither names two found issues, with a comma": ("Neither of the two issues I found, #12 and #14, tracks the "
                                                             "paging change.\n\nShould I create one for the index?", False),
            "neither of my searches": ("Neither of my searches found an existing issue.\n\n" + self.CREATE_QUESTION, True),
            "neither search_issues call": ("Neither `search_issues` call found an existing issue.\n\n" + self.CREATE_QUESTION,
                                           True),
            "neither keyword": ("Neither keyword found an existing issue.\n\n" + self.CREATE_QUESTION, True),
            "neither of the issue searches": ("Neither of the issue searches found a match.\n\n" + self.CREATE_QUESTION, True),
            "neither names the search of found issues": ("Neither of the issues the search found tracks the paging "
                                                         "change.\n\nShould I create one for the index?", False),
            "neither names one found issue": ("Neither issue my search found tracks the paging change.\n\n"
                                              "Should I create one for the index?", False),
            "the question first": (self.CREATE_QUESTION + "\n\nThe search found none.", True),
            "question first, could not find": (self.CREATE_QUESTION + "\n\nI could not find an existing issue.", True),
            "question first, zero results": (self.CREATE_QUESTION + "\n\nThe issue search returned zero results.", True),
            "question first, came back empty": (self.CREATE_QUESTION + "\n\nThe issue search came back empty.", True),
            "question first, a long quoted title": ('Create "Add index on customer column of orders table" as a new issue?\n\n'
                                                    "I searched and found no existing issue.", True),
            "question first, a ticket": ("Should I open a tracking ticket for this?\n\nI searched and found no existing issue.",
                                         True),
            "question first, neither names found issues": (self.CREATE_QUESTION + "\n\nNeither of the two issues I found "
                                                           "tracks the paging change.", False),
            "question first, neither of my searches": (self.CREATE_QUESTION + "\n\nNeither of my searches found an "
                                                       "existing issue.", True),
            "question first, neither names the search of found issues": (self.CREATE_QUESTION + "\n\nNeither of the "
                                                                         "issues the search found tracks the paging "
                                                                         "change.", False),
            "question first, neither names one found issue": (self.CREATE_QUESTION + "\n\nNeither issue my search found "
                                                              "tracks the paging change.", False),
            "question first, neither of the issue searches": (self.CREATE_QUESTION + "\n\nNeither of the issue searches "
                                                              "found a match.", True),
            "a title in backticks": ("I searched and found no existing issue.\n\n"
                                     "Create `Add index on customer column of orders table` as a new issue?", True),
            "an issue with no question": ("I searched and found none. I created issue #7 and posted the reply.", False),
            "another question": ("I searched for an existing issue and found none.\n\n"
                                 "Should I open a follow-up PR for the index instead?", False),
            "a question with no search result": (self.CREATE_QUESTION, False),
            "the question far from the search result": ("The search found none.\n\n" + draft * 3 + self.CREATE_QUESTION, False),
        }
        for name, (reply, expected) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(self.matches("ppc-outofscope-autonomous", "asks-create", reply), expected)

    def test_question_drafted_needs_the_draft_of_the_question_reply(self):
        runs = {
            "post this answer": ("### 1. T#9102 `[Question]` at `src/pager.py:21`: post this answer?\n\n" + self.DRAFT
                                 + "**yes / edit / skip?**", True),
            "post this reply": (self.DRAFT + "Post this reply to T#9102?", True),
            "post this reply under the quoted draft": (self.DRAFT + "→ **Post this reply?** (yes / edit / skip)", True),
            "post the answer": (self.DRAFT + "Post the answer?", True),
            "post this reply on the line of the question thread": ("### 1. T#9102 `[Question]`: post this reply?\n\n"
                                                                   + self.DRAFT + "**yes / edit / skip?**", True),
            "a file path after the answer": (self.DRAFT + "Post this answer to the thread at src/pager.py:21?", True),
            "the draft tag": ("[AI][Draft] The check comes first.", True),
            "the question of the skill": ("Post this [Question] reply to T#9102?", True),
            "a reply question with the choices": ("Reply to T#9102 with this text? (yes / edit / skip)", True),
            "only the issue question": (self.CREATE_QUESTION, False),
            "a plan with no question": ("I post this reply after your answer about the issue.", False),
            "only the reply of the issue thread": ("T#9102 `[Question]`: I left it for you.\n\nT#9103 `[OutOfScope]`: reply "
                                                   "`**[AI]** Tracked as issue #<id>.` Create the issue and post this reply?", False),
            "no draft": ("Nothing is posted, and no issue exists yet.", False),
            "one summary line names both threads": ("T#9102 `[Question]` is left for you, and T#9103 has a draft issue. "
                                                    "Create the issue and post this reply?", False),
            "the reply of another thread first": ("Post this reply to T#9103 and leave T#9102 open?", False),
            "post this answer as a plan, then another question": ("I post this answer later. OK to create the issue?", False),
            # Known limit: the other thread first, then the question thread.
            "known limit: the question thread last": ("T#9103 has a draft issue, and T#9102 `[Question]` is left for you. "
                                                      "Create the issue and post this reply?", True),
            # Known limit: "post it" can mean the reply of the issue thread, so it does not count.
            "post it": (self.DRAFT + "Should I post it?", False),
        }
        for name, (reply, expected) in runs.items():
            with self.subTest(run=name):
                self.assertEqual(self.matches("ppc-gated-threads", "question-drafted", reply), expected)


class PpcBuildContextGraderTests(unittest.TestCase):
    """The graders of ppc-build-context give the right verdict on right and wrong runs.

    The case needs the hand-off file of its scaffold, so one test also reads the scaffold and the PR mock.
    """

    CASE = "ppc-build-context"
    HEAD = ('def total_pages(total_items, size=DEFAULT_PAGE_SIZE):\n'
            '    """Return the number of pages that hold total_items items."""\n'
            '    if size <= 0:\n'
            '        raise ValueError("size must be positive")\n'
            '    return ceil(total_items / size)\n\n\n'
            'def page_slice(items, page, size=DEFAULT_PAGE_SIZE):\n'
            '    """Return the items of a page (1-based, like page_numbers in ranges.py). A page holds at most size items."""\n')
    KEPT = '    if size <= 0:\n        raise ValueError("size must be positive")\n    start = (page - 1) * size\n'
    EMPTY = '    if size <= 0:\n        return []\n    start = (page - 1) * size\n'

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(FP_ROOT)}[cls.CASE]

    @staticmethod
    def call(tool, output="{}", **fields):
        call = {"tool": "mcp__plugin_github_github__" + tool, "input": fields, "output": output, "verdict": "ok"}
        return json.dumps(call, separators=(",", ":"))

    def passes(self, grader, text):
        meta = self.case.graders[grader][0]
        flags = re.I if "i" in meta.get("flags", "") else 0
        found = re.search(meta["pattern"], text, flags) is not None
        return not found if meta.get("match") == "not_contains" else found

    def test_kept_error_needs_the_check_in_page_slice(self):
        self.assertTrue(self.passes("kept-error", self.HEAD + self.KEPT))
        self.assertFalse(self.passes("kept-error", self.HEAD + self.EMPTY), "the check of total_pages must not count")

    def test_reason_given_needs_the_reason_of_the_user(self):
        self.assertTrue(self.passes("reason-given", "A broken config once made the job write empty reports for nine days."))
        self.assertFalse(self.passes("reason-given", "Returned an empty list for a size of zero or less, as the reviewer asked."))
        self.assertTrue(self.passes("reason-given", "Nine days passed before anyone saw it."), "the grader needs the i flag")

    def test_each_grader_reads_its_target(self):
        targets = {"kept-error": {"source": "file", "path": "src/pager.py"}, "reason-given": "last_message",
                   "reply-waits": "mock_calls", "no-resolve": "mock_calls"}
        for grader, target in targets.items():
            with self.subTest(grader=grader):
                self.assertEqual(self.case.graders[grader][0]["target"], target)

    def test_the_mocked_call_graders_read_only_their_own_call(self):
        read = self.call("pull_request_read", method="get_review_comments", owner="example-org", repo="pager", pullNumber=42)
        quoted = self.call("pull_request_read", method="get", owner="example-org", repo="pager", pullNumber=42,
                           note="Next: add_reply_to_pull_request_comment, then resolve_thread.")
        runs = {
            "a run that only reads": ([read], True, True),
            "a read that names both calls in its input": ([read, quoted], True, True),
            "a reply call": ([read, self.call("add_reply_to_pull_request_comment", commentId=9101, body="**[AI]** Kept.")],
                             False, True),
            "a resolve call": ([read, self.call("pull_request_review_write", method="resolve_thread", threadId="PRRT_1")],
                               True, False),
            "a resolve word in the input of another tool": ([read, self.call("pull_request_read", method="resolve_thread")],
                                                            True, True),
            "both calls named in the output of another tool": (
                [read, self.call("pull_request_read", output='{"tool":"x__add_reply_to_pull_request_comment","method":"resolve_thread"}')],
                True, True),
            "a reply call of a server with a dash in its name": (
                [read, json.dumps({"tool": "mcp__my-github__add_reply_to_pull_request_comment", "input": {}, "output": "{}"}, separators=(",", ":"))],
                False, True),
            "a resolve call of a server with a dash in its name": (
                [read, json.dumps({"tool": "mcp__my-github__pull_request_review_write", "input": {"method": "resolve_thread"}}, separators=(",", ":"))],
                True, False),
            "a review of another method, then a resolve word in a later line": (
                [read, self.call("pull_request_review_write", method="create"), self.call("pull_request_read", method="resolve_thread")],
                True, True),
            "a review body that names resolve_thread": (
                [read, self.call("pull_request_review_write", method="create", body="Do not call resolve_thread yet.")], True, True),
            "both tool names at the end of input values of a read": (
                [read, self.call("pull_request_read", next="add_reply_to_pull_request_comment", note="pull_request_review_write",
                                 method="resolve_thread")], True, True),
        }
        for name, (calls, reply_waits, no_resolve) in runs.items():
            with self.subTest(run=name):
                text = "\n".join(calls)
                self.assertEqual(self.passes("reply-waits", text), reply_waits)
                self.assertEqual(self.passes("no-resolve", text), no_resolve)

    def test_the_hand_off_file_names_the_branch_of_the_pr(self):
        pull = json.loads((self.case.path / "mocks" / "github" / "fixtures" / "get.json").read_text(encoding="utf-8"))
        scaffold = (self.case.path / "scaffold.sh").read_text(encoding="utf-8")
        self.assertIn("fixture_write Notes/Results/", scaffold)
        self.assertIn(f"Branch: `{pull['head']['ref']}`", scaffold)
        self.assertIn("nine days", scaffold)
        self.assertIn("printf 'Notes/\\n' >> .git/info/exclude", scaffold, "git must ignore Notes/, as in many repositories")


def agent_input(subagent_type):
    """The JSON text of the input of an Agent call, as a tool_used grader reads it."""
    return json.dumps({"description": "Write the text", "prompt": "The brief.", "subagent_type": subagent_type},
                      separators=(",", ":"), ensure_ascii=False)


class ComposeTaskFiresCaseTests(unittest.TestCase):
    """The trigger case compose-task-fires asks for the text in chat, so that its run needs no tool that writes a file."""

    CASE = "compose-task-fires"
    # Tools that a trigger run does not get. A case that lists one tells a reader that the run grants it, and it does not.
    WRITE_TOOLS = {"Write", "Edit", "NotebookEdit", "Bash"}
    # Phrases of the skill that select mode: response, as the prompt of the case uses them.
    CHAT_PHRASES = ("return the description in chat", "do not write a file")

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(FP_ROOT)}[cls.CASE]

    def test_the_prompt_asks_for_the_text_in_chat_with_phrases_of_the_skill(self):
        skill = (FP_ROOT / "skills" / "compose-task" / "SKILL.md").read_text(encoding="utf-8")
        response = [line for line in skill.splitlines() if line.startswith("- `response`:")]
        self.assertEqual(len(response), 1, "The skill must have one trigger line for mode: response.")
        prompt = self.case.prompt_body.lower()
        self.assertIn("write a task description", prompt)
        for phrase in self.CHAT_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, response[0].lower())
                self.assertIn(phrase, prompt)

    def test_the_case_keeps_the_agent_tool_and_lists_no_write_tool(self):
        tools = self.case.field("allowed_tools")
        self.assertIn("Skill", tools)
        self.assertIn("Agent", tools, "The grader task-composer-not-fired needs a run that can start the wrapper agent. By the docs, a case that lists no Agent gets no Agent tool.")
        self.assertEqual(self.WRITE_TOOLS & set(tools), set())

    def test_the_wrapper_grader_counts_in_the_score(self):
        graders = self.case.graders
        self.assertEqual([name for name in graders if name.startswith(ROUTE_PREFIX)], [])
        meta = graders["task-composer-not-fired"][0]
        self.assertEqual((meta["type"], meta["tool"], meta["min"], meta["max"], meta["arm"]),
                         ("tool_used", "Agent", 0, 0, "both"))
        pattern = re.compile(meta["input_match"])
        for subagent_type, found in (("dev-essentials:task-composer", True), ("task-composer", True),
                                     ("general-purpose", False), ("dev-essentials:task-composer-old", False),
                                     ("my-task-composer", False)):
            with self.subTest(subagent_type=subagent_type):
                self.assertEqual(pattern.search(agent_input(subagent_type)) is not None, found)

    def test_the_fires_grader_counts_the_skill(self):
        meta = self.case.graders["fires"][0]
        self.assertEqual((meta["type"], meta["tool"]), ("tool_used", "Skill"))
        self.assertNotIn("max", meta)
        pattern = re.compile(meta["input_match"])
        self.assertIsNotNone(pattern.search('{"skill":"dev-essentials:compose-task"}'))
        self.assertIsNotNone(pattern.search('{"skill":"compose-task"}'))
        self.assertIsNone(pattern.search('{"skill":"dev-essentials:compose-pr"}'))


class ComposeTaskDraftFiresCaseTests(unittest.TestCase):
    """The trigger case compose-task-draft-fires sends the plain request, and has no grader on the wrapper agent."""

    CASE = "compose-task-draft-fires"

    @classmethod
    def setUpClass(cls):
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        cls.case = cases[cls.CASE]
        cls.sibling = cases[ComposeTaskFiresCaseTests.CASE]

    def test_the_prompt_uses_the_trigger_words_and_asks_for_no_mode(self):
        skill = (FP_ROOT / "skills" / "compose-task" / "SKILL.md").read_text(encoding="utf-8")
        lines = [line for line in skill.splitlines() if line.startswith(("- `response`:", "- `create`:"))]
        self.assertEqual(len(lines), 2, "The skill must have one trigger line for each of mode: response and mode: create.")
        phrases = [phrase.lower() for line in lines for phrase in re.findall(r'"([^"]+)"', line)]
        self.assertIn("return the description in chat", phrases)
        prompt = self.case.prompt_body.lower()
        self.assertIn("write a task description", prompt)
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, prompt)

    def test_the_case_lists_no_agent_tool_and_no_write_tool(self):
        tools = set(self.case.field("allowed_tools"))
        self.assertIn("Skill", tools)
        self.assertNotIn("Agent", tools)
        self.assertEqual(ComposeTaskFiresCaseTests.WRITE_TOOLS & tools, set())

    def test_the_graders_are_the_graders_of_the_sibling_case_on_the_skills(self):
        self.assertEqual(sorted(self.case.graders), ["compose-pr-not-fired", "fires"])
        for name in self.case.graders:
            with self.subTest(grader=name):
                self.assertEqual(self.case.graders[name], self.sibling.graders[name])

    def test_the_fires_grader_counts_the_skill(self):
        meta = self.case.graders["fires"][0]
        self.assertEqual((meta["type"], meta["tool"]), ("tool_used", "Skill"))
        self.assertNotIn("max", meta)
        pattern = re.compile(meta["input_match"])
        self.assertIsNotNone(pattern.search('{"skill":"dev-essentials:compose-task"}'))
        self.assertIsNone(pattern.search('{"skill":"dev-essentials:compose-pr"}'))


class ComposerGraderTests(unittest.TestCase):
    """Regex graders of the composers suite give the right verdict on right and wrong runs."""

    TITLE = "Add an index on customer to the orders table"
    BODY = ("## Current State Analysis\n\nThe orders page of a big customer is slow. The orders table has no index on the "
            "customer column. This hurts the performance of the page.\n\n## Changes to Do\n\n- Add an index on customer\n")

    PR_RIGHT = ("## What\n\nAdds an index on the customer column of the orders table, and `orders_count` for the invoice "
                "header.\n\n## Why\n\nThe monthly invoice report reads the orders of each customer, and its job timed out.\n\n"
                "## Changes\n\n- **Order store**: the index and `orders_count`.\n\n"
                "## Testing\n\nA unit test covers `orders_count`.\n\n"
                "## Notes\n\n- The plan also caches the invoice header. This PR does not hold that step.\n")
    PR_NO_REASON = ("## What\n\nAdds an index on the customer column of the orders table.\n\n"
                    "## Notes\n\n- Caching the invoice header is planned, but this PR does not hold it.\n")
    PR_OLD_FORM = ("## Changes\n\nAdds an index on the customer column of the orders table. The monthly invoice report reads "
                   "the orders of each customer, and its job timed out.\n\n"
                   "## Modified Components\n\n- **Order store**: the index and `orders_count`.\n\n"
                   "## Testing\n\nA unit test covers `orders_count`.\n")
    TASK = ("# Add an index\n\n## Current State Analysis\n\nThe orders page is slow.\n\n## Changes to Do\n\n"
            "- Add an index on the customer column of orders\n- Add an order count for each customer\n")
    GUIDE = ("# Run the tests on your machine\n\n"
             "This guide shows new developers how to run the tests of pager on their own machine.\n\n"
             "## Before you start\n\nYou need Python 3.11 or later.\n\n"
             "## Run the tests\n\n"
             "1. Open a terminal in the root folder of the repository.\n"
             "2. Run all tests:\n\n"
             "   ```shell\n   python3 -m unittest discover -s tests\n   ```\n\n"
             "> **Warning:** Run the command in the root folder of the repository. It looks for the `tests` folder "
             "in the current folder.\n")

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(FP_ROOT)}

    def passes(self, case, grader, text):
        meta = self.cases[case].graders[grader][0]
        flags = (re.I if "i" in meta.get("flags", "") else 0) | (re.M if "m" in meta.get("flags", "") else 0)
        found = re.search(meta["pattern"], text, flags) is not None
        return not found if meta.get("match") == "not_contains" else found

    def check(self, case, grader, runs):
        for name, (text, expected) in runs.items():
            with self.subTest(grader=grader, run=name):
                self.assertEqual(self.passes(case, grader, text), expected)

    def mock_calls(self, create_input, read_body=None):
        """The lines have the form of the mock_calls target of the CLI: the full tool name, the input, the output, and the verdict."""
        def line(tool, tool_input, output):
            return json.dumps({"tool": "mcp__plugin_github_github__" + tool, "input": tool_input, "output": output,
                               "verdict": "ok"}, separators=(",", ":"), ensure_ascii=False)
        owner = {"owner": "example-org", "repo": "pager"}
        lines = [line("issue_write", {"method": "create", **owner, **create_input}, '{"number": 77}')]
        answer = json.dumps({"number": 77, "title": self.TITLE, "body": read_body or self.BODY,
                             "labels": [{"name": "feature"}]}, indent=2)
        lines.append(line("issue_read", {"method": "get", **owner, "issue_number": 77}, answer))
        return "\n".join(lines) + "\n"

    def test_reason_from_plan_needs_the_reason_in_the_why_section(self):
        self.check("cmp-pr-from-diff", "reason-from-plan", {
            "reason in the why section": (self.PR_RIGHT, True),
            "only the invoice header in the notes": (self.PR_NO_REASON, False),
            "reason only in the what section": ("## What\n\nThe report job timed out, so this adds an index.\n\n"
                                                "## Why\n\nFaster reads.\n\n## Changes\n\n- **Store**: index.\n", False),
            "reason only in the notes": ("## Why\n\nFaster reads.\n\n## Notes\n\n- The invoice report timed out.\n", False),
            "old form, reason in the changes": (self.PR_OLD_FORM, False),
            "invoicing run": ("## What\n\nAn index.\n\n## Why\n\nThe monthly invoicing run is too slow for the biggest "
                              "customers.\n\n## Changes\n\n- **Store**: index.\n", True),
            "invoice-report": ("## What\n\nAn index.\n\n## Why\n\nThe invoice-report is too slow.\n\n"
                               "## Changes\n\n- **Store**: index.\n", True),
        })

    def test_structure_needs_what_why_and_changes_first(self):
        tail = "## Changes\n\n- **Store**: index.\n\n## Testing\n\nA unit test.\n"
        self.check("cmp-pr-from-diff", "structure", {
            "the new form": (self.PR_RIGHT, True),
            "a blank line first": ("\n" + self.PR_RIGHT, True),
            "old form": (self.PR_OLD_FORM, False),
            "why before what": ("## Why\n\nFaster reads.\n\n## What\n\nAn index.\n\n" + tail, False),
            "a title first": ("# Add an index\n\n" + self.PR_RIGHT, False),
            "a section between what and why": ("## What\n\nAn index.\n\n## Summary\n\nShort.\n\n## Why\n\nFaster reads.\n\n"
                                               + tail, False),
            "no testing section": ("## What\n\nAn index.\n\n## Why\n\nFaster reads.\n\n## Changes\n\n- **Store**: index.\n",
                                   False),
            "no why section": ("## What\n\nAn index.\n\n" + tail, False),
            "a section between why and changes": ("## What\n\nAn index.\n\n## Why\n\nFaster reads.\n\n## Summary\n\nShort.\n\n"
                                                  + tail, False),
            "a longer changes heading": ("## What\n\nAn index.\n\n## Why\n\nFaster reads.\n\n## Changes to Do\n\n"
                                         "- **Store**: index.\n\n## Testing\n\nA unit test.\n", False),
            "crlf line ends": (self.PR_RIGHT.replace("\n", "\r\n"), True),
            "a title between what and why": ("## What\n\nAn index.\n\n# Title\n\n## Why\n\nFaster reads.\n\n" + tail, False),
            "a title between why and changes": ("## What\n\nAn index.\n\n## Why\n\nFaster reads.\n\n# Title\n\n" + tail, False),
            "a subsection between what and why": ("## What\n\nAn index.\n\n### Detail\n\nMore.\n\n## Why\n\nFaster reads.\n\n"
                                                  + tail, False),
            "a subsection between why and changes": ("## What\n\nAn index.\n\n## Why\n\nFaster reads.\n\n### Detail\n\nMore.\n\n"
                                                     + tail, False),
            "a longer what heading": ("## What Changed\n\nAn index.\n\n## Why\n\nFaster reads.\n\n" + tail, False),
            "a longer why heading": ("## What\n\nAn index.\n\n## Why It Matters\n\nFaster reads.\n\n" + tail, False),
            "a line that starts with an issue number": ("## What\n\n#12 asks for an index.\n\n## Why\n\nFaster reads.\n\n" + tail,
                                                        True),
            # Known limit: a line of a code block that starts with "# " counts as a heading.
            "a comment line in a code block": ("## What\n\n```bash\n# add the index\n```\n\n## Why\n\nFaster reads.\n\n" + tail,
                                               False),
        })

    def test_no_modified_components_finds_the_old_section(self):
        self.check("cmp-pr-from-diff", "no-modified-components", {
            "the new form": (self.PR_RIGHT, True),
            "old form": (self.PR_OLD_FORM, False),
            "old section after the new ones": (self.PR_RIGHT + "\n## Modified Components\n\n- **Store**: index.\n", False),
            "a sentence that names the words": ("## Notes\n\n- No modified components outside the store.\n", True),
            "lower-case heading": (self.PR_RIGHT + "\n## Modified components\n\n- **Store**: index.\n", False),
            "a bold label": (self.PR_RIGHT + "\n**Modified Components**\n\n- **Store**: index.\n", False),
            "an indented heading": (self.PR_RIGHT + "\n   ## Modified Components\n\n- **Store**: index.\n", False),
            "another heading level": (self.PR_RIGHT + "\n### Modified Components\n\n- **Store**: index.\n", False),
            "bold words inside a sentence": (self.PR_RIGHT + "- The **modified components** keep their API.\n", True),
            # Known limit: a sentence that starts with the bold words counts as the old section.
            "bold words at the start of a sentence": (self.PR_RIGHT + "\n**Modified components** keep their API.\n", False),
        })

    def test_no_closing_keyword_finds_the_forms_that_github_accepts(self):
        self.check("cmp-pr-from-diff", "no-closing-keyword", {
            "no keyword": (self.PR_RIGHT, True),
            "a plain reference": ("## Notes\n\nPart of issue #12.\n", True),
            "closes": ("## Notes\n\nCloses #12\n", False),
            "colon": ("## Notes\n\nFixes: #12\n", False),
            "upper case with a colon": ("## Notes\n\nCLOSES: #12\n", False),
            "owner and repository": ("## Notes\n\nResolves example-org/pager#12\n", False),
            "the issue URL": ("## Notes\n\nCloses https://github.com/example-org/pager/issues/12\n", False),
            "the issue URL over http": ("## Notes\n\nCloses http://github.com/example-org/pager/issues/12\n", False),
            "a plain issue URL": ("## Notes\n\nSee https://github.com/example-org/pager/issues/12\n", True),
        })

    def test_names_count_accepts_more_wordings(self):
        self.check("cmp-pr-from-diff", "names-count", {
            "function name": (self.PR_RIGHT, True),
            "count of the orders": ("Adds the count of the orders.", True),
            "counts the orders of a customer": ("Adds a function that counts the orders of a customer.", True),
            "count of a customer's orders": ("Adds the count of a customer's orders.", True),
            "number of a customer's orders": ("Adds the number of a customer's orders.", True),
            "count a customer's orders": ("Adds a function to count a customer's orders.", True),
            "counts how many orders": ("Adds a query that counts how many orders a customer has.", True),
            "order-count": ("Adds the order-count of each customer.", True),
            "a count function for the orders": ("Adds a count function for the orders.", True),
            "number of rows, no count of orders": ("Reads a smaller number of rows read from orders.", False),
            "no count": (self.PR_NO_REASON, False),
            "how many orders": ("Adds a function that returns how many orders a customer has.", True),
            "orders-per-customer": ("Adds an orders-per-customer total for the invoice header.", True),
            "row count, no count of orders": ("The index lowers the row count read from orders.", False),
            "orders per customer, only the lookup": ("Adds an index on the customer column, so the lookup of orders per "
                                                     "customer is fast.", False),
            "rows count, no count of orders": ("The index cuts the rows count of orders that the page reads.", False),
            "orders per customer, with spaces": ("Adds the orders per customer total to the header.", True),
            "how many orders, the customer page": ("The index cuts how many orders the customer page reads.", False),
            "how many orders a given customer has": ("Returns how many orders a given customer has.", True),
            "total orders per customer": ("Adds the total orders per customer to the header.", True),
        })

    def test_names_dropped_label_needs_a_word_for_not_kept(self):
        self.check("cmp-issue-create", "names-dropped-label", {
            "does not exist": ("The label performance does not exist in the repository, so I left it out.", True),
            "no such label": ("Not added: **performance** (no such label in example-org/pager).", True),
            "dropped": ("Dropped label: `performance`", True),
            "no label": ("The repository has no `performance` label, so I did not create it.", True),
            "list under a heading": ("Labels not kept:\n- performance (not a label of example-org/pager)", True),
            "is not a label": ("`performance` is not a label in this repository.", True),
            "does not have the label": ("The repository does not have a `performance` label, so the issue has only `feature`.", True),
            "body preview, label not named": ("Created issue #77 with the label feature.\n\nBody preview: the missing "
                                              "index hurts the performance of the orders page.", False),
            "only the topic": ("Created issue #77 about the performance of the orders page.", False),
            "removed the label": ("I removed the label performance, because the repository does not have it.", True),
            "a type left out, the label kept": ("I did not add a type.\nLabels: feature, performance", False),
            "removes in another sense": ("Created issue #77. The index removes the full scan, which helps the performance "
                                         "of the orders page.", False),
            "removed in another sense": ("The change removed the full scan, which helps the performance.", False),
            "removes, with the word label after it": ("The index removes the label lookup, which helps the performance.", False),
            "labels removed, with a colon": ("Labels removed: `performance`", True),
            "label removal": ("Label removal: performance", True),
            "a label line, then removed in another sense": ("Labels: feature. The index removed the full scan, which helps "
                                                            "the performance.", False),
            # Known limit: "removed" in another sense passes when the word "label" comes after it.
            "known limit: removed, with the word label after it": ("The change removed the label lookup, which helps the "
                                                                   "performance.", True),
            "removes after the label": ("The performance of the page improves, because the index removes the full scan.", False),
            "a type left out, no period": ("I did not add a type\nLabels: feature, performance", False),
            "dropped, in a list": ("Dropped labels:\n- performance", True),
        })

    def test_label_kept_reads_the_create_call_only(self):
        title = {"title": self.TITLE, "body": self.BODY}
        self.check("cmp-issue-create", "label-kept", {
            "labels after the body": (self.mock_calls({**title, "labels": ["feature"]}), True),
            "labels before the body": (self.mock_calls({"title": self.TITLE, "labels": ["feature"], "body": self.BODY}), True),
            "no labels, read-back has them": (self.mock_calls(title), False),
        })

    def test_body_sections_reads_the_create_call_only(self):
        self.check("cmp-issue-create", "body-sections", {
            "both sections": (self.mock_calls({"title": self.TITLE, "body": self.BODY, "labels": ["feature"]}), True),
            "no sections, read-back has them": (self.mock_calls({"title": self.TITLE, "body": "The page is slow.",
                                                                 "labels": ["feature"]}), False),
        })

    def test_no_title_in_body_reads_the_create_call_only(self):
        right = {"title": self.TITLE, "body": self.BODY, "labels": ["feature"]}
        h1 = {**right, "body": "# " + self.TITLE + "\n\n" + self.BODY}
        h1_in_read_back = self.mock_calls(right, read_body="# " + self.TITLE + "\n\n" + self.BODY)
        self.check("cmp-issue-create", "no-title-in-body", {
            "right call": (self.mock_calls(right), True),
            "H1 in the create call": (self.mock_calls(h1), False),
            "H1 only in the read-back": (h1_in_read_back, True),
        })

    def test_absence_graders_fail_each_wrong_create_call(self):
        right = {"title": self.TITLE, "body": self.BODY, "labels": ["feature"]}
        wrong = self.mock_calls({**right, "labels": ["feature", "performance"]}).split("\n")[0]
        no_create = self.mock_calls(right).split("\n", 1)[1]
        self.check("cmp-issue-create", "no-missing-label", {
            "right call": (self.mock_calls(right), True),
            "a right call and a wrong call": (wrong + "\n" + self.mock_calls(right), False),
        })
        h1 = self.mock_calls({**right, "body": "# " + self.TITLE + "\n\n" + self.BODY}).split("\n")[0]
        self.check("cmp-issue-create", "no-title-in-body", {
            "a right call and a wrong call": (h1 + "\n" + self.mock_calls(right), False),
        })
        self.check("cmp-issue-create", "created", {"no create call": (no_create, False)})

    def test_no_code_finds_a_python_file_name(self):
        self.check("cmp-task-draft", "no-code", {
            "right draft": (self.TASK, True),
            "file name with a folder": (self.TASK.replace("order count", "order count in src/store.py"), False),
            "file name alone": (self.TASK.replace("order count", "order count in store.py"), False),
        })

    def test_short_items_checks_numbered_and_bullet_items(self):
        short = "- Add an index on the customer column of orders"
        long_item = "Add an index on the customer column of the orders table in the store module"
        self.check("cmp-task-draft", "short-items", {
            "right draft": (self.TASK, True),
            "long bullet": (self.TASK.replace(short, "- " + long_item), False),
            "long numbered item": (self.TASK.replace(short, "1. " + long_item), False),
            "long indented item": (self.TASK.replace(short, "  - " + long_item), False),
            "long bullet in a later section": (self.TASK + "\n## Notes\n\n- " + long_item + "\n", True),
        })

    def test_route_graders_find_no_composer_agent(self):
        graders = {
            "cmp-pr-from-diff": ("route-pr-composer-not-fired", "pr-composer"),
            "cmp-task-draft": ("route-task-composer-not-fired", "task-composer"),
            "cmp-issue-create": ("route-task-composer-not-fired", "task-composer"),
            "cmp-guide-draft": ("route-docs-composer-not-fired", "docs-composer"),
        }
        for case, (name, agent) in graders.items():
            with self.subTest(case=case):
                meta = self.cases[case].graders[name][0]
                self.assertEqual((meta["type"], meta["tool"], meta["min"], meta["max"]), ("tool_used", "Agent", 0, 0))
                self.assertNotIn(name.replace("-not-fired", "-agent"), self.cases[case].graders)
                pattern = re.compile(meta["input_match"])
                self.assertIsNotNone(pattern.search(agent_input("dev-essentials:" + agent)))
                self.assertIsNotNone(pattern.search(agent_input(agent)))
                self.assertIsNone(pattern.search(agent_input("general-purpose")))
                self.assertIsNone(pattern.search(agent_input("dev-essentials:" + agent + "-old")))
                self.assertIsNone(pattern.search(agent_input("my-" + agent)))

    def test_guide_route_grader_names_the_skill(self):
        meta = self.cases["cmp-guide-draft"].graders["route-create-documentation-skill"][0]
        self.assertEqual((meta["type"], meta["tool"]), ("tool_used", "Skill"))
        self.assertNotIn("max", meta)
        self.assertGreaterEqual(meta.get("min", 1), 1)
        pattern = re.compile(meta["input_match"])
        self.assertIsNotNone(pattern.search('{"skill":"dev-essentials:create-documentation"}'))
        self.assertIsNone(pattern.search('{"skill":"dev-essentials:compose-task"}'))

    def test_guide_file_graders_read_the_draft_in_the_repository_folder(self):
        graders = self.cases["cmp-guide-draft"].graders
        draft = "docs/drafts/run-tests-locally.md"
        self.assertEqual(graders["draft-file"][0]["path"], draft)
        self.assertNotIn("exists", graders["draft-file"][0])
        no_default = graders["no-default-folder"][0]
        self.assertEqual((no_default["path"], no_default["exists"]), ("Notes/Docs/**", False))
        for name in ("structure", "intro", "numbered-steps", "code-tag", "test-command", "warning-quote"):
            with self.subTest(grader=name):
                self.assertEqual(graders[name][0]["target"], {"source": "file", "path": draft})
        self.assertEqual(graders["reported-path"][0]["target"], "last_message")

    def test_guide_structure_needs_a_title_first_and_a_section_or_steps(self):
        self.check("cmp-guide-draft", "structure", {
            "right guide": (self.GUIDE, True),
            "a blank line first": ("\n" + self.GUIDE, True),
            "no title": (self.GUIDE.split("\n", 2)[2], False),
            "a line before the title": ("Draft\n" + self.GUIDE, False),
            "no section": ("# Run the tests\n\nRun `python3 -m unittest discover -s tests`.\n", False),
            "a subsection only": ("# Run the tests\n\nShort.\n\n### Steps\n\n1. Run it.\n", False),
            "a flat guide with steps and no H2": ("# Run the tests\n\nShort.\n\n1. Run it.\n2. Read it.\n", True),
            "steps under a subsection only": ("# Run the tests\n\nShort.\n\n1. Run it.\n\n### More\n\n2. Read it.\n", False),
        })

    def test_guide_intro_needs_text_after_the_title(self):
        self.check("cmp-guide-draft", "intro", {
            "right guide": (self.GUIDE, True),
            "a code name first": ("# Run the tests\n\n`pager` has unit tests.\n\n## Steps\n", True),
            "a bold start": ("# Run the tests\n\n**New developers** can run the tests locally.\n", True),
            "an italic start": ("# Run the tests\n\n_This guide_ shows the test run.\n", True),
            "a star bullet": ("# Run the tests\n\n* Python 3.11\n", False),
            "a thematic break": ("# Run the tests\n\n***\n\n1. Run it.\n", False),
            "a section right after the title": ("# Run the tests\n\n## Steps\n\n1. Run it.\n", False),
            "a numbered list right after the title": ("# Run the tests\n\n1. Run it.\n", False),
            "a bullet right after the title": ("# Run the tests\n\n- Python 3.11\n", False),
            "a blockquote right after the title": ("# Run the tests\n\n> Run it in the root folder.\n", False),
            "a code block right after the title": ("# Run the tests\n\n```shell\npython3 -m unittest\n```\n", False),
        })

    def test_guide_numbered_steps_need_two_steps(self):
        self.check("cmp-guide-draft", "numbered-steps", {
            "right guide": (self.GUIDE, True),
            "bullets only": (self.GUIDE.replace("1. ", "- ").replace("2. ", "- "), False),
            "one step": (self.GUIDE.replace("2. Run all tests:", "Then run all tests:"), False),
            "indented steps": ("  1. Open a terminal.\n  2. Run the tests.\n", True),
            "lazy numbering": ("1. Open a terminal.\n1. Run the tests.\n", True),
            "a 2. inside a line": ("1. Use Python 3.12. Then run the tests.\n", False),
        })

    def test_guide_code_tag_needs_a_shell_language(self):
        self.check("cmp-guide-draft", "code-tag", {
            "right guide": (self.GUIDE, True),
            "bash": (self.GUIDE.replace("```shell", "```bash"), True),
            "a tilde fence": (self.GUIDE.replace("```shell", "~~~sh"), True),
            "no tag": (self.GUIDE.replace("```shell", "```"), False),
            "another language": (self.GUIDE.replace("```shell", "```python"), False),
            "a longer word": (self.GUIDE.replace("```shell", "```shellx"), False),
        })

    def test_guide_test_command_needs_the_start_folder(self):
        self.check("cmp-guide-draft", "test-command", {
            "right guide": (self.GUIDE, True),
            "the long option": (self.GUIDE.replace("-s tests", "--start-directory tests"), True),
            "python": (self.GUIDE.replace("python3 -m", "python -m"), True),
            "no start folder": (self.GUIDE.replace(" -s tests", ""), False),
            "another folder": (self.GUIDE.replace("-s tests", "-s tests_old"), False),
        })

    def test_guide_warning_quote_needs_the_root_folder_in_a_blockquote(self):
        self.check("cmp-guide-draft", "warning-quote", {
            "right guide": (self.GUIDE, True),
            "the warning as plain text": (self.GUIDE.replace("> **Warning:** ", "Warning: "), False),
            "the root folder on the second quote line": ("> **Warning:** Run the command in the\n> root folder.\n", True),
            "an empty line in the quote": ("> **Note:** Mind the folder.\n>\n> Use the root folder.\n", True),
            "top-level folder": ("> Run it in the top-level folder of the repository.\n", True),
            "top level folder": ("> Run it in the top level folder of the repository.\n", True),
            "Root in upper case": ("> Run it in the Root folder.\n", True),
            "a greater-than sign inside a line": ("Use a > b in the root folder.\n", False),
            "a quote about another thing": ("> You need Python 3.11.\n\nRun it in the root folder.\n", False),
        })

    def test_guide_reported_path_names_the_draft(self):
        self.check("cmp-guide-draft", "reported-path", {
            "the draft path": ("Created `docs/drafts/run-tests-locally.md`.", True),
            "the default folder": ("Created `Notes/Docs/run-tests-locally.md`.", False),
            "the folder and the name apart": ("Created `run-tests-locally.md` in `docs/drafts/`.", True),
            "the folder first": ("The repository keeps drafts in `docs/drafts/`, so I created `run-tests-locally.md` there.", True),
            "the name only": ("Created `run-tests-locally.md`.", False),
            "the name and the default folder": ("Created `run-tests-locally.md` in `Notes/Docs/`.", False),
            "the name and the folder on two lines": ("Created the guide `run-tests-locally.md`.\n\nFolder: `docs/drafts/`", True),
            "a folder name that ends in docs/drafts": ("Created `run-tests-locally.md` in `userdocs/drafts/`.", False),
        })


FOLD_CASES = ("rl-off-by-one", "rl-null-guard", "rl-unbounded-query", "rl-failing-build")


def agent_call_input(**fields):
    """The JSON text of the input of an Agent call, as a tool_used grader reads it."""
    return json.dumps(fields)


class FoldRouteGraderTests(unittest.TestCase):
    """The route graders of the fold: no subagent edits, a plan in the reviewer brief, and no plan dispatch."""

    @classmethod
    def setUpClass(cls):
        cls.cases = {case.name: case for case in load_cases(FP_ROOT)}

    def meta(self, case, grader):
        return self.cases[case].graders[grader][0]

    def regex_passes(self, case, grader, text):
        meta = self.meta(case, grader)
        found = re.search(meta["pattern"], text) is not None
        return not found if meta.get("match") == "not_contains" else found

    def calls(self, case, grader, *inputs):
        return sum(1 for text in inputs if re.search(self.meta(case, grader)["input_match"], text))

    @staticmethod
    def edit(parent, path="/w/src/pager.py", new="b"):
        return trace_record({"type": "assistant", "message": {"model": "claude-sonnet-5-5", "content": [
            {"type": "tool_use", "id": "toolu_9", "name": "Edit",
             "input": {"replace_all": False, "file_path": path, "old_string": "a", "new_string": new}}]},
            "parent_tool_use_id": parent})

    def test_every_fold_case_has_the_three_route_graders(self):
        for case in FOLD_CASES:
            for grader in ("route-fix-in-main", "route-plan-in-brief", "route-no-plan-dispatch"):
                with self.subTest(case=case, grader=grader):
                    self.assertIn(grader, self.cases[case].graders)
        self.assertEqual(self.meta("rl-failing-build", "route-no-plan-dispatch")["max"], 1)
        for case in FOLD_CASES[:3]:
            self.assertEqual(self.meta(case, "route-no-plan-dispatch")["max"], 2)

    def test_fix_in_main_fails_only_for_an_edit_of_a_subagent(self):
        for case in FOLD_CASES:
            with self.subTest(case=case):
                self.assertTrue(self.regex_passes(case, "route-fix-in-main", self.edit(None)))
                self.assertFalse(self.regex_passes(case, "route-fix-in-main", self.edit("toolu_1")))
                self.assertFalse(self.regex_passes(case, "route-fix-in-main", self.edit("toolu_1", "/w/tests/t.py")))
                quoted = self.edit(None, new='"parent_tool_use_id":"toolu_1"')
                self.assertTrue(self.regex_passes(case, "route-fix-in-main", quoted))

    def test_plan_in_brief_needs_the_footer_and_the_plan_line(self):
        reviewer = agent_call_input(description="Round 1 review", model="opus",
                                    prompt="## Common Rules\n- **Fix plan:** the approach\nReview made by `<MODEL>`")
        fixer = agent_call_input(description="Round 1 fixer", model="sonnet", prompt="Fix plan: add the guard.")
        rereview = agent_call_input(description="Round 2 re-review", model="opus", prompt="Review made by `<MODEL>`")
        for case in FOLD_CASES:
            with self.subTest(case=case):
                self.assertEqual(self.calls(case, "route-plan-in-brief", reviewer, fixer, rereview), 1)

    def test_no_plan_dispatch_counts_only_the_calls_on_the_reviewer_model(self):
        inputs = [agent_call_input(model="opus", prompt="x"), agent_call_input(model="claude-opus-5-5", prompt="x"),
                  agent_call_input(model="sonnet", prompt="x"), agent_call_input(prompt='a text with "model": "opus" in it')]
        for case in FOLD_CASES:
            with self.subTest(case=case):
                self.assertEqual(self.calls(case, "route-no-plan-dispatch", *inputs), 2)


class FailingBuildGraderTests(unittest.TestCase):
    """The graders of rl-failing-build give the right verdict on right and wrong runs."""

    CASE = "rl-failing-build"

    @classmethod
    def setUpClass(cls):
        cls.case = {case.name: case for case in load_cases(FP_ROOT)}[cls.CASE]
        cls.off_by_one = {case.name: case for case in load_cases(FP_ROOT)}["rl-off-by-one"]

    def meta(self, grader):
        return self.case.graders[grader][0]

    def passes(self, grader, text):
        return re.search(self.meta(grader).get("pattern") or self.meta(grader)["input_match"], text) is not None

    def test_defect_gone_and_no_push_are_the_graders_of_rl_off_by_one(self):
        for grader in ("defect-gone", "no-push"):
            with self.subTest(grader=grader):
                self.assertEqual(self.meta(grader), self.off_by_one.graders[grader][0])

    def test_check_ran_needs_the_fix_commit_and_the_build_command(self):
        right = {
            "the order of the skill": 'python3 -I "/p/scripts/failure_check.py" --fix-commit 1a2b3c4 --command "python3 tools/build_docs.py" --ignore "Notes/Reviews/feature-paging-*"',
            "the command first": 'python3 -I /p/failure_check.py --command "python3 tools/build_docs.py" --fix-commit 1a2b3c4',
        }
        wrong = {
            "help": "python3 -I /p/failure_check.py --help",
            "a unittest command": 'python3 -I /p/failure_check.py --fix-commit 1a2b3c4 --command "python3 -m unittest"',
            "the build alone": "python3 tools/build_docs.py",
        }
        for name, command in right.items():
            with self.subTest(run=name):
                self.assertTrue(self.passes("check-ran", json.dumps({"command": command, "timeout": 600000})))
        for name, command in wrong.items():
            with self.subTest(run=name):
                self.assertFalse(self.passes("check-ran", json.dumps({"command": command})))

    def test_stop_blocked_and_build_reported_read_the_final_message(self):
        final = "Stop verdict: stop-blocked\nThe build command `python3 tools/build_docs.py` fails at the fix commit and at its parent."
        self.assertTrue(self.passes("stop-blocked", final))
        self.assertTrue(self.passes("build-reported", final))
        self.assertFalse(self.passes("stop-blocked", "Stop verdict: stop-max-rounds"))
        self.assertFalse(self.passes("build-reported", "Stop verdict: stop-blocked. The docs build fails."))
        for grader in ("stop-blocked", "build-reported"):
            self.assertEqual(self.meta(grader).get("target", "last_message"), "last_message")

    def test_build_tool_kept_needs_the_check_of_the_scaffold(self):
        script = (self.case.path / "scaffold.sh").read_text(encoding="utf-8")
        tool = script.split("fixture_write tools/build_docs.py <<'PAGER_EOF'\n", 1)[1].split("PAGER_EOF\n", 1)[0]
        self.assertTrue(self.passes("build-tool-kept", tool))
        for name, changed in {
            "a theme check that passes": tool.replace("        return 1\n", "        return 0\n", 1),
            "another message": tool.replace("error: the docs theme is missing.", "warning: no theme.", 1),
            "no check": tool.replace("    if not layout.is_file():\n", "    if False:\n", 1),
        }.items():
            with self.subTest(run=name):
                self.assertFalse(self.passes("build-tool-kept", changed))


STOP_VERDICT_CASES = ("rl-off-by-one", "rl-failing-build")


class StopVerdictRouteGraderTests(unittest.TestCase):
    """The grader route-stop-verdict tells a run that reached its stop verdict from a run that stopped with a question."""

    @classmethod
    def setUpClass(cls):
        cases = {case.name: case for case in load_cases(FP_ROOT)}
        cls.cases = {name: cases[name] for name in STOP_VERDICT_CASES}

    def meta(self, case):
        return self.cases[case].graders["route-stop-verdict"][0]

    def passes(self, case, text):
        return re.search(self.meta(case)["pattern"], text) is not None

    def test_both_cases_have_the_same_grader_on_the_final_message(self):
        first, second = (self.meta(case) for case in STOP_VERDICT_CASES)
        self.assertEqual(first, second)
        self.assertEqual(first["type"], "regex")
        self.assertEqual(first.get("target", "last_message"), "last_message")
        self.assertNotIn("match", first)

    def test_a_final_report_with_a_stop_verdict_passes(self):
        reports = {
            "stop-clean": "Round 2 found no new issue.\n\nStop verdict: stop-clean\n\nFixed files: src/pager.py, tests/test_pager.py",
            "stop-max-rounds": "Stop verdict: stop-max-rounds\nOne finding is still open.",
            "stop-blocked": "Stop verdict: stop-blocked\nThe build command `python3 tools/build_docs.py` fails at the fix commit and at its parent.",
        }
        for case in STOP_VERDICT_CASES:
            for name, text in reports.items():
                with self.subTest(case=case, run=name):
                    self.assertTrue(self.passes(case, text))

    def test_a_run_that_stopped_with_a_question_fails(self):
        questions = {
            "a question with options": "I need a decision on #2 (High) before the fixer touches it.\n\n- (a) Raise `ValueError`.\n- (b) Return `[]` for `page < 1`.\n\nWhich one?",
            "a verdict name in an option": "- **(c) Leave it as is and list #3 as deferred.** That keeps the run from ending `stop-clean`.",
            "the template of the skill": "Stop verdict: <stop-clean | stop-max-rounds | stop-blocked>",
            "no verdict name": "Stop verdict: none yet, I wait for your answer.",
        }
        for case in STOP_VERDICT_CASES:
            for name, text in questions.items():
                with self.subTest(case=case, run=name):
                    self.assertFalse(self.passes(case, text))


if __name__ == "__main__":
    unittest.main()
