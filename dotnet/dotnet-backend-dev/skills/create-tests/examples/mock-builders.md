# Test Mock Builders

Use Test Mock Builders for every interface mock, instead of an inline setup with the test data library (for example, `Fixture.Freeze<T>()` in AutoFixture).

The code examples in this file use NUnit, FluentAssertions, NSubstitute, and AutoFixture. With another test framework, assertion library, mocking library, or test data library, use its equivalent attributes and calls.

## When to Use Mock Builders

**Always.** Mock Builders are **mandatory** for every interface mock, with no exceptions.

A direct mock from the mocking library or the test data library is **strictly forbidden** in test fixtures and test cases. Examples are `Substitute.For<T>()`, `Fixture.Freeze<IInterface>()`, and `Fixture.Create<IInterface>()`. If a builder does not exist for the interface you need, create one first in `Tests.Common/Helpers/Mocks/{Feature}/`.

## Mock Builder Structure

Location: `Tests.Common/Helpers/Mocks/{Feature}/`

```text
Mocks/
├── Accounts/
│   └── Repositories/
│       └── TestCustomerAccountRepositoryBuilder.cs
├── Sessions/
│   └── Repositories/
│       └── TestSessionRepositoryBuilder.cs
└── Sales/
    └── Customers/
        └── Repositories/
            └── TestCustomerRepositoryBuilder.cs
```

## Repository Mock Builder Example

```csharp
// Copyright (c) Vasily Vasilyev

using NSubstitute.Core;
using MyApp.Application.Accounts.Repositories;
using MyApp.Sdk.Domain.Customers;
using MyApp.Sdk.Domain.Accounts;

namespace MyApp.Tests.Common.Helpers.Mocks.Accounts.Repositories;

public sealed class TestCustomerAccountRepositoryBuilder
{
    private readonly IFixture _fixture;
    private readonly List<ICustomerAccount> _items;

    public TestCustomerAccountRepositoryBuilder(IFixture fixture)
    {
        _fixture = fixture.ThrowIfNull();
        _items = new();
    }

    /// <summary>
    /// Creates a repository without any pre-configured data.
    /// </summary>
    public static ICustomerAccountRepository CreateWithoutSetup(IFixture fixture)
    {
        fixture.ThrowIfNull();
        var builder = new TestCustomerAccountRepositoryBuilder(fixture);
        return builder.Build();
    }

    public TestCustomerAccountRepositoryBuilder AddCustomerAccount(
        ICustomerAccount item)
    {
        item.ThrowIfNull();
        _items.Add(item);
        return this;
    }

    public TestCustomerAccountRepositoryBuilder AddCustomerAccountRange(
        IEnumerable<ICustomerAccount> items)
    {
        items.ThrowIfNull();
        _items.AddRange(items);
        return this;
    }

    public ICustomerAccountRepository Build()
    {
        var repository = _fixture.Create<ICustomerAccountRepository>();

        // FindByPrimaryKeyAsync - lookup by ID
        repository.FindByPrimaryKeyAsync(Arg.Any<AccountNumber>(), Arg.Any<CancellationToken>())
            .Returns(FindByPrimaryKeyInternal);

        // FindByAlternateKeyAsync - lookup by alternate key
        repository.FindByAlternateKeyAsync(Arg.Any<AccountId>(), Arg.Any<CancellationToken>())
            .Returns(FindByAlternateKeyInternal);

        // GetAllAsync - return all items
        repository.GetAllAsync(Arg.Any<CancellationToken>())
            .Returns(_items);

        // AddAsync - add to internal list
        repository.AddAsync(Arg.Any<ICustomerAccount>(), Arg.Any<CancellationToken>())
            .Returns(AddInternalAsync);

        // UpdateAsync - update in internal list
        repository.UpdateAsync(Arg.Any<ICustomerAccount>(), Arg.Any<CancellationToken>())
            .Returns(UpdateInternalAsync);

        // DeleteByPrimaryKeyAsync - remove from internal list
        repository.DeleteByPrimaryKeyAsync(Arg.Any<AccountNumber>(), Arg.Any<CancellationToken>())
            .Returns(DeleteByPrimaryKeyInternalAsync);

        return repository;
    }

    // Private handlers implement stateful behavior
    private ICustomerAccount? FindByPrimaryKeyInternal(CallInfo ci)
    {
        var primaryKey = ci.ArgAt<AccountNumber>(0);
        return _items.Find(x => x.AccountNumber == primaryKey);
    }

    private ICustomerAccount? FindByAlternateKeyInternal(CallInfo ci)
    {
        var alternateKey = ci.ArgAt<AccountId>(0);
        return _items.Find(x => x.AccountId == alternateKey);
    }

    private Task<ICustomerAccount> AddInternalAsync(CallInfo ci)
    {
        var item = ci.ArgAt<ICustomerAccount>(0);
        _items.Add(item);
        return Task.FromResult(item);
    }

    private Task<ICustomerAccount> UpdateInternalAsync(CallInfo ci)
    {
        var item = ci.ArgAt<ICustomerAccount>(0);
        var index = _items.FindIndex(x => x.AccountNumber == item.AccountNumber);
        if (index >= 0) _items[index] = item;
        return Task.FromResult(item);
    }

    private Task<Boolean> DeleteByPrimaryKeyInternalAsync(CallInfo ci)
    {
        var primaryKey = ci.ArgAt<AccountNumber>(0);
        var removed = _items.RemoveAll(x => x.AccountNumber == primaryKey) > 0;
        return Task.FromResult(removed);
    }
}
```

## Usage in Tests

Test cases must not call builders or generators directly. All such calls must be wrapped in private helper methods.

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class AccountSelectionServiceTests : BaseMockTest
{
    private readonly AccountGenerator _generator;

    public AccountSelectionServiceTests()
    {
        _generator = new AccountGenerator();
    }

    [Test]
    public async Task SelectAccount_WithExistingAccounts_ReturnsLeastUsed()
    {
        // Arrange.
        var account1 = GenerateAccount(usageCount: 5);
        var account2 = GenerateAccount(usageCount: 2);
        var account3 = GenerateAccount(usageCount: 8);

        var repository = CreateAccountRepository(accounts: new[] { account1, account2, account3 });
        Fixture.Inject(repository);

        var service = CreateService();

        // Act.
        var result = await service.SelectAccountAsync();

        // Assert.
        result.Should().Be(account2); // Least usage
    }

    [Test]
    public async Task SelectAccount_WithNoAccounts_ReturnsNull()
    {
        // Arrange.
        var repository = CreateAccountRepository();
        Fixture.Inject(repository);

        var service = CreateService();

        // Act.
        var result = await service.SelectAccountAsync();

        // Assert.
        result.Should().BeNull();
    }

    // Tests call the generator only through this helper, never directly.
    private ICustomerAccount GenerateAccount(Int32 usageCount = 0)
    {
        return _generator.GenerateCustomerAccount(usageCount: usageCount);
    }

    private ICustomerAccountRepository CreateAccountRepository(ICustomerAccount[]? accounts = null)
    {
        return new TestCustomerAccountRepositoryBuilder(Fixture)
            .ApplyIf(accounts is not null, b => b.AddCustomerAccountRange(accounts!))
            .Build();
    }

    private AccountSelectionService CreateService()
    {
        return Fixture.Create<AccountSelectionService>();
    }
}
```

## Key Points

1. **Mandatory for all interface mocks**: never a direct mock from the mocking library or the test data library (for example, `Substitute.For`, `Fixture.Freeze<IInterface>`, or `Fixture.Create<IInterface>`)

2. **Fluent API**: Use builder pattern with method chaining: `.AddItem(x).AddItem(y).Build()`

3. **Static CreateWithoutSetup**: Convenience method for empty mock

4. **Stateful behavior**: Internal list tracks add/update/delete operations

5. **Use generators**: Create test data with a generator that the test class creates with `new {Model}Generator()`

6. **Fixture.Inject**: In AutoFixture, replace the default mock of the fixture with the configured builder result

7. **Never call builders or generators directly in test cases**: always wrap them in private `Create{Mock}` or `Generate{Model}` helper methods
