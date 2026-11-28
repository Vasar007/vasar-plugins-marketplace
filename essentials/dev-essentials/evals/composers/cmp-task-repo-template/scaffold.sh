#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

# The repository has two issue templates, and the prompt names neither. The bug template fits the task.
# Its rules are in HTML comments, and its front matter gives the title form and the label.
make_pager_repo
fixture_notes_folder
fixture_write .github/ISSUE_TEMPLATE/bug_report.md <<'TEMPLATE_EOF'
---
name: Bug report
about: Report a defect of the pager package
title: "fix(<area>): <what is wrong>"
labels: ["type: bug"]
---

## What happens

<!-- Say in one or two sentences what goes wrong, and for whom. -->

## Steps to reproduce

<!-- A numbered list. Start from a fresh clone of the repository. -->

## Expected result

<!-- Say what must happen instead. -->
TEMPLATE_EOF
fixture_write .github/ISSUE_TEMPLATE/feature_request.md <<'TEMPLATE_EOF'
---
name: Feature request
about: Ask for a new feature of the pager package
title: "feat(<area>): <what to add>"
labels: ["type: feature"]
---

## Goal

<!-- Say what the user wants to do, and why. -->

## Proposal

<!-- List the parts of the change, one short bullet for each. -->
TEMPLATE_EOF
fixture_commit "add the issue templates"
fixture_publish main
