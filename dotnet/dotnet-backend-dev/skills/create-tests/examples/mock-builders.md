# Test Mock Builders

Use Test Mock Builders for complex mock configurations instead of inline `Fixture.Freeze<T>()` setup.

## When to Use Mock Builders

**ALWAYS.** Mock Builders are **mandatory** for every interface mock — no exceptions.

`Substitute.For<T>()`, `Fixture.Freeze<IInterface>()`, and `Fixture.Create<IInterface>()` are **strictly forbidden** in test fixtures and test cases. If a builder does not exist for the interface you need, create one first in `Tests.Common/Helpers/Mocks/{Feature}/`.

## Mock Builder Structure

Location: `Tests.Common/Helpers/Mocks/{Feature}/`

```text
Mocks/
├── Provisioning/
│   └── Accounts/
│       └── Deployments/
│           └── Repositories/
│               └── TestAccountDeploymentResultRepositoryBuilder.cs
├── Sessions/
│   └── Repositories/
│       └── TestSessionRepositoryBuilder.cs
└── Workload/
    └── Tenants/
        └── Repositories/
            └── TestTenantRepositoryBuilder.cs
```

## Repository Mock Builder Example

```csharp
// Copyright (c) Vasily Vasilyev

using NSubstitute.Core;
using MyApp.Application.Provisioning.Accounts.Deployments.Repositories;
using MyApp.Sdk.Domain.Deployments;
using MyApp.Sdk.Domain.Accounts;

namespace MyApp.Tests.Common.Helpers.Mocks.Provisioning.Accounts.Deployments.Repositories;

public sealed class TestAccountDeploymentResultRepositoryBuilder
{
    private readonly IFixture _fixture;
    private readonly List<IAccountDeploymentResult> _items;

    public TestAccountDeploymentResultRepositoryBuilder(IFixture fixture)
    {
        _fixture = fixture.ThrowIfNull();
        _items = new();
    }

    /// <summary>
    /// Creates a repository without any pre-configured data.
    /// </summary>
    public static IAccountDeploymentResultRepository CreateWithoutSetup(IFixture fixture)
    {
        fixture.ThrowIfNull();
        var builder = new TestAccountDeploymentResultRepositoryBuilder(fixture);
        return builder.Build();
    }

    public TestAccountDeploymentResultRepositoryBuilder AddAccountDeploymentResult(
        IAccountDeploymentResult item)
    {
        item.ThrowIfNull();
        _items.Add(item);
        return this;
    }

    public TestAccountDeploymentResultRepositoryBuilder AddAccountDeploymentResultRange(
        IEnumerable<IAccountDeploymentResult> items)
    {
        items.ThrowIfNull();
        _items.AddRange(items);
        return this;
    }

    public IAccountDeploymentResultRepository Build()
    {
        var repository = _fixture.Create<IAccountDeploymentResultRepository>();

        // FindByPrimaryKeyAsync - lookup by ID
        repository.FindByPrimaryKeyAsync(Arg.Any<DeploymentId>(), Arg.Any<CancellationToken>())
            .Returns(FindByPrimaryKeyInternal);

        // FindByAlternateKeyAsync - lookup by alternate key
        repository.FindByAlternateKeyAsync(default, Arg.Any<CancellationToken>())
            .ReturnsForAnyArgs(FindByAlternateKeyInternal);

        // GetAllAsync - return all items
        repository.GetAllAsync(Arg.Any<CancellationToken>())
            .Returns(_items);

        // AddAsync - add to internal list
        repository.AddAsync(Arg.Any<IAccountDeploymentResult>(), Arg.Any<CancellationToken>())
            .Returns(AddInternalAsync);

        // UpdateAsync - update in internal list
        repository.UpdateAsync(Arg.Any<IAccountDeploymentResult>(), Arg.Any<CancellationToken>())
            .Returns(UpdateInternalAsync);

        // DeleteByPrimaryKeyAsync - remove from internal list
        repository.DeleteByPrimaryKeyAsync(Arg.Any<DeploymentId>(), Arg.Any<CancellationToken>())
            .Returns(DeleteByPrimaryKeyInternalAsync);

        return repository;
    }

    // Private handlers implement stateful behavior
    private IAccountDeploymentResult? FindByPrimaryKeyInternal(CallInfo ci)
    {
        var primaryKey = ci.ArgAt<DeploymentId>(0);
        return _items.Find(x => x.DeploymentId == primaryKey);
    }

    private IAccountDeploymentResult? FindByAlternateKeyInternal(CallInfo ci)
    {
        var alternateKey = ci.ArgAt<AccountId>(0);
        return _items.Find(x => x.AccountId == alternateKey);
    }

    private Task<IAccountDeploymentResult> AddInternalAsync(CallInfo ci)
    {
        var item = ci.ArgAt<IAccountDeploymentResult>(0);
        _items.Add(item);
        return Task.FromResult(item);
    }

    private Task<IAccountDeploymentResult> UpdateInternalAsync(CallInfo ci)
    {
        var item = ci.ArgAt<IAccountDeploymentResult>(0);
        var index = _items.FindIndex(x => x.DeploymentId == item.DeploymentId);
        if (index >= 0) _items[index] = item;
        return Task.FromResult(item);
    }

    private Task<Boolean> DeleteByPrimaryKeyInternalAsync(CallInfo ci)
    {
        var primaryKey = ci.ArgAt<DeploymentId>(0);
        var removed = _items.RemoveAll(x => x.DeploymentId == primaryKey) > 0;
        return Task.FromResult(removed);
    }
}
```

## Usage in Tests

**IMPORTANT:** Test cases must NOT call builders or generators directly. All such calls must be wrapped in private helper methods.

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class AccountSelectionServiceTests : BaseMockTest
{
    private readonly DeploymentGenerator _generator;

    public AccountSelectionServiceTests()
    {
        _generator = DeploymentGenerator.Instance;
    }

    [Test]
    public async Task SelectAccount_WithExistingAccounts_ReturnsLeastUsed()
    {
        // Arrange.
        var account1 = GenerateAccount(usageCount: 5);
        var account2 = GenerateAccount(usageCount: 2);
        var account3 = GenerateAccount(usageCount: 8);

        var repository = CreateAccountRepository(account1, account2, account3);
        Fixture.Inject(repository);

        var sut = Fixture.Create<AccountSelectionService>();

        // Act.
        var result = await sut.SelectAccountAsync();

        // Assert.
        result.Should().Be(account2); // Least usage
    }

    [Test]
    public async Task SelectAccount_WithNoAccounts_ReturnsNull()
    {
        // Arrange.
        var repository = CreateAccountRepository();
        Fixture.Inject(repository);

        var sut = Fixture.Create<AccountSelectionService>();

        // Act.
        var result = await sut.SelectAccountAsync();

        // Assert.
        result.Should().BeNull();
    }

    // --- Private helper methods (mandatory indirection) ---

    private IAccountDeploymentResult GenerateAccount(Int32 usageCount = 0)
    {
        return _generator.GenerateAccountDeploymentResult(usageCount: usageCount);
    }

    private IAccountDeploymentResultRepository CreateAccountRepository(
        params IAccountDeploymentResult[] accounts)
    {
        return new TestAccountDeploymentResultRepositoryBuilder(Fixture)
            .AddAccountDeploymentResultRange(accounts)
            .Build();
    }
}
```

## Key Points

1. **Mandatory for ALL interface mocks** — no `Substitute.For`, `Fixture.Freeze<IInterface>`, or `Fixture.Create<IInterface>` ever

2. **Fluent API** - Use builder pattern with method chaining: `.AddItem(x).AddItem(y).Build()`

3. **Static CreateWithoutSetup** - Convenience method for empty mock

4. **Stateful behavior** - Internal list tracks add/update/delete operations

5. **Use generators** - Create test data with `{Model}Generator.Instance`

6. **Fixture.Inject** - Replace AutoFixture's default mock with configured builder result

7. **Never call builders/generators in test cases directly** — always wrap in private `Create{Mock}` / `Generate{Model}` helper methods
