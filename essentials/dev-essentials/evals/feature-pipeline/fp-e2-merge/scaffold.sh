#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

make_inventory_repo
fp_write_context with-provider
sed -i 's/^- \*\*PR creation:\*\* none$/- **PR creation:** `mcp__plugin_github_github__create_pull_request`/' .claude/feature-pipeline-context.md
grep -q 'create_pull_request' .claude/feature-pipeline-context.md
fixture_commit "add the pipeline context"
git checkout -q -b work/merge
start_sha="$(git rev-parse HEAD)"

# The state after Step 9 of an earlier run: the change of issue 822 is committed and pushed, and PR 77 is open.
# A run makes a commit with another SHA each time. So the scaffold makes this commit, and a test pins its SHA in the mock.
fixture_write src/Inventory/SkuFormatter.cs <<'DOTNET_EOF'
namespace Inventory;

/// <summary>
/// Formats sku codes.
/// </summary>
public static class SkuFormatter
{
    /// <summary>
    /// Trims a sku code and changes it to upper case.
    /// Throws an ArgumentException if the sku is empty or only white space.
    /// </summary>
    public static string Normalize(string sku)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(sku);
        return sku.Trim().ToUpperInvariant();
    }
}
DOTNET_EOF
fixture_write tests/Inventory.Tests/SkuFormatterTests.cs <<'DOTNET_EOF'
using Inventory;

namespace Inventory.Tests;

[TestFixture]
public sealed class SkuFormatterTests
{
    [TestCase("")]
    [TestCase("   ")]
    public void Normalize_EmptySku_ThrowsArgumentException(string sku)
    {
        Assert.That(() => SkuFormatter.Normalize(sku), Throws.ArgumentException);
    }

    [Test]
    public void Normalize_SkuWithSpaces_TrimsAndUsesUpperCase()
    {
        Assert.That(SkuFormatter.Normalize(" ab-1 "), Is.EqualTo("AB-1"));
    }
}
DOTNET_EOF
fixture_commit "reject an empty sku"
fixture_publish work/merge 77:work/merge

# The artifacts of the earlier run. They are not tracked, as in a real run.
fixture_write .pipeline/822/task-context.md <<'FP_EOF'
# Task Context

- **Task ID:** 822
- **Source:** provider
- **Provider Record ID:** 822
- **Title:** Reject an empty sku
- **Priority:** unknown
- **Labels:** none
- **URL:** https://github.com/example-org/inventory/issues/822
- **Branch:** work/merge

## Description

If the sku is empty or only white space, SkuFormatter.Normalize must throw an ArgumentException. Add a test for it.

## Attachments

none

## Doc Candidates

[]
FP_EOF
fixture_write .pipeline/822/requirements.md <<'FP_EOF'
# Requirements: 822

## 1. Task Summary

`SkuFormatter.Normalize` accepts an empty sku today and returns an empty text. It must throw an `ArgumentException` for an empty sku and for a sku of white space only.

## 2. Scope

In scope: `src/Inventory/SkuFormatter.cs` and a test for it. Out of scope: the callers of `Normalize`.

## 3. Acceptance Criteria

- `Normalize("")` throws an `ArgumentException`.
- `Normalize("   ")` throws an `ArgumentException`.
- A test covers both inputs.

## 4. Technical Constraints

Pass `-m:1` to every `dotnet build` and `dotnet test` command.

## 5. Open Questions & Recommendations

None.

## 6. Risks & Considerations

`StockService` calls `Normalize`, so it now throws for an empty sku too. The issue asks for that.
FP_EOF
fixture_write .pipeline/822/spec.md <<'FP_EOF'
# Spec: 822

## 1. Resolved Questions

None.

## 2. Architecture Overview

One guard at the start of `SkuFormatter.Normalize`.

## 3. Implementation Steps

1. In `src/Inventory/SkuFormatter.cs`, replace the null guard of `Normalize` with `ArgumentException.ThrowIfNullOrWhiteSpace(sku)`.
2. Add `tests/Inventory.Tests/SkuFormatterTests.cs` with a test for an empty sku and for white space.

## 4. Execution Order

Step 1, then step 2.

## 6. Edge Cases & Error Handling

A null sku still throws an `ArgumentNullException`, which is an `ArgumentException`.
FP_EOF
fixture_write .pipeline/822/test-plan.md <<'FP_EOF'
# Test Plan: 822

## 1. Test Strategy Overview

Unit tests with NUnit in `tests/Inventory.Tests`.

## 2. Test Cases

- `Normalize_EmptySku_ThrowsArgumentException` for `""` and for `"   "`.
- `Normalize_SkuWithSpaces_TrimsAndUsesUpperCase`.

## 3. Tests for Existing Code (regression)

The three tests of `StockServiceTests` still pass.

## 4. Coverage Expectations

Each branch of `Normalize` has a test.
FP_EOF
fixture_write .pipeline/822/review.md <<'FP_EOF'
## Blocking Issues

None.

## Warnings

None.

## Suggestions

None.

## Summary

Approve. The guard and its tests do what the spec asks.
0 blocking issues / 0 warnings / 0 suggestions
FP_EOF
fixture_write .pipeline/822/security-review.md <<'FP_EOF'
# Security Review — 822

## Blocking Issues

None.

## Warnings

None.

## Summary

Approve.
0 blocking issues / 0 warnings
No security vulnerabilities identified.
FP_EOF
fixture_write .pipeline/822/pipeline-state.json <<FP_EOF
{
  "taskId": "822",
  "taskSource": "provider",
  "worktree": "work/merge",
  "noWorktree": true,
  "stage": "finalization",
  "completed": ["requirements", "spec", "implementation", "test-coverage", "docs", "review", "security-review", "finalization"],
  "taskComments": {
    "analysisPostedAt": "2026-01-01T00:20:00Z",
    "analysisCommentId": 5001,
    "preFinalizationPostedAt": "2026-01-01T00:40:00Z",
    "preFinalizationCommentId": 5002
  },
  "buildGate": {
    "result": "pass",
    "attempts": 1
  },
  "pr": {
    "number": 77,
    "url": "https://github.com/example-org/inventory/pull/77",
    "owner": "example-org",
    "repo": "inventory"
  },
  "models": {
    "requirements": "opus",
    "spec": "opus",
    "implementation": "sonnet",
    "test-coverage": "sonnet",
    "docs": "sonnet",
    "review": "opus",
    "security-review": "opus"
  },
  "stageStartSha": {
    "implementation": "$start_sha",
    "test-coverage": "$start_sha",
    "docs": "$start_sha",
    "finalization": "$start_sha"
  },
  "planArtifact": {
    "path": ".pipeline/822/822-implementation-plan.html",
    "status": "skipped"
  },
  "commitMode": "finalization",
  "startChanges": [],
  "failed": null,
  "startedAt": "2026-01-01T00:10:00Z",
  "updatedAt": "2026-01-01T00:45:00Z"
}
FP_EOF
dotnet_warm Inventory.sln
