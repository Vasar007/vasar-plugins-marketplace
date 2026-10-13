# Resume and failure handling

The orchestrator reads this file in three cases: the report folder holds `_bug-hunt-session-progress.md` at the start, an agent stops or fails, or a structure check fails.

## Resume check

1. Read `_bug-hunt-session-progress.md` and continue from its `## NEXT`. If it records the meta-plan approval, do not ask for it again. If `## NEXT` records a pause, do not continue. Wait for the user, or for the scheduled resume prompt that names this file.
2. If a snapshot or the digest is missing, run step 1 again in full with the commit SHAs from the progress file. If the recorded scratch folder still exists, use it. Else pick a scratch folder as step 0 point 2 of `SKILL.md` says. If the report already lists `N-NN` IDs, tell the collector to keep them. Then run the step-1 structure check.
3. Write the scratch folder path that is now in use into the progress file before you fill the next brief.
4. If `## NEXT` says "Waiting for agent <ID>", find out if that agent still runs. When this session dispatched it, and its progress file changed in the last 30 minutes (the modification time, not the creation time), it runs. If the agent has no progress file yet, use the dispatch time in the note instead. If the agent runs, write one line to chat: "Waiting for agent <ID> (<role>). If it stopped, say so." Then end the turn. A scheduled resume prompt that fires while the agent runs ends here. In all other cases, the agent stopped, for example after a crash or a restart. The user can also say that it stopped, or the agent reply can report a crash or a usage limit. Then go to point 5.
5. Restore the stopped agent as follows:
   - The scoping, setup, and cleanup helpers have no progress file. If one of them stopped, dispatch a new agent of the same role with the same brief and no resume note. These helpers are short and safe to run again.
   - For the collector, a hunter, a verifier, or the auditor, first send the resume note from [agent-briefs.md](agent-briefs.md) with `SendMessage` to the recorded agent ID. Then write into `## NEXT`: "Waiting for agent <ID> (<role>), restored <time>." The agent then continues with its full history and its progress file. After a restart of Claude Code, the user must resume the same session for this to work.
   - If no agent ID is recorded, or `SendMessage` fails or finds no agent, go on here. Look for the progress file of that agent for the step in `## NEXT`.
     - If the file exists, fill the brief for that role again from the recorded values. Add the resume note, and dispatch a new agent of the same role.
     - If the file does not exist, the agent finished or never started. Run the structure check of that step from [structure-checks.md](structure-checks.md). The work of the step is as follows. For the collector, the digest exists. For a hunter, the area is filled. For a verifier, no verdict is pending in the range. For the auditor, the stage `final` passes. If the check prints no DEFECT line and shows the work of the step, the step is done. Record it as done in the session progress file, and continue with the next step. If not, dispatch a new agent of the same role with the same brief and no resume note.

## Failure handling

- If an agent stops on a usage limit or crashes, restore it as point 5 of the resume check says.
- If a structure check fails, dispatch one repair agent of the same role. Give it the same brief and the repair note with the list of defects. If the check fails again, stop the run. Keep all files, and report the defects under "Blocked on me".
- If the collector cannot reach GitHub: without `--interactive`, continue with the notes files only, and write this limit into the Scope section. With `--interactive`, ask the user what to do. The user can reconnect the GitHub MCP server with `/mcp`, or continue with the notes files only. Do not fall back to another GitHub client.
- If an agent reports a blocker, such as a missing snapshot, fix the cause with the right helper. Then dispatch the agent again.
