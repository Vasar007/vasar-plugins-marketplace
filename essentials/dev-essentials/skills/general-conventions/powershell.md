# PowerShell Script Conventions

## Invocation

Invoke `.ps1` scripts via `pwsh` (PowerShell 7+), never the legacy `powershell.exe`
(Windows PowerShell 5.1). The two versions differ in their default module versions, in
`$PSVersionTable`, and in the behavior of some cmdlets. A script that works under `pwsh`
can fail under `powershell.exe`, and the reverse is also true.

## Script Structure

Every script must include comment-based help at the top:

```powershell
<#
.SYNOPSIS
    Brief description of what the script does.

.DESCRIPTION
    Detailed description including use cases and prerequisites.

.PARAMETER ParameterName
    Description of the parameter.

.EXAMPLE
    .\Scripts\Script-Name.ps1 -Region us-east-1
    Example description.
#>
```

## Parameter Conventions

- Use `[CmdletBinding()]` and `param()` blocks.
- Destructive scripts: default `$DryRun = $true`. Require explicit `-DryRun $false`.
- Provide sensible defaults, for example `-Region "eu-central-1"`.
- Use `[ValidateSet()]`, `[ValidateNotNullOrEmpty()]` where appropriate.

## Output and Logging

- Use `Write-Host` with `-ForegroundColor` for status messages:
  - **Green**: Success, completion
  - **Yellow**: Warnings, skipped items
  - **Red**: Errors, failures
  - **Cyan**: Informational, progress
  - **White**: Standard output, headers
- Use `Write-Warning` for non-fatal issues.
- Use `Write-Error` for failures.

## Error Handling

- Wrap the API calls of the cloud provider (for example, AWS or Azure) in `try/catch`.
- Handle API throttling with exponential backoff or built-in retry.
- Provide meaningful error context (what was being attempted, which resource).

## Cloud Provider Examples

The sections below are examples for AWS and Azure. For another cloud provider, follow the same rules with its own CLI: no embedded credentials, and JSON output.

### AWS Conventions

- Use named profiles (`-ProfileName`) rather than hardcoded credentials.
- Support multiple regions where applicable.
- Use `aws` CLI v2 with `--output json` for parseable output.

### Azure Conventions

- Use `az` CLI with `--output json`.
- Authenticate with `az login`. Never embed credentials.
- Use `az account set` for subscription targeting.
