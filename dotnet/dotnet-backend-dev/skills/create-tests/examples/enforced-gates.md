# Enforced Gates

Seven additional conventions, each corroborated by real corrections on shipped code, that this
skill enforces on top of the patterns documented elsewhere in [SKILL.md](../SKILL.md) and the
other files in this directory. Each gate below states the rule, the concrete example, and — where
the source correction specified one — a pre-completion grep self-check.

## Gate 1 — Method-level null-arg coverage (not just constructors)

**Why:** The constructor null-arg pattern (see
[constructor-null-arg-tests.md](constructor-null-arg-tests.md)) also applies to every **public
method** on the SUT, not only constructors. Per-parameter individual tests
(`MethodAsync_ShouldThrow_WhenOrderIdIsNull`, `MethodAsync_ShouldThrow_WhenCustomerDetailsIsNull`,
…) bloat the fixture, fragment the null-arg surface across several test names per method, and make
it tedious to verify "every required param has a null check" at a glance. The foreach-merged form
keeps the surface visible in one place — adding a new required param means adding ONE line to the
list, not authoring a new test.

For every public method with at least one required reference-type parameter, write ONE combined
test: `<Method>_ShouldThrowArgumentNullException_ForEachRequiredArgument`. Iterate a
`List<Func<Task>>` for async methods (`List<Action>` for sync methods), with each entry passing
`null!` positionally for exactly one required reference parameter — the same required-positional
mechanism as the constructor pattern, never `null! ?? CreateXxx()`.

Unlike the constructor pattern, where each lambda calls `CreateServiceWithAllArguments` fresh so
there is no shared "all valid" instance a null substitution could hide behind, this pattern reuses
one `processor` instance across every lambda in the list — that is only safe if the SUT's guard
clauses run before any side effect, so no earlier lambda in the `foreach` can mutate state the
processor depends on before a later lambda's guard clause gets a chance to throw. If that
precondition can't be guaranteed for the SUT under test, build a fresh instance per lambda instead
(the constructor pattern's approach), rather than sharing `processor`.

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

- ONE foreach-merged test per public method per fixture. NEVER per-parameter individual
  `WhenXIsNull` tests.
- **General principle: partition required-param null-arg tests by expected exception type, not
  by an ad hoc parameter-type list.** Different guard clauses throw different exceptions —
  `ThrowIfNull()` throws `ArgumentNullException`; `ThrowIfNullOrWhiteSpace()` (used for `String`)
  throws `ArgumentException` (Gate 6's assertion split). A single foreach test can only assert one
  exception type per `Should().ThrowAsync<T>()` call, so each exception-type partition gets its
  own merged foreach test. The concrete exclusions below are consequences of this rule, not a
  separate ad hoc list:
  - `CancellationToken`, value types, and nullable-by-design reference types: excluded entirely —
    `null` is a legal value for those, not a guard violation, so there is no exception to partition
    by.
  - Required `String` parameters: guarded with `ThrowIfNullOrWhiteSpace()`, which throws
    `ArgumentException`, not `ArgumentNullException` — so they belong to a different partition than
    the merged `ArgumentNullException` foreach test. Route each to its own
    `[TestCaseSource(typeof(StringNullOrWhiteSpace_TestCases))]` test instead of the foreach.
  - For a method mixing `String` and other required reference parameters: write the foreach
    `ArgumentNullException` test for the non-`String` parameters (one partition) and a separate
    `StringNullOrWhiteSpace_TestCases` test per `String` parameter (the `ArgumentException`
    partition).
- If a method has NO required reference parameters, skip the foreach test entirely for that
  method — don't create an empty list.
- Group the test with the method's other behaviour tests inside the same `#region <Method> Tests`
  block (see Gate 4 for fixture-body ordering).

Source: corroborated by repeated review corrections on shipped test code.

## Gate 2 — No async-wrapping single-expression lambdas

**Why:** `async () => await x.MethodAsync(...)` adds a pointless extra state machine and async
layer when the inner call already returns a `Task` — `Func<Task>` is exactly what
`Should().ThrowAsync()` and `List<Func<Task>>` entries consume directly. Reviewers (human and AI)
flag the wrapped form as overblown.

```csharp
// ❌ WRONG — needless async/await wrapping of a single expression
var act = async () => await processor.ProcessAsync(orderId, customerDetails);

// ✅ CORRECT — the lambda body is already a Task-returning expression
var act = () => processor.ProcessAsync(orderId, customerDetails);
```

Also drop a trailing `CancellationToken.None` argument when the method signature already
defaults the token (`CancellationToken cancellationToken = default`) — pass nothing.

**Exception:** keep the `async`/`await` form when the lambda body genuinely has multiple awaits or
non-trivial async logic — only single-expression wrapping is forbidden.

**Pre-completion grep gate:** before claiming a test fixture done, grep your new/changed tests for
`async () => await` (case-sensitive). For every match, either collapse it to the direct form or
confirm the body has more than one await/non-trivial logic that justifies keeping it.

Source: corroborated by repeated review corrections on shipped test code.

## Gate 3 — SUT naming from the class's role suffix

**Why:** Reading a test where every variable is `sut` forces the reader to remember which class is
under test. `var processor = CreateProcessor(...)` instantly signals both the SUT's kind and that
the test is doing processor-shaped things.

Name the SUT variable and its factory helper after the class's role-suffix noun — `Service`,
`Processor`, `Resolver`, `Updater`, `Validator`, `Provider`, `Handler`, `Manager`, `Coordinator`,
`Repository`, etc. NEVER `sut` / `CreateSut`.

```csharp
// ✅ CORRECT
var processor = CreateProcessor(orderRepository: ...);      // OrderProcessor
var updater = CreateUpdater(customerProfileRepository: ...); // CustomerProfileUpdater
var repository = CreateRepository(...);                      // OrderRepository

// ❌ WRONG
var sut = CreateSut(...);
```

Edge cases (use judgement, and say so in a comment):

- **Two SUTs in scope** (unusual): pick a more specific noun for each (`primaryProcessor`,
  `retryProcessor`) rather than falling back to `sut1` / `sut2`.
- **No obvious role suffix** (e.g. a class named `Order` standalone): pick the most concrete
  domain noun available (`order`, `orderDetails`) and add a short comment noting that the class
  has no role suffix — this is a design smell worth flagging, not silently working around.

Source: corroborated by repeated review corrections on shipped test code, including the SUT
naming used throughout Gate 1's example above.

## Gate 4 — Helper-file ordering and the inheritance rule

**Why:** Reading order matters — the reader scrolls top-down through
`#region Constructor Tests` → `#region <Method> Tests` for each public method and sees the actual
test cases first; helpers are reference material for when the reader needs to know HOW a mock was
built. Putting helpers at the top (or interleaved with tests) forces scrolling past
arrange-machinery before reaching the behaviour assertions.

Fixture body order, top to bottom:

1. Class-level fields (rarely needed beyond what the base class already exposes).
2. `#region Constructor Tests` (ctor null-arg `foreach`-over-`List<Action>`, see
   [constructor-null-arg-tests.md](constructor-null-arg-tests.md)).
3. `#region <PublicMethod1> Tests`, `#region <PublicMethod2> Tests`, … — one region per public
   method, containing both behaviour tests and that method's null-arg foreach test (Gate 1).
4. ALL private helper methods last, inside a single `#region Helper Methods` — private, except
   for a base-fixture helper a derived fixture must call; use `protected` for those (see the
   inheritance pair rule below).

**Inheritance pair rule:** when a base fixture (`XxxBaseTests`) is shared by derived fixtures,
helpers live in the base class ONLY. Derived classes contain ONLY `[Test]` methods plus their own
explicit parameterless constructor — never a re-declared or overridden helper. A helper that only
the base fixture's own tests call stays `private`; a helper a derived fixture must also call needs
`protected` — `private` members aren't accessible outside their declaring type.

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

Source: corroborated by repeated review corrections on shipped test code.

## Gate 5 — NSubstitute `Arg.Any<T>()` vs `default`

**Why:** Record structs in C# generate compiler-synthesized value equality; when NSubstitute
resolves `Arg.Any<TRecordStruct>()` at call time it can collide with an ordinary argument value
that happens to equal the type's `default`, producing
`NSubstitute.Exceptions.AmbiguousArgumentsException`. Passing `default` directly (no matcher)
bypasses the collision, but that is a narrow workaround — not a license to blanket every argument
with `default`.

Use `Arg.Any<T>()` for:

- reference types and nullable reference types,
- interfaces,
- ordinary value types (`Int32`, `Boolean`, `Guid`, `DateTime`, …).

Use `default` ONLY for the specific record-struct wrapper types you've confirmed trigger
`AmbiguousArgumentsException` in this codebase — try `Arg.Any<T>()` first, and fall back to
`default` only after confirming the exception actually fires for that type. Always add a one-line
comment identifying which type and why when you use `default`.

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

Note: `ReceivedWithAnyArgs(N)` ignores argument *values* for call-matching, but that doesn't make
the matcher choice irrelevant here — `Arg.Any<T>()` / `default` are evaluated as part of building
the call expression itself, before NSubstitute ever gets to the "received" comparison. The
`AmbiguousArgumentsException` risk is a property of that evaluation step, so it applies equally
under `ReceivedWithAnyArgs` even though the received-args comparison it performs doesn't care
about the values.

This applies everywhere NSubstitute takes an argument matcher: `Received(N)` /
`ReceivedWithAnyArgs(N)` assertions and `.Returns(...)` / `.Throws(...)` setups inside Test Mock
Builders.

Source: corroborated by repeated review corrections on shipped test code.

## Gate 6 — Prefer this repo's own null-guard extension over the raw BCL form

**Why:** This repo's own conventions (see
[dotnet-conventions/application-services.md](../../dotnet-conventions/application-services.md) and
[dotnet-conventions/domain-models.md](../../dotnet-conventions/domain-models.md)) standardize
constructor and method-parameter guarding on a fluent `obj.ThrowIfNull()` extension, not the BCL
static `ArgumentNullException.ThrowIfNull(obj)` form. Mixing in the BCL static form creates needless
heterogeneity in a codebase that has standardized on the fluent extension — including in test
helper code that mirrors production guard-clause style.

```csharp
// ❌ WRONG — BCL static form
ArgumentNullException.ThrowIfNull(repository);
_repository = repository;

// ✅ CORRECT — this repo's fluent extension
_repository = repository.ThrowIfNull();
```

Applies to every constructor guard, every public-method parameter guard, and every SUT-helper
builder, in both production code and test code. Both the assignment form (`_field =
obj.ThrowIfNull();`) and the guard-only form (`obj.ThrowIfNull();`) are valid.

**Assertion split:** the guard type determines the expected exception in the corresponding
negative test — `ThrowIfNull()` pairs with `ArgumentNullException`; the string-specific
`ThrowIfNullOrWhiteSpace()` pairs with `ArgumentException` (it covers null, empty, and
whitespace-only string arguments in one guard).

Source: corroborated by repeated review corrections on shipped test code, consistent with the
guard-clause convention already documented in this repo's `dotnet-conventions`.

## Gate 7 — No expression-bodied methods

**Why:** This repo's review convention is to read a method body inside braces even when it is one
statement — this reduces visual ambiguity between methods and properties, and keeps future diffs
(adding logging, tracing, or a conditional) small instead of requiring a body-shape rewrite.

Methods — including one-line delegate forwarders and test helper methods — use block `{ ... }`
bodies. Expression-bodied `=>` syntax is forbidden for methods specifically.

**Scope:** test fixtures and service-under-test helper methods. Production wrapper-factory/equality-member
expression bodies are a separate, established convention — see
`dotnet-backend-dev:create-primitive-wrapper` and
[dotnet-conventions/domain-models.md](../../dotnet-conventions/domain-models.md) — and are out of
scope for this gate.

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
- Lambdas — inside LINQ, `Substitute.For<T>()`, `Arg.Is<T>(x => ...)`,
  `Should().ThrowAsync<T>().WithMessage(...)`, `.ApplyIf(...)`, etc.
- Local functions (expression-bodied local functions are discouraged for consistency, but not
  banned the way methods are).

Source: corroborated by repeated review corrections on shipped test code.
