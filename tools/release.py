#!/usr/bin/env python3
"""Write the release section of CHANGELOG.md with the version bumps, or the notes of a GitHub release.

A pull request with a version bump adds a release section right below "## [Unreleased]". It moves the
[Unreleased] link line, adds the link line of the release, and writes the new version into each plugin.json.
After the merge, the GitHub release gets its notes from that section. The script does these fixed steps.
It needs Python 3.7 or later and git, and it uses only the standard library. Each tool of tools/ runs alone
under python3 -I, so this script repeats the link logic of changelog_merge.py and does not import it.

Subcommands:
  section  Put the section of --section-file right below "## [Unreleased]" of CHANGELOG.md in --repo.
           The [Unreleased] link line then compares from the new release, and the link line of the release
           comes right below it. Each --bump writes its version into the plugin.json of that plugin folder.
           If an entry is under [Unreleased], the section file must hold it already. The entry then leaves
           [Unreleased]. Each file keeps its line ends: CRLF if most of its lines end with CRLF, else LF.
           It stages nothing.
  notes    Write the notes of a GitHub release to --output: "## What's changed", the --lead text, and the
           body of the section of --release in CHANGELOG.md at --ref. The file has LF line ends.

The script refuses, and writes nothing, in each of these cases:
  - section: CHANGELOG.md has no "## [Unreleased]" heading, or more than one.
  - section: the section file does not start with a heading "## <plugin> <version> in release [X.Y.Z]",
    or it has a second "## " line or a link line "[label]: ...".
  - section: the heading names another release than --release, or other plugins or versions than --bump.
  - section: CHANGELOG.md has a heading or a link line of the release already.
  - section: CHANGELOG.md has no single "[Unreleased]: .../compare/vX.Y.Z...HEAD" link line below the
    release sections, or the link does not start at the release of the newest release section.
  - section: --release is not higher than the release of the newest release section.
  - section: an entry under [Unreleased] is not in the section file.
  - section: a plugin folder has no .claude-plugin/plugin.json, or the file is not JSON or has a key twice.
  - section: the top-level "version" of a plugin.json is not X.Y.Z or is not on a line of its own.
  - section: a --bump version is not higher than the version in its plugin.json.
  - notes: CHANGELOG.md at --ref has no section of --release, or more than one.

Output lines, one fact on each line: SECTION, ABSORBED, LINK, VERSION, NOTES, NOTE, and STOP. The last line is
RESULT. A line shows at most 200 characters.

Exit codes: 0 = done, 1 = a file of section cannot be written (the RESULT line gives the count of the
written files) or the script failed with a Python traceback, 2 = usage error, or a setup error (no git, a
ref or a file that cannot be read, or a notes file that cannot be written), 3 = refused (a STOP line).
Nothing changes with exit code 2 or 3.

Examples:
  python3 -I tools/release.py section --section-file section.md --release 5.4.4 \\
      --bump essentials/dev-essentials=4.4.4
  python3 -I tools/release.py notes --release 5.4.4 --lead "PR #320 closes issue #315." --output notes.md
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LF = "\n"
CHANGELOG = "CHANGELOG.md"
MANIFEST = ".claude-plugin/plugin.json"
UNRELEASED = "## [Unreleased]"
VERSION = re.compile(r"\d+\.\d+\.\d+")
HEADING = re.compile(r"## (?P<plugins>.+) in release \[(?P<release>\d+\.\d+\.\d+)\].*")
PLUGIN_VERSION = re.compile(r"(?P<name>[a-z0-9][a-z0-9-]*) (?P<version>\d+\.\d+\.\d+)")
RELEASE_IN_HEADING = re.compile(r"\[(?P<release>\d+\.\d+\.\d+)\]")
LINK = re.compile(r"\[Unreleased\]: (?P<base>\S+/compare/)v(?P<previous>\d+\.\d+\.\d+)\.\.\.HEAD")
LINK_LINE = re.compile(r"\[[^\]]+\]: \S")
VERSION_LINE = re.compile(r'^(?P<head>\s*"version"\s*:\s*")(?P<version>[^"]*)(?P<tail>".*)$', re.M)
LINE_CHARS = 200
MAX_ABSORBED = 20


class Stop(Exception):
    """A setup error. main() prints its text and returns exit code 2."""


class Refused(Exception):
    """A refusal. main() prints a STOP line and returns exit code 3."""


def say(kind, text=""):
    line = f"{kind} {text}".rstrip()
    print(line if len(line) <= LINE_CHARS else f"{line[:LINE_CHARS]} ... {len(line) - LINE_CHARS} more characters")


def as_tuple(version):
    return tuple(int(part) for part in version.split("."))


def read_text(path):
    """The text of a file with LF line ends, and True if most of its lines end with CRLF."""
    try:
        raw = path.read_bytes()
        return raw.decode("utf-8").replace("\r\n", LF), raw.count(b"\r\n") * 2 > raw.count(b"\n")
    except (OSError, ValueError) as error:
        raise Stop(f"cannot read {path}: {error}") from error


def encode(text, crlf):
    return (text.replace(LF, "\r\n") if crlf else text).encode("utf-8")


def section_lines(text, release, versions):
    """The lines of the section file with no blank line at either end, after the checks of its heading."""
    lines = text.lstrip("\ufeff").strip(LF).split(LF)
    match = HEADING.fullmatch(lines[0])
    if not match:
        raise Refused(f"the section file does not start with a heading '## <plugin> <version> in release [X.Y.Z]': {lines[0]}")
    extra = next((line for line in lines[1:] if line.startswith("## ")), None)
    if extra:
        raise Refused(f"the section file has a second '## ' line: {extra}")
    link = next((line for line in lines if LINK_LINE.match(line)), None)
    if link:
        raise Refused(f"the section file has a link line: {link}")
    if match.group("release") != release:
        raise Refused(f"the heading names release {match.group('release')}, but --release is {release}")
    named = {m.group("name"): m.group("version") for m in PLUGIN_VERSION.finditer(match.group("plugins"))}
    if named != versions:
        raise Refused(f"the heading names {sorted(named.items())}, but --bump gives {sorted(versions.items())}")
    return lines


def unreleased_entries(block):
    """The entries of the [Unreleased] block. An entry is a line with the indented lines below it."""
    entries = []
    for line in block:
        if not line.strip() or line.startswith("### "):
            continue
        if line.startswith((" ", "\t")) and entries:
            entries[-1].append(line)
        else:
            entries.append([line])
    return entries


def holds(lines, entry):
    return any(lines[i:i + len(entry)] == entry for i in range(len(lines) - len(entry) + 1))


def new_links(lines, release, newest):
    """Point the [Unreleased] link line at the new release, and add the line of the new release below it."""
    found = [(i, m) for i, m in enumerate(LINK.fullmatch(line) for line in lines) if m]
    if len(found) != 1:
        raise Refused(f"{len(found)} '[Unreleased]: .../compare/vX.Y.Z...HEAD' link lines below the release sections, not 1")
    at, link = found[0]
    previous = link.group("previous")
    if previous != newest:
        raise Refused(f"the [Unreleased] link starts at {previous}, but the newest release section is {newest}")
    if as_tuple(release) <= as_tuple(previous):
        raise Refused(f"--release {release} is not higher than the newest release {previous}")
    base = link.group("base")
    say("LINK", f"[{release}] compares v{previous}...v{release}")
    return lines[:at] + [f"[Unreleased]: {base}v{release}...HEAD", f"[{release}]: {base}v{previous}...v{release}"] + lines[at + 1:]


def new_changelog(text, section, release):
    """The CHANGELOG text with the section below [Unreleased], an empty [Unreleased] block, and the new links."""
    lines = text.split(LF)
    found = [i for i, line in enumerate(lines) if line == UNRELEASED]
    if len(found) != 1:
        raise Refused(f"{CHANGELOG} has {len(found)} lines '{UNRELEASED}', not 1")
    start = found[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    entries = unreleased_entries(lines[start:end])
    solid = [line for line in section if line.strip()]
    missing = next((entry for entry in entries if not holds(solid, entry)), None)
    if missing:
        raise Refused(f"an entry under [Unreleased] is not in the section file. Put it into the section first: {missing[0]}")
    newest = RELEASE_IN_HEADING.search(lines[end]) if end < len(lines) else None
    below = new_links(lines[end:], release, newest.group("release") if newest else "no release")
    for entry in entries[:MAX_ABSORBED]:
        say("ABSORBED", entry[0])
    if len(entries) > MAX_ABSORBED:
        say("ABSORBED", f"... {len(entries) - MAX_ABSORBED} more entries")
    return LF.join(lines[:start] + ["", *section, ""] + below)


def unique_keys(pairs):
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"a key is there twice: {sorted(key for key in set(keys) if keys.count(key) > 1)}")
    return dict(pairs)


def loads(text):
    try:
        return json.loads(text, object_pairs_hook=unique_keys)
    except ValueError:
        return None


def new_manifest(path, text, version):
    """The plugin.json text with the new top-level version, and its plugin name and old version."""
    try:
        data = json.loads(text, object_pairs_hook=unique_keys)
    except ValueError as error:
        raise Refused(f"{path} is not JSON: {error}") from error
    old = data.get("version") if isinstance(data, dict) else None
    if not isinstance(old, str) or not VERSION.fullmatch(old):
        raise Refused(f"{path}: the top-level version is {old!r}, not X.Y.Z")
    if as_tuple(version) <= as_tuple(old):
        raise Refused(f"{path}: the version {version} is not higher than {old}")
    news = [text[:match.start()] + match.group("head") + version + match.group("tail") + text[match.end():]
            for match in VERSION_LINE.finditer(text)]
    news = [new for new in news if loads(new) == dict(data, version=version)]
    if len(news) != 1:
        raise Refused(f"{path} has {len(news)} lines with the top-level '\"version\"' key, not 1")
    return news[0], str(data.get("name")), old


def run_section(args):
    top = args.repo
    changelog, changelog_crlf = read_text(top / CHANGELOG)
    # A second run for one release stops here, before the version check names a less clear reason.
    if any(line.startswith(("## ", f"[{args.release}]: ")) and f"[{args.release}]" in line for line in changelog.split(LF)):
        raise Refused(f"{CHANGELOG} has a heading or a link line of release {args.release} already. If an earlier run ended with ERROR, put the written files back with git first")
    manifests, versions = {}, {}
    for folder, version in args.bump:
        path = top / folder / MANIFEST
        if not path.is_file():
            raise Refused(f"the plugin folder {folder} has no {MANIFEST}")
        text, crlf = read_text(path)
        new, name, old = new_manifest(f"{folder}/{MANIFEST}", text, version)
        manifests[path] = (encode(new, crlf), f"{folder}/{MANIFEST} {old} -> {version}")
        versions[name] = version
    section = section_lines(read_text(args.section_file)[0], args.release, versions)
    say("SECTION", section[0])
    files = {top / CHANGELOG: encode(new_changelog(changelog, section, args.release), changelog_crlf)}
    for path, (content, fact) in manifests.items():
        say("VERSION", fact)
        files[path] = content
    for done, (path, content) in enumerate(files.items()):
        try:
            path.write_bytes(content)
        except OSError as error:
            say("NOTE", "a written CHANGELOG.md makes a second run refuse. Put each written file back with git, also the file that failed, because a failed write can cut it short. Remove the cause, then run again")
            say("RESULT", f"ERROR. {done} of {len(files)} files are written, {CHANGELOG} first. Cannot write {path}: {error}")
            return 1
    say("NOTE", "nothing is staged. Read git diff, then stage the files")
    say("RESULT", f"DONE. {len(files)} files written")
    return 0


def git_show(repo, ref, path):
    try:
        result = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], capture_output=True,
                                stdin=subprocess.DEVNULL)
    except OSError as error:
        raise Stop(f"cannot run git: {error}") from error
    if result.returncode != 0:
        raise Stop(f"git show {ref}:{path} failed: {' '.join(result.stderr.decode('utf-8', 'replace').split())}")
    return result.stdout.decode("utf-8").replace("\r\n", LF)


def run_notes(args):
    lines = git_show(args.repo, args.ref, CHANGELOG).split(LF)
    starts = [i for i, line in enumerate(lines) if line.startswith("## ") and f"[{args.release}]" in line]
    if len(starts) != 1:
        raise Refused(f"{CHANGELOG} at {args.ref} has {len(starts)} sections of release {args.release}, not 1")
    start = starts[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ") or LINK_LINE.match(lines[i])),
               len(lines))
    body = LF.join(lines[start:end]).strip(LF)
    say("SECTION", lines[starts[0]])
    try:
        args.output.write_bytes(f"## What's changed{LF}{LF}{args.lead}{LF}{LF}{body}{LF}".encode("utf-8"))
    except OSError as error:
        raise Stop(f"cannot write {args.output}: {error}") from error
    say("NOTES", f"{args.output}: {body.count(LF) + 1} lines of the section body")
    say("RESULT", "DONE. 1 file written")
    return 0


def parse_bump(value):
    folder, _, version = value.rpartition("=")
    folder = "/".join(part for part in folder.replace("\\", "/").split("/") if part not in ("", "."))
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
    shared.add_argument("--repo", type=Path, default=Path("."),
                        help="the top folder of the clone (default: .)")
    shared.add_argument("--release", type=parse_version, required=True, metavar="X.Y.Z", help="the release")
    section = commands.add_parser("section", parents=[shared], help="add the release section and the bumps")
    section.add_argument("--section-file", type=Path, required=True, metavar="FILE",
                         help="a file with the whole release section, heading first, with the real numbers")
    section.add_argument("--bump", action="append", type=parse_bump, required=True, metavar="FOLDER=X.Y.Z",
                         help="a plugin folder and its new version; give it once for each plugin of the heading")
    notes = commands.add_parser("notes", parents=[shared], help="write the notes of a GitHub release")
    notes.add_argument("--ref", default="origin/main", help="the commit to read CHANGELOG.md from (default: origin/main)")
    notes.add_argument("--lead", required=True, metavar="TEXT",
                       help="the sentences above the section body, for example the pull request and its issues")
    notes.add_argument("--output", type=Path, required=True, metavar="FILE", help="the file to write the notes to")
    args = parser.parse_args(argv)
    folders = [folder for folder, _ in getattr(args, "bump", [])]
    if len(set(folders)) != len(folders):
        parser.error("give each --bump folder once")
    return args


def main(argv=None):
    # A CHANGELOG line can hold any character. The reader takes the output as UTF-8, also on Windows.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args(argv)
    try:
        return run_section(args) if args.command == "section" else run_notes(args)
    except Stop as error:
        say("RESULT", f"ERROR. {error}")
        return 2
    except Refused as error:
        say("STOP", str(error))
        say("RESULT", "REFUSED. Nothing changed")
        return 3


if __name__ == "__main__":
    sys.exit(main())
