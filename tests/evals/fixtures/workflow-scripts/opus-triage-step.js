export const meta = {
  name: 'review-loop-feature-paging',
  description: 'Review loop (2 rounds) on feature/paging vs origin/main: review, verify-then-fix, test, commit, re-review',
  phases: [
    { title: 'Round 1 review' },
    { title: 'Round 1 fix' },
    { title: 'Round 2 re-review' },
    { title: 'Round 2 fix' },
  ],
}

const REPO = args.repo
const DISCIPLINE = args.discipline
const USER_DECISION = 'Decision of the user (pre-answered, authoritative): for page < 1, page_slice must raise ValueError, as it does for size <= 0.'

const FINDINGS = {
  type: 'object',
  properties: {
    report_markdown: { type: 'string', description: 'The full report in the Full format' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      severity: { type: 'string', enum: ['Blocker','Critical','High','Medium','Low','Nit'] },
      type: { type: 'string', enum: ['Bug','Reliability','Security','Performance','Maintainability','Test','Style','Architecture','Spec','Docs'] },
      file_line: { type: 'string' },
      problem: { type: 'string' },
      failure_example: { type: 'string' },
      confidence: { type: 'string', enum: ['high','medium','low'] },
      fix_plan: { type: 'string' },
      conclusion: { type: 'string', enum: ['must_fix','acceptable_risk','needs_discussion'] },
    }, required: ['id','severity','type','file_line','problem','confidence','fix_plan','conclusion'] } },
  },
  required: ['report_markdown','findings'],
}

const FIX = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, verdict: { type: 'string', enum: ['APPLY','PARTIAL','REJECT'] },
      reason: { type: 'string' }, primary_source: { type: 'string' },
    }, required: ['id','verdict','reason'] } },
    changed_files: { type: 'array', items: { type: 'string' } },
    test_command_output_tail: { type: 'string' },
    tests_green: { type: 'boolean' },
    commit_sha: { type: 'string', description: 'SHA of the round commit, empty if no commit' },
  },
  required: ['verdicts','changed_files','tests_green','commit_sha'],
}

const COMMON = `## Common Rules
Output format: use the Full format below exactly (put it in report_markdown) and also list every finding in the structured findings array.
Severity tokens: Blocker (cannot merge: data loss, security hole, broken contract, crash), Critical (must fix before merge: high-impact logic error), High (fix before merge by default: unsound assumptions, weak coverage of critical paths), Medium (quality issue: pattern violation, small coverage gap), Low (nice to have), Nit (style only).
Types: Bug, Reliability, Security, Performance, Maintainability, Test, Style, Architecture, Spec, Docs.
Read the code, not only the diff: read changed files in full and the files the changed code calls or references.
Proof before a confident fix: prove a concrete fix with a primary source (official docs, working code of the repo, or a throwaway test, e.g. python3 -c ...). Otherwise frame it as a theory.
Fix plan for each finding: approach in 1-3 sentences, not code; name files to change and the existing code that solves the same case (path:line); name the test or command that shows the fix works. Do NOT edit any file.
Ask, do not guess: if material is insufficient, file a question as a finding (Docs/Spec, Low, higher if blocking).
Missing tests: name missing tests or weak coverage explicitly, type Test.
Report every finding at every severity, with the input/state and the wrong result.
Reviewer model footer: end the report with exactly: Review made by \`<MODEL>\`

## Full format
# Review by AI Agent (Round-<N>) — <target-summary>
## Description  (100-200 chars)
## Summary table  | # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
## Details per item  (### <#> header; Problem, Impact, Confidence, Recommendation, Verification source, Fix plan)
## Conclusion  (Must fix before merge / Acceptable risks / Needs discussion — lists of #)
## Final verdict  (one of: ✅ **Approve** | ✅➕ **Approve with suggestions** | 🕒 **Wait for author** | ❌ **Reject**)
## Reviewer model`

const FIXER_RULES = `Rules (follow word for word):
- Classify each finding as APPLY, PARTIAL, or REJECT before you touch any file.
  - APPLY: a primary source proves the finding: official docs, a known working example, the working code of the repository, CLAUDE.md, or a throwaway test. Apply the fix as described.
  - PARTIAL: the finding is partly correct, but the proposed fix needs a change. Apply the proven part, and note what you changed.
  - REJECT: no primary source proves the finding, or the finding is ambiguous, or it rests on pattern matching only. Do not apply it. Report the reason for the rejection.
- Never touch unrelated files. Edit only the files that the triage names, plus a directly related supporting file that the fix structurally needs (e.g. the matching test file for a test-coverage finding). Do not start unrelated refactors.
- Do not over-fix. Fix the named issue only.
- Be honest about uncertainty. Mark an ambiguous finding as PARTIAL or REJECT, with reasons.
- After each fix, make sure the edit matches the intent of the reviewer. If unclear, keep only the proven part (PARTIAL) or undo (REJECT), with the open question in the reason.
- Report the verdict of every finding, REJECT included.
- Make no critical decision alone that the triage does not allow (public signature change, new dependency, weaker test assertion). If a fix needs a design decision the user has not made, REJECT it with reason "needs user decision".
Read ${DISCIPLINE} before your first edit.
After the edits: run the test command from CLAUDE.md (python3 -m unittest discover -s tests) in ${REPO} and report the tail and whether it is green.
Then, if you changed any file, commit ONLY the changed files with explicit paths (never git add -A or git add .), on the current branch, never push. Commit message:
  Review round <N>: Fix <short summary>

  <optional 1-3 lines on the most significant fix>

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Commit even if tests fail (the orchestrator investigates). Return the commit SHA.`

function triage(findings, round) {
  const fix = [], deferred = []
  for (const f of findings) {
    const high = ['Blocker','Critical','High'].includes(f.severity)
    const take = high || f.severity === 'Medium' || f.conclusion === 'must_fix'
    const blocking = high || f.conclusion === 'must_fix'
    const item = { ...f, round, blocking }
    if (take) fix.push(item); else deferred.push(item)
  }
  return { fix, deferred }
}

function findingLines(list) {
  return list.map(f => `- [${f.id}] ${f.severity} ${f.type} at ${f.file_line}: ${f.problem}\n  Fix plan: ${f.fix_plan}`).join('\n')
}

async function fixPass(round, fix, phaseName) {
  return agent(`You are the fixer of review round ${round} in the git repo ${REPO} (branch feature/paging). Apply the fixes below from their plans.

${USER_DECISION}

Findings cleared for a fix (each with the reviewer's plan):
${findingLines(fix)}

${FIXER_RULES.replace(/<N>/g, String(round))}`, { label: `fix:round-${round}`, phase: phaseName, schema: FIX, agentType: 'general-purpose' })
}

// ---------- Round 1 ----------
phase('Round 1 review')
const r1 = await agent(`You review a git branch. Repo: ${REPO}. Run the commands there.

## branch — Full branch diff against base
Scope: git diff origin/main...HEAD (run it; base SHA ${args.baseSha}). Round: Round 1. Use this value.
Find the problems that this diff brings in. Focus areas in priority order: 1. Bugs and logic errors (read changed files in full and files the changed code references, e.g. src/ranges.py named in the docstring). 2. Security. 3. Data integrity. 4. Performance. 5. DI lifetime. 6. Contract breaks. 7. Test coverage.
Coherence check (mandatory): read git log origin/main..HEAD and report breaks across commits.
Context: ${USER_DECISION} Report the page < 1 handling as a finding if the code does not meet it, with that as the fix plan.

${COMMON}

The diff:
${args.diff}`, { label: 'review:round-1', phase: 'Round 1 review', schema: FINDINGS, agentType: 'general-purpose' })

if (!r1) return { error: 'round 1 reviewer returned nothing (not covered)' }
const t1 = triage(r1.findings, 1)
log(`Round 1: ${r1.findings.length} findings, fix=${t1.fix.length}, deferred=${t1.deferred.length}`)

let fix1 = null
if (t1.fix.length) {
  phase('Round 1 fix')
  fix1 = await fixPass(1, t1.fix, 'Round 1 fix')
}

const result = { round1: { review: r1, triage: t1, fix: fix1 } }
if (!fix1 || !fix1.changed_files.length || !fix1.commit_sha) { result.stopReason = 'no edits in round 1'; return result }
if (!fix1.tests_green) { result.stopReason = 'tests not green after round 1 fix'; return result }

// ---------- Round 2: re-review of fix diff ----------
phase('Round 2 re-review')
const lines = t1.fix.map(f => {
  const v = (fix1.verdicts || []).find(x => x.id === f.id)
  return `- ${f.severity} ${v ? v.verdict : 'NO VERDICT'}: ${f.fix_plan}${v && v.verdict === 'REJECT' ? ' — fixer reason: ' + v.reason : ''}`
}).join('\n')
const r2 = await agent(`You re-review the fix commit of review round 1. Repo: ${REPO}.
Scope: git show ${fix1.commit_sha} (only the files it changed: ${fix1.changed_files.join(', ')}). Round: Round 2. Use this value.
Question: did each fix resolve its issue, with no new regression? Read the changed files in full.
Fix-pass findings of Round 1 (<severity> <verdict>: <fix plan>):
${lines}
Report a wrong REJECT as a finding only with a primary source, also outside the files of the fix commit.
${USER_DECISION}

${COMMON}`, { label: 'review:round-2', phase: 'Round 2 re-review', schema: FINDINGS, agentType: 'general-purpose' })
if (!r2) { result.stopReason = 'round 2 reviewer returned nothing (not covered)'; return result }
const t2 = triage(r2.findings, 2)
log(`Round 2: ${r2.findings.length} findings, fix=${t2.fix.length}, deferred=${t2.deferred.length}`)
result.round2 = { review: r2, triage: t2, fix: null }

if (t2.fix.length) {
  phase('Round 2 fix')
  result.round2.fix = await fixPass(2, t2.fix, 'Round 2 fix')
}
return result
