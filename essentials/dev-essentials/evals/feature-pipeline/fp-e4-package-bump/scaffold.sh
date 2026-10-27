#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

INVENTORY_NUNIT_VERSION="4.6.1"

# The run has no network. So the new version goes into the shared folder before dotnet_warm copies it.
prefetch_package() {
    [ "${EVAL_FIXTURE_SKIP_DOTNET:-}" = "1" ] && return 0
    dotnet_prepare_cache
    local folder
    folder="$(mktemp -d)"
    printf '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup><ItemGroup><PackageReference Include="%s" Version="%s" /></ItemGroup></Project>\n' "$1" "$2" > "$folder/prefetch.csproj"
    dotnet restore "$folder/prefetch.csproj" --packages /tmp/plugin-evals/nuget --verbosity quiet
    rm -rf "$folder"
}

make_inventory_repo
fp_write_context with-provider
fixture_commit "add the pipeline context"
git checkout -q -b work/package-bump
fixture_publish work/package-bump
prefetch_package NUnit 5.0.0
dotnet_warm Inventory.sln
