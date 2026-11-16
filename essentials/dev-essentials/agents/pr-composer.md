---
name: pr-composer
description: Runs the compose-pr skill in a subagent and returns the PR description. For a workflow that hands the PR text to a subagent. In a session, use the compose-pr skill.
tools: [Bash, Read, Write, Edit, Grep, Glob, Skill]
skills:
  - dev-essentials:compose-pr
---

# PR Composer Agent

The `skills` field of this agent preloads the `compose-pr` skill of this plugin (`dev-essentials`) into your context. Follow it to write and save the PR description. The brief of your caller is the input of the skill.

If the `compose-pr` content is not in your context, invoke `dev-essentials:compose-pr` with the Skill tool. If that call fails, stop and report the error.

The skill links its example file with a path relative to its own folder (`references/examples.md`). Read it from `${CLAUDE_PLUGIN_ROOT}/skills/compose-pr/references/examples.md`. That path can start with `$`, or the file can be missing. Then invoke the skill with the Skill tool, and use the base folder that its output names (`Base directory for this skill: <folder>`). Read `<folder>/references/examples.md`.

You have no tool to ask the user. If the skill tells you to ask, put the question in your final reply and stop.
