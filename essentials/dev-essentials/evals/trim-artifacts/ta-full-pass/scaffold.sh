#!/usr/bin/env bash
set -euo pipefail

# The notes of a small order export tool: 12 Markdown files in notes/. Two passages are planted cuts: the History
# section of decisions.md and the review notes of requirements.md. The session log in notes/archive/ is the only file
# of its folder, and README.md cites it. The decision blocks and the ids must survive the pass.
lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"

fixture_init

fixture_write notes/README.md <<'EOF'
# Notes of the order export tool

- decisions.md: the decisions in force.
- requirements.md: the requirements REQ-1 to REQ-6.
- open-questions.md: the open questions with their defaults.
- risks.md: the risks.
- plan.md: the milestones.
- tools.md: the chosen tools.
- interfaces.md: the inputs and the outputs.
- research-cache.md: the research on the cache file.
- handoff.md: the state and the next step.
- glossary.md: the terms.
- archive/session-log-2026-10.md: the session log of October.
EOF

fixture_write notes/decisions.md <<'EOF'
# Decisions

This file holds the decisions in force for the order export tool.

## History

On Monday the team first tried a Redis cache for the export queue. The trial ran for two days. Then the team dropped
it, because the export host has no network access to a cache server. Later a review round asked for a file cache, and
the team agreed. This section records how the team reached the decisions below.

## DEC-1

Quote: "Exports must work with no network."
Decision: The export runs on the local host and writes CSV files only.

## DEC-2

Quote: "Keep a cache of the last export."
Decision: The tool keeps one file cache of the last export in the folder cache/.

## DEC-3

Quote: "Do not delete old exports by hand."
Decision: A nightly job deletes the exports that are older than 30 days.
EOF

fixture_write notes/requirements.md <<'EOF'
# Requirements

- REQ-1: The tool exports each order of the day to one CSV file.
- REQ-2: Each CSV file has a header row.
- REQ-3: The export finishes in less than 10 minutes for 50,000 orders.
- REQ-4: The tool writes a log line for each export, with the count of orders.
- REQ-5: A failed export leaves no partial CSV file.
- REQ-6: The user can run the export again for one day.

## Review round notes

Review round 1 found 4 issues in this list, and the fixer agent closed all of them. Review round 2 found no issue.
The reviewer used the strong model, and the fixer used the cheap model. These notes stay here until the next trim.
EOF

fixture_write notes/open-questions.md <<'EOF'
# Open questions

- Q-1: Which time zone names the day of an export? It blocks REQ-1. Default: UTC.
- Q-2: Does the CSV file use a comma or a semicolon? It blocks REQ-2. Default: a comma. (unverified: the finance
  team named both in the kickoff call)
- Q-3: Do refunds go into the same file? It blocks REQ-1. Default: yes, as negative rows. (unverified)

## Search notes

We searched the old wiki for the time zone rule on 2026-10-04 and again on 2026-10-05, and we found nothing. We also
asked in the team chat. Nobody answered.
EOF

fixture_write notes/risks.md <<'EOF'
# Risks

- RISK-1: The export host runs out of disk space. Mitigation: the nightly job of DEC-3.
- RISK-2: A slow database query breaks REQ-3. Mitigation: an index on the order date.
- RISK-3: A partial file reaches the finance share. Mitigation: write to a temporary name, then rename (REQ-5).

Status of this list as of 2026-10-03: 3 risks open, 0 closed. The count was 2 on 2026-09-28.
EOF

fixture_write notes/plan.md <<'EOF'
# Plan

- M-1: The CSV writer with a header row. Done.
- M-2: The export command for one day. In progress.
- M-3: The nightly cleanup job. Not started.
- M-4: The run-again command (REQ-6). Not started.

Update 2026-10-02: M-2 was first planned for the week of 2026-09-21. It moved to the week of 2026-09-28, and then to
the week of 2026-10-05. This update supersedes the update of 2026-09-25, which superseded the plan of 2026-09-14.
EOF

fixture_write notes/tools.md <<'EOF'
# Tools

- CSV: the module csv of the Python standard library. Source: https://docs.python.org/3/library/csv.html, read on
  2026-10-01.
- Scheduler: cron on the export host. Rejected: a systemd timer, because the image of the host has no systemd.

Note that we looked at three CSV libraries before this choice. We read their docs pages one by one, and we compared
the speed of each one on a test file of 10,000 rows. The standard module was fast enough, so we kept it.
EOF

fixture_write notes/interfaces.md <<'EOF'
# Interfaces

- Input: the orders table of the shop database, read only.
- Output: one CSV file for each day in exports/, with the name orders-YYYY-MM-DD.csv.
- Log: one line for each export in logs/export.log.

The team first wrote this list on 2026-09-15. It rewrote the list on 2026-09-20, after a talk with the owner of the
database. The old list had two more outputs, and the team dropped them.
EOF

fixture_write notes/research-cache.md <<'EOF'
# Research: the cache file

- Finding: a JSON file of 2 MB loads in about 40 ms on the export host. Source: a test run on 2026-10-06. (unverified
  on the final host)
- Finding: a pickle file loads faster, but a new Python version can fail to read it. Source:
  https://docs.python.org/3/library/pickle.html, read on 2026-10-06.

Search narration: first I searched for "python file cache". Then I searched for "json vs pickle speed". Then I read
four blog posts. Two of them were old, and I did not use them.
EOF

fixture_write notes/handoff.md <<'EOF'
# Handoff

Current state: M-1 is done, and M-2 is in progress.
Next step: finish the export command of M-2, then start M-3.

Decisions in force (a copy of decisions.md): the export runs on the local host and writes CSV files only. The tool
keeps one file cache of the last export in the folder cache/. A nightly job deletes the exports that are older than
30 days.

What was done this week: I read the code, I ran the tests two times, I fixed a typo in the README, and I updated this
file.
EOF

fixture_write notes/glossary.md <<'EOF'
# Glossary

- Export: one run of the tool for one day.
- Export host: the server that runs the tool.
- Cache: the file of the last export in cache/ (DEC-2).
EOF

fixture_write notes/archive/session-log-2026-10.md <<'EOF'
# Session log, October

- 2026-10-01: Session 1. Read the requirements. Wrote REQ-1 to REQ-6 into requirements.md.
- 2026-10-02: Session 2. Planned the milestones in plan.md. Moved M-2 again.
- 2026-10-03: Session 3. Wrote the risks into risks.md.
- 2026-10-04: Session 4. Searched the wiki for the time zone rule. Found nothing.
- 2026-10-05: Session 5. Asked the team about the CSV separator. No answer.
- 2026-10-06: Session 6. Tested the JSON cache file. It loads in about 40 ms.
EOF

fixture_commit "the notes of the order export tool"
