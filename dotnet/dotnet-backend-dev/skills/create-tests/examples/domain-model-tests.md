# Domain Model Tests - BaseEqualityMemberTests\<T\>

Use `BaseEqualityMemberTests<T>` for **all** domain models implementing `IEquatable<T>` and `IEqualityOperators<T, T, Boolean>`.

**MANDATORY:** If the model implements these interfaces, the test class MUST inherit from `BaseEqualityMemberTests<T>`. Do NOT inherit from `BaseTest` or `BaseMockTest` for such models.

## Base Class

Location: `MyApp.OnlyForTests.Basic.Equality.BaseEqualityMemberTests<T>`

Type constraint: `where TValue : IEquatable<TValue>, IEqualityOperators<TValue, TValue, Boolean>`

Provides automatic tests for:

- Equality operators (`==`, `!=`)
- `Equals()` method (same object, identical objects, different objects, null/default, different type)
- `GetHashCode()` consistency (same, identical, different, mutator-based)
- `ToString()` consistency (same vs different objects)
- Field-level inequality via `GetValueMutatorsForInequality()`
- Field-level equality via `GetValueMutatorsForEquality()`

## Required Override

There is only **one** abstract method to implement:

```csharp
/// <summary>
/// Creates a unique, fully populated instance. Each call MUST return a different instance
/// (different equality-significant fields) so the base class can test inequality.
/// </summary>
protected abstract TValue CreateUniqueValue();
```

**NOTE:** `CreateConstantValue()` is already provided by the base class — it lazily caches the first `CreateUniqueValue()` call. Do NOT override it.

## Optional Overrides (Mutators)

Override these to test field-level equality semantics:

```csharp
/// <summary>
/// Yields mutators that change fields that AFFECT equality (important fields).
/// Base class asserts: mutated value != original, hash codes differ.
/// </summary>
protected virtual IEnumerable<Func<TValue, TValue>> GetValueMutatorsForInequality()
{
    yield break; // default: no mutators
}

/// <summary>
/// Yields mutators that change fields that DO NOT affect equality (unimportant fields).
/// Base class asserts: mutated value == original, hash codes are same.
/// </summary>
protected virtual IEnumerable<Func<TValue, TValue>> GetValueMutatorsForEquality()
{
    yield break; // default: no mutators
}
```

## Complete Example (Simple record — all fields affect equality)

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.Domain.Appliances.Deployment.Resources;
using MyApp.Tests.Common.Helpers.Generators.Appliances;
using MyApp.Tests.Common.Helpers.Generators.Aws.Deployments;
using MyApp.OnlyForTests.Basic.Equality;

namespace MyApp.Domain.Tests.Appliances.Deployment.Resources;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class ApplianceDeploymentResourcesTests : BaseEqualityMemberTests<ApplianceDeploymentResources>
{
    private readonly ApplianceGenerator _applianceGenerator;
    private readonly DeploymentGenerator _deploymentGenerator;

    public ApplianceDeploymentResourcesTests()
    {
        _applianceGenerator = new ApplianceGenerator();
        _deploymentGenerator = new DeploymentGenerator();
    }

    [Test]
    public void Constructor_SetsPropertiesCorrectly()
    {
        // Arrange.
        var computeAccountDeploymentId = GenerateDeploymentId();
        var serverVpcDeploymentId = GenerateDeploymentId();
        var rdsVpcDeploymentId = GenerateDeploymentId();
        var rdsClusterDeploymentId = GenerateDeploymentId();
        var applianceId = GenerateApplianceId();

        // Act.
        var resources = CreateApplianceDeploymentResources(
            computeAccountDeploymentId: computeAccountDeploymentId,
            serverVpcDeploymentId: serverVpcDeploymentId,
            rdsVpcDeploymentId: rdsVpcDeploymentId,
            rdsClusterDeploymentId: rdsClusterDeploymentId,
            applianceId: applianceId
        );

        // Assert.
        resources.Should().NotBeNull();
        resources.ComputeAccountDeploymentId.Should().Be(computeAccountDeploymentId);
        resources.ServerVpcDeploymentId.Should().Be(serverVpcDeploymentId);
        resources.RdsVpcDeploymentId.Should().Be(rdsVpcDeploymentId);
        resources.RdsClusterDeploymentId.Should().Be(rdsClusterDeploymentId);
        resources.ApplianceId.Should().Be(applianceId);
    }

    [Test]
    public void ToString_ShouldReturnStringContainingAllProperties()
    {
        // Arrange.
        var resources = CreateUniqueValue();

        // Act.
        var stringRepresentation = resources.ToString();

        // Assert.
        stringRepresentation.Should().NotBeNullOrEmpty();
        stringRepresentation.Should().Contain(nameof(ApplianceDeploymentResources));
        stringRepresentation.Should().Contain(nameof(ApplianceDeploymentResources.ComputeAccountDeploymentId));
        stringRepresentation.Should().Contain(resources.ComputeAccountDeploymentId.ToString());
        stringRepresentation.Should().Contain(nameof(ApplianceDeploymentResources.ServerVpcDeploymentId));
        stringRepresentation.Should().Contain(resources.ServerVpcDeploymentId.ToString());
    }

    // --- BaseEqualityMemberTests overrides ---

    protected override ApplianceDeploymentResources CreateUniqueValue()
    {
        return _applianceGenerator.GenerateApplianceDeploymentResources();
    }

    protected override IEnumerable<Func<ApplianceDeploymentResources, ApplianceDeploymentResources>> GetValueMutatorsForInequality()
    {
        yield return x => x with { ComputeAccountDeploymentId = GenerateDeploymentId() };
        yield return x => x with { ServerVpcDeploymentId = GenerateDeploymentId() };
        yield return x => x with { RdsVpcDeploymentId = GenerateDeploymentId() };
        yield return x => x with { RdsClusterDeploymentId = GenerateDeploymentId() };
        yield return x => x with { ApplianceId = GenerateApplianceId() };
    }

    // NOTE: Do NOT override GetValueMutatorsForEquality — only needed when some fields are excluded from equality

    // --- Private helpers ---

    private ApplianceDeploymentResources CreateApplianceDeploymentResources(
        DeploymentId computeAccountDeploymentId,
        DeploymentId serverVpcDeploymentId,
        DeploymentId rdsVpcDeploymentId,
        DeploymentId rdsClusterDeploymentId,
        ApplianceId applianceId)
    {
        return _applianceGenerator.CreateApplianceDeploymentResources(
            computeAccountDeploymentId: computeAccountDeploymentId,
            serverVpcDeploymentId: serverVpcDeploymentId,
            rdsVpcDeploymentId: rdsVpcDeploymentId,
            rdsClusterDeploymentId: rdsClusterDeploymentId,
            applianceId: applianceId
        );
    }

    private DeploymentId GenerateDeploymentId()
    {
        return _deploymentGenerator.GenerateDeploymentId();
    }

    private ApplianceId GenerateApplianceId()
    {
        return _applianceGenerator.GenerateApplianceId();
    }
}
```

## Complete Example (Complex model — some fields are excluded from equality)

When a model has fields that do NOT affect equality (e.g., mutable properties like Name, Status), **only then** override `GetValueMutatorsForEquality()`:

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.Domain.Workload.Tenants;
using MyApp.Tests.Common.Helpers.Generators.Workload.Tenants;
using MyApp.OnlyForTests.Basic.Equality;

namespace MyApp.Domain.Tests.Workload.Tenants;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class TenantTests : BaseEqualityMemberTests<Tenant>
{
    private readonly TenantGenerator _tenantGenerator;
    private readonly ApplianceGenerator _applianceGenerator;
    private readonly OrganizationGenerator _organizationGenerator;
    private readonly ManagementRegionGenerator _managementRegionGenerator;

    public TenantTests()
    {
        _tenantGenerator = new TenantGenerator();
        _applianceGenerator = new ApplianceGenerator();
        _organizationGenerator = new OrganizationGenerator();
        _managementRegionGenerator = new ManagementRegionGenerator();
    }

    // --- BaseEqualityMemberTests overrides ---

    protected override Tenant CreateUniqueValue()
    {
        return _tenantGenerator.GenerateTenant();
    }

    protected override IEnumerable<Func<Tenant, Tenant>> GetValueMutatorsForInequality()
    {
        // Fields that AFFECT equality — changing them makes instances unequal
        yield return x => x with { TenantId = GenerateTenantId() };
        yield return x => x with { ManagementRegionId = _managementRegionGenerator.GenerateManagementRegionId() };
        yield return x => x with { CreatedTime = x.CreatedTime.AddDays(1) };
    }

    protected override IEnumerable<Func<Tenant, Tenant>> GetValueMutatorsForEquality()
    {
        // Fields that DO NOT affect equality — changing them keeps instances equal
        yield return x => CreateTenant(x.TenantId, GenerateTenantName(), x.ManagementRegionId, x.Status, x.TenantAppliance, x.Organizations, x.CreatedTime, x.DeployedResources);
        yield return x => CreateTenant(x.TenantId, x.TenantName, x.ManagementRegionId, x.Status.SelectOtherUniqueEnumValue(), x.TenantAppliance, x.Organizations, x.CreatedTime, x.DeployedResources);
        yield return x => CreateTenant(x.TenantId, x.TenantName, x.ManagementRegionId, x.Status, GenerateAppliance(), x.Organizations, x.CreatedTime, x.DeployedResources);
    }

    // --- Additional tests beyond automatic equality tests ---

    [Test]
    public void Constructor_Sets_Properties_Correctly()
    {
        // Arrange.
        var tenantId = GenerateTenantId();
        var tenantName = GenerateTenantName();
        // ...

        // Act.
        var tenant = CreateTenant(tenantId: tenantId, tenantName: tenantName, ...);

        // Assert.
        tenant.Should().NotBeNull();
        tenant.TenantId.Should().Be(tenantId);
        tenant.TenantName.Should().Be(tenantName);
    }

    [Test]
    public void ToString_ShouldReturnStringContainingAllProperties()
    {
        // Arrange.
        var tenant = CreateUniqueValue();

        // Act.
        var stringRepresentation = tenant.ToString();

        // Assert.
        stringRepresentation.Should().NotBeNullOrEmpty();
        stringRepresentation.Should().Contain(nameof(Tenant));
        stringRepresentation.Should().Contain(nameof(Tenant.TenantId));
        stringRepresentation.Should().Contain(tenant.TenantId.ToString());
        // ... check all properties
    }

    // --- Private helpers ---

    private TenantId GenerateTenantId() => _tenantGenerator.GenerateTenantId();
    private TenantName GenerateTenantName() => _tenantGenerator.GenerateTenantName();
    private Appliance GenerateAppliance() => _applianceGenerator.GenerateAppliance();

    private Tenant CreateTenant(
        TenantId tenantId,
        TenantName tenantName,
        ManagementRegionId managementRegionId,
        TenantStatus status,
        Appliance appliance,
        IReadOnlyList<Organization> organizations,
        DateTimeUtc createdTime,
        TenantDeployedResources deployedResources)
    {
        return _tenantGenerator.CreateTenant(
            tenantId: tenantId,
            tenantName: tenantName,
            managementRegionId: managementRegionId,
            status: status,
            appliance: appliance,
            organizations: organizations,
            createdTime: createdTime,
            deployedResources: deployedResources
        );
    }
}
```

## Key Points

1. **MANDATORY inheritance** — if model implements `IEquatable<T>` + `IEqualityOperators`, the test MUST use `BaseEqualityMemberTests<T>`

2. **Only one abstract method** — `CreateUniqueValue()`. Each call must return a distinct instance (different equality-significant fields). The base class calls this multiple times to test inequality

3. **`CreateConstantValue()`** — provided by the base class, returns the same cached instance. Used by the base to test that identical instances are equal. Do NOT override

4. **Mutators for inequality** — override `GetValueMutatorsForInequality()` to yield `with` expressions that change one equality-significant field at a time. The base asserts these produce unequal instances

5. **Mutators for equality** — override `GetValueMutatorsForEquality()` **only** when the model has fields excluded from equality (e.g., mutable Name, Status). If all fields participate in equality, do NOT override — omit it entirely

6. **Additional tests** — add Constructor, ToString, method behavior tests as `[Test]` methods alongside the automatic equality tests

7. **Private helpers** — all generator/factory calls via private methods, same rules as everywhere

8. **When unsure about the pattern** — read the [examples/](examples/) folder first. If no matching example exists, search existing tests in the repo's Domain.Tests project (typically under `Sources/Tests/<Project>.Domain.Tests/` or `Tests/<Project>.Domain.Tests/`) to find a similar test class and follow its pattern
