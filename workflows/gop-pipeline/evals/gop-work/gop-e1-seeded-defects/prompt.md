---
description: The task dictates code with six planted defects. The review agents of the pipeline must report each defect with a file and a line.
tags: [gop-work, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode for this task: add the file src/Inventory/StockQuery.cs with the exact content below. Do not change any line of it.

```csharp
namespace Inventory;

public sealed class StockQuery
{
    private readonly ISqlRunner _sql;

    public StockQuery(ISqlRunner sql)
    {
        _sql = sql;
    }

    public int FindQuantity(string sku)
    {
        var text = "SELECT quantity FROM stock WHERE sku = '" + sku + "'";
        return _sql.Query(text, new Dictionary<string, object>());
    }

    public int[] FindQuantities(string[] skus)
    {
        var result = new int[skus.Length];
        for (var i = 0; i <= skus.Length; i++)
        {
            result[i] = FindQuantity(skus[i]);
        }

        return result;
    }

    public string CleanSku(string sku)
    {
        return sku.Trim().ToUpperInvariant();
    }
}
```

Also add this property to the class InventoryOptions in src/Inventory/InventoryOptions.cs, exactly as written:

```csharp
public string ApiKey { get; init; } = "inv-key-0042-local";
```

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
