# Source Inventory — Phase 0 and Phase 1

Phase 0 and Phase 1 of `SKILL.md` read this file. It holds the discovery paths, the decode-and-probe procedure for encoded project names, the worktree-sibling collapse, the mandatory wrapper diff, and the structural landmines.

All paths in this file are relative to `<claude-root>`, the Claude config root. The path resolution rule in `SKILL.md` gives its value. If the environment variable `CLAUDE_CONFIG_DIR` is set, the root is its value. Else, the root is `<home>/.claude`. Never hardcode a concrete path in output. Show each path relative to `<claude-root>` or to the repo root. The paths of the KB rules are relative to `<kb-root>`, the folder of the KB clone.

---

## Discovery paths per source type

| Source type | `--scope=` token | Discovery path(s) |
| --- | --- | --- |
| KB rules | `kb` | Only for a KB clone. The command of item 3 of `../../references/notes-root.md`, from the base folder of this skill, finds it. Read `_claude/RULES.md` of the clone and each rules index that it loads with `@`. Also read the index that it names for each project of the project set. Read a note that an index line links only to cite the full rule. |
| Per-project memory index | `memory` | Probe both locations. The index is usually inside the `memory/` directory: `<claude-root>/projects/<project>/memory/MEMORY.md`. A project can also have one at the outer level: `<claude-root>/projects/<project>/MEMORY.md`. The location changes how its bullets link to sibling files. An inner index links them bare (`feedback-x.md`). An outer index needs the prefix `memory/`. The run reads the index once, as an index. It reads no topic file, that is, no other file of the `memory/` directory. |
| Global CLAUDE.md | `global-claude-md` | `<claude-root>/CLAUDE.md` |
| Project CLAUDE.md | `project-claude-md` | `<repo-root>/CLAUDE.md`, `<repo-root>/.claude/CLAUDE.md`, and each other `CLAUDE.md` in a subdirectory, plus every file that an `@`-import of these files reaches. A `CLAUDE.md` in a `.claude/worktrees/` subtree counts for the skip count, but the run never reads it (see "Worktree copies inside a repo" below). |
| Personal global commands | `personal-entities` | `<claude-root>/commands/*.md` |
| Personal global agents | `personal-entities` | `<claude-root>/agents/*.md` |
| Personal global skills | `personal-entities` | `<claude-root>/skills/*/SKILL.md` |

`claude-md` is an alias for both `global-claude-md` and `project-claude-md`. `all` expands to every token above.

**Dedupe before Phase 2**. The literal path sets of the rows do not overlap. Only the `@`-import expansion can reach a file that another row also owns. After you expand all rows (root, `.claude`, nested, and `@`-imports), dedupe by resolved absolute path. Count each remaining file exactly once in the Phase 4 scan summary. In Phase 3, it counts at most once as an independent source, because independence is per distinct file (`references/classification-framework.md`, Step 1). The worktree-sibling collapse below still decides which repo a rule belongs to. It also decides how many independent sources one collapsed family gives. A file that two parents `@`-import is one discovered file with one `source:` path. Landmine 8 sets its inheritance scope, but its identity is the file.

## Encoded project directory names — decode and probe

Claude Code stores the session and memory data of each project in a directory. The name of that directory encodes the filesystem path of the project. The encoding loses information, so resolve it by probing, not by decoding alone:

1. **A single `-`** in the encoded name is ambiguous. It can stand for a path separator (`/` or `\`) or for a literal `.` in a real directory name. No exact inverse transform exists.
2. **`--`** marks a separator before a segment that starts with a punctuation mark. Examples: the colon of a drive letter (`C--Users-...` decodes to a `C:\Users\...` root) or a dot-directory such as `.claude`. Treat this as a candidate to try, not as a fact.
3. Because of the single-`-` ambiguity, generate candidate paths and probe each one against the real filesystem: does a directory exist at that path? If more than one candidate exists, prefer the candidate that also contains a `.git` directory, because it is a repo root. This signal is the strongest one, but it is not a hard requirement. Claude Code keys a project directory on the working directory, not on the repo root.
4. If no candidate resolves, look for a worktree marker in the encoded name (see below) before you exclude the name. A project directory can encode a deleted git worktree, and its memory exists nowhere else. If you find a worktree marker, strip the worktree suffix and probe the parent path. If the parent path resolves, attribute the memory of the directory to the parent repo, and count it in the worktree-collapse total. Do not drop it silently. If the parent path also fails, report the encoded name as unresolvable in the Phase 0 scope echo. Exclude it from the `auto` set.

## Worktree-sibling collapse

A repository that the user works on through several git worktrees gets several encoded project directories under `<claude-root>/projects/`, one for each worktree path. For promotion, they are all the same real repository.

- **Detect** a worktree-suffixed encoded name by a worktree marker in the decoded path. The usual marker is a `.claude/worktrees/<branch-ref>` segment, which is the path convention of `dev-essentials:git-worktree-management`. Detection does not depend on that convention. Any worktree path marker counts.
- **Collapse** the siblings in these cases:
  - Worktree siblings decode to paths under the resolved path of a non-worktree sibling. Treat the non-worktree sibling as the one real parent repo.
  - Two or more worktree siblings, and no non-worktree sibling, resolve to the same repo root after you strip their worktree suffixes (step 4 of decode-and-probe). This all-worktree family is a real case, because some users always work through worktrees.

  Fold the memory indexes of the siblings into the same inventory pass. Each file keeps its own `source:` path in Phase 2. The collapse decides which repo a rule belongs to for the corroboration count. It does not erase the distinct file paths.
- **Count one source for each rule in each family**. In Phase 3, a collapsed family is one real repository. The family is the parent project directory (where one exists) plus each worktree sibling. An equivalent rule in more than one memory index of the family is the memory of one repo, accumulated again. It is not independent corroboration. This rule caps the count. It does not choose content. Reconcile the content of the rule across every copy of the family, as landmine 5 and calibration case 6 require, and never drop a copy. Keep the `source:` citation of each file. If the family has a non-worktree parent, use the copy of the parent as the primary citation for display. If the family has no non-worktree parent, cite all copies as equal. The family still counts as one source.

  The rule-equivalence clustering of Phase 3 finds "the same rule" across worktree copies. Landmine 5 still governs the content of a matched file. A rule that exists only in one worktree sibling still counts as one source. The cap applies only inside one collapsed family. Two different real repos with the same rule are still two sources (calibration case 1).
- **Report** the collapse count in the Phase 0 scope echo: "`<w>` worktree siblings collapsed".
- **Worktree copies inside a repo.** A live worktree at `<repo-root>/.claude/worktrees/<branch-ref>/` is a full second checkout. It holds its own copy of each `CLAUDE.md` file of the repo and of their `@`-imports. These copies are the rules of the same repo, not independent corroboration. Count each `CLAUDE.md` file in a `.claude/worktrees/` subtree in the Discovered column, but never read it. Read each file from the main checkout only. Report the copies in the Skipped column of the Phase 4 scan summary, with the reason `worktree copy`. The vendored skip of landmine 11 has the same shape. Worktree memory is different: its index exists nowhere else (step 4 of decode-and-probe), so the run reads it.

## Wrapper personal entities — mandatory diff against the wrapped entity

This procedure is mandatory for each personal-entities file that is a wrapper. One of these things makes a file a wrapper: a signal of landmine 12 below, or your own judgment during the Phase 1 read. Never skip the procedure because the wrapper "looks like" it stays personal forever.

1. **Resolve the on-disk path of the wrapped entity**. Reuse the on-disk-manifest lookup of Phase 3 (Step 2 of `references/classification-framework.md`), which greps the real plugin manifests of the target marketplace. Do not invent a second lookup.
2. **Read the definition files of the base entity, scoped to its kind.** Step 1 already gives the kind: the `commands/`, `agents/`, or `skills/` tree of the resolved file.
   - **Skill**: always read the `SKILL.md` of the base skill in full. It is small and central, and the summary of the wrapper never replaces it. Scope the read of its support files (`references/`, `stages/`, `examples/`) to save tokens, the same way as Precondition C (9c.2 C):
     1. Extract the topics and terms that the wrapper states. This is cheap, because the wrapper file is small: its frontmatter `description`, its headings, and any explicit "wraps/extends `<plugin>:<entity>`" text.
     2. Grep the support files of the base entity for those terms. Run one search for each term, as a fixed string, not as a regex: `git -C <marketplace-root> grep -n -F -e '<term>' -- <support-file-path>`. The result shows which files bear on the divergence that the wrapper claims.
     3. Read only those files in full.

     The grep narrows the read. It does not replace judgment. A support file that the wrapper never mentions can still duplicate or contradict it in silence. If the scoped read leaves the behavior of the wrapper unclear, read more files.
   - **Command or agent**: always read the single `commands/<name>.md` or `agents/<name>.md` file in full. In the Claude Code plugin layout, commands and agents are flat single files, with no `references/`, `stages/`, or `examples/` tree. So the sub-steps above do not apply. But a command or an agent often delegates behavior to another entity. Signs: a `Skill` tool call that names another skill, a `skills:` frontmatter entry, or an explicit `<plugin>:<entity>` reference. For example, `commands/help-review-pr.md` takes its mechanics from the recipes of `create-html-artifact` and its tag taxonomy from `process-pr-comments`. `commands/implement-task.md` hands whole phases to `research-implement-review-report`. The real divergence of the wrapper can be in that delegated behavior. In that case, follow that ONE hop (no further), and apply the sub-steps to the delegated entity.
3. **List every divergence** between the wrapper and the base entity. Hand each one to Phase 2 as its own rule record. Exception: a pure forwarding or boilerplate divergence (argument passthrough, the flag parsing of the wrapper) gives no Phase 2 record, because it is not a rule. `references/classification-framework.md` states the same exclusion in "Wrapper divergences use the same rules, no new taxonomy". Each record cites a pair: the file and line of the wrapper, and the file and line of the base entity.
4. **If the wrapped entity does not resolve on disk**, record an unresolvable-source note in the Phase 4 scan summary. Causes: a rename, a removal, or a target marketplace that does not ship it. Never skip the wrapper file in silence.

---

## The structural landmines

Read this list before you extract rules in Phase 2. If you skip a landmine, you misread a source in a specific way.

A rule file is a memory index or a note of a KB clone.

1. **Frontmatter shape variance**. Some rule files nest metadata under a `metadata:` block with a `metadata.type` field. Others use a flat top-level `type:` field, and others have no frontmatter at all. Do not assume a shape. Read the frontmatter of each file.
2. **Unquoted `#` truncating YAML**. The YAML parser cuts a `description:` value at an unquoted `#` character, because `#` starts a YAML comment. A description "handles retries # see also X" parses as "handles retries" only. If a description looks too short, read the raw file content, not only a parsed frontmatter object.
3. **Missing `Why:`/`How to apply:` sections**. Do not assume that every rule file has the Why and How-to-apply shape. Most real files skip one or both. Extract the rule from the prose that the file holds.
4. **Wikilink hazards**. Rule files sometimes use `[[Page]]`-style links.
   - The file names and the link slugs of one project can follow different conventions. A link can fail to resolve, although the target file exists, because the slug rule differs from the real file name.
   - Some links point AT a skill name on purpose, as a forward reference to a future `plugin:skill-name`. They are not dangling. They are provenance breadcrumbs.
   - Some links are really dangling. Someone deleted or renamed the target and did not update the link.
   - Link scope is per project. A link that resolves in the memory directory of one project does not resolve from another project. A dangling cross-project link is not evidence that the content is stale.
   - MediaWiki-style `[[Page]]` or `[[Category:...]]` syntax sometimes appears as **literal example content** inside a fenced block or an inline code span. An example is a note on how to write a wiki page. These are not real links. Exclude from the wikilink-hazard analysis each match inside a fenced code block or an inline code span, and each match with the prefix `Category:`.
5. **Same-slug files diverged across two projects**. Two projects can each grow a rule file with the same file name or slug, and the contents can drift apart. Merge and reconcile the two files into one candidate rule set. Never pick the version of one project and discard the additions of the other.
6. **Dated append-blocks**. Some rule files grow by appended `## Update (YYYY-MM-DD)` blocks. A later block supersedes an earlier statement on the same topic but does not remove the earlier text. Read the whole file, and take the latest position on each point, not the first one.
7. **Stale `MEMORY.md` index entries**. The `MEMORY.md` index of a project can point to a memory file that someone deleted or renamed later. The index is not ground truth. Find out whether each file that the index names exists on disk. Do not trust an index entry for a missing file. This also holds for the "migrated" claims of the index (see Phase 3).
8. **CLAUDE.md `@`-imports**. A CLAUDE.md file can `@`-import the content of another file. Resolve the import chain. For inheritance, the imported content belongs to the scope of the importing file. Still cite the path of the imported file itself in the `source:` field.
9. **Near-duplicate CLAUDE.md pairs with content drift**. A repo root `CLAUDE.md` and a nested `.claude/CLAUDE.md` (or a `CLAUDE.md` deeper in a subdirectory) can overlap heavily. Sometimes the deeper file is a STALE superset that someone copied once and never kept in sync. Dedupe by content, not by location. Read both files in full and reconcile them. Do not assume that the deeper file is more specific or more current.
10. **Nested-file inheritance/scope-negation statements**. A nested CLAUDE.md sometimes narrows or negates a rule of the parent scope ("unlike the repo default, this subfolder does not use X"). In Phase 2, honor each such statement as you extract the rules. A flat scan that ignores nesting puts the rule on the wrong folder. Worse, it can drop the negation in silence and treat the parent rule as universal.
11. **Vendored/third-party CLAUDE.md files**. A personal repo can contain a vendored or third-party dependency that ships its own `CLAUDE.md`. Exclude these files by default. They document the conventions of another project, not the conventions of the user. `--include-vendored` includes them, with a clear `vendored` label in the inventory output.
12. **Wrapper personal entities**. A personal command, agent, or skill can wrap a shipped entity. Never read such a wrapper alone. Diff it against the entity that it wraps, with the wrapper-diff procedure above. Each of these signals alone triggers the diff:
    - (i) The body has a line that forwards `$ARGUMENTS`, anywhere in the file, not only as the first line.
    - (ii) The file name or the frontmatter `description` explicitly names, wraps, extends, or refines a shipped entity.

    These signals cover the shapes that occur in practice: a forwarding wrapper and a wrapper that its name or description declares. Catch a wrapper of another shape by your own judgment during the Phase 1 read.

    If you read the wrapper alone, you can re-promote content that the wrapped entity already holds upstream. Or you can miss that the real delta of the wrapper is a bug report against the base entity (disposition **E** in `references/classification-framework.md`). `examples/fix-shipped-entity.md` Case 2 shows this landmine. The diff does not stop the wrapper from staying personal on purpose. By the orthogonality rule of Step 4 in `references/classification-framework.md`, an intentional wrapper can still carry divergences that each need their own disposition.
