#!/usr/bin/env bash
# The "Billing" .NET fixture for the write-tests eval cases. A scaffold sources this file after
# git-fixture.sh and dotnet-fixture.sh.
#
# make_billing_repo: Billing.sln with src/Billing.Domain and tests/Billing.Domain.Tests.
# The test project has the base classes in Tests.Common/ and one sample test class in the style of create-tests.
# main is checked out with one fixture commit. The function does not make a remote, and it does not restore or build.
# A scaffold checks out its work branch and calls dotnet_warm Billing.sln.
set -euo pipefail

BILLING_TEST_SDK_VERSION="18.11.0"
BILLING_NUNIT_VERSION="5.0.0"
BILLING_NUNIT_ADAPTER_VERSION="6.3.1"
BILLING_FLUENT_ASSERTIONS_VERSION="7.2.2"
BILLING_NSUBSTITUTE_VERSION="5.3.0"
BILLING_AUTOFIXTURE_VERSION="4.18.1"

make_billing_repo() {
    fixture_init
    dotnet_write_common_files
    fixture_write Directory.Packages.props <<DOTNET_EOF
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.NET.Test.Sdk" Version="$BILLING_TEST_SDK_VERSION" />
    <PackageVersion Include="NUnit" Version="$BILLING_NUNIT_VERSION" />
    <PackageVersion Include="NUnit3TestAdapter" Version="$BILLING_NUNIT_ADAPTER_VERSION" />
    <PackageVersion Include="FluentAssertions" Version="$BILLING_FLUENT_ASSERTIONS_VERSION" />
    <PackageVersion Include="NSubstitute" Version="$BILLING_NSUBSTITUTE_VERSION" />
    <PackageVersion Include="AutoFixture" Version="$BILLING_AUTOFIXTURE_VERSION" />
    <PackageVersion Include="AutoFixture.AutoNSubstitute" Version="$BILLING_AUTOFIXTURE_VERSION" />
  </ItemGroup>
</Project>
DOTNET_EOF
    dotnet_write_solution Billing.sln \
        src/Billing.Domain/Billing.Domain.csproj \
        tests/Billing.Domain.Tests/Billing.Domain.Tests.csproj
    fixture_write README.md <<'DOTNET_EOF'
# Billing

A small .NET solution for invoices and prices.

- Build: `dotnet build Billing.sln`
- Test: `dotnet test Billing.sln`
DOTNET_EOF
    fixture_write CLAUDE.md <<'DOTNET_EOF'
# Billing

- Build command: `dotnet build Billing.sln`
- Test command: `dotnet test Billing.sln`
- Tests use NUnit, FluentAssertions, NSubstitute, and AutoFixture.
- Test base classes are in `tests/Billing.Domain.Tests/Tests.Common`.
DOTNET_EOF
    fixture_write src/Billing.Domain/Billing.Domain.csproj <<'DOTNET_EOF'
<Project Sdk="Microsoft.NET.Sdk">
</Project>
DOTNET_EOF
    fixture_write src/Billing.Domain/Money.cs <<'DOTNET_EOF'
namespace Billing.Domain;

/// <summary>
/// An amount of money in one currency.
/// </summary>
public sealed record Money(decimal Amount, string Currency)
{
    /// <summary>
    /// Adds two amounts. Both must have the same currency.
    /// </summary>
    public Money Add(Money other)
    {
        ArgumentNullException.ThrowIfNull(other);
        if (other.Currency != Currency)
        {
            throw new InvalidOperationException("The currencies differ.");
        }

        return this with { Amount = Amount + other.Amount };
    }

    /// <summary>
    /// Multiplies the amount by a factor.
    /// </summary>
    public Money Multiply(decimal factor)
    {
        return this with { Amount = Amount * factor };
    }
}
DOTNET_EOF
    fixture_write src/Billing.Domain/Invoices/InvoiceNumberGenerator.cs <<'DOTNET_EOF'
namespace Billing.Domain.Invoices;

/// <summary>
/// Makes and reads invoice numbers such as INV-2026-000042.
/// </summary>
public sealed class InvoiceNumberGenerator
{
    private const string Prefix = "INV";

    /// <summary>
    /// Makes the invoice number for a sequence number and a date.
    /// </summary>
    public string Generate(int sequence, DateOnly date)
    {
        if (sequence <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(sequence), "The sequence must be positive.");
        }

        return $"{Prefix}-{date.Year:D4}-{sequence:D6}";
    }

    /// <summary>
    /// Reads the sequence number of an invoice number. Returns false if the text has another format.
    /// </summary>
    public bool TryParseSequence(string value, out int sequence)
    {
        sequence = 0;
        var parts = value.Split('-');
        return parts.Length == 3
            && parts[0] == Prefix
            && int.TryParse(parts[2], out sequence)
            && sequence > 0;
    }
}
DOTNET_EOF
    fixture_write src/Billing.Domain/Pricing/RoundingPolicy.cs <<'DOTNET_EOF'
namespace Billing.Domain.Pricing;

/// <summary>
/// Rounds money amounts.
/// </summary>
public interface IRoundingPolicy
{
    /// <summary>
    /// Rounds an amount to the smallest unit of the currency.
    /// </summary>
    decimal Round(decimal amount);
}

/// <summary>
/// Rounds to two decimal places. A middle value goes to the even neighbor.
/// </summary>
public sealed class RoundingPolicy : IRoundingPolicy
{
    /// <inheritdoc />
    public decimal Round(decimal amount)
    {
        return Math.Round(amount, 2, MidpointRounding.ToEven);
    }
}
DOTNET_EOF
    fixture_write src/Billing.Domain/Pricing/DiscountCalculator.cs <<'DOTNET_EOF'
namespace Billing.Domain.Pricing;

/// <summary>
/// Applies percent discounts to prices.
/// </summary>
public sealed class DiscountCalculator
{
    private readonly IRoundingPolicy _rounding;

    /// <summary>
    /// Makes the calculator.
    /// </summary>
    public DiscountCalculator(IRoundingPolicy rounding)
    {
        _rounding = rounding ?? throw new ArgumentNullException(nameof(rounding));
    }

    /// <summary>
    /// Returns the price after a discount of 0 to 100 percent.
    /// </summary>
    public Money Apply(Money price, int percent)
    {
        ArgumentNullException.ThrowIfNull(price);
        if (percent is < 0 or > 100)
        {
            throw new ArgumentOutOfRangeException(nameof(percent), "The percent must be from 0 to 100.");
        }

        var discounted = price.Amount * (100 - percent) / 100m;
        return price with { Amount = _rounding.Round(discounted) };
    }
}
DOTNET_EOF
    fixture_write src/Billing.Domain/Pricing/TaxCalculator.cs <<'DOTNET_EOF'
namespace Billing.Domain.Pricing;

/// <summary>
/// Adds tax to net prices.
/// </summary>
public sealed class TaxCalculator
{
    private readonly IRoundingPolicy _rounding;

    /// <summary>
    /// Makes the calculator.
    /// </summary>
    public TaxCalculator(IRoundingPolicy rounding)
    {
        _rounding = rounding ?? throw new ArgumentNullException(nameof(rounding));
    }

    /// <summary>
    /// Returns the tax of a net price for a rate such as 0.2 for 20 percent.
    /// </summary>
    public Money GetTax(Money net, decimal rate)
    {
        ArgumentNullException.ThrowIfNull(net);
        if (rate < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(rate), "The rate must not be negative.");
        }

        return net with { Amount = _rounding.Round(net.Amount * rate) };
    }

    /// <summary>
    /// Returns the gross price: the net price plus its tax.
    /// </summary>
    public Money AddTax(Money net, decimal rate)
    {
        return net.Add(GetTax(net, rate));
    }
}
DOTNET_EOF
    fixture_write tests/Billing.Domain.Tests/Billing.Domain.Tests.csproj <<'DOTNET_EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" />
    <PackageReference Include="NUnit" />
    <PackageReference Include="NUnit3TestAdapter" />
    <PackageReference Include="FluentAssertions" />
    <PackageReference Include="NSubstitute" />
    <PackageReference Include="AutoFixture" />
    <PackageReference Include="AutoFixture.AutoNSubstitute" />
  </ItemGroup>
  <ItemGroup>
    <Using Include="NUnit.Framework" />
    <Using Include="FluentAssertions" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\Billing.Domain\Billing.Domain.csproj" />
  </ItemGroup>
</Project>
DOTNET_EOF
    dotnet_write_run_marker tests/Billing.Domain.Tests
    fixture_write tests/Billing.Domain.Tests/Tests.Common/BaseTest.cs <<'DOTNET_EOF'
using AutoFixture;

namespace Billing.Domain.Tests.Common;

/// <summary>
/// The base class of tests that need no mocks.
/// </summary>
[TestFixture]
public abstract class BaseTest
{
    /// <summary>
    /// Gets the generator of test data.
    /// </summary>
    protected IFixture Fixture { get; } = new Fixture();
}
DOTNET_EOF
    fixture_write tests/Billing.Domain.Tests/Tests.Common/BaseMockTest.cs <<'DOTNET_EOF'
using AutoFixture;
using AutoFixture.AutoNSubstitute;

namespace Billing.Domain.Tests.Common;

/// <summary>
/// The base class of tests that need mocks. AutoFixture makes the mocks with NSubstitute.
/// </summary>
[TestFixture]
public abstract class BaseMockTest
{
    /// <summary>
    /// Gets the generator of test data and mocks.
    /// </summary>
    protected IFixture Fixture { get; } = new Fixture().Customize(new AutoNSubstituteCustomization
    {
        ConfigureMembers = true,
    });

    /// <summary>
    /// Makes a mock and reuses it for each later request of the same type.
    /// </summary>
    protected T CreateMock<T>()
        where T : class
    {
        return Fixture.Freeze<T>();
    }
}
DOTNET_EOF
    fixture_write tests/Billing.Domain.Tests/MoneyTests.cs <<'DOTNET_EOF'
using AutoFixture;
using Billing.Domain.Tests.Common;

namespace Billing.Domain.Tests;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class MoneyTests : BaseTest
{
    [Test]
    public void Add_SameCurrency_ReturnsSum()
    {
        // Arrange.
        var first = new Money(Fixture.Create<Decimal>(), "EUR");
        var second = new Money(Fixture.Create<Decimal>(), "EUR");
        var expected = first.Amount + second.Amount;

        // Act.
        var actual = first.Add(second);

        // Assert.
        actual.Amount.Should().Be(expected);
        actual.Currency.Should().Be(first.Currency);
    }

    [Test]
    public void Add_OtherCurrency_Throws()
    {
        // Arrange.
        var first = new Money(Fixture.Create<Decimal>(), "EUR");
        var second = new Money(Fixture.Create<Decimal>(), "USD");

        // Act.
        var act = () => first.Add(second);

        // Assert.
        act.Should().Throw<InvalidOperationException>();
    }

    [Test]
    public void Multiply_Factor_ReturnsProduct()
    {
        // Arrange.
        var money = new Money(10m, "EUR");
        var factor = 3m;
        var expected = money.Amount * factor;

        // Act.
        var actual = money.Multiply(factor);

        // Assert.
        actual.Amount.Should().Be(expected);
    }
}
DOTNET_EOF
    fixture_commit "add the Billing solution"
}
