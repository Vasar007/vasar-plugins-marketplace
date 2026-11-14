"""Static checks of the `claude plugin eval` cases of every plugin. The tests call no model.

A case folder is a folder under <plugin>/evals/ that holds prompt.md or case.yaml.
The checks follow the eval suite reference of the Claude Code docs: the keys of
prompt.md and case.yaml, the grader types and their options, and the plugins
and scaffold fields. A small parser reads the subset of YAML that the cases use:
block mappings, block lists of scalars, quoted and plain scalars, and inline
lists and maps. Block scalars (| and >) and anchors are not supported.
"""
import json
import re
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from support import REPO, tool_missing
from testkit import ScratchCase, run

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
IGNORED_REGEX_FLAGS = set("guyd")

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
    """Each tracked .sh file under an eval folder: LF only, executable in the index, and valid Bash syntax."""
    problems = []
    for path, mode in sorted(modes.items()):
        if not (path.endswith(".sh") and f"/{EVALS}/" in path and (Path(repo) / path).is_file()):
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
    """The record that ends a stage subagent: a task notification with the final reply as its summary."""
    return trace_record({"type": "system", "subtype": "task_notification", "task_id": "a1",
                         "tool_use_id": "toolu_1", "status": "completed", "summary": text})


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


if __name__ == "__main__":
    unittest.main()
