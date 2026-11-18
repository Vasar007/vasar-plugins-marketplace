# Rules for push, force push, and --no-verify

A skill of this marketplace pushes in three cases: the user says yes, the user passes a push flag such as `--push` or `--commit-push`, or the user passes `--autonomous`. Some skills that push say never to force-push, for example `process-pr-comments` and `feature-pipeline`. Some skills that commit say never to pass `--no-verify`. These rules are text in the skills. A plugin cannot ship permission rules, so the plugins cannot enforce them. To enforce them, add the rules below to your own configuration file, for example `~/.claude/settings.json`. Claude Code evaluates deny rules first, then ask rules, then allow rules, and the first match decides. A deny rule also applies to each part of a compound command (`&&`, `;`, `|`).

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

You can also add ask rules for a push. With these rules, Claude Code prompts you for each push. In `dontAsk` mode, it denies the push instead. The prompt appears also in an `--autonomous` run, and also after you said "push". If you want that cost, add them.

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

No skill of this marketplace merges a pull request on its own. The skill `merge-pr` merges only after you ask for the merge in your own words. The flag `--merge` of the workflow `feature-pipeline` also counts as that request, and the workflow calls the skill only with this flag. Before the merge, the skill makes sure that the checks of the pull request are green and that the merge state is clean. An `--autonomous` flag alone does not approve a merge. This rule is also only text. To get a prompt before each merge, add an ask rule for the merge tool of the GitHub MCP server:

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
