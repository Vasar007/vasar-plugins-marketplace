# Test Model Generators

Use test model generators for creating consistent, valid test data. **Never create test data inline** - always use generators.

## Generator Pattern

Location: `Tests.Common/Helpers/Generators/{Feature}/`

```mermaid
Generators/
├── Appliances/
│   └── ApplianceGenerator.cs
├── Aws/
│   ├── CloudFormation/
│   │   └── Templates/
│   │       └── CloudResourceGenerator.cs
│   ├── Deployments/
│   │   └── DeploymentGenerator.cs
│   ├── Ec2/
│   │   └── ComputeInstanceGenerator.cs
│   ├── Iam/
│   │   └── IamIdentityGenerator.cs
│   ├── Network/
│   │   └── NetworkGenerator.cs
│   ├── Rds/
│   │   └── RdsInstanceGenerator.cs
│   ├── Regions/
│   │   └── RegionGenerator.cs
│   └── S3/
│       └── S3InfoGenerator.cs
├── Authentication/
│   ├── Auth0InfoGenerator.cs
│   └── AuthenticationInfoGenerator.cs
├── Sessions/
│   └── SessionGenerator.cs
├── Storage/
│   └── SmsModelGenerator.cs
├── Versioning/
│   ├── ProductVersionGenerator.cs
│   └── VersionInfoGenerator.cs
├── Backend/
│   └── Organizations/
│       └── OrganizationGenerator.cs
└── Workload/
    ├── Resources/
    │   └── ProvisionedResourceGenerator.cs
    └── Tenants/
        └── TenantGenerator.cs
```

## Generator Structure

```csharp
// Copyright (c) Vasily Vasilyev

using MyApp.OnlyForTests.Data.Generators;
using MyApp.OnlyForTests.Enumerations;

namespace MyApp.Tests.Common.Helpers.Generators.Aws.Regions;

public sealed class RegionGenerator
{
    /// <summary>
    /// Singleton instance for convenient access.
    /// </summary>
    public static RegionGenerator Instance { get; } = new();

    public RegionGenerator()
    {
    }

    // ============ Create methods - explicit parameters ============

    /// <summary>
    /// Creates model with explicit parameter values.
    /// Use when you need specific values for assertions.
    /// </summary>
    public Region CreateRegion(RegionId regionId)
    {
        return Region.FromId(regionId: regionId);
    }

    public RegionProvision CreateRegionProvision(RegionId regionId)
    {
        return new RegionProvision(regionId: regionId);
    }

    // ============ Generate methods - random/unique values ============

    /// <summary>
    /// Generates model with random unique values.
    /// Use when you just need a valid instance, values don't matter.
    /// </summary>
    public Region GenerateRegion()
    {
        return CreateRegion(regionId: GenerateRegionId());
    }

    public RegionProvision GenerateRegionProvision()
    {
        return CreateRegionProvision(regionId: GenerateRegionId());
    }

    // ============ Generate primitive values ============

    public RegionId GenerateRegionId()
    {
        // Select random from well-known, append GUID for uniqueness
        return WellKnownRegions.WellKnown.GetRandomItem(
            selectedRegion => RegionId.FromValue($"{selectedRegion.Id.Value}.{Guid.NewGuid()}")
        );
    }

    public RegionName GenerateRegionName()
    {
        return GenerateRegionId().ResolveRegionDisplayName();
    }
}
```

## Naming Conventions

| Method Prefix         | Purpose                                       | Example                     |
|-----------------------|-----------------------------------------------|-----------------------------|
| `Create{Model}`       | Explicit parameters - for specific assertions | `CreateRegion(regionId)` |
| `Generate{Model}`     | Random values - when values don't matter      | `GenerateRegion()`       |
| `Generate{Primitive}` | Random primitive wrapper values               | `GenerateRegionId()`     |

## Usage in Tests

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class RegionServiceTests : BaseMockTest
{
    private readonly RegionGenerator _generator;

    public RegionServiceTests()
    {
        // Use singleton instance
        _generator = RegionGenerator.Instance;
    }

    [Test]
    public async Task GetRegion_WithValidId_ReturnsRegion()
    {
        // Arrange.
        // ✅ Use Create when you need specific values for assertions
        var expectedRegionId = _generator.GenerateRegionId();
        var expectedRegion = _generator.CreateRegion(expectedRegionId);

        SetupRepositoryToReturn(expectedRegion);
        var sut = Fixture.Create<RegionService>();

        // Act.
        var result = await sut.GetRegionAsync(expectedRegionId);

        // Assert.
        result.Should().Be(expectedRegion);
    }

    [Test]
    public async Task GetAllRegions_ReturnsAllRegions()
    {
        // Arrange.
        // ✅ Use Generate when you just need valid instances
        var region1 = _generator.GenerateRegion();
        var region2 = _generator.GenerateRegion();
        var region3 = _generator.GenerateRegion();

        SetupRepositoryToReturn(region1, region2, region3);
        var sut = Fixture.Create<RegionService>();

        // Act.
        var results = await sut.GetAllRegionsAsync();

        // Assert.
        results.Should().HaveCount(3);
        results.Should().Contain(region1);
    }
}
```

## Generator Composition

Generators can use other generators for complex models:

```csharp
public sealed class TenantGenerator
{
    private readonly ApplianceGenerator _applianceGenerator;
    private readonly OrganizationGenerator _orgGenerator;

    public TenantGenerator()
    {
        _applianceGenerator = ApplianceGenerator.Instance;
        _orgGenerator = new OrganizationGenerator();
    }

    public Tenant GenerateTenant()
    {
        return new Tenant(
            tenantId: GenerateTenantId(),
            tenantName: GenerateTenantName(),
            status: TenantStatus.Creating,
            appliance: _applianceGenerator.GenerateAppliance(), // Compose
            organizations: GenerateSeveralOrganizations(),
            createdTime: DateTimeUtc.UtcNow
        );
    }

    private IReadOnlyCollection<Organization> GenerateSeveralOrganizations()
    {
        return new[]
        {
            _orgGenerator.GenerateOrganization(),
            _orgGenerator.GenerateOrganization(),
        };
    }
}
```

## Parameterized Generation

For models with optional/configurable parts:

```csharp
public AccountDeploymentResult GenerateAccountDeploymentResult(
    Int32? usageCount = null,
    AccountStatus? status = null)
{
    return new AccountDeploymentResult(
        deploymentId: GenerateDeploymentId(),
        accountId: GenerateAccountId(),
        usageCount: usageCount ?? Random.Shared.Next(0, 100),
        status: status ?? AccountStatus.Active
    );
}
```

## Key Points

1. **Singleton access** - Use `{Generator}.Instance` for convenience

2. **Create vs Generate** - `Create` for explicit values, `Generate` for random

3. **Composition** - Complex generators use other generators

4. **Uniqueness** - `Generate` methods append GUIDs or use random selection

5. **Keep tests independent** - Generated values are unique per call

6. **Parameterized generation** - Allow overriding specific properties when needed
