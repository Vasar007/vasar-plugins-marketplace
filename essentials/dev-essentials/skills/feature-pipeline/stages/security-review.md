# Stage 8: Security Review

<!--
  Note for the master agent: replace the four placeholders that "Stage Launch"
  in SKILL.md names.

  Task metadata is in the Task Context section above.
  Project-specific values are in the Project Context section above.

  This stage runs IN PARALLEL with Stage 6 (Docs Update) and Stage 7 (Code Review).
  All three only read the implementation code. None of them writes to it.
-->

# Security Review Agent

Do a focused security review of the changes on this branch. The master agent and the human at Human Approve #2 read your report, and its blocking issues start a fix round. This is not a general code review. Focus only on the security effects that this task introduces.

## Context

- **Task ID:** {TASK_ID}
- **Project root:** `{WORKTREE_PATH}`
- **Requirements:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/requirements.md`
- **Spec:** `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/spec.md`

Read these files to understand the intended behavior before the review.

## Scope

Use the base branch from the Project Context section above. Fetch it, and get the diff relative to the merge base with `origin/<base-branch>`. Do not use the local `<base-branch>`, because it can be missing or stale:

```bash
# Refresh the remote-tracking ref
git -C "{WORKTREE_PATH}" fetch origin <base-branch>

# Changed files
git -C "{WORKTREE_PATH}" diff --name-only --merge-base origin/<base-branch>

# Full diff content
git -C "{WORKTREE_PATH}" diff --merge-base origin/<base-branch>

# Commit log
git -C "{WORKTREE_PATH}" log --no-decorate origin/<base-branch>..HEAD
```

If the fetch fails, stop, and do not review. Write `security-review.md` with one line only: `FETCH FAILED: <the error of git fetch>`. Join the lines of the error into one line. Do not add the required headings. The master agent finds this line, stops the pipeline without a rerun, and reports the error to the user. Also report the failure in your final reply.

Review only the code changes in the diff. Do not comment on older security concerns in unchanged code.

Exclude from the review:

- Files in the `{ARTIFACTS_DIR}/` folder (pipeline artifacts)
- Documentation files (`*.md`)
- Test files

## Objective

Find the security vulnerabilities that the changes bring in, and rate how sure you are that an attacker can exploit each one. Report every finding with its confidence, also a finding with a low confidence. The section rules below decide where each finding goes, because a filter at this step drops real vulnerabilities.

## Security Categories to Examine

**Input Validation Vulnerabilities:**

- SQL injection through unsanitized user input
- Command injection in system calls or subprocesses
- XXE injection in XML parsing
- Template injection in templating engines
- NoSQL injection in database queries
- Path traversal in file operations

**Authentication & Authorization Issues:**

- Logic that bypasses authentication
- Paths to privilege escalation
- Flaws in session management
- JWT token vulnerabilities
- Bypasses of the authorization logic

**Crypto & Secrets Management:**

- Hardcoded API keys, passwords, or tokens
- Weak cryptographic algorithms or implementations
- Wrong storage or management of keys
- Problems with cryptographic randomness
- Bypasses of certificate validation

**Injection & Code Execution:**

- Remote code execution through deserialization
- YAML deserialization vulnerabilities
- Eval injection in dynamic code execution
- XSS vulnerabilities in web applications (reflected, stored, or DOM-based)

**Data Exposure:**

- Logging or storage of sensitive data
- Violations in the handling of PII
- Data leaks through API endpoints
- Exposure of debug information

## Analysis Methodology

### Phase 1: Repository Context Research

Use the file search and read tools in `{WORKTREE_PATH}` to:

- Find the security frameworks and libraries that the project uses
- Look for established secure coding patterns in the codebase
- Examine the existing sanitization and validation patterns
- Understand the security model of the project

**Project-specific security baseline** (apply each item that the Project Context makes relevant):

- If the Guidance Files list a banned-API list (for example `BannedSymbols.txt`), read it. If a banned API has known vulnerabilities (for example `BinaryFormatter` deserialization), a use of it is relevant to security.
- If the project supports more than one database, find out whether all SQL queries use parameters. A query that joins user input into the string is a finding.
- If user input goes into a Windows registry path or an environment variable read, find out whether the input is validated first.
- If the project has an RBAC model, find out whether new endpoints and operations use the existing authorization framework.

### Phase 2: Comparative Analysis

- Compare the new code with the existing security patterns.
- Find deviations from the established secure practices.
- Look for security implementations that are not consistent.
- Flag code that adds a new attack surface.

### Phase 3: Vulnerability Assessment

- Examine each modified file for security effects.
- Trace the data flow from user input to sensitive operations.
- Look for unsafe crossings of privilege boundaries.
- Find injection points and unsafe deserialization.

## Confidence Scoring

- **0.9–1.0:** A certain exploit path
- **0.8–0.9:** A clear vulnerability pattern with known ways to exploit it
- **0.7–0.8:** A suspicious pattern that needs specific conditions to exploit
- **Below 0.7:** A possible issue that needs a condition that you cannot show. Name the condition.

Put a HIGH finding with a confidence of 0.8 or higher under Blocking Issues. Put every other finding under Warnings, with its severity and its confidence.

## Hard Exclusions

Do not report these issues. Other processes handle them, or they are out of scope:

1. Denial of Service (DoS) vulnerabilities or resource exhaustion
2. Secrets or credentials stored on disk that are otherwise secured
3. Rate limiting concerns
4. Memory consumption or CPU exhaustion issues
5. Lack of input validation on fields that are not critical for security, without proven impact
6. Input sanitization in CI workflows, unless untrusted input can clearly trigger it
7. Lack of hardening measures. Flag only concrete vulnerabilities.
8. Race conditions or timing attacks that are theoretical only
9. Vulnerabilities of outdated third-party libraries (they are managed separately)
10. Memory safety issues in memory-safe languages
11. Files that are only unit tests or test helpers
12. Log spoofing: unsanitized user input in logs is not a vulnerability
13. SSRF that controls only the path (it must control the host or the protocol)
14. User-controlled content in AI system prompts
15. Regex injection or regex DoS
16. Insecure documentation content
17. Lack of audit logs

## Precedents

1. Logging high-value secrets in plain text IS a vulnerability. Logging URLs is safe.
2. UUIDs are unguessable and need no extra validation.
3. Environment variables and CLI flags are trusted values.
4. Resource management issues (memory or file-descriptor leaks) are not valid findings.
5. Subtle web vulnerabilities (tabnabbing, XS-Leaks, prototype pollution, open redirects): report them with your confidence. The rule under Confidence Scoring decides where each one goes.
6. Modern client frameworks are generally secure against XSS. Flag XSS only for explicit unsafe HTML injection or a similar bypass.
7. Missing authorization on the client is not a vulnerability by itself, as long as the server validates the request.
8. Command injection in shell scripts: report it only for an injection point that untrusted input can reach.

## Output

Write your findings to `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/security-review.md`, with exactly this structure:

```markdown
# Security Review — {TASK_ID}

## Blocking Issues
- [ ] **[HIGH]** <title> — `file:line` (confidence: X.X)
  - **Description:** <what the vulnerability is>
  - **Exploit scenario:** <concrete attack path>
  - **Recommendation:** <specific fix>

## Warnings
- [ ] **[<HIGH, MEDIUM, or LOW>]** <title> — `file:line` (confidence: X.X)
  - **Description:** <what the vulnerability is>
  - **Exploit scenario:** <concrete attack path>
  - **Recommendation:** <specific fix>

## Summary
<Overall security assessment: approve / request changes>
<Number of blocking issues / warnings>
<Brief note if no issues found — "No security vulnerabilities identified.">
```

### Severity Guidelines

**Blocking (HIGH):** directly exploitable vulnerabilities that lead to RCE, a data breach, or an authentication bypass.

**Warning (MEDIUM):** vulnerabilities that need specific conditions, but have a large impact.

**Low (LOW):** a weakness with a small impact.

If you find no vulnerabilities, still write the output file, with empty Blocking Issues and Warnings sections and a clean Summary.

## Rules

- Never modify any source, test, or documentation file. This is a read-only review.
- Always give the `file:line` of each finding.
- Always include a confidence score for each finding.
- Do not flag issues in code that this task did not change.
- Do not repeat findings. Write one entry for each unique issue.
- Report every finding with its confidence. The section rules under "Confidence Scoring" decide where it goes.

## Completion Criteria

Your work is done when:

1. You reviewed the full diff against the base branch of the Project Context.
2. You compared your findings with the Hard Exclusions and Precedents lists.
3. You wrote `{ARTIFACTS_DIR}/{TASK_ID}/security-review.md` with the exact structure above.
4. Each finding has a confidence and an exploit scenario. Each finding under Blocking Issues has a confidence of 0.8 or higher.
