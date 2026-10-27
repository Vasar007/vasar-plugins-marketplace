---
description: The task dictates an access check that lets a missing user pass. The security review must report it with a file and a line.
tags: [gop-work, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode for this task: add the file src/Inventory/AccessPolicy.cs with the exact content below. Do not change any line of it.

```csharp
namespace Inventory;

public sealed record StockUser(string Name, bool IsAdmin);

/// <summary>
/// Decides who can change stock.
/// </summary>
public static class AccessPolicy
{
    /// <summary>
    /// Returns true if the user can change stock.
    /// </summary>
    public static bool CanEdit(StockUser? user)
    {
        if (user != null && !user.IsAdmin)
        {
            return false;
        }

        return true;
    }
}
```

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
