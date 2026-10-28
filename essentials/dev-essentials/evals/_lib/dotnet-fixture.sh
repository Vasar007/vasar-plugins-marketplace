#!/usr/bin/env bash
# .NET setup for eval fixtures. A scaffold sources this file after git-fixture.sh.
#
# dotnet_write_common_files: .gitignore, Directory.Build.props, and nuget.config.
# Directory.Build.props turns off the git queries of the SDK, because the sandbox of a run denies reads of .gitmodules.
# dotnet_write_solution <file> <project>...: a classic .sln file, so that the scaffold needs no dotnet command.
# dotnet_write_run_marker <folder>: RunMarker.cs for an NUnit test project.
# dotnet_warm <solution>: restore and build once, so that the packages and the first-run files of dotnet exist before the agent starts.
#
# All runs share one download folder, /tmp/plugin-evals/nuget. Only the first restore downloads packages.
# The sandbox of a run cannot read /tmp. So dotnet_warm copies the shared folder into $HOME/.nuget/packages of the run,
# and nuget.config names that folder. If the shared folder is a link or another user owns it, dotnet_warm stops.
# The scaffold never runs the tests. If EVAL_FIXTURE_SKIP_DOTNET=1, dotnet_warm does nothing. Only a test sets it.
#
# This file is copied into each plugin that has .NET fixtures. A test makes sure that the copies are equal.
set -euo pipefail

dotnet_write_common_files() {
    fixture_write .gitignore <<'DOTNET_EOF'
bin/
obj/
.test-runs/
DOTNET_EOF
    fixture_write Directory.Build.props <<'DOTNET_EOF'
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <EnableSourceControlManagerQueries>false</EnableSourceControlManagerQueries>
  </PropertyGroup>
</Project>
DOTNET_EOF
    fixture_write nuget.config <<'DOTNET_EOF'
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <config>
    <add key="globalPackagesFolder" value="%HOME%/.nuget/packages" />
  </config>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  </packageSources>
</configuration>
DOTNET_EOF
}

# dotnet_write_solution <file> <project path>...: the paths use /, and the file name of each project is its name.
dotnet_write_solution() {
    local file="$1"
    shift
    local number=0 project name guid
    local guids=()
    {
        printf 'Microsoft Visual Studio Solution File, Format Version 12.00\n'
        printf '# Visual Studio Version 17\n'
        printf 'VisualStudioVersion = 17.0.31903.59\n'
        printf 'MinimumVisualStudioVersion = 10.0.40219.1\n'
        for project in "$@"; do
            number=$((number + 1))
            name="$(basename "$project" .csproj)"
            guid="$(printf '%08X-0000-4000-8000-%012X' "$number" "$number")"
            guids+=("$guid")
            printf 'Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "%s", "%s", "{%s}"\nEndProject\n' \
                "$name" "${project//\//\\}" "$guid"
        done
        printf 'Global\n'
        printf '\tGlobalSection(SolutionConfigurationPlatforms) = preSolution\n'
        printf '\t\tDebug|Any CPU = Debug|Any CPU\n\t\tRelease|Any CPU = Release|Any CPU\n'
        printf '\tEndGlobalSection\n'
        printf '\tGlobalSection(ProjectConfigurationPlatforms) = postSolution\n'
        for guid in "${guids[@]}"; do
            printf '\t\t{%s}.Debug|Any CPU.ActiveCfg = Debug|Any CPU\n' "$guid"
            printf '\t\t{%s}.Debug|Any CPU.Build.0 = Debug|Any CPU\n' "$guid"
            printf '\t\t{%s}.Release|Any CPU.ActiveCfg = Release|Any CPU\n' "$guid"
            printf '\t\t{%s}.Release|Any CPU.Build.0 = Release|Any CPU\n' "$guid"
        done
        printf '\tEndGlobalSection\n'
        printf '\tGlobalSection(SolutionProperties) = preSolution\n\t\tHideSolutionNode = FALSE\n\tEndGlobalSection\n'
        printf 'EndGlobal\n'
    } | fixture_write "$file"
}

# dotnet_write_run_marker <folder>
# At setup, the marker makes .test-runs/started-<ticks> in the repo root. At teardown, it writes the outcome
# of the run (Passed or Failed) to .test-runs/last.txt. It finds the repo root by a walk up to a .git entry.
# A grader reads these files, also when the tests ran in a subagent.
dotnet_write_run_marker() {
    fixture_write "$1/RunMarker.cs" <<'DOTNET_EOF'
using NUnit.Framework;
using NUnit.Framework.Interfaces;

[SetUpFixture]
public sealed class RunMarker
{
    [OneTimeSetUp]
    public void WriteStartFile()
    {
        var folder = GetMarkerFolder();
        File.WriteAllText(Path.Combine(folder, $"started-{DateTime.UtcNow.Ticks}"), string.Empty);
    }

    [OneTimeTearDown]
    public void WriteOutcome()
    {
        var result = TestContext.CurrentContext.Result;
        var failed = result.FailCount > 0 || result.Outcome.Status == TestStatus.Failed;
        File.WriteAllText(Path.Combine(GetMarkerFolder(), "last.txt"), failed ? "Failed" : "Passed");
    }

    private static string GetMarkerFolder()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !Path.Exists(Path.Combine(directory.FullName, ".git")))
        {
            directory = directory.Parent;
        }

        var root = directory?.FullName ?? throw new InvalidOperationException("No .git entry above the test folder.");
        var folder = Path.Combine(root, ".test-runs");
        Directory.CreateDirectory(folder);
        return folder;
    }
}
DOTNET_EOF
}

dotnet_prepare_cache() {
    local folder
    for folder in /tmp/plugin-evals /tmp/plugin-evals/nuget; do
        mkdir -p "$folder" || return 1
        if [ -L "$folder" ] || [ ! -O "$folder" ]; then
            printf '%s is a link or another user owns it. Remove it, then run the scaffold again.\n' "$folder" >&2
            return 1
        fi
        chmod 700 "$folder" || return 1
    done
}

dotnet_warm() {
    if [ "${EVAL_FIXTURE_SKIP_DOTNET:-}" = "1" ]; then
        return 0
    fi
    dotnet_prepare_cache || return 1
    export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
    dotnet restore "$1" --packages /tmp/plugin-evals/nuget --verbosity quiet
    mkdir -p "$HOME/.nuget/packages"
    cp -R /tmp/plugin-evals/nuget/. "$HOME/.nuget/packages/"
    # The agent builds with the same nuget.config, so its restore finds every package and needs no network.
    dotnet restore "$1" --verbosity quiet
    dotnet build "$1" --no-restore --verbosity quiet
}
