# Pauses and scheduled resume

If the run has pause points, a start time, or resume times, or if the user asks for a stop, the orchestrator reads this file. The facts about scheduled tasks come from the Claude Code docs: <https://code.claude.com/docs/en/scheduled-tasks>.

## Pause points

A pause point names a step boundary:

| Point | The run stops after |
| --- | --- |
| `1` | step 1 (isolation) |
| `2` | step 2 (report skeleton) |
| `3.K` | the hunter of area K |
| `4.P` | verifier part P |
| `4` | the last verifier part |
| `5` | the auditor |

Example: `--stop-after=3.3,3.4,3.5,4`. The user can also ask for a stop during the run. Then stop at the next boundary.

Earlier runs, for planning only: one hunter took about 25 to 60 minutes and 300k to 600k tokens. One verifier part took about 15 to 35 minutes. The auditor took about 10 to 15 minutes.

## At a pause point

1. Run the structure check of the step, as at any step boundary.
2. Update the session progress file. Write the pause into `## NEXT`, for example: "Paused after 3.3. Do not continue until the user says so, or until resume job <ID> fires at 17:01. Then run 3.4."
3. Write one status line in chat, and end the turn.

A restarted session reads `## NEXT` and waits. It does not continue on its own.

## Scheduled resume and start

If the user gives a resume time or a start time, schedule a one-shot job with the `CronCreate` tool.

1. Run `CronList` first. If a job for this run already exists, do not create another one. Two jobs give two resumes. After a restart, `claude --resume` restores the one-shot jobs whose time did not pass.
2. If the time follows a usage-limit reset, choose a minute 1 to 3 minutes after the reset, for example 07:01 for a reset at 07:00. A one-shot job at minute 00 or 30 can fire up to 90 seconds early.
3. Write a self-contained prompt. Fill `<report folder>` and `{SKILL_DIR}` with absolute paths:

   ```text
   Resume the bug hunt. If <report folder>/_bug-hunt-session-progress.md does not exist,
   do nothing. Else read it first. If its NEXT section says "Waiting for agent", and this
   session dispatched that agent, and the progress file of that agent changed in the last 30
   minutes (or the dispatch time in the note is less than 30 minutes ago, if the agent has
   no progress file yet), write one line to chat that names the agent and end the turn. Else
   follow "Resume check" in {SKILL_DIR}/references/resume-and-failures.md: run the check
   from point 1. At point 4, the agent stopped, so go to point 5. Then continue from its NEXT section. This
   scheduled prompt is the OK of the user for these steps: <steps>. Stop at <the next pause
   point, or "the end of the run">.
   ```

4. Write the job ID, the time, and the steps into the session progress file. Step 6 of the run deletes each of these jobs with `CronDelete`.

A start time works the same way. After the OK to the meta-plan, write the session progress file, schedule the job for step 1, and end the turn.

The main session can reach its own usage limit while it waits for an agent. If the user gives the reset times, schedule a resume job for 1 to 3 minutes after each reset. The run then goes on without a wait for the user.

Limits from the docs:

- A job fires only while Claude Code runs and is idle. If the user closes the session, the job does not fire until `claude --resume` restores it.
- A job fires between turns. If the session is busy, the job waits until the turn ends. A job can fire while a background agent runs. The prompt above then does nothing, because the progress file of the agent is recent. After a crash, the progress file stops changing, so after 30 minutes the job dispatches a new agent of the same role.
- Times are in the local time zone.
- The environment variable `CLAUDE_CODE_DISABLE_CRON=1` turns the tools off. If the cron tools are not available, tell the user, and wait for the user at each pause point.
