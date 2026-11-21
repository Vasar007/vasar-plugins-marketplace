#!/usr/bin/env python3
"""Structure checks and the snapshot and cleanup steps of a bug hunt. Uses only the standard library.

The checks test the form of the report and the files around it. They do not
judge whether a finding is true. Each problem prints one line:

  DEFECT: a structure error. A repair dispatch fixes it.
  WARN:   a fact for the orchestrator. It does not fail the check.
  INFO:   counts to compare with the reply of the agent.

Exit codes: 0 = no defect, 1 = at least one defect, 2 = usage error.

Commands:
  setup       --report-dir D --scratch S --base yes|no [--allow NAME]
  report      --report R --scratch S --areas-done K --stage STAGE
              [--verified-to N] [--base yes|no] [--allow NAME]
              [--snapshot S/snapshot-ref] [--base-snapshot S/snapshot-base]
  next-id     --report R
  open-notes  --report R
  cleanup     --report-dir D --scratch S
  snapshot    --repo REPO --ref-sha SHA --scratch S --base-from local|remote|none
              [--base-sha SHA] [--base-branch NAME] [--base-url URL]
  delete-temp --report-dir D --scratch S --repo REPO [--pid PID=STARTED]... [--apply]

STAGE is search (after a hunter), verify (after a verifier part, with
--verified-to set to the number of the last ID of the part, for example 20
for BH-20), summary (after the last verifier part), or final (after the
auditor).

snapshot exports the commit SHA of REPO into S/snapshot-ref with git archive,
and makes S/work and S/tools. It writes the marker file S/.bug-hunt-scratch,
which delete-temp needs. S must be missing, empty, or hold the marker and
only the names of a run. The base goes into S/snapshot-base: an export of
--base-sha for local, a shallow clone of --base-branch from --base-url for
remote, and nothing for none or for a local base with the same SHA. Each
snapshot holds the bytes of the commit, whatever core.autocrlf says. Against
REPO, it runs only git rev-parse, ls-tree, show, and archive. Output lines:
SNAPSHOT (a snapshot and its counts), LIMIT (content that a snapshot does not
hold), WARN, and ERROR. Exit codes: 0 = done, 1 = a git command or the
extraction failed, 2 = usage error or REFUSED, and nothing was created.

delete-temp deletes the folder S and each regular file D/_bug-hunt-progress-*.md.
S must be an absolute path and hold the marker file of snapshot. An empty S
with no marker also passes, because it holds nothing to lose. The delete
removes the marker last, so a later run can finish a failed delete. First it
stops each --pid process whose start time and command line match. Then it
waits up to 5 seconds for the end of each process. Without --apply, it
prints WOULD STOP and WOULD DELETE lines and changes nothing. Each guard
refuses the whole run before any change: a REFUSED line names the reason.
With --apply, it runs the cleanup check at the end. Exit codes: 0 = done or
the plan is ready, 1 = a delete failed or the cleanup check gives a DEFECT,
2 = usage error or REFUSED, and nothing changed.

snapshot and delete-temp share the guards of the place of S. They refuse a
link or a junction, a drive root, a mount point, the home folder, the temp
root, and each folder of REPO and its worktrees.

Known limits. git archive has no time limit. So in a partial clone with a
remote that does not answer, snapshot waits with no output. No guard can see
a repository outside S that borrows objects from a repository in S (git clone
--shared or --reference). The delete breaks that repository. An empty folder
passes the content guards, so delete-temp deletes any empty folder that passes
the place guards. On Windows, a network path such as //host/share gets past
the guards of the report folder, the home folder, the temp root, and REPO.
The marker rule still refuses a folder that snapshot did not make.

The output of snapshot and delete-temp has at most 40 lines, and the last one
gives the count of the lines that it leaves out. The exit code still holds
the whole result.
"""
import argparse
import contextlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

SESSION_FILE = "_bug-hunt-session-progress.md"
KNOWN = "Known issues that this report does not repeat"
APPENDIX = "Appendix: rejected findings"
SEVERITY = "Critical|High|Medium|Low"
CONFIDENCE = "High|Medium|Low"
VERDICT = re.compile(
    r"^(Pending verification|Confirmed|Unconfirmed \(needs owner review\)|Rejected"
    r"|Duplicate of (#\d+|N-\d+|BH-\d+))$")
LABEL = re.compile(r"^(?:- )?([A-Z][a-z]+(?: (?:[a-z]+|I))*):(?: |$)")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
COUNTS = re.compile(
    r"^Findings: (\d+)\.(?: Confirmed: (\d+)\. Unconfirmed \(needs owner review\): (\d+)\."
    r" Rejected: (\d+)\. Duplicate: (\d+)\.)?$", re.M)
MAX_ARTIFACT_BYTES = 1024 * 1024
MAX_LINES = 40
LINE_CHARS = 300
# The report check prints at most this many DEFECT lines, so that a broken report does not flood the Bash tool.
MAX_DEFECTS = 100
LOCATION = re.compile(r"`([^`]+?):(\d+)(?:-(\d+))?`")
FULL_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
PROGRESS_GLOB = "_bug-hunt-progress-*.md"
# The entries that a run makes at the top of the scratch folder. delete-temp refuses a folder with others.
SCRATCH_MARKER = ".bug-hunt-scratch"
SCRATCH_NAMES = ("snapshot-ref", "snapshot-base", "work", "tools", "known-issues.md", SCRATCH_MARKER)
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "LC_ALL": "C", "LANGUAGE": "C"}
# The line ends of the commit, on each system. A .gitattributes rule of the commit still applies.
PLAIN_LINE_ENDS = ("-c", "core.autocrlf=false", "-c", "core.eol=lf")
GIT_SECONDS = 300
# Below the limit of 10 minutes of the Bash tool. On POSIX, a clone that hangs stops here with an ERROR line.
# On Windows, a git helper keeps the pipes open, so the Bash tool ends the call first, with no ERROR line.
CLONE_SECONDS = 540
STOP_SECONDS = 5

problems = []


class Refused(Exception):
    """A reason to change nothing. The command prints a REFUSED line and returns exit code 2."""


def defect(text):
    problems.append(text)
    if len(problems) <= MAX_DEFECTS:
        print("DEFECT: " + text)


def read(path):
    data = Path(path).read_bytes().decode("utf-8-sig", errors="replace")
    return data.replace("\r\n", "\n")


def drive_forms(path):
    """A path in both slash styles and both drive styles."""
    forms = set()
    base = str(path).rstrip("/\\")
    for p in (base, base.replace("\\", "/")):
        forms.add(p)
        forms.add(p.replace("/", "\\"))
        m = re.match(r"^([A-Za-z]):[/\\](.*)$", p)
        if m:
            forms.add("/" + m.group(1).lower() + "/" + m.group(2).replace("\\", "/"))
        m = re.match(r"^/([A-Za-z])/(.*)$", p)
        if m:
            rest = m.group(2)
            forms.add(m.group(1).upper() + ":/" + rest)
            forms.add(m.group(1).upper() + ":\\" + rest.replace("/", "\\"))
    return {f.lower() for f in forms}


def path_forms(scratch):
    """The scratch path as agents can write it. Includes the Git Bash /tmp mount form."""
    forms = drive_forms(scratch)
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp and len(temp) > 3:
        for t in {f.replace("\\", "/") for f in drive_forms(temp)}:
            for f in list(forms):
                norm = f.replace("\\", "/")
                if norm.startswith(t + "/"):
                    forms.add("/tmp" + norm[len(t):])
    return {f for f in forms if len(f) > 3}


def left_progress_files(report_dir, allow):
    """The names of the progress files in report_dir, without the session file and the allowed names."""
    allowed = {SESSION_FILE, *allow}
    return [p.name for p in sorted(Path(report_dir).glob("_bug-hunt-*")) if p.name not in allowed]


def progress_files(report_dir, allow):
    for name in left_progress_files(report_dir, allow):
        defect(f"progress file left: {name}")


def leftovers(scratch):
    work = Path(scratch) / "work"
    if work.is_dir():
        for d in sorted(work.iterdir()):
            if d.is_dir() and any(d.iterdir()):
                print(f"WARN: files left in work folder {d.name}")
    forms = path_forms(scratch)
    records = list_processes()
    if records is None:
        print("WARN: cannot list processes")
        return
    own = own_chain(records)
    for pid, _, started, cmdline in records:
        low = cmdline.lower()
        if pid in own or "check_report.py" in low:
            continue
        if names_folder(cmdline, forms):
            print(f"WARN: process uses the scratch folder: pid={pid} started={started} "
                  f"command={cmdline.strip()[:200]}")


def names_folder(cmdline, forms):
    """True if the command line holds a path form, and the path name ends there: /tmp/run is not in /tmp/run-2."""
    low = cmdline.lower()
    return any(re.search(re.escape(form) + r"(?=$|[\\/\s\"'])", low) for form in forms)


def own_chain(records):
    """The ID of this process and of each process above it in the records."""
    parent = {pid: ppid for pid, ppid, _, _ in records}
    own = set()
    pid = os.getpid()
    while pid in parent and pid not in own:
        own.add(pid)
        pid = parent[pid]
    own.add(os.getpid())
    return own


def list_processes():
    """Return (pid, parent pid, start time, command line) for each process, or None.

    Each record is one line: newlines inside a command line become spaces.
    """
    try:
        if os.name == "nt":
            script = (
                "Get-CimInstance Win32_Process | ForEach-Object { "
                "$s = if ($_.CreationDate) { $_.CreationDate.ToString('s') } else { '' }; "
                "$c = [string]$_.CommandLine -replace '[\\r\\n]+', ' '; "
                "\"$($_.ProcessId)`t$($_.ParentProcessId)`t$s`t$c\" }")
            cmd = ["powershell.exe", "-NoProfile", "-Command", script]
        else:
            cmd = ["ps", "-eo", "pid=,ppid=,lstart=,args="]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    records = []
    for line in done.stdout.splitlines():
        if os.name == "nt":
            parts = line.split("\t", 3)
            ok = len(parts) == 4 and parts[0].strip().isdigit() and parts[1].strip().isdigit()
            if ok:
                records.append((int(parts[0]), int(parts[1]), parts[2].strip(), parts[3]))
        else:
            parts = line.split(None, 7)
            if len(parts) == 8 and parts[0].isdigit() and parts[1].isdigit():
                records.append((int(parts[0]), int(parts[1]), " ".join(parts[2:7]), parts[7]))
    return records


def fenced(text):
    """Yield each line with True when it is part of a fenced code block, as CommonMark reads it."""
    fence, marker = False, ""
    for line in text.split("\n"):
        opener = re.match(r"^ {0,3}(```|~~~)(.*)$", line)
        if not fence and opener and not (opener.group(1) == "```" and "`" in opener.group(2)):
            fence, marker = True, opener.group(1)
            yield line, True
            continue
        if fence and re.match(r"^ {0,3}" + re.escape(marker) + r"\s*$", line):
            fence = False
            yield line, True
            continue
        yield line, fence


def sections(text):
    """Split the report into H2 sections. Lines in fenced code blocks are not headings."""
    result, name, body = [], None, []
    for n, (line, fence) in enumerate(fenced(text), 1):
        if not fence and line.startswith("## "):
            if name is not None:
                result.append((name, body))
            name, body = line[3:].strip(), []
            continue
        if name is not None:
            body.append((n, line, fence))
    if name is not None:
        result.append((name, body))
    return result


def body_text(body):
    return "\n".join(line for _, line, _ in body).strip()


def entries(secs):
    """Yield (id, title, section name, lines, raw id) for each BH entry."""
    for name, body in secs:
        cur = None
        for n, line, fence in body:
            m = None if fence else re.match(r"^### BH-(\d+): (.+)$", line)
            if m or (not fence and line.startswith("### ")):
                if cur:
                    yield cur
                cur = (int(m.group(1)), m.group(2).strip(), name, [], m.group(1)) if m else None
                continue
            if cur:
                cur[3].append(line)
        if cur:
            yield cur


def open_notes(secs):
    notes = []
    for name, body in secs:
        m = re.match(r"^Area (\d+): ", name)
        if not m:
            continue
        area, inside = int(m.group(1)), False
        for n, line, fence in body:
            if fence:
                continue
            if line.startswith("### "):
                inside = line.startswith("### Notes for other areas")
                continue
            nm = re.match(r"^- For Area (\d+)\b", line)
            if inside and nm and int(nm.group(1)) <= area and "Result:" not in line:
                notes.append((int(nm.group(1)), area, n, line.strip()))
    return notes


def first_value(value):
    """The value of a field or a cell without its old value: 'Medium (was High)' gives 'Medium'."""
    return value.split(" (was ", 1)[0].strip()


def summary_values(summary, fields, base):
    """Each row of the Summary table has the severity, confidence, verdict, and base answer of its entry.

    A cell that is not a value of the format, such as N/A, gives no DEFECT. Only another value of the format gives one.
    """
    columns = [(3, "Severity", first_value, rf"^({SEVERITY})$"), (4, "Confidence", first_value, rf"^({CONFIDENCE})$"),
               (5, "Verdict", first_value, VERDICT.pattern)]
    if base:
        # Only the first word: the entry says "Yes, `path:line`", and the row says "Yes".
        columns.append((6, "Also on base", lambda value: (re.findall(r"[A-Za-z]+", value) or [""])[0], r"^(Yes|No|Not)$"))
    for line in summary.split("\n"):
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip())[1:]]
        # A row can end with no last |, so only an empty last piece goes.
        if cells and not cells[-1]:
            cells.pop()
        found = re.match(r"^BH-(\d+)$", cells[0]) if cells else None
        if not found or int(found.group(1)) not in fields:
            continue
        num, labels = int(found.group(1)), fields[int(found.group(1))]
        for index, label, key, legal in columns:
            if index >= len(cells) or label not in labels:
                continue
            cell = key(cells[index])
            if re.match(legal, cell) and cell != key(labels[label]):
                defect(f"BH-{num:02d}: Summary {label} '{cells[index]}' differs from the entry '{labels[label]}'")


def references(secs, fields, by_name, digest):
    """Each reference to an entry or a known issue names one that exists.

    An entry ID counts only where the format puts one, because prose can name an entry of an older report.
    """
    plain = [re.sub(r"`[^`\n]*`", "", line) for _, body in secs for _, line, fence in body if not fence]
    known = body_text(by_name.get(KNOWN, []))
    named = [(num, m.group(1)) for num, labels in fields.items()
             for m in [re.match(r"^Duplicate of (BH-\d+|N-\d+|#\d+)$", labels.get("Verdict", ""))] if m]
    for num, ref in named:
        if ref.startswith("BH-") and int(ref[3:]) >= num:
            defect(f"BH-{num:02d}: Duplicate of {ref} must name an earlier entry")
    ids = {int(ref[3:]) for _, ref in named if ref.startswith("BH-")}
    ids |= {int(x) for line in plain for tail in re.findall(r"\bResult: (.*)$", line)
            for x in re.findall(r"\bBH-(\d+)\b", tail)}
    ids |= {int(x) for line in plain for x in re.findall(r"\bNew details for BH-(\d+)\b", line)}
    review = False
    for _, line, fence in by_name.get("Summary", []):
        if not fence and line.startswith("### "):
            review = line.strip() == "### For the owner's review"
        elif review and not fence:
            ids |= {int(x) for x in re.findall(r"^- BH-(\d+)\b", re.sub(r"`[^`\n]*`", "", line))}
    for ref in sorted(ids - set(fields)):
        defect(f"the report names BH-{ref:02d}, but no entry has this ID")
    named += [(None, ref) for line in plain for ref in re.findall(r"\bNew details for (N-\d+|#\d+)\b", line)]
    named = list(dict.fromkeys(named))
    digest_text = read(digest) if digest.is_file() else None
    warned = False
    for num, ref in named:
        where = f"BH-{num:02d}: " if num else ""
        if ref.startswith("N-") and not re.search(rf"(?<![\w-]){ref}\b", known):
            defect(f"{where}{ref} is not in the Known issues section")
        if ref.startswith("#"):
            if digest_text is None:
                if not warned:
                    print(f"WARN: no known-issues digest at {digest}, so the check of #NN references did not run")
                warned = True
            elif not re.search(rf"(?<![\w#]){ref}\b", digest_text):
                defect(f"{where}{ref} is not in the known-issues digest")


def locations(bid, label, value, root):
    """Each path:line of the field names a file of the snapshot and a line inside it. A path out of it is never read."""
    for path, start, end in LOCATION.findall(value):
        path = path.strip()
        parts = path.replace("\\", "/").split("/")
        if path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path) or ".." in parts:
            defect(f"{bid}: {label} path leaves the snapshot: {path}")
            continue
        if re.search(r":\d+$", path) or int(start) < 1 or int(end or start) < int(start):
            form = f"{path}:{start}" + (f"-{end}" if end else "")
            defect(f"{bid}: {label} is not in the form path:line or path:line-line: {form}")
            continue
        file = Path(root) / path.replace("\\", "/")
        if not file.resolve().is_relative_to(Path(root).resolve()):
            defect(f"{bid}: {label} path leaves the snapshot through a link: {path}")
            continue
        if not file.is_file():
            defect(f"{bid}: {label} names a file that the snapshot does not hold: {path}")
            continue
        text = read(file)
        count = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        if int(end or start) > count:
            defect(f"{bid}: {label} line {end or start} is past the end of {path} ({count} lines)")


def check_report(a):
    r = Path(a.report)
    if not r.is_file():
        defect(f"report file missing: {r}")
        return
    text = read(r)
    report_dir = r.parent
    final = a.stage in ("summary", "final")
    verified_to = 10 ** 9 if final else (a.verified_to or 0)

    if not text.startswith("# Bug hunt report: "):
        defect("first line is not '# Bug hunt report: <project>'")
    for n, line in enumerate(text.split("\n"), 1):
        if CONTROL.search(line):
            defect(f"control character in the report, line {n}")
    secs = sections(text)
    names = [s[0] for s in secs]
    areas = [x for x in names if re.match(r"^Area \d+: ", x)]
    expected = ["Scope", "Summary", KNOWN] + [
        f"Area {i}: " for i in range(1, len(areas) + 1)] + [APPENDIX]
    got = [x if not x.startswith("Area ") else re.sub(r"^(Area \d+: ).*", r"\1", x) for x in names]
    if got != expected:
        defect("H2 sections missing or out of order: " + " | ".join(names))
    if not areas:
        defect("no area section")
    by_name = dict(secs)

    known = body_text(by_name.get(KNOWN, []))
    if a.areas_done >= 1 and known == "Pending the first search.":
        defect("Known issues section still pending")
    if a.areas_done == 0 and known != "Pending the first search.":
        defect("Known issues section filled before the first search")
    for name in areas:
        i = int(re.match(r"^Area (\d+)", name).group(1))
        body = body_text(by_name[name])
        if i <= a.areas_done:
            if body == "Pending search.":
                defect(f"Area {i} still pending")
            for sub in ("### New details for known issues", "### Notes for other areas"):
                if not re.search("^" + re.escape(sub) + "$", body, re.M):
                    defect(f"Area {i} has no '{sub[4:]}' subsection")
        elif body != "Pending search.":
            defect(f"Area {i} filled before its search")

    found = list(entries(secs))
    ids = sorted(e[0] for e in found)
    if ids != list(range(1, len(ids) + 1)):
        defect("IDs are not unique or not contiguous: " + ", ".join(f"BH-{i:02d}" for i in ids))
    required = ["Severity", "Confidence", "Category", "Location", "Verdict",
                "Problem", "Failure scenario", "Evidence", "Fix idea"]
    if a.base == "yes":
        required.insert(4, "Also on base")
    counts = {"Confirmed": 0, "Unconfirmed": 0, "Rejected": 0, "Duplicate": 0, "Pending": 0}
    titles, fields = {}, {}
    for num, title, sec, lines, raw in found:
        bid = f"BH-{raw}"
        titles[num] = title
        if len(raw) < 2:
            defect(f"{bid}: ID has fewer than two digits")
        labels = {}
        for line in lines:
            m = LABEL.match(line)
            if m:
                labels.setdefault(m.group(1), line[m.end():].strip())
        fields[num] = labels
        need = required + (["Verification"] if num <= verified_to else [])
        for lab in need:
            if lab not in labels:
                defect(f"{bid}: missing field '{lab}'")
        for lab in ("Severity", "Confidence", "Verdict"):
            if lab in labels and not labels[lab]:
                defect(f"{bid}: {lab} value is empty")
        sev, conf = labels.get("Severity", ""), labels.get("Confidence", "")
        if sev and not re.match(rf"^({SEVERITY})( \(was ({SEVERITY})\))?$", sev):
            defect(f"{bid}: Severity value '{sev}' is not legal")
        if conf and not re.match(rf"^({CONFIDENCE})( \(was ({CONFIDENCE})\))?$", conf):
            defect(f"{bid}: Confidence value '{conf}' is not legal")
        verdict = labels.get("Verdict", "")
        if verdict and not VERDICT.match(verdict):
            defect(f"{bid}: Verdict value '{verdict}' is not legal")
        key = verdict.split(" ")[0] if verdict else ""
        if key in counts:
            counts[key] += 1
        if key == "Pending" and num <= verified_to:
            defect(f"{bid}: verdict is still pending")
        if key == "Rejected" and sec != APPENDIX:
            defect(f"{bid}: Rejected entry outside the appendix")
        if sec == APPENDIX and key != "Rejected":
            defect(f"{bid}: entry in the appendix is not Rejected")
        if key == "Unconfirmed":
            for lab in ("Not covered", "Where I looked", "To decide"):
                if lab not in labels:
                    defect(f"{bid}: Unconfirmed entry has no '{lab}:' line")
        for link in re.findall(r"\((bug-hunt-artifacts/[^)\s]+)\)", "\n".join(lines)):
            if not (report_dir / link).exists():
                defect(f"{bid}: artifact link does not resolve: {link}")

    summary = body_text(by_name.get("Summary", []))
    if final:
        m = COUNTS.search(summary)
        if not m:
            defect("Summary has no count line in the format of report-format.md")
        else:
            nums = [int(x) if x else 0 for x in m.groups()]
            if nums[0] != len(found):
                defect(f"Summary says {nums[0]} findings, the report has {len(found)}")
            if len(found) and nums[1:] != [counts["Confirmed"], counts["Unconfirmed"],
                                           counts["Rejected"], counts["Duplicate"]]:
                defect("Summary verdict counts do not match the entries")
        rows = re.findall(r"^\| BH-(\d+) \| (.*?) \|", summary, re.M)
        if [int(x) for x, _ in rows] != ids:
            defect("Summary table rows do not match the IDs in ID order")
        for x, title in rows:
            if int(x) in titles and title.strip().replace("\\|", "|") != titles[int(x)]:
                defect(f"BH-{x}: Summary title differs from the heading")
        summary_values(summary, fields, a.base == "yes")
    references(secs, fields, by_name, Path(a.scratch) / "known-issues.md")
    for num, labels in sorted(fields.items()):
        if a.snapshot:
            locations(f"BH-{num:02d}", "Location", labels.get("Location", ""), a.snapshot)
        if a.base_snapshot and labels.get("Also on base", "").startswith("Yes"):
            locations(f"BH-{num:02d}", "Also on base", labels["Also on base"], a.base_snapshot)
    if a.stage == "final":
        appendix = [line.strip() for _, line, fence in by_name.get(APPENDIX, []) if not fence]
        if any(e[2] == APPENDIX for e in found) and "None yet." in appendix:
            defect("the appendix holds entries and still says 'None yet.'")
        if not re.search(r"^### For the owner's review$", summary, re.M):
            defect("Summary has no 'For the owner's review' subsection")
        plain = re.sub(r"`[^`\n]*`", "", "\n".join(line for line, fence in fenced(text) if not fence))
        for m in re.finditer(r"^Pending (search|verification|the first search)\.$|\{[A-Z0-9_]+\}",
                             plain, re.M):
            defect(f"placeholder left: {m.group(0)}")
        for area, src, n, line in open_notes(secs):
            defect(f"open note in Area {src}, line {n}, for Area {area}: no 'Result:'")

    art = report_dir / "bug-hunt-artifacts"
    folders = 0
    forms = path_forms(a.scratch)
    if art.is_dir():
        for d in sorted(art.iterdir()):
            if not d.is_dir():
                defect(f"file outside an entry folder in bug-hunt-artifacts: {d.name}")
                continue
            folders += 1
            m = re.match(r"^BH-(\d+)$", d.name)
            if not m or int(m.group(1)) not in titles:
                defect(f"artifact folder without an entry: {d.name}")
            if not (d / "repro.md").is_file():
                defect(f"no repro.md in {d.name}")
            for f in d.rglob("*"):
                rel = f.relative_to(art).as_posix()
                if f.is_dir():
                    if f.name.lower() in ("bin", "obj"):
                        defect(f"build output folder in artifacts: {rel}")
                    continue
                data = f.read_bytes()
                if len(data) > MAX_ARTIFACT_BYTES:
                    defect(f"artifact file larger than 1 MB: {rel}")
                if b"\x00" in data[:8192]:
                    defect(f"binary file in artifacts: {rel}")
                    continue
                txt = data.decode("utf-8", errors="replace")
                if any(form in txt.lower() for form in forms):
                    defect(f"scratch path in artifact file: {rel}")
                if f.suffix.lower() == ".md" and CONTROL.search(txt.replace("\r\n", "\n")):
                    defect(f"control character in {rel}")

    progress_files(report_dir, a.allow)
    leftovers(a.scratch)
    nxt = (max(ids) + 1) if ids else 1
    print(f"INFO: findings={len(found)} next=BH-{nxt:02d} confirmed={counts['Confirmed']} "
          f"unconfirmed={counts['Unconfirmed']} rejected={counts['Rejected']} "
          f"duplicate={counts['Duplicate']} pending={counts['Pending']} "
          f"artifact_folders={folders} open_notes={len(open_notes(secs))}")


class Output:
    """The output lines of snapshot and delete-temp: the urgent lines first, the LIMIT lines last, at most MAX_LINES."""

    URGENT = ("REFUSED", "ERROR", "FAILED", "DEFECT")

    def __init__(self):
        self.lines = []

    def add(self, line):
        if len(line) > LINE_CHARS:
            line = f"{line[:LINE_CHARS]} ... {len(line) - LINE_CHARS} more characters"
        self.lines.append(line)

    def flush(self):
        def rank(line):
            return 0 if line.startswith(self.URGENT) else 2 if line.startswith("LIMIT") else 1

        lines = sorted(self.lines, key=rank)
        if len(lines) > MAX_LINES:
            lines = lines[:MAX_LINES - 1] + [f"... {len(lines) - MAX_LINES + 1} more lines"]
        for line in lines:
            print(line)


def show(text):
    """The text for an output line. A text with a character that is not printable becomes a JSON string."""
    text = str(text)
    return text if text.isprintable() else json.dumps(text)


def real(path):
    """The real path in a form that compares right, also on a file system with no case."""
    return os.path.normcase(os.path.realpath(str(path)))


def relation(path, other):
    """How path relates to other after links resolve: "is", "is inside", "holds", or None."""
    mine, theirs = real(path), real(other)
    if mine == theirs:
        return "is"
    try:
        common = os.path.commonpath([mine, theirs])
    except ValueError:  # Two drives on Windows.
        return None
    if common == theirs:
        return "is inside"
    return "holds" if common == mine else None


def is_link(path):
    """True for a symbolic link and for a Windows junction."""
    try:
        info = os.lstat(str(path))
    except OSError:
        return False
    junction = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", -1)  # Only Windows has this tag.
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) == junction


def git(cwd, *args, timeout=GIT_SECONDS):
    """Run git with no input and no prompt. Return the exit code, stdout, and the last 5 lines of stderr.

    After timeout seconds, git stops, and the call gives the exit code 124. On Windows, a git helper that still
    runs, such as git-remote-https, keeps the pipes open. Then the call returns only after the end of the helper.
    """
    try:
        done = subprocess.run(["git", "-C", str(cwd), *args], stdin=subprocess.DEVNULL, capture_output=True,
                              env=dict(os.environ, **GIT_ENV), timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", f"no result after {timeout} seconds"
    except OSError as error:
        return 127, "", str(error)
    err = done.stderr.decode("utf-8", "replace").strip().splitlines()
    return done.returncode, done.stdout.decode("utf-8", "surrogateescape"), " | ".join(err[-5:])


def repo_paths(repo):
    """The folders of a repository: its path, its git folders, and each worktree. Raise Refused if git cannot read it.

    It runs only git rev-parse, and it reads the worktree list from the files of the git folder.
    """
    code, out, err = git(repo, "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir",
                         "--is-bare-repository")
    lines = out.splitlines()
    if code != 0 or len(lines) != 3:
        raise Refused(f"git cannot read the repository {show(repo)}: {err or 'no git folder'}")
    git_dir, common, bare = Path(lines[0]), Path(lines[1]), lines[2] == "true"
    paths = [Path(repo), git_dir, common]
    if not bare:
        code, out, err = git(repo, "rev-parse", "--path-format=absolute", "--show-toplevel")
        if code != 0:
            raise Refused(f"git cannot find the work tree of {show(repo)}: {err}")
        paths.append(Path(out.strip()))
    if common.name == ".git":
        paths.append(common.parent)  # The main worktree.
    try:
        paths += linked_worktrees(common)
    except OSError as error:
        raise Refused(f"the script cannot read the worktree list in {show(common / 'worktrees')}: {error}")
    return paths


def linked_worktrees(common):
    """The folder of each linked worktree that the git folder common lists. Raise OSError if it cannot read the list."""
    found = []
    worktrees = Path(common) / "worktrees"
    for entry in sorted(worktrees.iterdir()) if worktrees.is_dir() else []:
        gitdir = entry / "gitdir"
        if gitdir.is_file():
            target = gitdir.read_text(encoding="utf-8", errors="surrogateescape").strip()
            if target:
                # The file names the .git file of the worktree. A relative path starts at the folder of the file.
                found.append(Path(os.path.normpath(os.path.join(str(entry), target))).parent)
    return found


def repo_reasons(scratch, repo):
    """The reasons to refuse a scratch folder that is, holds, or is inside a folder of the repository."""
    try:
        paths = repo_paths(repo)
    except Refused as error:
        return list(error.args)
    reasons, seen = [], set()
    for path in paths:
        found = relation(scratch, path)
        if found and real(path) not in seen:
            seen.add(real(path))
            reasons.append(f"the scratch folder {found} the repository folder {show(path)}")
    return reasons


def tracked(cwd, sha, side, out):
    """The paths that git lists in the commit sha, or None after an ERROR line."""
    code, text, err = git(cwd, "ls-tree", "-r", "-z", "--name-only", sha)
    if code != 0:
        out.add(f"ERROR: git ls-tree of the {side} commit {sha}: {err}")
        return None
    return [name for name in text.split("\0") if name]


def count_files(folder):
    """The count of files and links in folder, without a .git folder at its top."""
    count = 0
    for top, dirs, files in os.walk(str(folder)):
        if top == str(folder) and ".git" in dirs:
            dirs.remove(".git")
        links = [name for name in dirs if is_link(os.path.join(top, name))]
        count += len(files) + len(links)
        dirs[:] = [name for name in dirs if name not in links]
    return count


def report_snapshot(side, folder, cwd, sha, out, extra="", clone=False):
    """Print the SNAPSHOT line, a WARN line for a count that differs from git, and the LIMIT lines. Return False on a git error."""
    names = tracked(cwd, sha, side, out)
    if names is None:
        return False
    files = count_files(folder)
    out.add(f"SNAPSHOT: {side} {show(folder)}{extra} files={files} git={len(names)}")
    if files != len(names):
        out.add(f"WARN: the {side} snapshot has {files} files, and git lists {len(names)}. An export-ignore rule, "
                "a submodule, or a link that the snapshot left out can explain it. So can file names that differ "
                "only by case, on a file system that ignores case")
    if ".gitmodules" in names:
        out.add(f"LIMIT: {side} snapshot: the commit has submodules (.gitmodules). The snapshot holds no submodule "
                "content")
    found = {"export-ignore": 0, "filter=lfs": 0}
    for name in names:
        if name != ".gitattributes" and not name.endswith("/.gitattributes"):
            continue
        code, text, err = git(cwd, "show", f"{sha}:{name}")
        if code != 0:
            out.add(f"WARN: git cannot show {show(name)} of the {side} commit: {err}")
            continue
        for line in text.splitlines():
            words = line.split()
            if words and not words[0].startswith("#"):
                for key in found:
                    found[key] += key in words[1:]
    if found["export-ignore"] and clone:
        out.add(f"LIMIT: {side} snapshot: export-ignore in .gitattributes ({found['export-ignore']} patterns). The "
                "base is a clone and holds the files that they match. A git archive export, such as the ref snapshot, "
                "leaves them out")
    elif found["export-ignore"]:
        out.add(f"LIMIT: {side} snapshot: export-ignore in .gitattributes ({found['export-ignore']} patterns). "
                "git archive leaves out the files that they match")
    if found["filter=lfs"]:
        out.add(f"LIMIT: {side} snapshot: filter=lfs in .gitattributes ({found['filter=lfs']} patterns). The "
                "snapshot holds Git LFS pointer files, not their content")
    return True


def can_link(folder):
    """True if this process can make a symbolic link in folder. Windows needs a right for it."""
    probe = os.path.join(str(folder), ".bug-hunt-link-probe")
    try:
        os.symlink("target", probe)
    except (OSError, NotImplementedError):
        return False
    os.unlink(probe)
    return True


def export(repo, sha, dest, side, out):
    """Extract git archive of sha into dest. Each member goes through the data filter of tarfile. Return True if it worked."""
    code, text, _ = git(repo, "ls-tree", "-r", "-z", "--name-only", sha)
    if code == 0 and not text.strip("\0"):
        return True  # tarfile cannot read the archive of a commit with no files.
    with tempfile.TemporaryFile() as errors:
        try:
            proc = subprocess.Popen(["git", "-C", str(repo), *PLAIN_LINE_ENDS, "archive", "--format=tar", sha],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errors,
                                    env=dict(os.environ, **GIT_ENV))
        except OSError as error:
            out.add(f"ERROR: git archive of the {side} commit {sha}: {error}")
            return False
        failed = None
        links = can_link(dest)
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
                for member in tar:
                    if member.issym() and not links:
                        # Else tarfile copies the target of the link, and the copy seeks back in the stream.
                        out.add(f"LIMIT: {side} snapshot: {show(member.name)} is not in the snapshot: this system "
                                "cannot make a symbolic link here")
                        continue
                    if not member.isdir() and os.path.lexists(os.path.join(str(dest), member.name)):
                        out.add(f"LIMIT: {side} snapshot: {show(member.name)} is not in the snapshot: another path "
                                "of the commit has the same name on this file system")
                        continue
                    try:
                        tar.extract(member, str(dest), filter="data")
                    except tarfile.FilterError as error:
                        out.add(f"LIMIT: {side} snapshot: {show(member.name)} is not in the snapshot: {error}")
        except (tarfile.TarError, OSError) as error:
            failed = error
        finally:
            if failed is None:
                # tarfile stops at the first end block. git still writes the rest of its last record.
                with contextlib.suppress(OSError):
                    while proc.stdout.read(65536):
                        pass
            proc.stdout.close()
            code = proc.wait()
        errors.seek(0)
        err = errors.read().decode("utf-8", "replace").strip().splitlines()
    if code != 0:
        out.add(f"ERROR: git archive of the {side} commit {sha}: {' | '.join(err[-5:])}")
    if failed is not None:
        out.add(f"ERROR: the extraction of the {side} snapshot failed: {failed}")
    return code == 0 and failed is None


def make_snapshots(a, out):
    """The subcommand snapshot. Return the exit code, or raise Refused before anything is created."""
    scratch = Path(a.scratch)
    reasons = []
    if not hasattr(tarfile, "data_filter"):
        reasons.append("the tarfile module of this Python has no data filter. Use Python 3.12 or later")
    for flag, value in (("--ref-sha", a.ref_sha), ("--base-sha", a.base_sha)):
        if value is not None and not FULL_SHA.match(value.lower()):
            reasons.append(f"{flag} is not a full commit SHA: {show(value)}")
    if a.base_from == "local" and a.base_sha is None:
        reasons.append("--base-from local needs --base-sha")
    if a.base_from == "remote" and not (a.base_branch and a.base_url):
        reasons.append("--base-from remote needs --base-branch and --base-url")
    reasons += place_reasons(scratch) + repo_reasons(scratch, a.repo)
    marker = scratch / SCRATCH_MARKER
    if not reasons and scratch.is_dir():
        names = os.listdir(str(scratch))
        if names and SCRATCH_MARKER not in names:
            reasons.append(f"the scratch folder {show(scratch)} is not empty and has no {SCRATCH_MARKER} file. "
                           "Use a new scratch folder")
        extra = [name for name in sorted(names) if name not in SCRATCH_NAMES]
        if extra and SCRATCH_MARKER in names:
            reasons.append(f"the scratch folder holds entries that a bug hunt does not make: "
                           f"{', '.join(show(name) for name in extra[:5])}. Use a new scratch folder")
        if os.path.lexists(marker) and not stat.S_ISREG(os.lstat(str(marker)).st_mode):
            reasons.append(f"{show(marker)} is not a regular file")
        for name in ("snapshot-ref", "snapshot-base"):
            folder = scratch / name
            if os.path.lexists(folder) and (is_link(folder) or not folder.is_dir() or any(folder.iterdir())):
                reasons.append(f"{show(folder)} exists and is not an empty folder. Use a new scratch folder")
    if reasons:
        raise Refused(*reasons)
    ref_sha = a.ref_sha.lower()
    base_sha = a.base_sha.lower() if a.base_sha else None
    local_base = a.base_from == "local" and base_sha != ref_sha
    for sha in [ref_sha] + ([base_sha] if local_base else []):
        code, _, err = git(a.repo, "rev-parse", "--verify", f"{sha}^{{commit}}")
        if code != 0:
            out.add(f"ERROR: git rev-parse --verify {sha}: {err}")
            return 1
    scratch.mkdir(parents=True, exist_ok=True)
    if not os.path.lexists(marker):
        # An exclusive create: a marker that is a hard link keeps the text of its other name.
        with open(marker, "x", encoding="utf-8") as file:
            file.write("made by check_report.py snapshot\n")
    for name in ("snapshot-ref", "work", "tools"):
        (scratch / name).mkdir(parents=True, exist_ok=True)
    ref = scratch / "snapshot-ref"
    if not (export(a.repo, ref_sha, ref, "ref", out) and report_snapshot("ref", ref, a.repo, ref_sha, out)):
        return 1
    base = scratch / "snapshot-base"
    if local_base:
        base.mkdir(exist_ok=True)
        done = export(a.repo, base_sha, base, "base", out)
        return 0 if done and report_snapshot("base", base, a.repo, base_sha, out, f" sha={base_sha}") else 1
    if a.base_from == "remote":
        # The clone runs in the current folder, so a relative URL means what it means to the caller.
        code, _, err = git(".", "clone", "-c", "core.longpaths=true", *PLAIN_LINE_ENDS, "--depth", "1",
                           "--single-branch", f"--branch={a.base_branch}", "--", a.base_url,
                           os.path.abspath(str(base)), timeout=CLONE_SECONDS)
        if code != 0:
            out.add(f"ERROR: git clone of the base branch {show(a.base_branch)}: {err}")
            return 1
        code, sha, err = git(base, "rev-parse", "HEAD")
        if code != 0:
            out.add(f"ERROR: git rev-parse HEAD in the cloned base: {err}")
            return 1
        sha = sha.strip()
        return 0 if report_snapshot("base", base, base, sha, out, f" sha={sha}", clone=True) else 1
    reason = "the analyzed commit is the base" if a.base_from == "local" else "no base comparison"
    out.add(f"SNAPSHOT: base none ({reason})")
    return 0


def homes():
    """Each form of the home folder that the environment names."""
    found = [os.environ.get("HOME"), os.environ.get("USERPROFILE"), os.path.expanduser("~")]
    return [path for path in dict.fromkeys(found) if path and path != "~"]


def mount_points(table="/proc/self/mountinfo"):
    """The mount points that the mount table of Linux lists, or an empty list on another system."""
    try:
        with open(table, encoding="utf-8", errors="surrogateescape") as file:
            lines = file.read().splitlines()
    except OSError:
        return []
    # Field 5 is the mount point. The file writes a space, a tab, a line break, and a backslash as \NNN.
    return [re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), line.split(" ")[4])
            for line in lines if len(line.split(" ")) > 4]


def place_reasons(scratch, report_dir=None):
    """The reasons to refuse the place of a scratch folder: a link, a root, a mount, home, temp, or the report folder."""
    reasons = []
    if report_dir is not None and not report_dir.is_dir():
        reasons.append(f"the report folder {show(report_dir)} is not a folder")
    if is_link(scratch):
        reasons.append(f"the scratch folder {show(scratch)} is a link or a junction. Give the real folder")
    elif os.path.lexists(scratch) and not scratch.is_dir():
        reasons.append(f"the scratch folder {show(scratch)} is not a folder")
    found = relation(scratch, report_dir) if report_dir is not None else None
    if found:
        reasons.append(f"the scratch folder {found} the report folder {show(report_dir)}")
    resolved = Path(os.path.realpath(str(scratch)))
    if resolved.parent == resolved or os.path.ismount(str(resolved)):
        reasons.append(f"the scratch folder {show(scratch)} is a drive root or a mount point")
    # os.path.ismount does not see a bind mount of the same file system, but the mount table lists it.
    mine = real(scratch)
    points = [point for point in mount_points()
              if os.path.normcase(point) == mine or os.path.normcase(point).startswith(mine.rstrip(os.sep) + os.sep)]
    if points:
        more = f" and {len(points) - 1} more" if len(points) > 1 else ""
        reasons.append(f"the scratch folder is or holds the mount point {show(points[0])}{more}")
    for name, folder in [("home folder", home) for home in homes()] + [("temp root", tempfile.gettempdir())]:
        found = relation(scratch, folder)
        if found in ("is", "holds"):
            reasons.append(f"the scratch folder {found} the {name} {show(folder)}")
    return reasons


def git_folder(dotgit):
    """The git folder that a .git file names, or None if the file names none."""
    try:
        first = dotgit.read_text(encoding="utf-8", errors="surrogateescape").splitlines()[:1]
    except OSError:
        return None
    found = re.match(r"^gitdir: (.+)$", first[0].strip()) if first else None
    return Path(os.path.join(str(dotgit.parent), found.group(1))) if found else None


def git_folder_reasons(folder, scratch):
    """The reasons to refuse a git folder in the scratch folder whose work tree or a linked worktree is outside it."""
    config = str(folder / "config")
    # git reads the quotes and the escapes of the file. A value with # or ; has quotes.
    _, worktree, _ = git(".", "config", "--file", config, "--get", "core.worktree")
    _, bare, _ = git(".", "config", "--file", config, "--bool", "--get", "core.bare")
    worktree = worktree.rstrip("\r\n")
    if worktree:
        trees = [Path(os.path.normpath(os.path.join(str(folder), worktree)))]
    elif bare.strip() == "true":
        trees = []
    elif folder.name == ".git":
        trees = [folder.parent]
    else:
        trees = [None]  # For example a git init --separate-git-dir: the work tree is not written down.
    try:
        trees += linked_worktrees(folder)
    except OSError as error:
        return [f"the script cannot read the worktree list of the git folder {show(folder)}: {error}"]
    return [f"the git folder {show(folder)} has its work tree outside the scratch folder, or no known work tree. "
            "The delete loses its commits. Move it out first" if tree is None else
            f"the git folder {show(folder)} has the worktree {show(tree)} outside the scratch folder. The delete "
            "loses its commits. Move it out first"
            for tree in trees if tree is None or relation(tree, scratch) != "is inside"]


def content_reasons(scratch):
    """The reasons to refuse what a scratch folder holds: names that a run does not make, or git data outside it."""
    try:
        names = sorted(os.listdir(str(scratch)))
    except OSError as error:
        return [f"the script cannot list the scratch folder {show(scratch)}: {error}"]
    extra = [name for name in names if name not in SCRATCH_NAMES]
    reasons = []
    if extra:
        more = f" and {len(extra) - 5} more" if len(extra) > 5 else ""
        reasons.append(f"the scratch folder holds entries that a bug hunt does not make: "
                       f"{', '.join(show(name) for name in extra[:5])}{more}. It can be the wrong folder")
    marker = scratch / SCRATCH_MARKER
    if not names:
        return reasons  # An empty folder holds nothing to lose. A delete that failed at its last step leaves one.
    if not os.path.lexists(marker) or not stat.S_ISREG(os.lstat(str(marker)).st_mode):
        # The snapshot command did not make this folder, so a walk of a large wrong folder has no use.
        reasons.append(f"the scratch folder has no {SCRATCH_MARKER} file, so the snapshot command did not make it. "
                       "It can be the wrong folder")
        return reasons
    unread = []
    for top, dirs, files in os.walk(str(scratch), onerror=lambda error: unread.append(error.filename)):
        dotgit = Path(top) / ".git"
        if ".git" in files and not is_link(dotgit):
            target = git_folder(dotgit)
            if target is None or relation(target, scratch) != "is inside":
                reasons.append(f"the folder {show(top)} is a worktree or a repository whose git folder is outside the "
                               "scratch folder. The delete loses its changes. Move it out first")
        if os.path.isfile(os.path.join(top, "HEAD")) and "objects" in dirs:
            reasons += git_folder_reasons(Path(top), scratch)
        # os.walk follows a Windows junction, so skip each link and each junction here.
        dirs[:] = [name for name in dirs if not is_link(os.path.join(top, name))]
    for folder in unread:
        reasons.append(f"the script cannot read the folder {show(folder)}, so it cannot look for a worktree in it")
    return reasons


def pid_value(text):
    """An argparse type: PID=STARTED, as the WARN line of a structure check names them."""
    found = re.match(r"^(\d+)=(.+)$", text)
    if not found:
        raise argparse.ArgumentTypeError(f"not PID=STARTED: {show(text)}")
    return int(found.group(1)), found.group(2)


def processes_to_stop(a, out):
    """The process IDs that pass all tests: the process runs, has the start time, and names the scratch folder."""
    if not a.pid:
        return []
    records = list_processes()
    if records is None:
        for pid, _ in a.pid:
            out.add(f"NOT STOPPED: pid={pid}: the script cannot list the processes")
        return []
    own = own_chain(records)
    forms = path_forms(os.path.abspath(a.scratch)) | path_forms(os.path.realpath(a.scratch))
    found = {pid: (started, cmdline) for pid, _, started, cmdline in records}
    stops = []
    for pid, started in a.pid:
        if pid not in found:
            out.add(f"NOT RUNNING: pid={pid}")
        elif pid in own:
            out.add(f"NOT STOPPED: pid={pid}: the process runs this script")
        elif found[pid][0].split() != started.split():
            out.add(f"NOT STOPPED: pid={pid}: it started at {show(found[pid][0])}, not at {show(started)}. "
                    "Another process has this ID now")
        elif not names_folder(found[pid][1], forms):
            out.add(f"NOT STOPPED: pid={pid}: its command line does not name the scratch folder")
        else:
            stops.append(pid)
    return stops


def ended(pid):
    """True if the process is gone, or is a zombie that waits for its parent."""
    if os.name == "nt":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE: the right to wait for the end.
        if not handle:
            return ctypes.get_last_error() == 87  # ERROR_INVALID_PARAMETER: no process has this ID.
        try:
            return kernel.WaitForSingleObject(ctypes.c_void_p(handle), 0) == 0
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        done = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode != 0 or done.stdout.strip().startswith("Z")


def stop(pid, out):
    """Stop one process with taskkill /F on Windows or SIGTERM on POSIX. Then wait up to STOP_SECONDS for its end."""
    if os.name == "nt":
        try:
            done = subprocess.run(["taskkill", "/PID", str(pid), "/F"], stdin=subprocess.DEVNULL, capture_output=True,
                                  text=True, errors="replace", timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            out.add(f"NOT STOPPED: pid={pid}: {error}")
            return
        if done.returncode != 0:
            lines = (done.stdout + done.stderr).strip().splitlines()
            out.add(f"NOT STOPPED: pid={pid}: taskkill: {lines[-1] if lines else done.returncode}")
            return
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            out.add(f"NOT RUNNING: pid={pid}")
            return
        except OSError as error:
            out.add(f"NOT STOPPED: pid={pid}: {error}")
            return
    deadline = time.monotonic() + STOP_SECONDS
    while not ended(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    out.add(f"STOPPED: pid={pid}" if ended(pid) else
            f"NOT STOPPED: pid={pid}: it still runs {STOP_SECONDS} seconds after the stop signal")


def delete_tree(path, base=None):
    """Delete a folder, and return the errors. A link inside goes as a link. A read-only file of Windows becomes writable first.

    Each error names its path relative to base, or to path without base, so the reason stays in a short line.
    """
    errors = []

    def retry(function, target, error):
        if os.name == "nt":
            try:
                os.chmod(target, stat.S_IWRITE)
                function(target)
                return
            except OSError as again:
                error = again
        relative = os.path.relpath(target, base or str(path))
        name = "the folder itself" if relative == "." else show(relative)
        errors.append(f"{name}: {error if isinstance(error, BaseException) else error[1]}")

    def remove():
        errors.clear()
        if sys.version_info >= (3, 12):
            shutil.rmtree(str(path), onexc=retry)
        else:
            shutil.rmtree(str(path), onerror=retry)

    remove()
    if errors and os.name != "nt" and not is_link(path):
        # On POSIX, a folder with no write right keeps its files. The module cache of Go has such folders.
        with contextlib.suppress(OSError):
            os.chmod(str(path), stat.S_IRWXU)
        for top, dirs, _ in os.walk(str(path)):
            for name in dirs:
                if not is_link(os.path.join(top, name)):
                    with contextlib.suppress(OSError):
                        os.chmod(os.path.join(top, name), stat.S_IRWXU)
        remove()
    return errors


def delete_run_folder(path):
    """Delete the scratch folder with its marker last, so that a run after a failed delete still passes the guards."""
    def delete_entries():
        errors = []
        for name in sorted(os.listdir(path)):
            if name != SCRATCH_MARKER:
                full = os.path.join(path, name)
                if os.path.isdir(full) and not is_link(full):
                    errors += delete_tree(full, base=path)
                else:
                    try:
                        os.unlink(full)
                    except OSError as error:
                        errors.append(f"{show(name)}: {error}")
        return errors

    errors = delete_entries()
    if errors:
        # The retry of delete_tree for the top level: a scratch folder with no write right, or a read-only file of Windows.
        with contextlib.suppress(OSError):
            os.chmod(path, stat.S_IRWXU)
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.name == "nt" and os.path.isfile(full) and not is_link(full):
                with contextlib.suppress(OSError):
                    os.chmod(full, stat.S_IWRITE)
        errors = delete_entries()
    return errors or delete_tree(path)


def delete_targets(a, out):
    """The subcommand delete-temp. Return the exit code, or raise Refused before anything changes."""
    if not Path(a.scratch).is_absolute():
        raise Refused(f"the scratch folder must be an absolute path: {show(a.scratch)}")
    scratch, report_dir = Path(a.scratch), Path(a.report_dir)
    target = os.path.realpath(str(scratch))  # The guards test this path, and the delete takes it and no other.
    reasons = place_reasons(scratch, report_dir) + repo_reasons(scratch, a.repo)
    if not reasons and scratch.is_dir():
        reasons += content_reasons(scratch)  # Only for a safe place: a walk of a home folder takes long.
    if reasons:
        raise Refused(*reasons)
    files = []
    for path in sorted(report_dir.glob(PROGRESS_GLOB)):
        if stat.S_ISREG(os.lstat(str(path)).st_mode):
            files.append(path)
        else:
            out.add(f"WARN: {show(path)} is not a regular file. The script does not delete it")
    stops = processes_to_stop(a, out)
    if not a.apply:
        for pid in stops:
            out.add(f"WOULD STOP: pid={pid}")
        for path in ([scratch] if os.path.lexists(scratch) else []) + files:
            out.add(f"WOULD DELETE: {show(path)}")
        if not os.path.lexists(scratch):
            out.add(f"NOT FOUND: {show(scratch)}")
        return 0
    for pid in stops:
        stop(pid, out)
    failed = False
    if not os.path.lexists(scratch):
        out.add(f"NOT FOUND: {show(scratch)}")
    elif is_link(scratch) or os.path.realpath(str(scratch)) != target:
        failed = True
        out.add(f"FAILED: {show(scratch)}: the path changed after the guards, so the script deleted nothing in it")
    else:
        errors = delete_run_folder(target)
        failed = os.path.lexists(scratch)
        if failed:
            more = f" (and {len(errors) - 1} more errors)" if len(errors) > 1 else ""
            out.add(f"FAILED: {show(scratch)}: {errors[0] if errors else 'the folder is still there'}{more}")
        else:
            out.add(f"DELETED: {show(scratch)}")
    for path in files:
        try:
            path.unlink()
        except FileNotFoundError:
            out.add(f"NOT FOUND: {show(path)}")
        except OSError as error:
            failed = True
            out.add(f"FAILED: {show(path)}: {error}")
        else:
            out.add(f"DELETED: {show(path)}")
    left = ([f"DEFECT: scratch folder still exists: {show(scratch)}"] if os.path.lexists(scratch) else []) + [
        f"DEFECT: progress file left: {show(name)}" for name in left_progress_files(report_dir, [])]
    for line in left:
        out.add(line)
    return 1 if failed or left else 0


def snapshot_value(text):
    """An argparse type: a snapshot folder that exists. Else each location gets a DEFECT line with a wrong cause."""
    if not text.strip() or not Path(text).is_dir():
        raise argparse.ArgumentTypeError(f"not a folder: {text!r}")
    return text


def folder_value(text):
    """An argparse type: a path that is not empty. An empty path means the current folder to pathlib."""
    if not text.strip():
        raise argparse.ArgumentTypeError("the path is empty")
    return text


def run_guarded(command, a):
    """Run snapshot or delete-temp, print the output, and return the exit code."""
    out = Output()
    try:
        code = command(a, out)
    except Refused as error:
        for reason in error.args:
            out.add(f"REFUSED: {reason}")
        out.add("REFUSED: nothing changed")
        code = 2
    except OSError as error:
        out.add(f"ERROR: {type(error).__name__}: {error}")
        code = 1
    out.flush()
    return code


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup")
    s.add_argument("--report-dir", required=True)
    s.add_argument("--scratch", required=True)
    s.add_argument("--base", choices=("yes", "no"), required=True)
    s.add_argument("--allow", action="append", default=[])
    r = sub.add_parser("report")
    r.add_argument("--report", required=True)
    r.add_argument("--scratch", required=True)
    r.add_argument("--areas-done", type=int, required=True)
    r.add_argument("--stage", choices=("search", "verify", "summary", "final"), required=True)
    r.add_argument("--verified-to", type=int, default=0)
    r.add_argument("--base", choices=("yes", "no"), default="yes")
    r.add_argument("--allow", action="append", default=[])
    r.add_argument("--snapshot", type=snapshot_value,
                   help="the ref snapshot: each Location must name a file and a line of it")
    r.add_argument("--base-snapshot", type=snapshot_value,
                   help="the base snapshot: each 'Also on base: Yes' location must name a file and a line of it")
    for name in ("next-id", "open-notes"):
        sub.add_parser(name).add_argument("--report", required=True)
    c = sub.add_parser("cleanup")
    c.add_argument("--report-dir", required=True)
    c.add_argument("--scratch", required=True)
    n = sub.add_parser("snapshot", allow_abbrev=False, description=(
        "Export the analyzed commit, and its base, into the scratch folder, and write the marker file "
        f"{SCRATCH_MARKER} there. Exit codes: 0 = done, 1 = a git command or the extraction failed, "
        "2 = usage error or REFUSED, and nothing was created."))
    n.add_argument("--repo", required=True, type=folder_value, help="the repository. The command only reads it")
    n.add_argument("--ref-sha", required=True, help="the full SHA of the analyzed commit")
    n.add_argument("--scratch", required=True, type=folder_value,
                   help="the scratch folder, outside the repository: missing, empty, or with the marker file "
                        "and only the names of a run")
    n.add_argument("--base-from", choices=("local", "remote", "none"), required=True,
                   help="the source of the base: a commit of the repository, a branch of a remote, or no base")
    n.add_argument("--base-sha", help="the full SHA of the base commit, for --base-from local")
    n.add_argument("--base-branch", help="the branch to clone, for --base-from remote")
    n.add_argument("--base-url", help="the URL to clone from, for --base-from remote")
    t = sub.add_parser("delete-temp", allow_abbrev=False, description=(
        "Stop the --pid processes, and delete the scratch folder and each file _bug-hunt-progress-*.md of the "
        "report folder. Exit codes: 0 = done, or the plan is ready, 1 = a delete failed or a file is left, "
        "2 = usage error or REFUSED, and nothing changed."))
    t.add_argument("--report-dir", required=True, type=folder_value, help="the report folder. The report stays")
    t.add_argument("--scratch", required=True, type=folder_value,
                   help=f"the scratch folder to delete: an absolute path that holds the marker file {SCRATCH_MARKER}, "
                        "or an empty folder")
    t.add_argument("--repo", required=True, type=folder_value,
                   help="the repository. A scratch folder that meets one of its folders is refused")
    t.add_argument("--pid", type=pid_value, action="append", default=[], metavar="PID=STARTED",
                   help="a process to stop first, with the start time that its WARN line gave. Repeat the option")
    t.add_argument("--apply", action="store_true", help="stop and delete. Without it, nothing changes")
    a = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):  # A path with a character that the console code page lacks.
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

    if a.cmd == "snapshot":
        return run_guarded(make_snapshots, a)
    if a.cmd == "delete-temp":
        return run_guarded(delete_targets, a)
    if a.cmd == "setup":
        need = ["snapshot-ref"] + (["snapshot-base"] if a.base == "yes" else [])
        for d in need:
            path = Path(a.scratch) / d
            if not path.is_dir() or not any(path.iterdir()):
                defect(f"snapshot missing or empty: {path}")
        digest = Path(a.scratch) / "known-issues.md"
        if not digest.is_file() or digest.stat().st_size == 0:
            defect(f"known-issues digest missing or empty: {digest}")
        progress_files(a.report_dir, a.allow)
    elif a.cmd == "report":
        check_report(a)
    elif a.cmd == "next-id":
        ids = [e[0] for e in entries(sections(read(a.report)))]
        print(f"BH-{(max(ids) + 1) if ids else 1:02d}")
    elif a.cmd == "open-notes":
        for area, src, n, line in open_notes(sections(read(a.report))):
            print(f"For Area {area} (written in Area {src}, line {n}): {line}")
    elif a.cmd == "cleanup":
        if Path(a.scratch).exists():
            defect(f"scratch folder still exists: {a.scratch}")
        progress_files(a.report_dir, [])
    if len(problems) > MAX_DEFECTS:
        print(f"DEFECT: more defects that this output does not show: {len(problems) - MAX_DEFECTS}. "
              "Fix the defects above, then run the check again")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
