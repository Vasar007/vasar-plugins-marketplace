# PowerShell Script Conventions

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
- Provide sensible defaults (e.g., `-Region "eu-central-1"`).
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

- Wrap AWS/Azure API calls in `try/catch`.
- Handle API throttling with exponential backoff or built-in retry.
- Provide meaningful error context (what was being attempted, which resource).

## AWS Conventions

- Use named profiles (`-ProfileName`) rather than hardcoded credentials.
- Support multiple regions where applicable.
- Use `aws` CLI v2 with `--output json` for parseable output.

## Azure Conventions

- Use `az` CLI with `--output json`.
- Authenticate via `az login` — never embed credentials.
- Use `az account set` for subscription targeting.
