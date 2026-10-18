# Worked example: audit of the bug-hunt skill

This is a real audit report of the skill `dev-essentials:bug-hunt`, written in step 1 of an earlier run. It keeps 7 of its 11 items in full. The Summary and the executor section still name all 11 items. Line numbers refer to the version of the skill at that time. Personal paths and the names of private notes are replaced with placeholders such as `<repo>` and `<notes>`. Use it as a model of the form only. If it differs from [../references/audit-report-format.md](../references/audit-report-format.md), for example in its sources, its section names, or its line ends, the format file wins.

Target: the `bug-hunt` skill and its three agents in `essentials/dev-essentials/` at the base commit. This audit proposes changes and a plan. It does not change any plugin file.

## Sources

Guideline set 1, skill-doctor and the official skill authoring guidance. I read these pages again on 2026-10-13:

- `/skill-doctor`: <https://code.claude.com/docs/en/skills#find-unused-skills>. It is a usage and cost report for the skill listing. Every listed skill "adds to your context on every turn". For this skill, the listing cost is the `description` (526 characters) and the three agent descriptions.
- Listing budget: <https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short> ("put the key use case first", 1,536-character cap for `description` plus `when_to_use`).
- Body cost: <https://code.claude.com/docs/en/skills#types-of-skill-content> ("Once a skill loads, its content stays in context across turns, so every line is a recurring token cost. State what to do rather than narrating how or why").
- Lifecycle: <https://code.claude.com/docs/en/skills#skill-content-lifecycle> ("re-attaches the most recent invocation of each skill after the summary, keeping the first 5,000 tokens of each").
- Troubleshooting: <https://code.claude.com/docs/en/skills#claude-stops-following-a-skill> ("put the most important instructions near the top of `SKILL.md`").
- Supporting files: <https://code.claude.com/docs/en/skills> ("Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files").
- Best practices: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>. Used: "Concise is key" ("Does this paragraph justify its token cost?") and "Pattern 3: Conditional details". Also used: "Avoid deeply nested references" (one level deep from `SKILL.md`), "Use consistent terminology", and "Name files descriptively". Also used: the Tip under "Conditional workflow pattern" ("consider pushing them into separate files and tell Claude to read the appropriate file").

Guideline set 2, `claude-md-management:claude-md-improver`: its `SKILL.md`, `references/quality-criteria.md`, and `references/update-guidelines.md` in the plugin cache. Criteria used: Conciseness ("Each line adds value", "No redundancy"), Actionability ("Steps are concrete"), Currency, the red flag "Duplicate info across multiple ... files", and the core principle that every line in the context window must earn its place. I did not run its write steps. I did not change any `CLAUDE.md`.

History: the earlier audit `<notes>/earlier-audit.md` (D-01 to D-14, applied in an earlier commit). No item below repeats or undoes a D item. O-02 keeps the D-11 resume list and moves it. O-05 keeps the D-07 progress-file text.

Token figures are estimates: characters divided by 4. Not proven: exact token counts. I did not run a tokenizer. Where I looked: `wc -c` and `wc -w` on the files, and on draft files in the session scratchpad.

## Summary

| ID | Title | Category | Estimated saving |
| --- | --- | --- | --- |
| O-01 | Step-0 material fills a third of `SKILL.md` | Tokens | ~5,270 characters, ~1,320 tokens of `SKILL.md` |
| O-02 | Resume check and failure handling load on every run | Tokens | ~2,380 characters, ~600 tokens of `SKILL.md` |
| O-03 | Two different restore paths for one stopped agent | Unclear | None |
| O-04 | "Less than 30 minutes old" can mean the creation time | Unclear | None |
| O-05 | Terms and rules 1, 2, 6, 7, and 8 restate or narrate | Tokens | ~840 characters, ~210 tokens of `SKILL.md` |
| O-06 | Steps 1, 3, 4, 5, and 6 restate the briefs and agent files | Tokens | ~955 characters, ~240 tokens of `SKILL.md` |
| O-07 | A research note in the meta-plan parts | Needless | ~180 characters, ~45 tokens |
| O-08 | The lint-hook paragraph goes into every brief | Tokens | ~600 characters for each dispatch, ~1,200 tokens for each default run (orchestrator) |
| O-09 | `--verified-to N` does not say that N is a number | Unclear | None |
| O-10 | Two reference files restate `SKILL.md` steps and the cleanup brief | Tokens | ~1,000 characters in files that the orchestrator reads |
| O-11 | "Delete only the paths that you recorded" reads as "delete nothing else" | Unclear | None |

No Frontmatter item. The skill `description` is 526 characters and starts with the key use case. The agent descriptions are short (D-01, D-02). The `argument-hint` does not go into the skill listing.

`SKILL.md` size:

| | Words | Characters | Rough tokens (characters / 4, estimate) |
| --- | --- | --- | --- |
| Now, whole file | 4,615 | 27,701 | ~6,925 |
| Now, body without frontmatter | 4,490 | 26,557 | ~6,640 |
| After the plan, whole file | ~2,950 | ~17,935 | ~4,480 |
| After the plan, body without frontmatter | ~2,830 | ~16,800 | ~4,200 |

The "after" values come from a full draft of the new file in the session scratchpad. They are estimates. Not proven: whether the re-attached part after compaction counts the frontmatter. The whole file is under 5,000 tokens at 4 characters for each token. If the real ratio is 3.6 characters for each token, the whole file is ~4,980 tokens and the body is ~4,670 tokens.

Why the size matters here: a default run has 5 hunters that each take 25 to 60 minutes (`pauses.md:20`). The orchestrator context compacts in most runs. Today, Claude Code keeps the first ~20,000 characters of `SKILL.md`. That cut falls inside step 4. So the run loses steps 5, 6, and 7 and "Failure handling" at the time it needs them. After the plan, every step survives compaction.

O-01 and O-02 move text. The orchestrator reads a moved file at the step that needs it. It reads the step-0 file once on every run, so O-01 does not make a fresh run cheaper. After step 0, the run no longer needs that detail, so it can drop at compaction. The resume and failure file is read only on a resume or a failure, so O-02 also saves tokens on a normal run.

## Items

### O-02: Resume check and failure handling load on every run

- Category: Tokens
- File:Line(s):
  - `SKILL.md:186-201` (Pause points, Resume check)
  - `SKILL.md:311-317` (Failure handling)
  - `SKILL.md:138-139` (rule 6, "The resume check in this file")
  - `SKILL.md:149` (rule 7, "the restore case in 'Failure handling'")
  - `references/pauses.md:36-47` (job prompt)
- Guideline: best practices, "Pattern 3: Conditional details". Its example loads a file such as REDLINING.md only for a user who needs that feature. skills#types-of-skill-content ("every line is a recurring token cost").
- Problem: The resume check (1,735 characters) and "Failure handling" (1,071 characters) apply only after a crash, a restart, a pause, or a failed check. On a normal run, nobody needs them, but they cost tokens for the whole run. "Failure handling" is the last section, so after compaction it is the first text that Claude Code drops. Rule 6 also says "The resume check in this file". "This file" can mean the progress file, which the same sentence names, or `SKILL.md`.
- Estimated saving: ~2,380 characters, ~600 tokens of `SKILL.md` on every run. The new file is ~2,800 characters, read only on a resume or a failure.
- Fix plan:
  1. Create `essentials/dev-essentials/skills/bug-hunt/references/resume-and-failures.md` with exactly this content (it already applies O-03 and O-04):

     ```markdown
     # Resume and failure handling

     The orchestrator reads this file in three cases: the report folder holds `_bug-hunt-session-progress.md` at the start, an agent stops or fails, or a structure check fails.

     ## Resume check

     1. Read `_bug-hunt-session-progress.md` and continue from its `## NEXT`. If it records the meta-plan approval, do not ask for it again. If `## NEXT` records a pause, do not continue. Wait for the user, or for the scheduled resume prompt that names this file.
     2. If a snapshot or the digest is missing, run step 1 again in full with the commit SHAs from the progress file. If the report already lists `N-NN` IDs, tell the collector to keep them. Then run the step-1 structure check.
     3. Write the scratch folder path that is now in use into the progress file before you fill the next brief.
     4. If `## NEXT` says "Waiting for agent <ID>", find out if that agent still runs. It runs when both of these are true: this session dispatched it, and its progress file changed in the last 30 minutes (the modification time, not the creation time). If the agent has no progress file yet, use the dispatch time in the note instead. If the agent runs, write one line to chat: "Waiting for agent <ID> (<role>). If it stopped, say so." Then end the turn. A scheduled resume prompt that fires while the agent runs ends here. In all other cases, the agent stopped, for example after a crash or a restart. The user can also say that it stopped, or the agent reply can report a crash or a usage limit. Then restore the agent as "Failure handling" says.
     5. If an agent progress file exists for the step in `## NEXT`, fill the brief for that role again from the recorded values. Add the resume note from [agent-briefs.md](agent-briefs.md), and dispatch the agent.

     ## Failure handling

     - To restore a stopped agent, send a message to its recorded agent ID with `SendMessage`. The agent continues with its full history. After a restart of Claude Code, the user must resume the same session for this to work. If the message fails, dispatch a new agent of the same role with the resume note. Use the same brief, or fill it again from the recorded values as point 5 of the resume check says. The new agent reads the progress file and continues.
     - If a structure check fails, dispatch one repair agent of the same role. Give it the same brief and the repair note with the list of defects. If the check fails again, stop the run. Keep all files, and report the defects under "Blocked on me".
     - If the collector cannot reach GitHub, ask the user what to do. The user can reconnect the GitHub MCP server with `/mcp` or continue with the notes files only. Do not fall back to another GitHub client.
     - If an agent reports a blocker, such as a missing snapshot, fix the cause with the right helper. Then dispatch the agent again.
     ```

  2. In `SKILL.md`, replace the two sections `### Pause points` and `### Resume check` (lines 186-201) with:

     ```markdown
     ### Pauses, resume, and failures

     After a step, an area, or a verifier part that is a pause point, stop as
     [references/pauses.md](references/pauses.md) says. If the user asks for a stop, a start time,
     or a resume time, read that file too.

     Before step 0, look for `_bug-hunt-session-progress.md` in the report folder. If the report
     folder becomes known only from a step-0 answer, look then, before you show the meta-plan
     again. If the file exists, follow "Resume check" in
     [references/resume-and-failures.md](references/resume-and-failures.md). If an agent stops or
     fails, or a structure check fails, follow "Failure handling" in the same file.
     ```

  3. In `SKILL.md`, delete the whole section `## Failure handling` (lines 311-317).
  4. Rule 6 and rule 7: O-05 replaces the sentences that point to these sections.
  5. In `references/pauses.md`, item 3 of "Scheduled resume and start" (lines 36-47): change the lead line "3. Write a self-contained prompt:" to "3. Write a self-contained prompt. Fill `<report folder>` and `<skill folder>` with absolute paths:". In the prompt text, replace "follow the resume check in the bug-hunt skill: the agent stopped, so restore it." with "follow \"Resume check\" in `<skill folder>/references/resume-and-failures.md`: the agent stopped, so restore it." Keep the rest of the prompt as it is.
- Risk: Low. The trigger for the resume check stays in `SKILL.md`, before step 0. A scheduled prompt now names the file by its absolute path. This is safer than "the bug-hunt skill", because after compaction the skill text can be gone.

### O-03: Two different restore paths for one stopped agent

- Category: Unclear
- File:Line(s): `SKILL.md:149` (rule 7), `:200` (resume check point 4), `:313-314` ("Failure handling" bullets 1 and 2)
- Guideline: claude-md-improver Actionability ("Steps are concrete"). Best practices, "Use consistent terminology". "Avoid offering too many options" ("Provide a default").
- Problem: Three texts give two answers for the same event.
  - Point 4: if the agent reply reports a crash or a usage limit, "restore the agent with `SendMessage` as 'Failure handling' says. If that fails, go to point 5."
  - "Failure handling" bullet 1: "If an agent stops on a usage limit or crashes, dispatch a new agent of the same role."
  - "Failure handling" bullet 2 and rule 7: `SendMessage` only "If the user asks to restore a stopped agent".

  Failure scenario: hunter 3 replies "stopped on a usage limit". Reader A follows point 4 and sends a message to the agent ID. Reader B follows bullet 1 and dispatches a new hunter, which reads all area files again on Fable at effort max. A scheduled resume prompt (`pauses.md:44`) reaches point 4. Point 4 points to bullet 2, and bullet 2 allows `SendMessage` only on a user request. The orchestrator cannot follow both texts.
- Estimated saving: None.
- Fix plan: Use one restore path: `SendMessage` first, then a new agent with the resume note. This is the path of the latest change (the base commit, fix plan in `<notes>/cycle-2-fix-plan.md:50`). The new text is in the O-02 file ("Failure handling" bullet 1, and the last sentence of point 4). Rule 7 gets the matching bullet in O-05: "Use `SendMessage` only to restore a stopped agent, as references/resume-and-failures.md says."
- Risk: Low. This changes one case: an agent reply that reports a crash in a normal run now gets a `SendMessage` restore first, not a new agent at once. If the message fails, the old path runs. The alternative is to keep a new agent as the default and to use `SendMessage` only on a user request. Then point 4 and the job prompt in `pauses.md` must change to "go to point 5". The feedback plan (`<notes>/feedback-plan.md`, section 8) had that alternative, and cycle 2 changed it. The user can pick the alternative before the executor runs.

### O-04: "Less than 30 minutes old" can mean the creation time

- Category: Unclear
- File:Line(s): `SKILL.md:200` against `references/pauses.md:40-42`
- Guideline: best practices, "Use consistent terminology". claude-md-improver Actionability.
- Problem: Point 4 uses this test for a running agent: "its progress file is less than 30 minutes old". The job prompt says "the progress file of that agent changed in the last 30 minutes". The fix plan of cycle 2 (`<notes>/cycle-2-fix-plan.md:50`) says "changed in the last 30 minutes". "Old" can mean the age since creation. Failure scenario: a hunter creates its progress file at 10:00 and updates it every few minutes. At 10:40, the user resumes the session, and point 4 runs. A reader who takes the creation time sees a 40-minute-old file and treats the running hunter as stopped. It then restores or dispatches a second hunter on the same area section.
- Estimated saving: None.
- Fix plan: The O-02 file uses "its progress file changed in the last 30 minutes (the modification time, not the creation time)". No other change.
- Risk: None. This is the test that the job prompt and the cycle-2 fix plan already describe.

### O-07: A research note in the meta-plan parts

- Category: Needless
- File:Line(s): `SKILL.md:213` (step 0, part 4)
- Guideline: skills#types-of-skill-content ("State what to do rather than narrating how or why"). Best practices, "Avoid time-sensitive information". claude-md-improver: "Verbose explanations". D-08 removed a similar version note.
- Problem: Part 4 ends with a "Not confirmed:" note about the behavior on versions older than v2.1.292. The note says that the author looked in the sub-agents docs page. That page gives only the minimum version of the per-call parameter. This is an author's research note. It gives the orchestrator no action, and the version number goes stale. If the `effort` parameter is missing, the sentence before it already tells the orchestrator what to say.
- Estimated saving: ~180 characters, ~45 tokens.
- Fix plan: Leave the sentence out of the new file for part 4. The O-01 file text already does this.
- Risk: None.

### O-08: The lint-hook paragraph goes into every brief

- Category: Tokens
- File:Line(s): `references/agent-briefs.md:81-91` (the installed plain-English block), `references/report-format.md:196-200` ("Words"), `agents/bug-report-auditor.md:56` (checklist point 13)
- Guideline: claude-md-improver red flag "Duplicate info across multiple ... files" and "every line must earn its place". The reasoning of D-03 (the orchestrator writes every brief as output, and every brief stays in its context).
- Problem: The installed plain-English block has 11 lines (~594 characters) about the lint hook. The orchestrator pastes it into the collector brief and into each hunter, verifier, and auditor brief. A default run has 8 copies (1 collector, 5 hunters, 1 verifier, 1 auditor), plus one for each resume or repair. The text is the same in each copy. The hunters, verifiers, and auditor all read `report-format.md` first, and its "Words" section already talks about the lint hook. The block also tells the auditor "Fix only the hits in your own lines". Auditor checklist point 13 says "Fix the document-wide hits of the lint hook that other agents left". The auditor reads both.
- Estimated saving: ~594 characters for each dispatch, ~4,750 characters (~1,190 tokens) of orchestrator context and output for each default run. The agents read the same text in `report-format.md`, so their input does not change.
- Fix plan:
  1. In `agent-briefs.md`, replace the code block under the heading of the installed plain-English block (lines 76-92) with:

     ```text
     Before you write any report text, load the skill simple-english:simple-english with the
     Skill tool and follow its document rules. Mark each claim that you did not confirm with
     "Not confirmed:" and say where you looked.
     ```

  2. In `report-format.md`, replace the section "## Words" (lines 196-200) with:

     ```markdown
     ## Words

     In report text, use `confirm` and `make sure that`. Do not use `check`, `verify`,
     `validate`, or `ensure`. The verdicts and the marker "Not confirmed:" already use `confirm`.

     If the simple-english plugin is installed, its lint hook lints the whole file after each
     Markdown edit. A hunter or a verifier fixes only the hits in its own lines, and lists the
     hits in other sections in its reply. The auditor fixes all hits. The hook reports these
     patterns:

     - A mix of "check", "checklist", "verify", "validate", "ensure", and "confirm" in one file.
     - An "if" or "when" clause after the main clause.
     - The words should, would, may, might, and could.
     - A quote that ends with a period inside the quote marks. The hook reads it as the end of a
       sentence.

     An edit by a script skips the hook, so read the result back.
     ```

- Risk: Low. The collector does not read `report-format.md`, so it loses the hook text. It writes only the digest in the scratch folder, which the report never links. If the hook reports hits in the digest, the collector can fix them, and nothing downstream depends on that.

### O-09: `--verified-to N` does not say that N is a number

- Category: Unclear
- File:Line(s): `references/structure-checks.md:27`, `scripts/check_report.py:21-22` (help text)
- Guideline: claude-md-improver Actionability ("Commands can be copy-pasted"). Best practices, "Make execution intent clear" and verbose script messages.
- Problem: The table row says "Verifier part with last ID N" and the command ends with `--verified-to N`. The help text says "--verified-to set to the last ID of the part". IDs are written as `BH-20` everywhere else, also in `{RANGE}` ("`BH-01` to `BH-20`"). The script takes an integer only. Failure scenario, which I ran: `python3 -I check_report.py report --report x.md --scratch . --areas-done 1 --stage verify --verified-to BH-20` prints `error: argument --verified-to: invalid int value: 'BH-20'` and exits with 2. It prints no `DEFECT` line and no `INFO` counts. The verifier runs `{CHECK_CMD}` before its reply and gets a usage error instead of the check.
- Estimated saving: None.
- Fix plan:
  1. In `structure-checks.md:27`, replace the row with:

     ```markdown
     | Verifier part that ends at `BH-N` | `python3 -I "$C" report --report "$R" --scratch "$S" --areas-done <number of areas> --stage verify --verified-to N`, with the number only (`--verified-to 20` for `BH-20`) |
     ```

  2. In the module docstring of `check_report.py:21-22`, replace "--verified-to set to the last ID of the part". The new text is "--verified-to set to the number of the last ID of the part, for example 20 for BH-20". Change only the docstring. Do not change code.
- Risk: None. The script behavior stays the same.

### O-11: "Delete only the paths that you recorded" reads as "delete nothing else"

- Category: Unclear
- File:Line(s): `agents/bug-hunter.md:26` (read-only rule 5), `agents/bug-verifier.md:25` (read-only rule 5)
- Guideline: claude-md-improver Actionability. simple-english rule 8 (one word, one meaning in a document).
- Problem: Rule 5 says "At the end, delete only the paths that you recorded". Then, two sentences later, it says "Delete your temporary files at the end." The recorded paths are the paths outside the work folder. A reader can take "only" to cover the work folder too and keep its temporary files. Failure scenario: a verifier keeps the build output in its work folder. The structure check prints a WARN line for files left in work folders, and the reply says that it did not delete them. No data is lost, because step 6 deletes the scratch folder. The cost is a WARN and a confused report.
- Estimated saving: None.
- Fix plan: In both files, replace "At the end, delete only the paths that you recorded". The new text is "At the end, delete these recorded paths, and nothing else outside your work folder".
- Risk: None.

## Executor section

Use the Edit tool for every change to an existing file. Do not use `sed -i` or a script that rewrites a file. Most of these files have CRLF line ends in the working tree. `pauses.md` and `structure-checks.md` have LF. Create the two new files with the Write tool. If the simple-english lint hook reports hits in text that this plan copies unchanged from the old files, leave them. Do not reword settled terms such as "check" in rule 3 or the verdict names.

All paths below are under `<repo>`, the root of the repository.

### Order of edits

1. Create `essentials/dev-essentials/skills/bug-hunt/references/inputs-and-meta-plan.md` (O-01, with O-07).
2. Create `essentials/dev-essentials/skills/bug-hunt/references/resume-and-failures.md` (O-02, with O-03 and O-04).
3. Edit `essentials/dev-essentials/skills/bug-hunt/SKILL.md` from the bottom up, so that the line numbers above stay valid. First delete "Failure handling" (O-02). Then edit steps 6, 5, 4, 3, and 1 (O-06), then step 0 (O-01). Then edit "Pause points" and "Resume check" (O-02), then rules 8, 7, 6, 2, and 1 (O-05). Then delete "Inputs" (O-01), and edit the Terms list (O-05).
4. Edit `references/pauses.md` (O-02, item 5).
5. Edit `references/agent-briefs.md` and `references/report-format.md` (O-08).
6. Edit `references/structure-checks.md` (O-09, O-10) and the docstring of `scripts/check_report.py` (O-09).
7. Edit `references/report-skeleton.md` (O-10).
8. Edit `agents/bug-hunter.md` and `agents/bug-verifier.md` (O-11).
9. Edit `CHANGELOG.md`. In the `dev-essentials 2.3.0` entry, replace the line that starts "- Added 6 reference files to the skill `bug-hunt`:" with this text. Keep the rest of that line ("Added the script ..."). Do not bump any version.

   ```markdown
   - Added 8 reference files to the skill `bug-hunt`: `report-format.md`, `report-skeleton.md`, `plain-english-fallback.md`, `agent-briefs.md`, `structure-checks.md`, `pauses.md`, `inputs-and-meta-plan.md`, and `resume-and-failures.md`.
   ```

### Pointer checks

Run these in the Bash tool from the repository root. Each one must give the result in its comment.

```bash
cd "<repo>/essentials/dev-essentials"
S=skills/bug-hunt
# Every reference link in SKILL.md resolves (prints nothing):
for f in $(grep -o 'references/[a-z-]*\.md' $S/SKILL.md | sort -u); do test -f "$S/$f" || echo "MISSING $f"; done
# Every link between reference files resolves (prints nothing):
for f in $(grep -oh '](\([a-z-]*\.md\))' $S/references/*.md | tr -d '()]' | sort -u); do test -f "$S/references/$f" || echo "MISSING $f"; done
# Both new files are linked from SKILL.md (2 lines or more each):
grep -c 'inputs-and-meta-plan.md' $S/SKILL.md
grep -c 'resume-and-failures.md' $S/SKILL.md
# No pointer to removed sections (0 hits):
grep -n 'Inputs table\|resume check in this file\|resume check in the bug-hunt skill\|restore case in' $S/SKILL.md $S/references/*.md
# "Failure handling" and "Resume check" appear only in the new file and as pointers to it:
grep -n 'Failure handling\|Resume check' $S/SKILL.md $S/references/*.md
# The job prompt points to the new file (1 hit):
grep -n 'resume-and-failures.md' $S/references/pauses.md
# The lint paragraph moved (0 hits in agent-briefs.md, 1 in report-format.md):
grep -c 'lint hook' $S/references/agent-briefs.md
grep -c 'lint hook' $S/references/report-format.md
# The 30-minute test uses "changed" (0 hits):
grep -rn 'minutes old' $S
# verified-to text (1 hit each):
grep -n 'the number only' $S/references/structure-checks.md
grep -n 'number of the last ID' $S/scripts/check_report.py
# Removed section (0 hits):
grep -n 'Agents run the check too' $S/references/structure-checks.md
# CHANGELOG (1 hit):
grep -n 'Added 8 reference files' ../../CHANGELOG.md
# Size of SKILL.md: about 17,900 characters and 2,950 words. It must stay under 20,000 characters.
wc -c -w $S/SKILL.md
# The script still runs (prints the usage text, exit 0):
python3 -I $S/scripts/check_report.py --help
```

### Validators and line ends

```bash
cd "<repo>"
claude plugin validate .
claude plugin validate ./essentials/dev-essentials
git -C "<repo>" ls-files --eol essentials/dev-essentials/skills/bug-hunt essentials/dev-essentials/agents CHANGELOG.md
```

Both validators must pass with no new warning. No line of `ls-files --eol` can show `w/mixed`. The two new files are not in the index until you run `git add`. Run the `ls-files --eol` command again after `git add`.

### Commit

Make one local commit with an explicit pathspec. Do not push.

```bash
R="<repo>"
git -C "$R" add -- \
  essentials/dev-essentials/skills/bug-hunt/references/inputs-and-meta-plan.md \
  essentials/dev-essentials/skills/bug-hunt/references/resume-and-failures.md
git -C "$R" commit -F - -- \
  essentials/dev-essentials/skills/bug-hunt/SKILL.md \
  essentials/dev-essentials/skills/bug-hunt/references/inputs-and-meta-plan.md \
  essentials/dev-essentials/skills/bug-hunt/references/resume-and-failures.md \
  essentials/dev-essentials/skills/bug-hunt/references/pauses.md \
  essentials/dev-essentials/skills/bug-hunt/references/agent-briefs.md \
  essentials/dev-essentials/skills/bug-hunt/references/report-format.md \
  essentials/dev-essentials/skills/bug-hunt/references/report-skeleton.md \
  essentials/dev-essentials/skills/bug-hunt/references/structure-checks.md \
  essentials/dev-essentials/skills/bug-hunt/scripts/check_report.py \
  essentials/dev-essentials/agents/bug-hunter.md \
  essentials/dev-essentials/agents/bug-verifier.md \
  CHANGELOG.md <<'EOF'
Optimize bug-hunt skill per skill-doctor and claude-md-improver guidelines

Move the step-0 inputs and meta-plan parts into references/inputs-and-meta-plan.md, and the
resume check and failure handling into references/resume-and-failures.md. SKILL.md drops from
about 27,700 to about 17,900 characters, so the whole skill fits in the 5,000-token part that
Claude Code keeps after compaction.

Use one restore path for a stopped agent: SendMessage first, then a new agent with the resume
note. Say that the 30-minute test uses the time the progress file last changed. Say that
--verified-to takes the number of the last ID. Move the lint-hook text from the plain-English
brief block into report-format.md. Cut text that restates the briefs, the agent files, or
other rules.

<the trailer that the repository asks for>
EOF
git -C "$R" log -1 --format=%B
git -C "$R" status --short
```

The message must end with the trailer that the repository asks for. `git status --short` must show no changed plugin file after the commit. Do not push.

## Not changed on purpose

- Read-only, GitHub, and progress-file rules in both `SKILL.md` and the agent files: the orchestrator and the agents have separate contexts, so each needs its own copy.
- The same read-only rules and "Sources you can read" in `bug-hunter.md` and `bug-verifier.md`: each agent sees only its own file.
- The "Not confirmed" sentence in the plain-English blocks and in the agent files: the collector gets only the block.
- The opening paragraph on the two most-forgotten rules: the docs say to put the most important instructions near the top of `SKILL.md`.
- The Terms section as a whole: it keeps the wording consistent, and O-05 only shortens it.
- The Agents table and step 7 in `SKILL.md`: the run needs them late, after compaction.
- The scratch-folder item in step 0: it carries a safety rule (not inside the project or the report folder).
- The cleanup brief with its process test: it is the kill re-check, and the cleanup helper sees only its brief.
- The crash-safety block and the resume note in `agent-briefs.md`: the collector has no agent file, and the resume note tells an agent that an earlier agent stopped.
- The `dotnet` examples in agent rule 8: they are examples after "for example", not a stack assumption.
- The planning times in `pauses.md:20`: the feedback plan kept them on purpose.
- The folder tree in `report-skeleton.md`: the orchestrator reads it once at step 2, and it is short.
- `argument-hint`: it does not go into the skill listing, and it serves autocomplete.
- No `when_to_use` field: the description fits the cap without it.
- No table of contents in reference files over 100 lines: the agents read whole files with Read.
- The settled decisions. The pipeline: the steps, the finding fields, the labels, the verdicts, and the three agents with their models and effort. The gates: the step-0 gate, the report-folder exception, and the dispatch guard. The formats: `N-NN` IDs, the plain-English fallback, and the run format. The rest: the options and defaults, the script behavior, the live/dead test, and the cleanup re-check.
