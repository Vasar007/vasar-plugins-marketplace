# Mocking Rules

Code examples and the builder rule for [Mocking Rules](../SKILL.md#mocking-rules) in `SKILL.md`.

## Forbidden Direct Mocks

```csharp
// ❌ FORBIDDEN - Substitute.For
var mock = Substitute.For<IService>();

// ❌ FORBIDDEN - Fixture.Freeze on interfaces
var repository = Fixture.Freeze<IMyRepository>();

// ❌ FORBIDDEN - Fixture.Create on interfaces
var mock = Fixture.Create<IMyService>();
```

## Test Mock Builder

**Always use a Test Mock Builder** (a `Test{Interface}Builder` class) instead:

```csharp
// ✅ CORRECT - use Test Mock Builder for ALL interface mocks
var repository = new TestMyRepositoryBuilder(Fixture)
    .AddItem(item1)
    .AddItem(item2)
    .Build();

// ✅ CORRECT - empty mock via static factory
var repository = TestMyRepositoryBuilder.CreateWithoutSetup(Fixture);
```

## Inside a Test Builder

**Inside a `Test{Interface}Builder`:** this rule is for NSubstitute through AutoFixture. Get the substitute with `_fixture.Create<IInterface>()`, not with `Substitute.For<IInterface>()`. The NSubstitute customization of AutoFixture makes an equivalent mock, works with the rest of the fixture configuration, and matches the other builders of the repository. With another mocking library or test data library, get the mock the way that the other builders of the repository do. Use `Substitute.For<T>` only in the rare case where AutoFixture cannot make the substitute. Examples are a sealed concrete type or a generic constraint that AutoFixture refuses. Then add a one-line comment that says why. Do not silently change `_fixture.Create<…>()` to `Substitute.For<T>` as a "fix".
