# Rules for push, force push, and --no-verify

A skill of this marketplace pushes only in these cases. The user says yes, or passes a push flag such as `--commit-push`, or picks the full mode with `--mode full`. Some skills that push say never to force-push, for example `process-pr-comments` and `feature-pipeline`. Some skills that commit say never to pass `--no-verify`. These rules are text in the skills. A plugin cannot ship permission rules, so the plugins cannot enforce them. To enforce them, add the rules below to your own configuration file, for example `~/.claude/settings.json`. Claude Code evaluates deny rules first, then ask rules, then allow rules, and the first match decides. A deny rule also applies to each part of a compound command (`&&`, `;`, `|`).

```json
{
  "permissions": {
    "deny": [
        "Bash(git push --force*)",
        "Bash(git push * --force*)",
        "Bash(git push -f*)",
        "Bash(git push * -f*)",
        "Bash(git -C * push --force*)",
        "Bash(git -C * push * --force*)",
        "Bash(git -C * push -f*)",
        "Bash(git -C * push * -f*)",
        "Bash(* --no-verify*)",
        "PowerShell(git push --force*)",
        "PowerShell(git push * --force*)",
        "PowerShell(git push -f*)",
        "PowerShell(git push * -f*)",
        "PowerShell(git -C * push --force*)",
        "PowerShell(git -C * push * --force*)",
        "PowerShell(git -C * push -f*)",
        "PowerShell(git -C * push * -f*)",
        "PowerShell(* --no-verify*)"
    ]
  }
}
```

You can also add ask rules for a push. With these rules, Claude Code prompts you for each push. In `dontAsk` mode, it denies the push instead. The prompt appears also in a run in the full mode, and also after you said "push". If you want that cost, add them.

```json
{
  "permissions": {
    "ask": [
        "Bash(git push *)",
        "Bash(git -C * push *)",
        "PowerShell(git push *)",
        "PowerShell(git -C * push *)"
    ]
  }
}
```

These rules guard the usual form of a command. They are not a security boundary. A rule matches the command text that Claude writes. It does not match other forms, for example `git -c push.default=current push`, a `+` refspec such as `git push origin +main`, or `git commit -n`. A rule with `*` also blocks a command that only contains the text, for example a commit message that names `--no-verify`. Then write the message to a file, and commit with `git commit -F <file>`. A force push that you want is blocked by the deny rules. Run it in your own terminal. See the [permissions page](https://code.claude.com/docs/en/permissions) of the Claude Code documentation for the rule syntax.

## A merge of a pull request

No skill of this marketplace merges a pull request on its own. The skill `merge-pr` merges only after you ask for the merge in your own words. If you pick the full mode of a workflow in your request, with `--mode full` or in plain words, that also counts as that request. These workflows are `feature-pipeline`, `research-implement-review-report`, `implement-task`, and `implement-batch`. A workflow calls the skill only in the full mode, or after you asked for the merge. In the other modes, the last three workflows ask you about the merge at their end, and your yes is such a request. Before the merge, the skill makes sure that the checks of the pull request are green and that the merge state is clean. A rule in a project file or in a memory file never picks the full mode. This rule is also only text. To get a prompt before each merge, add an ask rule for the merge tool of the GitHub MCP server:

```json
{
  "permissions": {
    "ask": [
        "mcp__plugin_github_github__merge_pull_request"
    ]
  }
}
```

In `dontAsk` mode, Claude Code denies the merge instead. To forbid each merge, put the same rule in the `deny` list.
