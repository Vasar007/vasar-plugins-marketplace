# Briefs

Fill every placeholder and paste the brief into the `prompt` of the dispatch. Each brief is
self-contained. The agent does not see this skill. It sees its brief and the `CLAUDE.md`
files. In each brief, `<common rules>` stands for the common rules block below. Paste it in
full. If `{RESUME_NOTE}` or `{DEFECTS}` is empty, leave out its line.

## Placeholders

| Placeholder | Meaning |
| --- | --- |
| `{SKILL_DIR}` | Absolute path of this skill folder (`${CLAUDE_SKILL_DIR}`) |
| `{REPO}` | Absolute path of the repository that holds the target |
| `{TARGET}` | The folder name of the target skill (no colon) |
| `{ROLE}` | The role of the agent: `auditor`, `applier`, `reviewer`, or `review-fixer` |
| `{TARGET_FILES}` | Absolute paths of the target files, one on each line |
| `{BASE_SHA}` | The full SHA of the base commit from step 0 |
| `{BRANCH}` | The branch from step 0 |
| `{APPLY_SHA}` | The full SHA of the step-3 commit |
| `{REPORT_DIR}` | Absolute path of the report folder |
| `{AUDIT_REPORT}` | `{REPORT_DIR}/optimization-audit-{TARGET}.md`. If the file exists, add the date: `optimization-audit-{TARGET}-<YYYY-MM-DD>.md`. |
| `{REVIEW_REPORT}` | `{REPORT_DIR}/optimization-review-{TARGET}.md`, with the same date rule |
| `{SETTLED}` | The Settled list, one decision on each line with its source |
| `{EARLIER_AUDITS}` | Absolute paths of earlier audits and plans of the target, or "none" |
| `{REJECTED}` | The items that the applier rejected after a step-2 decision, with the reasons, or "none" |
| `{FINDINGS}` | The accepted review findings, in full |
| `{PLAIN_ENGLISH}` | One of the two plain-English blocks below |
| `{RESUME_NOTE}` | The resume note below, or nothing |
| `{DEFECTS}` | The list of defects for a repair, or nothing |

## Shared blocks

If simple-english is installed, use this plain-English block:

```text
Before you write any text, load the skill simple-english:simple-english with the Skill tool
and follow its document rules. Do not reword text that the plan copies unchanged.
```

If simple-english is not installed, use this plain-English block:

```text
Before you write any text, read {SKILL_DIR}/../bug-hunt/references/plain-english-fallback.md
and follow its rules. Do not reword text that the plan copies unchanged.
```

Resume note:

```text
An earlier agent of this role stopped. Read your progress file first and continue from its
## NEXT. Do not redo the steps that its checklist marks done.
```

Common rules, pasted into every brief:

```text
Do this work yourself. Do not dispatch subagents. Never edit a CLAUDE.md file. Before the
first write, make sure that git -C "{REPO}" rev-parse --abbrev-ref HEAD prints {BRANCH}. If it
does not, stop and reply. Keep a progress file at
{REPORT_DIR}/_optimize-skill-progress-{ROLE}.md with a STATUS line, a checklist, a ## Log,
and a ## NEXT with the single next action. Update it after each step. Delete it as your last
action. Mark every claim that you did not prove with "Not proven:" and say where you
looked. Never change a decision on this Settled list:
{SETTLED}
```

## Auditor brief

```text
Audit the skill {TARGET} for tokens and clarity, and plan each fix. Change no file except the
audit report and your progress file.

Target files:
{TARGET_FILES}

Repository: {REPO} at commit {BASE_SHA}. Read the help text of each script, not its code.

1. Read {SKILL_DIR}/references/audit-report-format.md. It gives the guideline sources, what to
   look for, the categories, the report sections, and the item form. Then read
   {SKILL_DIR}/examples/bug-hunt-audit.md as the model of the report form. It is an audit of
   a different skill.
2. Read each guideline source yourself, and quote the passages that you use.
3. Read the earlier audits and plans: {EARLIER_AUDITS}. Do not repeat or undo their items.
4. Read every target file in full. Measure SKILL.md with wc -c -w.
5. Write the audit report to {AUDIT_REPORT}. For each item, give near-final text that the
   applier can paste.

Cuts must keep behavior. Every safety rule must still reach the agent or the step that needs
it. Each agent file stays self-sufficient. If an item changes behavior on purpose, say so in
its Risk and name the alternative.

<common rules>
{PLAIN_ENGLISH}
{RESUME_NOTE}
{DEFECTS}

Reply with the report path, the item count by category, the SKILL.md size now and after the
plan, and each item that offers a choice.
```

## Applier brief

```text
Apply the audit report {AUDIT_REPORT} to the skill {TARGET} in {REPO}. The report is the plan.
Follow its executor section. Each "Decision:" line under an item wins over the item text.

1. Classify each item first: APPLY (as planned), PARTIAL (a part of it, with the reason), or
   REJECT (with the reason). Reject an item that breaks the Settled list, that drops behavior,
   or whose old text does not match the file. Write the classes into your progress file
   before the first edit.
2. Edit existing files with the Edit tool, not with sed -i or a script that rewrites a file.
   Keep the line endings of each file. Create new files with the Write tool. Change the help
   text of a script, not its code. If an item is PARTIAL or REJECT, or its Decision line picks
   an alternative, adjust the commit message and the CHANGELOG line to match, and report it.
3. Run every pointer grep of the executor section. Compare each result with its expected
   result.
4. Report the SKILL.md word count and character count with wc -c -w.
5. Run the validators of the executor section, and its test command if it names one. Run
   git -C "{REPO}" ls-files --eol on the changed files after git -C "{REPO}" add. No file
   can show w/mixed. Commit only after the validators and the tests pass.
6. Make one local commit with git -C "{REPO}" commit, an explicit pathspec, and the message of
   the executor section. Follow the commit rules of the repository. Do not push. Then run
   git -C "{REPO}" status --short.

<common rules>
{PLAIN_ENGLISH}
{RESUME_NOTE}
{DEFECTS}

Reply with the class of each item and the reason for each PARTIAL and REJECT, the output of
each pointer grep, the word and character counts, the validator output, the test output, the
commit SHA, and the git status output.
```

## Behavior reviewer brief

```text
Review one optimization of the skill {TARGET} in {REPO}. You have one goal: did the
optimization keep behavior. Change no file except the review report and your progress file.

The old files are at {BASE_SHA}. The new files are at {APPLY_SHA}. The plan is
{AUDIT_REPORT}. Items that the applier rejected: {REJECTED}.

1. Run git -C "{REPO}" diff {BASE_SHA} {APPLY_SHA}. Read the old and the new version of every
   changed file in full.
2. For every deleted or moved block, find its new home. Report each instruction that has no
   home now, or whose home the reader of that instruction does not read.
3. For every new reference file, make sure that a step names it before the step needs it, and
   that the link is one level deep from SKILL.md.
4. Make sure that every safety rule still reaches the agent or the step that needs it, and
   that each agent file is still self-sufficient.
5. Make sure that no change breaks the Settled list.
6. Make sure that each changed sentence means the same as before, unless an item changed it
   on purpose.

Write the review report to {REVIEW_REPORT}. For each finding, give an ID (R-NN), the file and
line, why it is wrong, how to show that it fails, and a fix with near-final text. Do not
report a preference. If you find nothing, write "No finding" and list what you compared.

<common rules>
{PLAIN_ENGLISH}
{RESUME_NOTE}
{DEFECTS}

Reply with the report path and one line for each finding.
```

## Review fixer brief

```text
Fix the accepted findings of the behavior review of the skill {TARGET} in {REPO}. The review
report is {REVIEW_REPORT}. Fix only these findings:
{FINDINGS}

1. Edit existing files with the Edit tool, not with sed -i or a script that rewrites a file.
   Keep the line endings of each file. Change the help text of a script, not its code.
2. Run the pointer greps of the executor section in {AUDIT_REPORT} again.
3. Report the SKILL.md word count and character count with wc -c -w.
4. Run the validators of the executor section in {AUDIT_REPORT}, and its test command if it
   names one. Run git -C "{REPO}" ls-files --eol on the changed files after
   git -C "{REPO}" add. No file can show w/mixed. Commit only after the validators and the
   tests pass.
5. Make one local commit with git -C "{REPO}" commit and an explicit pathspec. The message
   names the finding IDs. Follow the commit rules of the repository. Do not push. Then run
   git -C "{REPO}" status --short.

<common rules>
{PLAIN_ENGLISH}
{RESUME_NOTE}
{DEFECTS}

Reply with the fix for each finding, the pointer grep output, the word and character counts,
the validator output, the test output, the commit SHA, and the git status output.
```
