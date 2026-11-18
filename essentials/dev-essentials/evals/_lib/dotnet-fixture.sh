#!/usr/bin/env bash
# .NET setup for eval fixtures. A scaffold sources this file after git-fixture.sh.
#
# DOTNET_TEST_SDK_VERSION, DOTNET_NUNIT_VERSION, DOTNET_NUNIT_ADAPTER_VERSION: the test packages of each .NET fixture.
# RunMarker.cs uses the NUnit API, so the NUnit version is set in this file.
# dotnet_write_common_files: .gitignore, Directory.Build.props, and nuget.config.
# Directory.Build.props turns off the git queries of the SDK, because the sandbox of a run denies reads of .gitmodules.
# It also has the target MarkTestOutcomeStale of the run marker.
# dotnet_write_solution <file> <project>...: a classic .sln file, so that the scaffold needs no dotnet command.
# dotnet_write_run_marker <folder>: RunMarker.cs for an NUnit test project.
# dotnet_warm <solution> [<package>@<version>...]: restore and build once, so that the packages and the first-run files of dotnet
# exist before the agent starts. Each named package also goes into the shared folder, so that a run with no network can use it.
#
# All runs share one download folder, /tmp/plugin-evals/nuget. Only the first restore downloads packages.
# The sandbox of a run cannot read /tmp. So dotnet_warm copies the shared folder into $HOME/.nuget/packages of the run,
# and nuget.config names that folder. If the shared folder is a link or another user owns it, dotnet_warm stops.
# Each run has its own TMPDIR, so the file locks of NuGet do not guard the shared folder. So dotnet_warm holds
# a lock on /tmp/plugin-evals/nuget.lock while it restores into the shared folder and copies it. The lock needs flock (util-linux).
# Each dotnet command has -nodeReuse:false. A reused MSBuild node keeps the NuGet lock folder in the TMPDIR of an earlier run.
# The eval tool seals the tmp folder of a kept run, so the next scaffold then fails on that lock (issue 250).
# The dotnet commands write their output to stderr. In the failed runs of issue 147, the error message of the scaffold was empty, and dotnet writes its errors to stdout.
# The scaffold never runs the tests. If EVAL_FIXTURE_SKIP_DOTNET=1, dotnet_warm does nothing.
# EVAL_FIXTURE_DOTNET_CACHE replaces the folder /tmp/plugin-evals. Only a test sets these two variables.
#
# dotnet-backend-dev has a git symlink to this file. A test makes sure that the link is there.
set -euo pipefail

DOTNET_TEST_SDK_VERSION="18.11.0"
DOTNET_NUNIT_VERSION="5.0.0"
DOTNET_NUNIT_ADAPTER_VERSION="6.3.1"

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
  <Target Name="MarkTestOutcomeStale" BeforeTargets="CoreCompile"
          Inputs="$(MSBuildAllProjects);@(Compile);@(ReferencePathWithRefAssemblies);@(CustomAdditionalCompileInputs)"
          Outputs="@(IntermediateAssembly)"
          Condition="Exists('$(MSBuildThisFileDirectory).test-runs/last.txt')">
    <WriteLinesToFile File="$(MSBuildThisFileDirectory).test-runs/last.txt" Lines="Stale" Overwrite="true" />
  </Target>
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
# The marker writes Started at setup, and Passed or Failed at teardown, to .test-runs/last.txt in the repo root.
# The target MarkTestOutcomeStale in Directory.Build.props writes Stale there before a compile of changed code.
# A grader reads the file, also when the tests ran in a subagent. docs/evals.md lists the limits of the marker.
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
        File.WriteAllText(Path.Combine(folder, "last.txt"), "Started");
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

# dotnet_prepare_cache <cache folder>
dotnet_prepare_cache() {
    local folder
    for folder in "$1" "$1/nuget"; do
        mkdir -p "$folder" || return 1
        if [ -L "$folder" ] || [ ! -O "$folder" ]; then
            printf '%s is a link or another user owns it. Remove it, then run the scaffold again.\n' "$folder" >&2
            return 1
        fi
        chmod 700 "$folder" || return 1
    done
}

# dotnet_warm <solution> [<package>@<version>...]
dotnet_warm() {
    if [ "${EVAL_FIXTURE_SKIP_DOTNET:-}" = "1" ]; then
        return 0
    fi
    local solution="$1"
    shift
    local cache="${EVAL_FIXTURE_DOTNET_CACHE:-/tmp/plugin-evals}"
    dotnet_prepare_cache "$cache" || return 1
    export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
    (
        flock 9
        # dotnet does not get the lock descriptor, because an MSBuild node that lives on keeps the lock.
        local folder package
        folder="$(mktemp -d)"
        trap 'rm -rf "$folder"' EXIT
        for package in "$@"; do
            printf '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup><ItemGroup><PackageReference Include="%s" Version="%s" /></ItemGroup></Project>\n' \
                "${package%@*}" "${package#*@}" > "$folder/prefetch.csproj"
            dotnet restore "$folder/prefetch.csproj" --packages "$cache/nuget" --verbosity quiet -nodeReuse:false >&2 9>&-
        done
        dotnet restore "$solution" --packages "$cache/nuget" --verbosity quiet -nodeReuse:false >&2 9>&-
        mkdir -p "$HOME/.nuget/packages"
        cp -R "$cache/nuget/." "$HOME/.nuget/packages/"
    ) 9>"$cache/nuget.lock"
    # The agent builds with the same nuget.config, so its restore finds every package and needs no network.
    dotnet restore "$solution" --verbosity quiet -nodeReuse:false >&2
    dotnet build "$solution" --no-restore --verbosity quiet -nodeReuse:false >&2
}
