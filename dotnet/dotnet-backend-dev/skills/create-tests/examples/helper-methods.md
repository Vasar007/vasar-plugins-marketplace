# Private Helper Methods

Code examples and long explanations for the rules of [Private Helper Methods](../SKILL.md#private-helper-methods) in `SKILL.md`.

## Contents

- Wrong and Correct Test Cases
- Rule 3: No Post-Setup on Returned Mocks
- Rule 4: Optional Parameters and ApplyIf
- Rule 5: Follow the Existing Test Class and Assembly
- Rule 6: Bulk Add Range Methods
- Rule 7: Reusable Assertion Helpers

## Wrong and Correct Test Cases

```csharp
// ❌ WRONG - builder called directly in test case
[Test]
public void TestCase()
{
    var item1 = _itemGenerator.GenerateItem(name: "A");
    var item2 = _itemGenerator.GenerateItem(name: "B");
    var repository = new TestMyRepositoryBuilder(Fixture)
        .AddItem(item1)
        .AddItem(item2)
        .Build();
    // ...
}

// ❌ WRONG - additional mock setup after calling Create helper
[Test]
public void TestCase()
{
    var repository = CreateMyRepository(new[] { item1, item2 });
    repository.FindByPrimaryKeyAsync(Arg.Any<MyId>(), Arg.Any<CancellationToken>())
        .Returns(ci => ...); // FORBIDDEN - setup must be inside the builder
    // ...
}

// ✅ CORRECT - all builder/generator calls in private methods, no post-setup
[Test]
public void TestCase()
{
    var item1 = GenerateItem(name: "A");
    var item2 = GenerateItem(name: "B");
    var repository = CreateMyRepository(new[] { item1, item2 });
    // repository is fully configured — no additional .Returns/.ReturnsForAnyArgs here
    // ...
}

private Item GenerateItem(String name)
{
    return _itemGenerator.GenerateItem(name: name);
}

private IMyRepository CreateMyRepository(Item[] items)
{
    return new TestMyRepositoryBuilder(Fixture)
        .AddItemRange(items) // use bulk Add*Range methods — no foreach/if-else in helpers
        .Build(); // ALL method setups live inside TestMyRepositoryBuilder
}
```

## Rule 3: No Post-Setup on Returned Mocks

Examples are `.Returns()`, `.ReturnsForAnyArgs()`, and any other NSubstitute setup. If you need a new behavior, **extend the Test Mock Builder** with a new method or option. Then expose it through the parameters of the `Create{Mock}` helper. One exception: `ExternalServicesMock` of `WebApiBaseTest` in Web API tests. The base test injects this mock into the ASP.NET pipeline, where it intercepts the calls of the running app to external services. So a test case can set up its behavior after the setup, as `controller-tests.md` shows.

## Rule 4: Optional Parameters and ApplyIf

Rule 1 ("exactly one helper for each dependency, no overloads") does not mean that the helper has no optional parameters. The single helper takes an **optional nullable parameter** (`Foo? p = null`) for each setting that a test case needs. It applies each one with an `.ApplyIf(condition, b => b.WithFoo(p!))` call in the fluent chain of the builder.

Two test cases that need different `Create{Mock}` inputs call the **same single** method with different named-argument values. A test class never has a second `CreateMyRepository` for the same dependency. `Generate{Model}` helpers follow the looser `Generate*` column in the table below: plain optional parameters with defaults are allowed, and `.ApplyIf` is not required.

| Location | `Create*` | `Generate*` |
| --- | --- | --- |
| Test class | `Create{Mock}` (a helper that wraps a Test Mock Builder): optional nullable parameters, applied with `.ApplyIf(...)` (except `CreateServiceWithAllArguments`) | Optional parameters with defaults are allowed |
| Generator class | Required parameters only | Optional parameters are allowed (nullable fallback) |

```csharp
// ✅ CORRECT - one helper, optional params, .ApplyIf chain
private IMyRepository CreateMyRepository(Item[]? items = null, Exception? failureException = null)
{
    return new TestMyRepositoryBuilder(Fixture)
        .ApplyIf(items is not null, b => b.AddItemRange(items!))
        .ApplyIf(failureException is not null, b => b.WithFailure(failureException!))
        .Build();
}

// ❌ WRONG - if-block with a separately-declared builder variable
private IMyRepository CreateMyRepository(Item[]? items = null)
{
    var builder = new TestMyRepositoryBuilder(Fixture);
    if (items is not null)
        builder.AddItemRange(items);
    return builder.Build();
}

// ❌ WRONG - ?? fallback inside .With(...)/.AddItemRange(...)
private IMyRepository CreateMyRepository(Item[]? items = null)
{
    return new TestMyRepositoryBuilder(Fixture)
        .AddItemRange(items ?? Array.Empty<Item>())
        .Build();
}
```

In generator classes (`xxxGenerator.cs` under `Tests.Common/Helpers/Generators/...`), `Create*` takes required parameters only. `Generate*` can take nullable optional parameters with `null` defaults, which mean "fill with random values".

## Rule 5: Follow the Existing Test Class and Assembly

Also read the nearby test classes of the same fixture and the shared helpers of the same test assembly. Copy the shapes that they use. Do not add a new `Create*` or `Generate*` pattern that conflicts with neighboring tests in the same fixture or assembly. Example: `CreateMyRepository` already exists and takes `Item[]`. Then your new test uses that signature with different `Item[]` values and does not add a second helper. If the existing shape is wrong (for example, it already has two `Create*` overloads), tell the user. Do not add a third overload.

## Rule 6: Bulk Add Range Methods

This rule is separate from rule 4. `Add*Range` adds a collection of items in one call. `.ApplyIf(...)` (rule 4) applies *one optional setting*. If a helper has both, use both.

## Rule 7: Reusable Assertion Helpers

```csharp
private void AssertModelEquals(MyModel expected, MyModel actual)
{
    actual.Id.Should().Be(expected.Id);
    actual.Name.Should().Be(expected.Name);
}
```
