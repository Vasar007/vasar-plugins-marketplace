# BuildEnvironment Pattern

Steps for a compile-time switch that business code needs. `SKILL.md` points here.

## BuildEnvironment Pattern

For compile-time environment-specific configuration, use the `BuildEnvironment` + `BuildEnvironmentInfo` pattern:

### Step 1: BuildEnvironment Static Class

```csharp
// BuildEnvironment.cs
public static class BuildEnvironment
{
    public const Boolean IsDebugConst =
#if DEBUG
        true;
#else
        false;
#endif

    public const Boolean UseFeatureXConst =
#if USE_FEATURE_X
        true;
#else
        false;
#endif
}
```

### Step 2: BuildEnvironmentInfo Singleton (for DI/testing)

```csharp
// BuildEnvironmentInfo.cs
public sealed class BuildEnvironmentInfo : I{ServiceName}BuildEnvironmentInfo
{
    public static BuildEnvironmentInfo Instance { get; } = new();

    /// <inheritdoc cref="BuildEnvironment.IsDebugConst"/>
    public Boolean IsDebugBuild => BuildEnvironment.IsDebugConst;

    /// <inheritdoc cref="BuildEnvironment.UseFeatureXConst"/>
    public Boolean UseFeatureX => BuildEnvironment.UseFeatureXConst;

    private BuildEnvironmentInfo()
    {
    }
}
```

### Step 3: Interface for Testing

```csharp
// I{ServiceName}BuildEnvironmentInfo.cs
public interface I{ServiceName}BuildEnvironmentInfo
{
    Boolean IsDebugBuild { get; }
    Boolean UseFeatureX { get; }
}
```

Avoid `#if` pragmas in business code. Inject `I{ServiceName}BuildEnvironmentInfo` instead:

```csharp
// ✅ Good - testable
public sealed class MyService
{
    private readonly I{ServiceName}BuildEnvironmentInfo _buildInfo;

    public MyService(
        I{ServiceName}BuildEnvironmentInfo buildInfo)
    {
        _buildInfo = buildInfo.ThrowIfNull();
    }

    public void DoWork()
    {
        if (_buildInfo.UseFeatureX)
        {
            // Feature X logic
        }
    }
}

// ❌ Bad - not testable
public sealed class MyService
{
    public void DoWork()
    {
#if USE_FEATURE_X
        // Feature X logic
#endif
    }
}
```
