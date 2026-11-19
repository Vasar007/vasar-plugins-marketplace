#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/billing-fixture.sh"

make_billing_repo
fixture_write src/Billing.Domain/Shipping/ShippingFeeCalculator.cs <<'DOTNET_EOF'
namespace Billing.Domain.Shipping;

/// <summary>
/// Computes the shipping fee of an order.
/// </summary>
public sealed class ShippingFeeCalculator
{
    /// <summary>
    /// The order total from which shipping is free.
    /// </summary>
    public const decimal FreeShippingThreshold = 50m;

    /// <summary>
    /// The fee for a parcel of one kilogram.
    /// </summary>
    public const decimal BaseFee = 4.90m;

    /// <summary>
    /// The fee for each kilogram after the first one.
    /// </summary>
    public const decimal FeePerKilogram = 1.20m;

    /// <summary>
    /// The largest parcel weight in kilograms.
    /// </summary>
    public const int MaxWeightKilograms = 30;

    /// <summary>
    /// Gets the name of the carrier.
    /// </summary>
    public string Carrier { get; } = "Standard Post";

    /// <summary>
    /// Returns the shipping fee for an order total and a parcel weight in whole kilograms.
    /// </summary>
    public decimal GetFee(decimal orderTotal, int weightKilograms)
    {
        if (orderTotal < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(orderTotal), "The order total must not be negative.");
        }

        if (weightKilograms is < 1 or > MaxWeightKilograms)
        {
            throw new ArgumentOutOfRangeException(nameof(weightKilograms), "The weight must be from 1 to 30 kilograms.");
        }

        if (orderTotal >= FreeShippingThreshold)
        {
            return 0m;
        }

        return BaseFee + FeePerKilogram * (weightKilograms - 1);
    }
}
DOTNET_EOF
fixture_commit "add the shipping fee calculator"
git checkout -q -b work/tests
dotnet_warm Billing.sln
