#!/usr/bin/env bash
# The "Inventory" .NET fixture for the feature-pipeline eval cases. A scaffold sources this file after
# git-fixture.sh and dotnet-fixture.sh.
#
# make_inventory_repo: Inventory.sln with src/Inventory, src/Inventory.Reports, and tests/Inventory.Tests.
# main is checked out with one fixture commit and a bare remote. The function does not publish, and it does not
# restore or build. A scaffold adds its branch, calls fixture_publish, and then calls dotnet_warm Inventory.sln.
set -euo pipefail

# fp-e4-package-bump sets an older NUnit version after it sources this file.
INVENTORY_NUNIT_VERSION="$DOTNET_NUNIT_VERSION"

make_inventory_repo() {
    fixture_init
    dotnet_write_common_files
    fixture_write Directory.Packages.props <<DOTNET_EOF
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.NET.Test.Sdk" Version="$DOTNET_TEST_SDK_VERSION" />
    <PackageVersion Include="NUnit" Version="$INVENTORY_NUNIT_VERSION" />
    <PackageVersion Include="NUnit3TestAdapter" Version="$DOTNET_NUNIT_ADAPTER_VERSION" />
  </ItemGroup>
</Project>
DOTNET_EOF
    dotnet_write_solution Inventory.sln \
        src/Inventory/Inventory.csproj \
        src/Inventory.Reports/Inventory.Reports.csproj \
        tests/Inventory.Tests/Inventory.Tests.csproj
    fixture_write README.md <<'DOTNET_EOF'
# Inventory

A small .NET solution that reads and changes stock levels.

- Build: `dotnet build Inventory.sln`
- Test: `dotnet test Inventory.sln`
DOTNET_EOF
    fixture_write CLAUDE.md <<'DOTNET_EOF'
# Inventory

- Build command: `dotnet build Inventory.sln`
- Test command: `dotnet test Inventory.sln`
- Package versions are in `Directory.Packages.props`.
- Pass `-m:1` to every `dotnet build` and `dotnet test` command.
DOTNET_EOF
    fixture_write REVIEW.md <<'DOTNET_EOF'
# Review rules

- Each public method in `src/Inventory` has an XML doc comment.
DOTNET_EOF
    fixture_write src/Inventory/Inventory.csproj <<'DOTNET_EOF'
<Project Sdk="Microsoft.NET.Sdk">
</Project>
DOTNET_EOF
    fixture_write src/Inventory/ISqlRunner.cs <<'DOTNET_EOF'
namespace Inventory;

/// <summary>
/// Runs SQL against the stock database.
/// </summary>
public interface ISqlRunner
{
    /// <summary>
    /// Runs a query that returns one number.
    /// </summary>
    int Query(string sql, IReadOnlyDictionary<string, object> parameters);

    /// <summary>
    /// Runs one query for many skus and returns one number for each sku.
    /// </summary>
    IReadOnlyDictionary<string, int> QueryMany(string sql, IReadOnlyCollection<string> skus);

    /// <summary>
    /// Runs a statement that changes data.
    /// </summary>
    void Execute(string sql, IReadOnlyDictionary<string, object> parameters);
}
DOTNET_EOF
    fixture_write src/Inventory/SqlParameters.cs <<'DOTNET_EOF'
namespace Inventory;

/// <summary>
/// Builds the parameter maps of SQL calls.
/// </summary>
public static class SqlParameters
{
    /// <summary>
    /// Makes a parameter map for one sku.
    /// </summary>
    public static IReadOnlyDictionary<string, object> ForSku(string sku)
    {
        return new Dictionary<string, object> { ["sku"] = sku };
    }

    /// <summary>
    /// Makes a parameter map for one sku and one amount.
    /// </summary>
    public static IReadOnlyDictionary<string, object> ForSku(string sku, int amount)
    {
        return new Dictionary<string, object> { ["sku"] = sku, ["amount"] = amount };
    }
}
DOTNET_EOF
    fixture_write src/Inventory/SkuFormatter.cs <<'DOTNET_EOF'
namespace Inventory;

/// <summary>
/// Formats sku codes.
/// </summary>
public static class SkuFormatter
{
    /// <summary>
    /// Trims a sku code and changes it to upper case.
    /// </summary>
    public static string Normalize(string sku)
    {
        ArgumentNullException.ThrowIfNull(sku);
        return sku.Trim().ToUpperInvariant();
    }
}
DOTNET_EOF
    fixture_write src/Inventory/InventoryOptions.cs <<'DOTNET_EOF'
namespace Inventory;

/// <summary>
/// The options of the inventory service.
/// </summary>
public sealed class InventoryOptions
{
    /// <summary>
    /// Gets the stock level at or below which an item counts as low.
    /// </summary>
    public int LowStockThreshold { get; init; } = 5;
}
DOTNET_EOF
    fixture_write src/Inventory/StockService.cs <<'DOTNET_EOF'
namespace Inventory;

/// <summary>
/// Reads and changes the stock level of each sku.
/// </summary>
public sealed class StockService
{
    private const string QuantitySql = "SELECT quantity FROM stock WHERE sku = @sku";
    private const string RestockSql = "UPDATE stock SET quantity = quantity + @amount WHERE sku = @sku";

    private readonly ISqlRunner _sql;

    /// <summary>
    /// Makes the service.
    /// </summary>
    public StockService(ISqlRunner sql)
    {
        _sql = sql ?? throw new ArgumentNullException(nameof(sql));
    }

    /// <summary>
    /// Returns the quantity in stock for a sku. A sku with no row has the quantity 0.
    /// </summary>
    public int GetQuantity(string sku)
    {
        return _sql.Query(QuantitySql, SqlParameters.ForSku(SkuFormatter.Normalize(sku)));
    }

    /// <summary>
    /// Adds an amount to the stock of a sku.
    /// </summary>
    public void Restock(string sku, int amount)
    {
        _sql.Execute(RestockSql, SqlParameters.ForSku(SkuFormatter.Normalize(sku), amount));
    }
}
DOTNET_EOF
    fixture_write src/Inventory.Reports/Inventory.Reports.csproj <<'DOTNET_EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <ProjectReference Include="..\Inventory\Inventory.csproj" />
  </ItemGroup>
</Project>
DOTNET_EOF
    fixture_write src/Inventory.Reports/ReportBuilder.cs <<'DOTNET_EOF'
using Inventory;

namespace Inventory.Reports;

public sealed class ReportBuilder
{
    private readonly StockService _stock;

    public ReportBuilder(StockService stock)
    {
        _stock = stock ?? throw new ArgumentNullException(nameof(stock));
    }

    public string BuildLine(string sku)
    {
        return $"{sku}: {_stock.GetQuantity(sku)}";
    }
}
DOTNET_EOF
    fixture_write tests/Inventory.Tests/Inventory.Tests.csproj <<'DOTNET_EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" />
    <PackageReference Include="NUnit" />
    <PackageReference Include="NUnit3TestAdapter" />
  </ItemGroup>
  <ItemGroup>
    <Using Include="NUnit.Framework" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\Inventory\Inventory.csproj" />
    <ProjectReference Include="..\..\src\Inventory.Reports\Inventory.Reports.csproj" />
  </ItemGroup>
</Project>
DOTNET_EOF
    dotnet_write_run_marker tests/Inventory.Tests
    fixture_write tests/Inventory.Tests/FakeSqlRunner.cs <<'DOTNET_EOF'
using Inventory;

namespace Inventory.Tests;

internal sealed class FakeSqlRunner : ISqlRunner
{
    private readonly Dictionary<string, int> _stock = new();

    public int Query(string sql, IReadOnlyDictionary<string, object> parameters)
    {
        return _stock.GetValueOrDefault((string)parameters["sku"]);
    }

    public IReadOnlyDictionary<string, int> QueryMany(string sql, IReadOnlyCollection<string> skus)
    {
        return skus.ToDictionary(sku => sku, sku => _stock.GetValueOrDefault(sku));
    }

    public void Execute(string sql, IReadOnlyDictionary<string, object> parameters)
    {
        var sku = (string)parameters["sku"];
        _stock[sku] = _stock.GetValueOrDefault(sku) + (int)parameters["amount"];
    }
}
DOTNET_EOF
    fixture_write tests/Inventory.Tests/StockServiceTests.cs <<'DOTNET_EOF'
using Inventory;

namespace Inventory.Tests;

[TestFixture]
public sealed class StockServiceTests
{
    [Test]
    public void GetQuantity_UnknownSku_ReturnsZero()
    {
        var service = new StockService(new FakeSqlRunner());

        var actual = service.GetQuantity("ab-1");

        Assert.That(actual, Is.EqualTo(0));
    }

    [Test]
    public void Restock_ThenGetQuantity_ReturnsNewAmount()
    {
        var service = new StockService(new FakeSqlRunner());
        var before = service.GetQuantity("ab-1");

        service.Restock("ab-1", 5);
        var after = service.GetQuantity("ab-1");

        Assert.That(before, Is.EqualTo(0));
        Assert.That(after, Is.EqualTo(5));
    }

    [Test]
    public void Restock_SkuInAnyCase_AddsToTheSameStock()
    {
        var service = new StockService(new FakeSqlRunner());

        service.Restock("ab-1", 2);
        service.Restock(" AB-1 ", 3);

        Assert.That(service.GetQuantity("Ab-1"), Is.EqualTo(5));
    }
}
DOTNET_EOF
    fixture_commit "add the Inventory solution"
    fixture_remote_init
}
