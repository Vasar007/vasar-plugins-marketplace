# Audit-team adapter

If `--reviewer` is `audit-team`, Phase 2 of `SKILL.md` reads this file. `audit-team` is a **slash command, not an agent ID**. So it does not go through the `subagent_type` path of the `Agent` tool that the other values use, and it needs this adapter.

## Target restriction

`audit-team` needs a target that Phase 1 resolved to a documentation path: `target=spec <path>`, or `target=file <path>` with the extension `.md`. `/audit-team` reads only `.md` files. This set is narrower than the non-code extensions of Phase 6, which also cover `.txt`, `.rst`, and `.adoc`.

Every other target resolves to a diff or a code symbol, not to a documentation path that `/audit-team` can take. These targets are `branch`, `pr <id>`, `commits <N>`, `diff <range>`, `class <FQN>`, `method <FQN>`, and a `file` that does not end in `.md`. For them, **fall back to `general-purpose` and print a warning**: "`--reviewer audit-team` needs a documentation path target. `target=<value>` is not one. Using `general-purpose`."

## Argument mapping

Run `/audit-team <path> [agent-count] [model]`. `<path>` is the target path that Phase 1 resolved. Then add the rest of `--audit-team-args` word for word.

- `[agent-count]`: the value from `--audit-team-args`, or else the default of `/audit-team` (`5`). A positional argument cannot be skipped. So always fill this slot, also for a user who gave only a model. Example: `--audit-team-args "opus"` must produce `/audit-team <path> 5 opus`. It must never produce `/audit-team <path> opus`, because `/audit-team` reads that `opus` as `[agent-count]`.
- `[model]`: the resolved `--reviewer-model`, so that the reviewer model really applies. **Exception**: leave the argument out for `--reviewer-model inherit`, and for an `--audit-team-args` value that already names a model. Then the "current model" default of `/audit-team` applies.
- A value of the user for `[agent-count]` or `[model]` in `--audit-team-args` always wins over a value that this skill fills in.

## Phase 3

`/audit-team` builds its own role prompts. Phase 3 builds no reviewer brief for it and passes nothing but the arguments above. The Output and Conclusion mappings below turn its report into the Full format.

## Output mapping

`/audit-team` returns 3 buckets, and this skill triages 6 severities. Map `Blockers` to **Blocker**, `Warnings` to **High**, and `Suggestions` to **Low**. Next to each mapped severity, record the bucket that it came from. Then Phase 4 can see that it was not a native grade of six levels.

If the text of a single finding clearly calls for it, grade the finding up or down. Examples: a `Warning` about a bug that corrupts data is Critical. A `Warning` about a `should` that is not normative is Medium.

`/audit-team` gives a confidence for each finding. Carry it into the Confidence field. It gives no **type** token. For `target=spec`, use `Spec`. For a documentation `target=file`, take the type from the text of the finding, with the type taxonomy of `SKILL.md`. The default is `Docs`.

## Conclusion mapping

The report of `/audit-team` has no section "Must fix before merge / Acceptable risks / Needs discussion". The Full format of the reviewer report expects one, so build it for that section of the report:

- The combined `Blockers` go to Must fix before merge.
- `Warnings` go to Needs discussion.
- `Suggestions` go to Acceptable risks.

Use the **agreement matrix** of `/audit-team` as the signal from several roles. A finding that several roles flag goes up. **Order of the rules**: an agreement of several roles raises a finding by one bucket only (Suggestion to Warning, Warning to Blocker). It never skips past Warnings, or Needs discussion, in one step. So a `Suggestion` that several roles flag goes to Needs discussion, not to Must fix. Only a `Warning` (or higher) that several roles flag goes to Must fix.

**This built bucket only informs the written report**. It does not decide on its own whether a finding goes to Phase 5 or to the discussion addendum. The `blocking` decision of Phase 4, by severity and by merit, decides that. A `Warning` that maps to High gets `blocking: true` by default, which means "will fix", like any other High. The Conclusion bucket that this mapping gave it does not change that. `examples/spec-review.md` shows this. There, #3 is a single-role `Warning`. It maps to High and gets `blocking: true` by the severity default of Phase 4. So the fixer fixes it, although the built Conclusion puts it under Needs discussion.

## Phase 5, step 5a

`/audit-team` reads only and returns no fix plan. Its subagents for each role cannot get a second question. So its findings have no usable plan, and step 5a plans them with one **plan dispatch on `--reviewer-model`**. The plan does not come from the `audit-team` run.

## Phase 8

The Round N+1 re-review of Phase 8 needs no adapter. It always uses one `general-purpose` agent, for any `--reviewer` value.
