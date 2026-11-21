#!/usr/bin/env python3
"""Rebuild CHANGELOG.md and plugin.json after a merge of the main branch into a work branch.

A merge of the main branch into an open branch of this repository gives the same conflicts each time:
the top of CHANGELOG.md, its link lines, and the version in plugin.json. The script writes these files
new from the two sides of the merge. Run it in the work tree of the branch while the merge is in
progress. Start the merge with git merge --no-commit, so that a merge with no conflict stays in
progress too. It stages nothing and commits nothing. Read "git diff" before you stage the result.
It needs Python 3.7 or later and git, and it uses only the standard library.

Subcommands:
  release     The branch adds a release section right below "## [Unreleased]". The CHANGELOG of
              --theirs is the base. The release section of the branch goes on top of it, with the
              versions of --bump and the number of --release in its heading. A bullet that --theirs
              already has is left out. An older section of the branch can have the text of that bullet.
              Then the script leaves it out only for an [Unreleased] entry of the merge base that
              --theirs released. If --theirs has a heading with the same text but the merge base does
              not, another branch took the same numbers and merged first. The section of
              the branch is still a new release, and it goes on top in full, with no line left out.
              The link lines get the new release. Each --bump writes its version into the
              plugin.json of that plugin. The other lines of that file come from --theirs, or from
              the branch if only the branch changed them since the merge base.
              The script cannot bump a plugin that --theirs does not have: it ends with exit code 2.
  unreleased  The branch adds entries under "## [Unreleased]" and no release. The CHANGELOG of
              --theirs is the base. The entries that the branch added since the merge base go under its
              [Unreleased] heading.

An entry is a "- " bullet with the lines below it that are indented or that start with "|", the rows
of a table. A blank line right above such a line belongs to the entry too, so unreleased and
--absorb-unreleased keep it.
An entry can also be indented lines or table rows right below a "### " heading, with no bullet
above them. The first line of such an entry matches only the first line under that heading on the
other side.

With --keep-both FILE, the script also keeps both sides of each conflict in FILE: first the side of
--theirs, then the side of --ours. Give one --keep-both for each file. FILE is a path from the top
folder of the repository.

The script refuses, and writes nothing, in each of these cases:
  - No merge is in progress, or --theirs is not the commit that merges in.
  - The CHANGELOG of a side has no "## [Unreleased]" heading, or more than one.
  - release: the top section of the branch is not a release section, or both --theirs and the merge
    base have it.
  - release: --theirs has the heading of the top section of the branch, and a "- "
    bullet of that section is new on --theirs. Then merge CHANGELOG.md by hand. A bullet is new
    on --theirs when the older sections of the branch lack it, or --theirs has it more often
    than the merge base.
  - release: --theirs does not have that heading, and each "- " bullet of that section is new on
    --theirs.
  - release: --theirs does not have that heading, and a "- " bullet of that section is new on
    --theirs. An indented line or a table row below that bullet is below no copy of it on --theirs or
    on the merge base. The script leaves out such a bullet with its indented lines and table rows.
    Without this stop, the result loses that line. The script also stops for an indented line or a
    table row after a blank line below such a bullet. Without this stop, that line moves below
    another bullet.
  - release: the plugins of --bump are not the plugins of the heading of that section.
  - release: a version of --bump is not higher than the version on --theirs, or --release is not
    higher than the release of the [Unreleased] link line of --theirs.
  - release: --theirs has entries under [Unreleased], and --absorb-unreleased is not given.
  - release: both sides changed lines of a plugin.json other than the version.
  - unreleased: the branch has no entries under [Unreleased], or it adds a release section.
  - unreleased: the branch changed or removed an entry that the merge base has under [Unreleased].
  - A line that the branch added to CHANGELOG.md is not in the result.
  - The result has a line of CHANGELOG.md more often or less often than the two sides keep it, for example
    a line that a side removed or changed since the merge base.
  - Both sides have an entry with the same first line under one heading, but with other indented lines
    or table rows.
  - A --keep-both file has no conflict, or a conflict marker stays after the step.

Output lines, one fact on each line: MODE, OURS, THEIRS, BASE, HEADING, DROPPED, ABSORBED, ADDED, LINK,
VERSION, KEPT, NOTE, and STOP. The last line is RESULT. A line shows at most 200 characters.

Exit codes: 0 = done, 1 = a file cannot be written (the RESULT line gives the count of the written
files), or the script failed with a Python traceback, 2 = usage error, or a setup error (no git, a ref
or a file that git cannot read), 3 = refused (a STOP line). Nothing changes with exit code 2 or 3.

Examples:
  python3 -I tools/changelog_merge.py release --bump essentials/dev-essentials=3.25.0 --release 4.23.0
  python3 -I tools/changelog_merge.py release --bump dotnet/dotnet-backend-dev=1.8.1 \\
      --bump essentials/dev-essentials=3.24.2 --release 4.22.2 --keep-both docs/evals.md
  python3 -I tools/changelog_merge.py unreleased --repo /path/to/clone
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

LF = "\n"
CHANGELOG = "CHANGELOG.md"
MANIFEST = ".claude-plugin/plugin.json"
UNRELEASED = "## [Unreleased]"
VERSION = re.compile(r"\d+\.\d+\.\d+")
HEADING = re.compile(r"## (?P<plugins>.+) in release \[(?P<release>\d+\.\d+\.\d+)\](?P<tail>.*)")
PLUGIN_VERSION = re.compile(r"(?P<name>[a-z0-9][a-z0-9-]*) (?P<version>\d+\.\d+\.\d+)")
LINK = re.compile(r"\[Unreleased\]: (?P<base>\S+/compare/)v(?P<previous>\d+\.\d+\.\d+)\.\.\.HEAD")
VERSION_KEY = re.compile(r'("version"\s*:\s*")[^"]*(")')
CONFLICT = re.compile(r"^<<<<<<< [^\n]*\n(?P<ours>.*?)(?:^\|\|\|\|\|\|\| [^\n]*\n.*?)?^=======\n"
                      r"(?P<theirs>.*?)^>>>>>>> [^\n]*(?:\n|\Z)", re.M | re.S)
MARKER = re.compile(r"^(?:<<<<<<< |>>>>>>> |\|\|\|\|\|\|\| |=======$)", re.M)
LINE_CHARS = 200
MAX_DROPPED = 20
STOP_CHARS = 40
# A line with one of these starts belongs to the entry above it: an indented line, or a table row.
CONTINUED = (" ", "\t", "|")


class Stop(Exception):
    """A setup error. main() prints its text and returns exit code 2."""


class Refused(Exception):
    """A refusal. main() prints a STOP line and returns exit code 3."""


def say(kind, text=""):
    line = f"{kind} {text}".rstrip()
    print(line if len(line) <= LINE_CHARS else f"{line[:LINE_CHARS]} ... {len(line) - LINE_CHARS} more characters")


def short(text):
    """The start of text, so that a STOP line with two texts stays below LINE_CHARS."""
    return text if len(text) <= STOP_CHARS else f"{text[:STOP_CHARS]}..."


def as_tuple(version):
    return tuple(int(part) for part in version.split("."))


def git(repo, *args):
    """Run git in repo and return its stdout as text with LF line ends. A failed command stops the script."""
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, stdin=subprocess.DEVNULL)
    except OSError as error:
        raise Stop(f"cannot run git: {error}") from error
    if result.returncode != 0:
        raise Stop(f"git {' '.join(args)} failed: {' '.join(result.stderr.decode('utf-8', 'replace').split())}")
    return result.stdout.decode("utf-8").replace("\r\n", LF)


def show(repo, ref, path):
    return git(repo, "show", f"{ref}:{path}")


def write_text(path, text):
    """Write text with CRLF line ends if the file in the work tree has CRLF, else with LF."""
    crlf = path.is_file() and b"\r\n" in path.read_bytes()
    path.write_bytes((text.replace(LF, "\r\n") if crlf else text).encode("utf-8"))


def split_top(text, label):
    """Split a CHANGELOG into the part up to the [Unreleased] heading, its block, and the rest."""
    lines = text.split(LF)
    found = [i for i, line in enumerate(lines) if line == UNRELEASED]
    if len(found) != 1:
        raise Refused(f"the {CHANGELOG} of {label} has {len(found)} lines '{UNRELEASED}', not 1")
    start = found[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return LF.join(lines[:start]) + LF, LF.join(lines[start:end]).strip(LF), LF.join(lines[end:])


def first_section(rest):
    """Split the rest of a CHANGELOG into its first section and the text after that section."""
    lines = rest.split(LF)
    end = next((i for i in range(1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return LF.join(lines[:end]).strip(LF), LF.join(lines[end:])


def subsections(block):
    """Split a block into (heading, lines) parts by its "### " lines. Lines before the first heading refuse.

    A blank line stays only inside an entry: below a line of the part and right above a line of CONTINUED.
    """
    parts = []
    for line in block.split(LF):
        if line.startswith("### "):
            parts.append((line, []))
        elif parts:
            parts[-1][1].append(line)
        elif line.strip():
            raise Refused(f"a line is not below a '### ' heading: {line}")
    result = []
    for heading, body in parts:
        lines = []
        for line, after in zip(body, body[1:] + [""]):
            if line.strip():
                lines.append(line)
            elif lines and after.strip() and after.startswith(CONTINUED):
                lines.append("")
        result.append((heading, lines))
    return result


def entries(block):
    """The (heading, entry) pairs of a block. An entry is a bullet with the lines of CONTINUED below it."""
    pairs = []
    for heading, body in subsections(block):
        for line in body:
            if (not line or line.startswith(CONTINUED)) and pairs and pairs[-1][0] == heading:
                pairs[-1] = (heading, pairs[-1][1] + LF + line)
            else:
                pairs.append((heading, line))
    return pairs


def merge_block(target, extra, kind):
    """Put the lines of extra below the same "### " headings of target. A new heading goes at the end."""
    lines = target.split(LF) if target else []
    for heading, body in subsections(extra):
        found = heading in lines
        start = at = lines.index(heading) + 1 if found else len(lines)
        while found and at < len(lines) and not lines[at].startswith("### "):
            at += 1
        present, new, keep, bullet = set(lines[start:at]), [], True, None
        first = next((line for line in lines[start:at] if line.strip()), None)
        # A first line that is no "- " bullet is not in the map, so its indented line can be in any place of the subsection.
        below = indented_lines(LF.join(line for line in lines[start:at] if line.strip()))
        for line in body:
            # A line of CONTINUED or a blank line belongs to the line above it. A first line of CONTINUED is the key of its entry.
            if line and (bullet is None or not line.startswith(CONTINUED)):
                # An entry with no bullet above it can only be the first entry of the target, so only its first line matches.
                keep, bullet = (line != first if line.startswith(CONTINUED) else line not in present), line
            elif not keep and line and line not in below.get(bullet, present):
                raise Refused(f"both sides have the entry '{bullet}' with other indented lines or table rows, so merge {CHANGELOG} by hand")
            if keep:
                new.append(line)
        for line in new:
            say(kind, line)
        if found:
            while lines[at - 1] == "":
                at -= 1
            lines[at:at] = new
        elif new:
            lines += ["", heading, "", *new] if lines else [heading, "", *new]
    return re.sub(r"\n{3,}", LF + LF, LF.join(lines)).strip(LF)


def has_bullet(text):
    return any(line.startswith("- ") for line in text.split(LF))


def drop_known_bullets(section, known):
    """Leave out each bullet of known with its lines of CONTINUED, and then each "### " heading with no lines."""
    kept, dropped, skip = [], 0, False
    for line in section.split(LF):
        if line.startswith("- "):
            skip = line in known
            if skip:
                dropped += 1
                if dropped <= MAX_DROPPED:
                    say("DROPPED", line)
        elif not line.startswith(CONTINUED):
            skip = False
        if not skip:
            kept.append(line)
    if dropped > MAX_DROPPED:
        say("DROPPED", f"... {dropped - MAX_DROPPED} more bullets")
    text = re.sub(r"^### [^\n]*\n\s*(?=^### |\Z)", "", LF.join(kept) + LF, flags=re.M)
    return re.sub(r"\n{3,}", LF + LF, text).strip(LF)


def indented_lines(text):
    """Map each "- " bullet of text to the set of lines of CONTINUED below all its copies, also after a blank line."""
    found, below = {}, None
    for line in text.split(LF):
        if line.startswith("- "):
            below = found.setdefault(line, set())
        elif below is not None and line.startswith(CONTINUED):
            below.add(line)
        elif below is not None and line == "":
            continue
        else:
            below = None
    return found


def lost_indented_line(section, known, theirs_text, base_text):
    """The first (bullet, line, loose) that drop_known_bullets loses or moves, or None.

    If --theirs or the merge base has an indented line below that bullet, that line passes.
    loose is True for a line after a blank line. The drop leaves such a line below another bullet, so it never passes.
    """
    theirs, base, bullet, loose = indented_lines(theirs_text), indented_lines(base_text), None, False
    # The same steps as drop_known_bullets, so this sees each indented line that the drop takes out.
    for line in section.split(LF):
        if line.startswith("- "):
            bullet, loose = (line if line in known else None), False
        elif line == "":
            loose = True
        elif not line.startswith(CONTINUED):
            bullet = None
        elif bullet and line.strip() and (loose or (line not in theirs.get(bullet, ()) and line not in base.get(bullet, ()))):
            return bullet, line, loose
    return None


def new_links(text, release):
    """Point the [Unreleased] link line at the new release, and add the line of the new release."""
    found = [m for m in (LINK.fullmatch(line) for line in text.split(LF)) if m]
    if len(found) != 1:
        raise Refused(f"{len(found)} '[Unreleased]: .../compare/v<release>...HEAD' link lines, not 1")
    link = found[0]
    previous = link.group("previous")
    if as_tuple(release) <= as_tuple(previous):
        raise Refused(f"--release {release} is not higher than the release {previous} of the link line")
    if re.search(rf"^\[{re.escape(release)}\]: ", text, re.M):
        raise Refused(f"the link line of release {release} already exists")
    base = link.group("base")
    lines = f"[Unreleased]: {base}v{release}...HEAD{LF}[{release}]: {base}v{previous}...v{release}"
    say("LINK", f"[{release}] compares v{previous}...v{release}")
    return text.replace(link.group(0), lines, 1)


def with_version(path, text, version):
    """The plugin.json text with the new version in its first "version" key."""
    new, count = VERSION_KEY.subn(lambda m: m.group(1) + version + m.group(2), text, count=1)
    try:
        written = count == 1 and json.loads(new).get("version") == version
    except (ValueError, AttributeError):
        written = False
    if not written:
        raise Refused(f"{path}: cannot write the version")
    return new


def side_manifest(repo, ref, path, version):
    """The plugin.json text of ref with the new version, or None if ref has no such file."""
    try:
        return with_version(path, show(repo, ref, path), version)
    except Stop:
        return None


def bump_manifests(repo, ours, theirs, base, bumps):
    """The plugin.json text of each --bump with the new version, and a map of plugin name to version.

    The other lines come from --theirs. If only the branch changed them since the merge base, they come from --ours.
    """
    files, names = {}, {}
    for folder, version in bumps:
        path = f"{folder}/{MANIFEST}"
        text = show(repo, theirs, path)
        try:
            data = json.loads(text)
        except ValueError as error:
            raise Refused(f"{path} on {theirs} is not JSON: {error}") from error
        old = str(data.get("version", ""))
        if not VERSION.fullmatch(old) or as_tuple(version) <= as_tuple(old):
            raise Refused(f"{path}: the version {version} is not higher than {old or 'no version'} on {theirs}")
        new = with_version(path, text, version)
        mine, old_text = (side_manifest(repo, ref, path, version) for ref in (ours, base))
        if mine is not None and mine != new:
            if old_text == new:
                new = mine
            elif old_text != mine:
                raise Refused(f"{path}: both sides changed lines other than the version. Stop the merge, take the "
                              "change of the branch out, commit, merge again, and make it again")
        files[path] = new
        names[data.get("name")] = version
        say("VERSION", f"{path} {old} -> {version}")
    return files, names


def release_changelog(ours, theirs_text, base_text, release, versions, absorb):
    """The new CHANGELOG text of the release subcommand, and the heading line of the branch."""
    _, ours_block, ours_rest = split_top(ours, "--ours")
    if ours_block:
        raise Refused("the branch has entries under [Unreleased]. Move them into its release section first")
    section, older = first_section(ours_rest)
    heading = section.split(LF)[0]
    match = HEADING.fullmatch(heading)
    if not match:
        raise Refused(f"the top section of the branch is not a release section: {heading}")
    theirs_lines = set(theirs_text.split(LF))
    same = heading in theirs_lines
    # Two open branches can take the same numbers. A heading that the merge base lacks is a new release of the branch.
    if same and heading in base_text.split(LF):
        raise Refused(f"--theirs has the top section of the branch too, so the branch adds no release: {heading}")
    named = {m.group("name") for m in PLUGIN_VERSION.finditer(match.group("plugins"))}
    if named != set(versions):
        raise Refused(f"the heading names {sorted(named)}, but --bump names {sorted(versions)}")
    plugins = PLUGIN_VERSION.sub(lambda m: f"{m.group('name')} {versions[m.group('name')]}", match.group("plugins"))
    new_heading = f"## {plugins} in release [{release}]{match.group('tail')}"
    say("HEADING", new_heading)
    body = LF.join(section.split(LF)[1:]).strip(LF)
    known = theirs_lines - set(older.split(LF))
    if same:
        # The section goes on top in full. A bullet that --theirs added since the merge base is an entry of both sides.
        known |= set(Counter(theirs_text.split(LF)) - Counter(base_text.split(LF)))
        shared = [line for line in body.split(LF) if line.startswith("- ") and line in known]
        if shared:
            raise Refused(f"the top section of the branch and --theirs both have the entry '{shared[0]}', so merge "
                          f"{CHANGELOG} by hand")
    else:
        # An entry of the merge base that --theirs moved from [Unreleased] into a release is known, also with an old text.
        _, unreleased, released = split_top(theirs_text, "--theirs")
        old = Counter(older.split(LF))
        moved = Counter(base_text.split(LF)) - old - Counter(unreleased.split(LF))
        known |= set(moved) & set(Counter(released.split(LF)) - old)
        lost = lost_indented_line(body, known, theirs_text, base_text)
        if lost:
            bullet, line = short(lost[0]), short(lost[1])
            kind = "table row" if line.startswith("|") else "indented line"
            if lost[2]:
                raise Refused(f"merge {CHANGELOG} by hand: a blank line is above the {kind} '{line}' of the bullet "
                              f"'{bullet}' that --theirs has")
            raise Refused(f"merge {CHANGELOG} by hand: --theirs has the bullet '{bullet}' without the {kind} "
                          f"'{line}' of the branch")
        body = drop_known_bullets(body, known)
        if not has_bullet(body) and has_bullet(section):
            raise Refused(f"the top section of the branch adds no '- ' bullet to --theirs, so the branch adds no release: {heading}")
    head, theirs_block, theirs_rest = split_top(theirs_text, "--theirs")
    if theirs_block and not absorb:
        raise Refused("--theirs has entries under [Unreleased]. Only the next pull request to merge takes them "
                      "in: pass --absorb-unreleased")
    if theirs_block:
        body = merge_block(body, theirs_block, "ABSORBED")
    text = f"{head}{LF}{new_heading}{LF}{LF}{body}{LF}{LF}{theirs_rest}"
    return new_links(text, release), heading, match.group("release")


def unreleased_changelog(ours, theirs_text, base):
    """The new CHANGELOG text of the unreleased subcommand."""
    _, ours_block, ours_rest = split_top(ours, "--ours")
    head, theirs_block, theirs_rest = split_top(theirs_text, "--theirs")
    # Only the entries that the branch added since the merge base go in. --theirs decides on the others.
    old, mine = entries(split_top(base, "the merge base")[1]), entries(ours_block)
    changed = [entry for heading, entry in old if (heading, entry) not in mine]
    if changed:
        raise Refused(f"the branch changed or removed an entry of the merge base, so merge {CHANGELOG} by hand: "
                      f"{changed[0].split(LF)[0]}")
    old = set(old)
    groups = {}
    for heading, entry in mine:
        if (heading, entry) not in old:
            groups.setdefault(heading, []).append(entry)
    if not groups:
        raise Refused("the branch has no entries under [Unreleased]")
    ours_block = LF.join(f"{heading}{LF}{LF}{LF.join(items)}{LF}" for heading, items in groups.items())
    heading = first_section(ours_rest)[0].split(LF)[0]
    if heading and heading not in set(theirs_text.split(LF)):
        raise Refused(f"the branch adds a release section, so use the subcommand release: {heading}")
    block = merge_block(theirs_block, ours_block, "ADDED")
    tail = f"{LF}{LF}{theirs_rest}" if theirs_rest else LF
    return f"{head}{LF}{block}{tail}"


def lost_lines(base, ours, result, ignore):
    """The lines that the branch added to the CHANGELOG and that the result does not have."""
    known = set(base.split(LF)) | set(result.split(LF))
    return [line for line in ours.split(LF) if line.strip() and line not in known and not ignore(line)]


def miscounted(base, ours, theirs, result):
    """The first line that the result has more often or less often than a merge keeps it, and True if more often.

    A merge keeps the copies that both sides keep, and adds the copies that each side added. Headings and links do not count.
    """
    b, o, t, r = (Counter(line for line in text.split(LF) if line.strip() and not line.startswith(("#", "[")))
                  for text in (base, ours, theirs, result))
    # A bullet names the entry better than an indented line, which many entries can share.
    for line in sorted(set(b) | set(o) | set(t) | set(r), key=lambda line: (line.startswith((" ", "\t")), line)):
        kept = min(b[line], o[line], t[line])
        added = (max(o[line] - b[line], 0), max(t[line] - b[line], 0))
        if not kept + max(added) <= r[line] <= kept + sum(added):
            return line, r[line] > kept + sum(added)
    return None


def keep_both(top, name):
    """The text of the file with both sides of each conflict, the side of --theirs first, and the conflict count."""
    try:
        text = (top / name).read_bytes().decode("utf-8").replace("\r\n", LF)
    except (OSError, ValueError) as error:
        raise Stop(f"cannot read the --keep-both file {name} in {top}: {error}") from error
    count = len(CONFLICT.findall(text))
    if not count:
        raise Refused(f"{name}: no conflict to keep both sides of")
    text = CONFLICT.sub(lambda m: m.group("theirs") + m.group("ours"), text)
    if MARKER.search(text):
        raise Refused(f"{name}: a conflict marker stays after the step")
    return text, count


def parse_bump(value):
    folder, _, version = value.rpartition("=")
    folder = folder.replace("\\", "/").strip("/")
    if not folder or not VERSION.fullmatch(version):
        raise argparse.ArgumentTypeError(f"give FOLDER=X.Y.Z, not {value!r}")
    return folder, version


def parse_version(value):
    if not VERSION.fullmatch(value):
        raise argparse.ArgumentTypeError(f"give X.Y.Z, not {value!r}")
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="Run with -h after a subcommand for its options.")
    commands = parser.add_subparsers(dest="command", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--repo", type=Path, default=Path("."), help="the work tree of the branch (default: .)")
    shared.add_argument("--ours", default="HEAD", help="the commit of the branch (default: HEAD)")
    shared.add_argument("--theirs", default="origin/main", help="the commit that merges in (default: origin/main)")
    shared.add_argument("--keep-both", action="append", default=[], metavar="FILE",
                        help="a file whose conflicts keep both sides, as a path from the top folder of the "
                             "repository; give it once for each file")
    release = commands.add_parser("release", parents=[shared], help="the branch adds a release section")
    release.add_argument("--bump", action="append", type=parse_bump, required=True, metavar="FOLDER=X.Y.Z",
                         help="a plugin folder and its new version; give it once for each plugin of the release")
    release.add_argument("--release", type=parse_version, required=True, metavar="X.Y.Z", help="the new release")
    release.add_argument("--absorb-unreleased", action="store_true",
                         help="move the [Unreleased] entries of --theirs into the release section")
    commands.add_parser("unreleased", parents=[shared], help="the branch adds entries under [Unreleased]")
    args = parser.parse_args(argv)
    if CHANGELOG in args.keep_both:
        parser.error(f"the script writes {CHANGELOG} itself, so do not give it to --keep-both")
    folders = [folder for folder, _ in getattr(args, "bump", [])]
    if len(set(folders)) != len(folders):
        parser.error("give each --bump folder once")
    return args


def execute(args):
    repo = args.repo
    top = Path(git(repo, "rev-parse", "--show-toplevel").strip())
    base_ref = git(repo, "merge-base", args.ours, args.theirs).strip()
    try:
        merging = git(repo, "rev-parse", "-q", "--verify", "MERGE_HEAD").strip()
    except Stop:
        raise Refused(f"no merge is in progress in {top}. Run git merge --no-commit {args.theirs} first") from None
    theirs_commit = git(repo, "rev-parse", "--verify", f"{args.theirs}^{{commit}}").strip()
    if merging != theirs_commit:
        raise Refused(f"the merge in progress takes in {merging[:12]}, but --theirs {args.theirs} is "
                      f"{theirs_commit[:12]}. Give --theirs the commit that merges in, for example "
                      "--theirs MERGE_HEAD")
    say("MODE", args.command)
    say("OURS", git(repo, "log", "-1", "--format=%h %s", args.ours).strip())
    say("THEIRS", git(repo, "log", "-1", "--format=%h %s", args.theirs).strip())
    say("BASE", base_ref[:12])
    ours, theirs, base = (show(repo, ref, CHANGELOG) for ref in (args.ours, args.theirs, base_ref))
    files = {}
    if args.command == "release":
        manifests, versions = bump_manifests(repo, args.ours, args.theirs, base_ref, args.bump)
        text, old_heading, old_release = release_changelog(ours, theirs, base, args.release, versions,
                                                           args.absorb_unreleased)
        files.update(manifests)

        def ignore(line):
            return line == old_heading or line.startswith(("[Unreleased]: ", f"[{old_release}]: "))
    else:
        text = unreleased_changelog(ours, theirs, base)

        def ignore(_line):
            return False
    lost = lost_lines(base, ours, text, ignore)
    if lost:
        raise Refused(f"{len(lost)} lines that the branch added would be lost, the first: {lost[0]}")
    wrong = miscounted(base, ours, theirs, text)
    if wrong:
        line, extra = wrong
        what = "has a line that a side removed or changed" if extra else "loses a line that a side added"
        raise Refused(f"the result {what} since the merge base, so merge {CHANGELOG} by hand: {line}")
    files[CHANGELOG] = text
    for name in args.keep_both:
        files[name], count = keep_both(top, name)
        say("KEPT", f"{name}: both sides of {count} conflicts, the side of --theirs first")
    for done, (name, content) in enumerate(files.items()):
        try:
            write_text(top / name, content)
        except OSError as error:
            say("RESULT", f"ERROR. {done} of {len(files)} files are written. Cannot write {name}: {error}")
            return 1
    say("NOTE", "nothing is staged. Read git diff, then stage the files")
    say("RESULT", f"DONE. {len(files)} files written")
    return 0


def main(argv=None):
    # A CHANGELOG line can hold any character. The reader takes the output as UTF-8, also on Windows.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args(argv)
    try:
        return execute(args)
    except Stop as error:
        say("RESULT", f"ERROR. {error}")
        return 2
    except Refused as error:
        say("STOP", str(error))
        say("RESULT", "REFUSED. Nothing changed")
        return 3


if __name__ == "__main__":
    sys.exit(main())
