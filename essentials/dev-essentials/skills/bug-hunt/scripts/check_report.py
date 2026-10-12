#!/usr/bin/env python3
"""Structure checks for a bug hunt report. Uses only the standard library.

The checks test the form of the report and the files around it. They do not
judge whether a finding is true. Each problem prints one line:

  DEFECT: a structure error. A repair dispatch fixes it.
  WARN:   a fact for the orchestrator. It does not fail the check.
  INFO:   counts to compare with the reply of the agent.

Exit codes: 0 = no defect, 1 = at least one defect, 2 = usage error.

Commands:
  setup      --report-dir D --scratch S --base yes|no [--allow NAME]
  report     --report R --scratch S --areas-done K --stage STAGE
             [--verified-to N] [--base yes|no] [--allow NAME]
  next-id    --report R
  open-notes --report R
  cleanup    --report-dir D --scratch S

STAGE is search (after a hunter), verify (after a verifier part, with
--verified-to set to the number of the last ID of the part, for example 20
for BH-20), summary (after the last verifier part), or final (after the
auditor).
"""
import argparse
import os
import re
import subprocess
import sys
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

problems = []


def defect(text):
    problems.append(text)
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


def progress_files(report_dir, allow):
    allowed = {SESSION_FILE, *allow}
    for p in sorted(Path(report_dir).glob("_bug-hunt-*")):
        if p.name not in allowed:
            defect(f"progress file left: {p.name}")


def leftovers(scratch):
    work = Path(scratch) / "work"
    if work.is_dir():
        for d in sorted(work.iterdir()):
            if d.is_dir() and any(d.iterdir()):
                print(f"WARN: files left in work folder {d.name}")
    forms = path_forms(scratch)
    records = list_processes()
    if records is None:
        print("WARN: could not list processes")
        return
    parent = {pid: ppid for pid, ppid, _, _ in records}
    own = set()
    pid = os.getpid()
    while pid in parent and pid not in own:
        own.add(pid)
        pid = parent[pid]
    own.add(os.getpid())
    for pid, _, started, cmdline in records:
        low = cmdline.lower()
        if pid in own or "check_report.py" in low:
            continue
        if any(f in low for f in forms):
            print(f"WARN: process uses the scratch folder: pid={pid} started={started} "
                  f"command={cmdline.strip()[:200]}")


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
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    records = []
    for line in out.splitlines():
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


def sections(text):
    """Split the report into H2 sections. Lines in fenced code blocks are not headings."""
    result, name, body, fence, marker = [], None, [], False, ""
    for n, line in enumerate(text.split("\n"), 1):
        if not fence and (line.startswith("```") or line.startswith("~~~")):
            fence, marker = True, line[:3]
        elif fence and line.startswith(marker):
            fence = False
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
            if line.startswith("### "):
                inside = line.startswith("### Notes for other areas")
                continue
            nm = re.match(r"^- For Area (\d+)\b", line)
            if inside and nm and int(nm.group(1)) <= area and "Result:" not in line:
                notes.append((int(nm.group(1)), area, n, line.strip()))
    return notes


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
    titles = {}
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
    if a.stage == "final":
        if not re.search(r"^### For the owner's review$", summary, re.M):
            defect("Summary has no 'For the owner's review' subsection")
        plain = re.sub(r"`[^`\n]*`", "", re.sub(r"```.*?```", "", text, flags=re.S))
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
    for name in ("next-id", "open-notes"):
        sub.add_parser(name).add_argument("--report", required=True)
    c = sub.add_parser("cleanup")
    c.add_argument("--report-dir", required=True)
    c.add_argument("--scratch", required=True)
    a = p.parse_args()

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
        ids = [int(x) for x in re.findall(r"^### BH-(\d+): ", read(a.report), re.M)]
        print(f"BH-{(max(ids) + 1) if ids else 1:02d}")
    elif a.cmd == "open-notes":
        for area, src, n, line in open_notes(sections(read(a.report))):
            print(f"For Area {area} (written in Area {src}, line {n}): {line}")
    elif a.cmd == "cleanup":
        if Path(a.scratch).exists():
            defect(f"scratch folder still exists: {a.scratch}")
        progress_files(a.report_dir, [])
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
