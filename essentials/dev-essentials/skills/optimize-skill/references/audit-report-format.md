# Audit report format

The auditor reads this file before it writes the audit report. The orchestrator reads it at
step 1 to test the form of the report. For a full worked report, see
[../examples/bug-hunt-audit.md](../examples/bug-hunt-audit.md).

## Guideline sources

The auditor reads these sources itself, on the day of the audit, and quotes the passages that
it uses:

- The skill docs of Claude Code: <https://code.claude.com/docs/en/skills>. Use the sections on the listing budget, the types of content, and the lifecycle after compaction. Also use the troubleshooting advice and the section on supporting files.
- The best practices for skills: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>.
- The criteria of the skill `claude-md-management:claude-md-improver`: its `references/quality-criteria.md` and `references/update-guidelines.md`. Apply the criteria to the skill files. Never run the write steps of that skill. Never change a `CLAUDE.md` file.

If a source cannot be read, the report says so in its Sources section, and the audit uses the
other sources.

## What to look for

- A `SKILL.md` over 5,000 tokens. Claude Code keeps only the first 5,000 tokens of an invoked skill after compaction. Move the text of one step into a reference file, and read that file at that step.
- The same rule in several files. Give it one home and pointers. But an agent file stays self-sufficient, because the agent does not see the skill.
- A rule that an agent cannot break anyway, for example a rule against a tool that the agent does not have.
- Text that restates what the model does without the text.
- Text that two readers follow in two ways. Give the failure scenario: two readers, two actions.
- Narration of how or why, where the reader only needs what to do.
- The quality and the length of the `description` and `when_to_use`, and the facts in them that the body does not support.
- A research note, a version note, or other text that goes stale and gives no action.

## Categories

| Category | Meaning |
| --- | --- |
| Tokens | The text costs tokens that the run does not need, or that it needs only in one step |
| Needless | The text gives the reader no action |
| Unclear | Two readers can follow the text in two ways |
| Frontmatter | The `description`, `when_to_use`, or another frontmatter field has a defect |

## Report sections

Write the sections in this order.

1. Title and target: the target files and the base commit. Say that the audit changes no file.
2. Sources: each source with its URL or path, the date of the reading, and the quoted passages. Also the earlier audits, and the statement that no item repeats or undoes one of their items. Also the method of the token estimates.
3. Summary: a table with ID, title, category, and estimated saving. Then the `SKILL.md` size now and after the plan, in words, characters, and estimated tokens. Then why the size matters for this target.
4. Items: one `### O-NN: <title>` section for each item, in the form below.
5. Executor section: the order of the edits, the pointer greps, the validators and the line-ending rule, the CHANGELOG line, and the commit.
6. Not changed on purpose: each text that looks like a cut but stays, with the reason. The last line lists the Settled decisions.

## Item form

```markdown
### O-NN: <title that names the problem>

- Category: Tokens, Needless, Unclear, or Frontmatter
- File:Line(s): `<path>:<line>-<line>`, one entry for each place
- Guideline: the source and the quoted passage, with its URL
- Problem: what is wrong. For Unclear, a failure scenario with two readers.
- Estimated saving: characters and estimated tokens, or "None"
- Fix plan: numbered edits with near-final text in a code block. Say "replace", "delete", or "create", and name the exact old text or lines.
- Risk: None, Low, or High, and what can go wrong. Name each alternative that the user can pick.
```

The fix plan gives text that the applier can paste. It does not say "shorten this". If an item
moves a block, it names the new home and the step that reads it.

## Executor section

The executor section has these parts:

- Order of edits: create new files first. Then edit each file from the bottom up, so that the line numbers of the plan stay valid.
- Pointer greps: one command for each moved block and each new link, with the expected result in a comment. Include a test that every reference link resolves. Include a test that no pointer to a removed section is left. Include the `wc -c -w` of `SKILL.md` with the expected size.
- Validators and line ends: `claude plugin validate` for the marketplace and for the plugin, and `git ls-files --eol` for the changed files. No file can show `w/mixed`.
- CHANGELOG and version: the line and the version bump that the rules of the repository ask for, or "none".
- Commit: one commit with an explicit pathspec and the full message. The message follows the rules of the repository.
