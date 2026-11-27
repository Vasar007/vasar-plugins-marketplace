export const meta = {
  name: 'review-loop-branch',
  description: 'Two-round review/fix loop on feature/paging vs main, with local commits only',
  phases: [{ title: 'Round 1' }, { title: 'Round 2' }],
}
const FINDINGS = {type:'object',properties:{findings:{type:'array',items:{type:'object',properties:{severity:{type:'string'},file:{type:'string'},line:{type:'number'},issue:{type:'string'},fixPlan:{type:'string'},blocking:{type:'boolean'}},required:['severity','file','issue','fixPlan']}}},required:['findings']}
const FIX = {type:'object',properties:{fixed:{type:'array',items:{type:'string'}},rejected:{type:'array',items:{type:'string'}},files:{type:'array',items:{type:'string'}},testsGreen:{type:'boolean'},testOutput:{type:'string'},commit:{type:'string'}},required:['fixed','rejected','files','testsGreen']}
const DECISION = 'Pre-approved user decision: for page < 1, page_slice (src/pager.py) must raise ValueError, consistent with its behavior for size <= 0.'
const RULES = 'Read CLAUDE.md first. Do not push. Stage explicit paths only.'
let prior = ''
const rounds = []
for (const n of [1, 2]) {
  phase(`Round ${n}`)
  const scope = n === 1 ? 'Review `git diff main...HEAD` (branch feature/paging).' : `Re-review only the files changed by the round ${n-1} fix commit (git show HEAD), and whether fixes resolved the issues without regressions. Previous fixes: ${prior}`
  const rev = await agent(`${scope}\n${DECISION}\nReport every finding with severity (Blocker|Critical|High|Medium|Low|Nit), file, line, issue, a fix plan (approach, not code), and blocking flag. Read-only: do not edit. ${RULES}`, {label:`review r${n}`, phase:`Round ${n}`, schema:FINDINGS})
  if (!rev || !rev.findings.length) { log(`round ${n}: no findings`); rounds.push({n, findings:[]}); break }
  const fix = await agent(`Fix the findings below on the current branch. For each, first prove it against a primary source (code, tests, docs); classify APPLY/PARTIAL/REJECT and fix only proven ones. No unrelated edits. ${DECISION} Then run the repo's tests per CLAUDE.md and report the result honestly. If you changed files, commit them locally with subject "Review round ${n}: Fix <summary>". Never push.\n${RULES}\nFindings:\n${JSON.stringify(rev.findings,null,1)}`, {label:`fix r${n}`, phase:`Round ${n}`, schema:FIX})
  rounds.push({n, findings:rev.findings, fix})
  if (!fix || !fix.files.length) break
  prior = fix.fixed.join('; ')
}
return rounds
