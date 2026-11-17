# Plan template

The planner writes one plan file per batch, at the path that the dispatch gives. The planner applies it to its `target` copy, and step 6 copies that copy into the workspace with no judgment. So every cut must be exact.

## File section (one per file of the batch)

````markdown
## {RELATIVE_PATH}

- Profile: {PROFILE}
- Action: keep | trim | delete | merge into {OTHER_FILE}
- Bytes: {BYTES_NOW} now, {BYTES_AFTER} expected ({PERCENT} percent kept)
- Above target because: {REASON, or "n/a"}

### Cuts

1. Anchor: `{SHORT VERBATIM QUOTE OF THE START OF THE PASSAGE}`
   - End: `{SHORT VERBATIM QUOTE OF THE END}`, or "end of section", or "end of line"
   - Operation: delete | replace with the text below | shrink to one line
   - Reason: {ROW OF THE CUT TABLE}
   - Replacement:

     ```text
     {EXACT NEW TEXT, including any corrected count}
     ```

### Cross-file fixes

- {OTHER_FILE}: anchor `{QUOTE}`, replace with `{TEXT}` (the reference pointed at a deleted or moved passage)
````

Rules for anchors:

- Quote the start of the passage verbatim, with enough words to match the file once.
- If a cut changes a count that the text states, the replacement gives the corrected count.
- If a passage is cited from another file, list the citation as a cross-file fix.

## Batch summary (end of the plan)

```markdown
## Deletions

| File | Reason |
| --- | --- |
| {RELATIVE_PATH} | {ONE LINE} |

## Tombstones

| File | Protected item | Regex for PATH:FIRST_LINE | Reason |
| --- | --- | --- | --- |
| {RELATIVE_PATH} | {ID} | {REGEX} | {ONE LINE} |

## Sizes

| File | Bytes before | Bytes after | Percent | What was cut |
| --- | ---: | ---: | ---: | --- |
| **Total** | {SUM} | {SUM} | {PERCENT} | |
```

The tombstone regex matches the string `{RELATIVE_PATH}:{FIRST LINE OF THE BLOCK}`. For one file, write for example `^notes/decisions\.md:## DEC-3\b`. Do not end it with `$`, so that it also matches the tombstone heading.

## Anchor proof

Each anchor and each end quote must match its file exactly once. Put them in a tab-separated file with the relative path, a tab, and the quote. Then run:

```bash
python3 -I - WORKSPACE anchors.tsv <<'EOF'
import sys
from pathlib import Path
root, bad = Path(sys.argv[1]), 0
for row in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    if not row.strip():
        continue
    path, quote = row.split("\t", 1)
    count = (root / path).read_text(encoding="utf-8").count(quote)
    if count != 1:
        bad += 1
        print(f"{count} matches: {path}: {quote}")
print(f"{bad} anchors fail")
sys.exit(1 if bad else 0)
EOF
```

If an anchor fails, lengthen the quote. Repeat until it matches once.
