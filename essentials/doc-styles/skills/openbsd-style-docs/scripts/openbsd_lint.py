#!/usr/bin/env python3
"""Check a Markdown document against the rules of the openbsd-style-docs skill that a script can test.

Rules:
  heading-case      if one ## heading is an uppercase canonical name, every ## heading is uppercase
  section-order     canonical sections in the mdoc(7) order; custom sections after DESCRIPTION
  empty-section     a ## section with no text
  name-line         "<name> - <description>" under the title: lowercase, no article, no final period
  sort-order        option, ENVIRONMENT, FILES and ERRORS tag lists are sorted
  default-sentence  a default in a tag item is its own sentence
  you               "you" and its forms
  word-list         the marketing and filler words of the skill, "!" and bold

Usage:
  python3 openbsd_lint.py FILE...   print each hit as FILE:LINE: RULE: MESSAGE
  python3 openbsd_lint.py --hook    read a PostToolUse event on stdin (hook of the doc-styles plugin)

Exit codes: 0 = no hit, 1 = hits, 2 = usage error or a file that cannot be read.
In --hook mode: 0 = nothing to report, 2 = hits on stderr for Claude.
The hook skips a file that does not look like a document in this style, and each path that matches
a glob in OPENBSD_STYLE_LINT_EXCLUDE (separator: os.pathsep). The pattern * turns the hook off.
Standard library only.
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

CANONICAL = ["NAME", "SYNOPSIS", "DESCRIPTION", "CONTEXT", "RETURN VALUES", "ENVIRONMENT", "FILES",
             "EXIT STATUS", "EXAMPLES", "DIAGNOSTICS", "ERRORS", "SEE ALSO", "STANDARDS", "HISTORY",
             "AUTHORS", "CAVEATS", "BUGS", "SECURITY CONSIDERATIONS"]
SORTED_SECTIONS = {"ENVIRONMENT", "FILES", "ERRORS"}
WORDS = ["simply", "just", "easily", "easy", "powerful", "robust", "seamless", "blazing", "modern",
         "intuitive", "leverage", "please"]
PHRASES = ["it is worth noting", "out of the box"]
YOU = re.compile(r"\b(?:you|your|yours|yourself|yourselves)\b", re.I)
WORD = re.compile(r"\b(?:" + "|".join(WORDS + [p.replace(" ", r"\s+") for p in PHRASES]) + r")\b", re.I)
BANG = re.compile(r"!(?!=)")
ARTICLES = {"a", "an", "the"}
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NAME_LINE = re.compile(r"^(\S.*?) - (.+)$")
TAG_ITEM = re.compile(r"^[-*+]\s+(?:\[)?`\[?([^`\]]+)\]?`")
DEFAULT_OPENER = re.compile(r"^(?:The default(?: value)? is|This is the default|By default|"
                            r"If not (?:specified|set|given), \S+ defaults? to|It defaults to|Defaults to)\b")
DEFAULT_INLINE = re.compile(r"\(\s*default|[,;:]\s*(?:the\s+)?defaults?\b|\bwhich defaults?\b|"
                            r"\bdefaulting to\b|\bdefault\s*[:=]|.\bby default\b", re.I)
TERM_LINE_REST = re.compile(r"^\s*\]?\s*(?:(?:\*[^*]*\*|_[^_]*_)\s*)*:")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
BARE_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s<>]*[^\s<>.,;:!?)\]'\"]", re.I)
REFERENCE_DEFINITION = re.compile(r"^ {0,3}\[(?!\^)[^\]]+\]:\s")
CODE_SPAN = re.compile(r"`[^`]*`")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\[])")
MAX_HOOK_HITS = 12
EXCLUDE_VAR = "OPENBSD_STYLE_LINT_EXCLUDE"


def prose_lines(text):
    """(line number, text with code spans as CODE, text) for each line outside front matter, fenced code and HTML comments."""
    lines = text.splitlines()
    out, fence, start, comment = [], None, 0, False
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() in ("---", "..."):
                start = i + 1
                break
    for number, line in enumerate(lines[start:], start + 1):
        match = FENCE.match(line)
        if fence:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                    and not line.strip()[len(match.group(1)):].strip():
                fence = None
            continue
        if match:
            fence = match.group(1)
            continue
        if comment:
            if "-->" not in line:
                line = ""
            else:
                line = line.split("-->", 1)[1]
                comment = False
        while not comment:
            at = re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), line).find("<!--")
            if at < 0:
                break
            end = line.find("-->", at + 4)
            if end < 0:
                line, comment = line[:at], True
                break
            line = line[:at] + line[end + 3:]
        out.append((number, CODE_SPAN.sub("CODE", line), line))
    return out


def headings(lines):
    """The ## headings as (line number, title), and the title of the # heading with its line number."""
    title, heads = None, []
    for number, _, raw in lines:
        match = HEADING.match(raw)
        if not match:
            continue
        level, text = len(match.group(1)), match.group(2).strip()
        if level == 1 and title is None:
            title = (number, text)
        elif level == 2:
            heads.append((number, text))
    return title, heads


def upper_outside_code(text):
    """The text in uppercase, except for the code spans."""
    parts = re.split(r"(`[^`]*`)", text)
    return "".join(p if p.startswith("`") else p.upper() for p in parts)


def check_headings(lines, heads, raw_lines):
    """Hits for heading-case, section-order and empty-section."""
    hits = []
    if any(text in CANONICAL for _, text in heads):
        hits += [(n, "heading-case", f"write the heading in uppercase: {upper_outside_code(text)}")
                 for n, text in heads if CODE_SPAN.sub("", text) != CODE_SPAN.sub("", text).upper()]
    last, last_name, seen_description = -1, None, False
    has_description = any(text.upper() == "DESCRIPTION" for _, text in heads)
    for n, text in heads:
        name = text.upper()
        if name in CANONICAL:
            index = CANONICAL.index(name)
            if index < last:
                hits.append((n, "section-order", f"{name} must come before {last_name}"))
            else:
                last, last_name = index, name
            seen_description = seen_description or name == "DESCRIPTION"
        elif has_description and not seen_description:
            hits.append((n, "section-order", f"put the custom section {text} after DESCRIPTION"))
    stops = [n for n, _, raw in lines if HEADING.match(raw) and len(HEADING.match(raw).group(1)) <= 2]
    for n, text in heads:
        nxt = min([s for s in stops if s > n], default=len(raw_lines) + 1)
        if not any(line.strip() for line in raw_lines[n:nxt - 1]):
            hits.append((n, "empty-section", f"delete the empty section {text}, or give it content"))
    return hits


def check_name_line(lines, title):
    """Hits for the form of the title and of the NAME line under it."""
    if title is None:
        return [(1, "name-line", "start the document with the title '# <name>'")]
    number, name = title
    after = [(n, raw) for n, _, raw in lines if n > number and raw.strip()]
    if not after or not NAME_LINE.match(after[0][1].strip()):
        return [(number, "name-line", f"write the NAME line under the title: '{name} - <short description>'")]
    n, raw = after[0]
    names, text = NAME_LINE.match(raw.strip()).groups()
    hits = []
    if name.strip("`") not in [part.strip().strip("`") for part in names.split(",")]:
        hits.append((n, "name-line", f"start the NAME line with the title {name}"))
    first = text.split()[0]
    if first.lower() in ARTICLES:
        hits.append((n, "name-line", f"drop the article '{first}'"))
    if first[0].isupper() and first != first.upper():
        hits.append((n, "name-line", "start the description in lowercase"))
    if text.endswith("."):
        hits.append((n, "name-line", "remove the final period"))
    return hits


def item_text(prose):
    """The description of a tag item: the prose after the term, without the argument placeholder of the term line."""
    rest = prose.split("CODE", 1)[1] if "CODE" in prose else prose
    if rest.rstrip().endswith("\\"):
        return ""
    colon = TERM_LINE_REST.match(rest)
    return rest[colon.end():] if colon else rest


def sort_key(term):
    return [(c.lower(), c.islower()) for c in term.lstrip("-")]


def tag_lists(lines):
    """Runs of top-level tag items: (section, [(line, term, item text)]).

    A run ends at a heading or at a top-level line that is not a tag item.
    """
    runs, run, section, item = [], [], None, None
    for number, prose, raw in lines:
        heading = HEADING.match(raw)
        tag = TAG_ITEM.match(raw)
        if tag and not tag.group(1).split():
            tag = None
        if heading or (raw.strip() and not raw[0].isspace() and not tag):
            if run:
                runs.append((section, run))
            run, item = [], None
            if heading and len(heading.group(1)) == 2:
                section = heading.group(2).strip().upper()
            continue
        if tag:
            item = [number, tag.group(1).split()[0], [item_text(prose)]]
            run.append(item)
        elif item is not None and raw.strip():
            item[2].append(prose.strip())
    if run:
        runs.append((section, run))
    return runs


def check_lists(lines):
    """Hits for sort-order and default-sentence in the tag lists."""
    hits = []
    for section, run in tag_lists(lines):
        terms = [term for _, term, _ in run]
        if section in SORTED_SECTIONS or all(t.startswith("-") for t in terms):
            for (n, term, _), (_, prev, _) in zip(run[1:], run):
                if sort_key(term) < sort_key(prev):
                    order = ", ".join(sorted(terms, key=sort_key))
                    hits.append((n, "sort-order", f"{term} comes after {prev}. Sort the list: {order}"))
                    break
        for n, _, parts in run:
            text = " ".join(parts).strip().lstrip("*_\\: ").strip()
            for sentence in SENTENCE_END.split(text):
                s = sentence.strip()
                if re.search(r"\bdefault", s, re.I) and not DEFAULT_OPENER.match(s) and DEFAULT_INLINE.search(s):
                    hits.append((n, "default-sentence", f"give the default its own sentence: '{s}'"))
    return hits


def check_words(lines):
    """Hits for you and word-list, outside code."""
    hits = []
    for number, prose, _ in lines:
        if REFERENCE_DEFINITION.match(prose):
            continue
        clean = BARE_URL.sub("", LINK_TARGET.sub("]()", prose.replace("![", "[")))
        hits += [(number, "you", f"'{m.group(0)}': describe the user as 'the user', or use the imperative")
                 for m in YOU.finditer(clean)]
        hits += [(number, "word-list", f"remove '{m.group(0)}', or give the reason in the reply")
                 for m in WORD.finditer(clean)]
        if BANG.search(clean):
            hits.append((number, "word-list", "remove the exclamation mark"))
        if "**" in clean:
            hits.append((number, "word-list", "remove the bold"))
    return hits


def lint(text):
    """The hits of a document as sorted (line, rule, message) tuples."""
    lines = prose_lines(text)
    title, heads = headings(lines)
    hits = check_headings(lines, heads, text.splitlines()) + check_name_line(lines, title) + check_lists(lines) + check_words(lines)
    return sorted(hits)


def in_style(text):
    """True if the text looks like a document in this style: ## DESCRIPTION, and a NAME line or another canonical heading."""
    lines = prose_lines(text)
    title, heads = headings(lines)
    names = [t for _, t in heads if t in CANONICAL]
    if "DESCRIPTION" not in names:
        return False
    return len(names) > 1 or not check_name_line(lines, title)


def excluded(path):
    """True if the path matches a glob of the exclusion variable."""
    patterns = [p for p in os.environ.get(EXCLUDE_VAR, "").split(os.pathsep) if p]
    return any(fnmatch.fnmatch(str(path), os.path.expanduser(p)) for p in patterns)


def hook():
    """Lint the file of a PostToolUse event. Return 2 and report the hits on stderr for Claude, or return 0."""
    try:
        event = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except ValueError:
        return 0
    tool_input = event.get("tool_input") if isinstance(event, dict) else None
    path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(path, str) or not path.lower().endswith(".md"):
        return 0
    target = Path(event.get("cwd") or ".", path)
    if excluded(target):
        return 0
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    if not in_style(text):
        return 0
    hits = lint(text)
    if not hits:
        return 0
    out = [f"openbsd-style-docs: {target.name} has {len(hits)} style hit(s)."]
    out += [f"  line {n}, {rule}: {message}" for n, rule, message in hits[:MAX_HOOK_HITS]]
    if len(hits) > MAX_HOOK_HITS:
        out.append(f"  and {len(hits) - MAX_HOOK_HITS} more hit(s).")
    out.append("Fix each hit in the file, or keep it and give the reason in the reply.")
    sys.stderr.buffer.write(("\n".join(out) + "\n").encode("utf-8"))
    return 2


def main(argv):
    if argv == ["--hook"]:
        return hook()
    if not argv or any(a.startswith("-") for a in argv):
        print(__doc__, file=sys.stderr)
        return 2
    found = False
    for name in argv:
        try:
            text = Path(name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            print(f"error: cannot read {name}: {error}", file=sys.stderr)
            return 2
        for n, rule, message in lint(text):
            found = True
            print(f"{name}:{n}: {rule}: {message}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
