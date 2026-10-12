# Structure checks

The orchestrator runs these checks between steps. They test the form of the report, not the
truth of the findings. When the check passes, each command prints nothing. The text names any exception. The commands need a POSIX shell with `grep`, `awk`, `sed`, `sort`, and `find`.

Set these variables first:

```bash
R="<absolute path of the report file>"
D="<absolute path of the report folder>"
S="<absolute path of the scratch folder>"
```

## Commands

C1. Number of findings (prints a number):

```bash
grep -c '^### BH-[0-9][0-9]*: ' "$R"
```

C2. Next free ID (prints for example `BH-08`):

```bash
grep -o '^### BH-[0-9][0-9]*' "$R" | sed 's/.*BH-//' | sort -n | tail -1 \
  | awk '{ printf "BH-%02d\n", $1 + 1 } END { if (NR == 0) print "BH-01" }'
```

C3. IDs are unique and have no gaps:

```bash
grep -o '^### BH-[0-9][0-9]*' "$R" | sed 's/.*BH-//' | sort -n \
  | awk '{ if ($1 + 0 != NR) { print "Gap or duplicate near BH-" $1; exit } }'
```

C4. Every finding has the required fields. Add `|Verification` to `req` after step 4:

```bash
awk -v req="Severity|Confidence|Category|Location|Also on base|Verdict|Problem|Failure scenario|Evidence|Fix idea" '
function check(   n, i, r) {
  n = split(req, r, "|")
  for (i = 1; i <= n; i++) if (index(seen, "|" r[i] "|") == 0) print id ": missing " r[i]
}
/^##/ { if (id != "") check(); id = ""; seen = "|" }
/^### BH-[0-9]+: / { id = $2; sub(/:$/, "", id) }
id != "" && match($0, /^(- )?[A-Z][a-z]+( [a-z]+)*: /) {
  label = substr($0, 1, RLENGTH - 2); sub(/^- /, "", label); seen = seen label "|"
}
END { if (id != "") check() }' "$R"
```

C5. Every verdict has a legal value:

```bash
grep '^- Verdict: ' "$R" | grep -vE '^- Verdict: (Pending verification|Confirmed|Unconfirmed \(needs owner review\)|Rejected|Duplicate of (#[0-9]+|BH-[0-9]+))$'
```

C6. No finding is still pending (after step 4, prints 0):

```bash
grep -c '^- Verdict: Pending verification' "$R"
```

C7. Rejected entries are in the appendix, and only they are:

```bash
awk '/^## Appendix: rejected findings/ { a = 1 }
/^- Verdict: Rejected/ && !a { print "Rejected entry outside the appendix, line " NR }
/^- Verdict: / && a && !/Rejected/ { print "Other verdict in the appendix, line " NR }' "$R"
```

C8. Each Unconfirmed finding has a "To decide:" line (prints two equal numbers):

```bash
grep -c '^- Verdict: Unconfirmed' "$R"; grep -c '^To decide: ' "$R"
```

C9. Every area section has its two subsections. When all areas are searched, the three numbers are equal:

```bash
grep -c '^## Area [0-9][0-9]*: ' "$R"
grep -c '^### New details for known issues' "$R"
grep -c '^### Notes for other areas' "$R"
```

C10. No placeholder is left (after step 5):

```bash
grep -nE '^Pending (search|verification|the first search)\.$|\{[A-Z_]+\}' "$R"
```

A hit inside quoted code in an entry, such as `${HOME}`, is not a defect.

C11. The Summary has a count line:

```bash
sed -n '/^## Summary/,/^## /p' "$R" | grep -c '^Findings: [0-9]'
```

C12. Every artifact link resolves, and every artifact folder has a `repro.md`:

```bash
grep -o 'bug-hunt-artifacts/BH-[0-9][0-9]*/[^]) (]*' "$R" | sort -u \
  | while read -r p; do [ -e "$D/$p" ] || echo "Missing $p"; done
for d in "$D"/bug-hunt-artifacts/BH-*/; do
  [ -d "$d" ] || continue; [ -f "$d/repro.md" ] || echo "No repro.md in $d"
done
```

C13. No progress file of a finished agent is left (prints the session progress file only, until step 6):

```bash
ls "$D"/_bug-hunt-* 2>/dev/null
```

## Which checks run after which step

| After | Checks | Pass when |
| --- | --- | --- |
| Step 1 | `$S/snapshot-ref` and `$S/known-issues.md` exist and are not empty. `$S/snapshot-base` exists, unless the analyzed commit is the base. C13. | All exist. C13 prints only `_bug-hunt-session-progress.md`. |
| Step 2 | `$R` exists. C9 shows one area heading for each area. | All match |
| Each hunter | C1, C3, C4, C5, C12, C13. The section of the area no longer says "Pending search.". After the first hunter, the Known issues section no longer says "Pending the first search.". | The other checks print nothing. C13 prints only `_bug-hunt-session-progress.md`. The counts match the reply. |
| Each verifier part | C4 with Verification, C5, C7, C8, C12, C13. C6 for the range of the part. After the last part, also C11. | The other checks print nothing. C6 prints 0. C8 prints two equal numbers. C13 prints only `_bug-hunt-session-progress.md`. The counts match the reply. |
| Step 5 | All checks C1 to C13. | The other checks print nothing. C6 prints 0. C8 prints two equal numbers. C9 prints three equal numbers. C11 prints 1. C13 prints only `_bug-hunt-session-progress.md`. |
| Step 6 | `$S` does not exist. C13 prints only `_bug-hunt-session-progress.md`. | All match |

To run C6 for one part, filter the entries of its range, for example with
`sed -n '/^### BH-01: /,/^### BH-21: /p' "$R" | grep -c '^- Verdict: Pending verification'`.
