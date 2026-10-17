# Enforced Gates

This file holds seven more conventions that this skill enforces. Gates 2, 3, 4, 6, and 7 apply to every test class. If the mocking library is not NSubstitute, Gate 5 does not apply. Gate 1 applies only to the test classes that its section names. The gates add to the patterns in [SKILL.md](../SKILL.md) and in the other files of this folder. Real corrections on shipped code support each gate. Each gate gives the rule and an example. Some gates also give a grep self-check to run before you finish.

The code examples in this file use NUnit, FluentAssertions, NSubstitute, and AutoFixture. With another test framework, assertion library, mocking library, or test data library, use its equivalent attributes and calls.

## Gate 1 — Method-level null-arg coverage (not just constructors)

**Why:** The constructor null-argument pattern (see [constructor-null-arg-tests.md](constructor-null-arg-tests.md)) also applies to every **public method** of the SUT, not only to constructors. Separate tests for each parameter (`MethodAsync_ShouldThrow_WhenOrderIdIsNull`, `MethodAsync_ShouldThrow_WhenCustomerDetailsIsNull`, and so on) make the fixture large. They spread the null-argument tests of one method over several test names. Then it is hard to see at a glance that each required parameter has a null test. The merged `foreach` form keeps all of them in one place. A new required parameter adds ONE line to the list, not a new test.

**Scope:** Gate 1 applies only to a test class that calls the methods of the SUT directly. Examples are the tests of a service, a repository, or a domain model. Gate 1 never applies to controller tests that send requests through the HTTP client (`WebApiBaseTest`, see [controller-tests.md](controller-tests.md)). These tests call no method of the SUT directly. Gate 1 also never applies to scenario tests (see [scenario-tests.md](scenario-tests.md)). This is true also for a scenario test that starts at an application service. A scenario test checks an end-to-end flow, not the guard clauses of one method.

For each public method with at least one required reference-type parameter, write ONE combined test: `<Method>_ShouldThrowArgumentNullException_ForEachRequiredArgument`. Iterate over a `List<Func<Task>>` for async methods, or a `List<Action>` for sync methods. Each entry passes `null!` in the position of exactly one required reference parameter. This is the same required-positional mechanism as in the constructor pattern, never `null! ?? CreateXxx()`.

In the constructor pattern, each lambda calls `CreateServiceWithAllArguments` again, so no shared valid instance exists. This pattern is different: it uses one `processor` instance in every lambda of the list. The shared instance is safe under one condition: the guard clauses of the SUT run before any side effect. Then no earlier lambda in the `foreach` can change state that the processor uses before the guard clause of a later lambda throws. If you cannot be sure of this condition for the SUT under test, build a new instance in each lambda, as the constructor pattern does. Do not share `processor` in that case.

```csharp
[Test]
public async Task ProcessAsync_ShouldThrowArgumentNullException_ForEachRequiredArgument()
{
    // Arrange.
    var processor = CreateProcessor(); // role-noun, NOT `sut` — see Gate 3
    var orderId = GenerateOrderId();
    var customerDetails = GenerateCustomerDetails();
    var nullArgActions = new List<Func<Task>>
    {
        () => processor.ProcessAsync(null!, customerDetails),
        () => processor.ProcessAsync(orderId, null!),
    };

    // Act & Assert.
    foreach (var action in nullArgActions)
        await action.Should().ThrowAsync<ArgumentNullException>();
}
```

Rules:

- ONE merged `foreach` test for each public method in each fixture. NEVER separate `WhenXIsNull` tests for each parameter.
- **General principle: group the null-argument tests of required parameters by the expected exception type, not by an ad hoc list of parameter types**. Different guard clauses throw different exceptions. `ThrowIfNull()` throws `ArgumentNullException`. `ThrowIfNullOrWhiteSpace()` (for `String`) throws `ArgumentException` (the assertion split of Gate 6). One `foreach` test can assert only one exception type in its assertion (for example, `Should().ThrowAsync<T>()`). So each exception-type group gets its own merged `foreach` test. The exclusions below follow from this rule. They are not a separate ad hoc list:
  - `CancellationToken`, value types, and reference types that are nullable by design: fully excluded. `null` is a legal value for them, not a guard violation, so no exception exists to group by.
  - Required `String` parameters: `ThrowIfNullOrWhiteSpace()` guards them and throws `ArgumentException`, not `ArgumentNullException`. So they belong to a different group than the merged `ArgumentNullException` `foreach` test. Give each one its own test with the `StringNullOrWhiteSpace_TestCases` test-case source (for example, `[TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]` in NUnit) instead of the `foreach`.
  - A method with both `String` and other required reference parameters: write the `foreach` `ArgumentNullException` test for the parameters that are not `String` (one group). Write a separate `StringNullOrWhiteSpace_TestCases` test for each `String` parameter (the `ArgumentException` group).
- If a method has NO required reference parameters, write no `foreach` test for it. Do not create an empty list.
- Put the test in the `#region <Method> Tests` block, next to the other behavior tests of the method. Gate 4 gives the order of the fixture body.

## Gate 2 — No async-wrapping single-expression lambdas

**Why:** `x.MethodAsync(...)` already returns a `Task`. The form `async () => await x.MethodAsync(...)` adds an extra state machine and async layer for nothing. `Should().ThrowAsync()` and the entries of a `List<Func<Task>>` take a `Func<Task>` directly. Reviewers, human and AI, flag the wrapped form as overblown.

```csharp
// ❌ WRONG — needless async/await wrapping of a single expression
var act = async () => await processor.ProcessAsync(orderId, customerDetails);

// ✅ CORRECT — the lambda body is already a Task-returning expression
var act = () => processor.ProcessAsync(orderId, customerDetails);
```

If the method signature already has a default for the token (`CancellationToken cancellationToken = default`), also drop a trailing `CancellationToken.None` argument. Pass nothing.

**Exception:** keep the `async`/`await` form for a lambda body with more than one `await` or with non-trivial async logic. Only the wrapping of a single expression is forbidden.

**Pre-completion grep gate:** before you report a test fixture as done, search your new and changed tests for `async () => await` (case-sensitive). For each match, find out whether the body has more than one `await` or non-trivial async logic. If it has, keep it. Else change it to the direct form.

## Gate 3 — SUT naming from the class's role suffix

**Why:** A test where every SUT variable is `sut` makes the reader remember which class is under test. `var processor = CreateProcessor(...)` shows at once the kind of the SUT and what the test does with it.

Name the SUT variable and its factory helper after the role suffix of the class: `Service`, `Processor`, `Resolver`, `Updater`, `Validator`, `Provider`, `Handler`, `Manager`, `Coordinator`, `Repository`, and so on. NEVER use `sut` or `CreateSut`.

```csharp
// ✅ CORRECT
var processor = CreateProcessor(orderRepository: ...);      // OrderProcessor
var updater = CreateUpdater(customerProfileRepository: ...); // CustomerProfileUpdater
var repository = CreateRepository(...);                      // OrderRepository

// ❌ WRONG
var sut = CreateSut(...);
```

Edge cases (use your judgment, and say so in a comment):

- **Two SUTs in scope** (unusual): give each one a more specific noun (`primaryProcessor`, `retryProcessor`). Do not fall back to `sut1` and `sut2`.
- **No clear role suffix** (for example, a class named only `Order`): use the most concrete domain noun (`order`, `orderDetails`). Add a short comment that says that the class has no role suffix. This is a design smell to report, not to work around in silence.

## Gate 4 — Helper-file ordering and the inheritance rule

**Why:** The reader reads from the top down: `#region Constructor Tests`, then `#region <Method> Tests` for each public method. So the reader sees the test cases first. Helpers are reference material for the moment the reader needs to know HOW the test built a mock. Helpers at the top, or between the tests, make the reader scroll past the arrange code before the behavior assertions.

Fixture body order, top to bottom:

1. Class-level fields (rarely needed beyond what the base class already exposes).
2. `#region Constructor Tests` (ctor null-arg `foreach`-over-`List<Action>`, see
   [constructor-null-arg-tests.md](constructor-null-arg-tests.md)).
3. `#region <PublicMethod1> Tests`, `#region <PublicMethod2> Tests`, and so on: one region for each public method. Each region holds the behavior tests of that method, and its null-argument `foreach` test where Gate 1 applies.
4. ALL helper methods last, inside one `#region Helper Methods`. They are private. The exception is a helper of a base fixture that a derived fixture must call: make it `protected` (see the inheritance pair rule below).

**Inheritance pair rule:** the helpers of derived fixtures that share a base fixture (`XxxBaseTests`) live in the base class ONLY. A derived class contains ONLY test methods (for example, `[Test]` methods in NUnit) and its own explicit parameterless constructor. It never declares a helper again and never overrides one. A helper that only the tests of the base fixture call stays `private`. A helper that a derived fixture also calls needs `protected`, because a `private` member is not accessible outside its declaring type.

```csharp
// ✅ CORRECT — base owns all helpers; CreateRequest is protected because the derived
// fixture below calls it directly (private would not compile there — CS0122).
public abstract class OrderRequestBaseTests : BaseMockTest
{
    #region Constructor Tests
    // ...
    #endregion

    #region Helper Methods
    protected OrderRequest CreateRequest(...) { ... }
    #endregion
}

public sealed class OrderRequestTests : OrderRequestBaseTests
{
    public OrderRequestTests()
    {
    }

    [Test]
    public void SomeAdditionalScenario_ShouldBehaveAsExpected()
    {
        // uses the base class's CreateRequest(...) helper
    }
}
```

## Gate 5 — NSubstitute `Arg.Any<T>()` vs `default`

This gate is for NSubstitute as the mocking library. Another mocking library has its own argument matchers. Then use them by the rules of that library.

**Why:** The C# compiler generates value equality for record structs. NSubstitute resolves `Arg.Any<TRecordStruct>()` at call time. Then the matcher can collide with an ordinary argument value that equals the `default` of the type, and NSubstitute throws `NSubstitute.Exceptions.AmbiguousArgumentsException`. If you pass `default` directly (no matcher), the collision does not happen. But that is a narrow workaround. It does not allow `default` for every argument.

Use `Arg.Any<T>()` for:

- reference types and nullable reference types,
- interfaces,
- ordinary value types (`Int32`, `Boolean`, `Guid`, `DateTime`, …).

Use `default` ONLY for the record-struct wrapper types that you saw throw `AmbiguousArgumentsException` in this codebase. Try `Arg.Any<T>()` first. Use `default` only after you saw the exception for that type. Each time that you use `default`, add a one-line comment that names the type and the reason.

```csharp
// ❌ WRONG — blanket default across the whole argument list
await orderProcessor.ReceivedWithAnyArgs(1).ProcessOrderAsync(
    default, default!, default, default!);

// ✅ CORRECT — Arg.Any<T>() everywhere except the one record struct that needs default
// Use default for ProductId record struct (NSubstitute AmbiguousArgumentsException workaround).
await orderProcessor.ReceivedWithAnyArgs(1).ProcessOrderAsync(
    Arg.Any<OrderId>(),
    Arg.Any<CustomerDetails?>(),
    default,                       // ProductId record struct
    Arg.Any<String>());
```

Note: `ReceivedWithAnyArgs(N)` ignores the argument *values* in its call matching. The choice of matcher still matters. `Arg.Any<T>()` and `default` run while the call expression is built, before NSubstitute compares the received calls. The `AmbiguousArgumentsException` comes from that step. So the risk is the same under `ReceivedWithAnyArgs`, although its comparison ignores the values.

This applies everywhere NSubstitute takes an argument matcher: `Received(N)` /
`ReceivedWithAnyArgs(N)` assertions and `.Returns(...)` / `.Throws(...)` setups inside Test Mock
Builders.

## Gate 6 — Prefer this repo's own null-guard extension over the raw BCL form

**Why:** The conventions of this repository guard constructor and method parameters with the fluent `obj.ThrowIfNull()` extension. See [dotnet-conventions/application-services.md](../../dotnet-conventions/application-services.md) and [dotnet-conventions/domain-models.md](../../dotnet-conventions/domain-models.md). They do not use the static BCL form `ArgumentNullException.ThrowIfNull(obj)`. A mix of both forms makes the code inconsistent, also in test helper code that copies the guard-clause style of production code.

```csharp
// ❌ WRONG — BCL static form
ArgumentNullException.ThrowIfNull(repository);
_repository = repository;

// ✅ CORRECT — this repo's fluent extension
_repository = repository.ThrowIfNull();
```

This applies to each constructor guard, each parameter guard of a public method, and each SUT-helper builder, in production code and in test code. The assignment form (`_field = obj.ThrowIfNull();`) and the guard-only form (`obj.ThrowIfNull();`) are both valid.

**Assertion split:** the guard type sets the expected exception in the negative test. `ThrowIfNull()` goes with `ArgumentNullException`. The string guard `ThrowIfNullOrWhiteSpace()` goes with `ArgumentException`. It covers null, empty, and whitespace-only string arguments in one guard.

## Gate 7 — No expression-bodied methods

**Why:** The review convention of this repository puts a method body inside braces, also for one statement. Methods and properties then look different. A later change (logging, tracing, or a condition) then gives a small diff and does not change the body shape.

Methods use block `{ ... }` bodies, also one-line delegate forwarders and test helper methods. The expression-bodied `=>` syntax is forbidden for methods.

**Scope:** test fixtures and the helper methods of the service under test. Expression bodies in production wrapper factories and equality members are a separate convention (see `dotnet-backend-dev:create-primitive-wrapper` and [dotnet-conventions/domain-models.md](../../dotnet-conventions/domain-models.md)). This gate does not cover them.

```csharp
// ❌ WRONG — expression-bodied method
public Task<X> FooAsync(...) => _collaborator.FooAsync(...);

private SomeType CreateMock() => new TestSomeTypeBuilder(Fixture).Build();

// ✅ CORRECT — block body
public Task<X> FooAsync(...)
{
    return _collaborator.FooAsync(...);
}

private SomeType CreateMock()
{
    return new TestSomeTypeBuilder(Fixture).Build();
}
```

**Not affected by this rule** (still allowed to use `=>`):

- Property getters/setters (auto-properties and computed properties).
- Lambdas, for example inside LINQ, `Substitute.For<T>()`, `Arg.Is<T>(x => ...)`, `Should().ThrowAsync<T>().WithMessage(...)`, and `.ApplyIf(...)`.
- Local functions (expression-bodied local functions are discouraged for consistency, but not
  banned the way methods are).
