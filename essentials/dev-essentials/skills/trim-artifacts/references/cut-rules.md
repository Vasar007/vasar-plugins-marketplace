# Cut rules

Each cut in a plan names one row of the cut table as its reason.

## Cut table

| Reason | What it covers |
| --- | --- |
| History and narration | Changelogs, "History" sections, "what was done", dated round logs. Also "created in one pass", "since DATE" asides, "superseded by" chains, version-bump notes |
| Review and audit records | Review reports, audit reports, and every reference to them in other files, once their fixes live in the files |
| Process residue | "Fixed in review", "per audit", counts of findings, notes on which agent or model did what |
| Duplication | The same fact in an overview, a state file and a plan. Keep it in its owning file. Elsewhere, keep a pointer or nothing. |
| Audit-log bulk | Log rows that only repeat "OK" or a similar status for a claim whose source is already cited. Keep rows with a correction, an uncertainty marker, or the only citation of a claim. |
| Stale snapshots | Dated counts and states that the owning file recalculates, and "as of" lists that go stale |
| Long prose | Explanations where one table row or one sentence says the same thing |
| Filler | "Note that", hedges, bold lead-ins that repeat the heading, restatements of the previous sentence |

Tie-break: if you are not sure, keep the fact and cut its narration.

## Depth rules

Shallow plans that only remove headings and blank lines miss most of the cost. Plan to these depths.
These rules shorten wording in the substance tier. Each fact, source and uncertainty marker must stay. Byte-identical text does not shrink.

- Research notes: keep only the findings that a requirement, a direction, a recommendation, a risk or an open question uses. Write one or two lines each, with source URL and date.
- Plan and design files: write one statement per fact.
- Answered questions: shrink the row to one short line that names the answer, for example "Answered, see DEC-7". The id stays.
- Withdrawn items: shrink to a one-line tombstone. The id stays. Template:

  ```text
  {HEADING_MARK} {ID}: Withdrawn. {DATE}: {REASON}. See {POINTER}.
  ```

- Cited sections: if other files cite a section by number or title, keep its number and title. Otherwise the citations break.
- Sources: keep only the sources that kept lines cite.

## Row rules

- A requirement row is one short sentence. If the user declared the requirement word for word, keep it byte-identical. Otherwise it is in the substance tier, so keep its meaning.
- An open-question row has three parts: the question in one sentence, why it blocks in one clause, and the default in one clause.
- A risk is one row.
- A tool or technology choice keeps the chosen option and one row per rejected option.
- Remove audit-log rows that restate findings from the body.

## Byte targets

Targets give the share of current bytes that a file keeps. They are defaults. The user can override them per pass or per profile.
If a file ends above its target, the plan or the results file says why.
The script applies one global `--target-percent`. The reviewer judges the per-profile targets from the size table.

| Profile | Default target (bytes kept) |
| --- | --- |
| Research notes | 20 to 50 percent |
| Design and plan documents | 50 to 65 percent |
| State and handoff files | 40 to 60 percent |
| Agent-memory files | No fixed target. A lost rule costs more than a long line. |
| Logs and changelogs | 0 to 20 percent, or delete the file |
| Task and issue lists | 30 to 60 percent |
| Files that hold mostly protected text | Only the framing goes |
| Whole workspace | About 60 percent or less |

## What does not count as a cut

- Joining lines or removing line breaks. The bytes stay, and so does the token cost.
- Moving text to another file without removing a duplicate.
- Shortening a byte-identical block. That text stays unchanged, or it becomes an approved tombstone.
- Paraphrasing user text. Keep it verbatim, or remove it.
