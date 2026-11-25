# Fix Shipped Entity — The E-Disposition Path, End to End

Sanitized cases, each based on a real finding. Cases 1 and 2 end the same way: an edit to an already-shipped entity, and the source pruned. Neither case makes a new entity. Case 3 shows the mixed outcome that one wrapper file can produce after a diff of each section. The repo names and the rule content are fictional. No marketplace is named.

## Contents

- Case 1: Self-labelled stopgap for a shipped skill's wrong example
- Case 2: Wrapper command's "delta" is actually a base-skill correction
- Case 3: Mixed wrapper: one section stays, one is extracted as E, one is F-stale

---

## Case 1 — Self-labelled stopgap for a shipped skill's wrong example

### The source

A section of `<claude-root>/CLAUDE.md`, the global CLAUDE.md, contains:

```markdown
## Stopgap until dev-essentials:example-external-client is updated

The skill's worked example configures `HttpClient` with a `using` block around the injected
client instance. Don't do that — the client is injected via `IHttpClientFactory` and is
intentionally long-lived; wrapping it in `using` disposes the shared handler and breaks
connection pooling for every other caller sharing that named client. Until the skill's example
is fixed, remember to drop the `using` when copying its pattern.
```

### Phase 3 classification

- **Corroboration**: a single source (this one section of the global CLAUDE.md). That alone does not usually clear the bar for C/D. But here the disposition does not depend on corroboration at all.
- **Marker phrase**: "Stopgap until `dev-essentials:example-external-client` is updated" is the near-certain E marker that Step 4 of `references/classification-framework.md` names.
- **Test of the self-label before the run accepts it**: read the current worked example of the shipped skill. It still shows the `HttpClient` inside a `using` block. The described defect is still there, so the disposition stays **E-fix-shipped**. It is not F-stale. F-stale applies only to a defect that an unrelated change already fixed in the shipped skill.
- **Why not C (promote as new)**: the content is not a new, independent rule. It corrects something that the shipped skill already teaches wrong. A new entity leaves the wrong example in the shipped skill, and that example still teaches the bug to every future reader of the skill.

### Phase 6 outcome

An edit to the `SKILL.md` of `dev-essentials:example-external-client`. The edit removes the `using` block around the injected `HttpClient` from the worked example. It adds one sentence: clients that `IHttpClientFactory` injects are long-lived, and the caller must not dispose them. The run creates no new entity.

Phase 9b reports that the section can become a pointer, because the correction of the shipped skill now holds all of its content. With `--update-global-claude-md`, Phase 9b asks, and then it puts a pointer bullet in place of the section. The bullet has the form of 9c.5 in `../../promote-conventions/references/cleanup-and-provenance.md`, with its one-line gist:

```markdown
## Cross-project rules — migrated to marketplace skills

- **Injected HttpClient** (never dispose a client that IHttpClientFactory injects) -> `dev-essentials:example-external-client`
```

---

## Case 2 — Wrapper command's "delta" is actually a base-skill correction

### The source

A personal global command, `<claude-root>/commands/create-controller-with-audit.md`:

```markdown
---
description: Create a WebAPI controller with an audit-log call, on top of the standard pattern
---

First run `dotnet-backend-dev:example-controller-pattern` for the base controller shape. Then, in
addition to what that skill produces, add a call to `IAuditLogger.LogAsync` at the top of the
action method, passing the request's `CorrelationId` field.
```

Read alone, this looks like a real personal addition: an extra step on top of a base skill that works. **The wrapper-entity landmine (`references/source-inventory.md`, landmine 12) requires a diff against the base skill**. A read of the wrapper alone is not enough.

### The diff against the base skill

The run reads the current `SKILL.md` of `dotnet-backend-dev:example-controller-pattern` in full, not only the summary that the wrapper gives. The worked example of the base skill already calls `IAuditLogger.LogAsync`. But it passes a field named `RequestId`, not `CorrelationId`. A grep of the domain model of that example shows that the model has no `RequestId` field at all. The real field is `CorrelationId`. So the "addition" of the wrapper is not new function on top of a working base. The wrapper works around a wrong field name in the example of the base skill in silence. It uses the correct field name and never reports the error of the base skill.

### Phase 3 classification

- **Found by the diff**: this is the exact scenario that landmine 12 exists to catch. A read of the wrapper alone leads to disposition C (promote the audit-log call as a new rule). The correct field name then ships again as an independent addition. The example of the base skill stays broken for everyone who reads only the base skill.
- **Marker**: this time, no explicit "stopgap" self-label exists. Cases 1 and 2 are the two different ways to find E, as calibration case 5 of `references/classification-framework.md` says. Here the marker is structural. The diff shows that the stated delta of the wrapper is a corrected version of the example of the base skill. That example already tries the same call and gets it wrong.
- **Disposition**: **E-fix-shipped.** The correction (`CorrelationId`, not `RequestId`) belongs in the example of `dotnet-backend-dev:example-controller-pattern`, not in a derived wrapper entity.

### Phase 6 outcome

An edit to the `SKILL.md` of `dotnet-backend-dev:example-controller-pattern`. The `IAuditLogger.LogAsync` call of the worked example now passes `CorrelationId` instead of `RequestId`. The run creates no new entity for the audit-log content of the wrapper, because the base skill covers it correctly after the fix.

Phase 9d (personal-entities cleanup) lists the personal wrapper command `create-controller-with-audit.md` as superseded by `dotnet-backend-dev:example-controller-pattern`. The suggested manual action is deletion. The only reason for the wrapper was to work around a defect, and the corrected base skill no longer has it. This run did not pass `--delete-personal-entities`, so the report-only default applies. The file stays in place until the user takes the manual action.

---

## Case 3 — Mixed wrapper: one section stays, one is extracted as E, one is F-stale

Unlike Cases 1 and 2, this wrapper does not resolve to one disposition. After the diff against the base skill that it wraps, each of its three sections gets a different outcome. This is the worked instance of the orthogonality rule of Step 4 in `references/classification-framework.md`. "The wrapper is intentional" is never a reason to skip the diff, because the diff decides per DIVERGENCE, not per file.

### The source

A personal global command, `<claude-root>/commands/deploy-service-custom.md`:

```markdown
---
description: Wraps dotnet-backend-dev:example-deploy-service with our team's release habits
---

Run `dotnet-backend-dev:example-deploy-service $ARGUMENTS` for the standard deploy. In addition:

- Skip the smoke-test step by default for this team — pass `--skip-smoke-test`; our staging
  environment doesn't have a reachable health endpoint, so the smoke test always times out anyway.
- Tag the release commit `rel-<version>` before deploying, not `v<version>` — our internal tooling
  greps for the `rel-` prefix specifically.
- Remember to bump `CHANGELOG.md` manually before tagging — the deploy skill doesn't do this for you.
```

### The diff against the base skill

The file name matches landmine 12 signal (ii): `-custom.md`, and it holds the name of the wrapped entity. The body has a `$ARGUMENTS` forwarding line (signal (i)). Both signals trigger the mandatory diff. The run reads the current `SKILL.md` of `dotnet-backend-dev:example-deploy-service` in full:

1. **Smoke-test opt-out**. The base skill has no opinion on the smoke-test cadence. This is only a limit of the staging environment of this team, from nothing but their own experience. No external authority anchors it.
2. **Tag prefix**. The worked example of the base skill tags releases `v<version>`. It calls this "the convention every consuming pipeline expects". A grep of their trigger configuration shows that the real consuming pipelines match on `rel-`, not on `v`. `rel-` is the tag pattern of the wrapper. The example of the base skill is wrong, and it was wrong from the start.
3. **Changelog bump**. The current `SKILL.md` of the base skill (its latest on-disk version) already has a "Step 4: Update `CHANGELOG.md`" section. That section came after the last change to this wrapper. The reminder of the wrapper is no longer accurate, because the base skill now does this step itself.

### Phase 3 classification (per section, not per file)

- **Smoke-test opt-out → B-taste.** No external anchor. It is a preference from a limit of the own environment of this team. The wrapper keeps it. No promotion and no fix anywhere.
- **Tag prefix → E-fix-shipped.** The example of the base skill contradicts what its real consumers require. The correction belongs in the base skill, not in a personal workaround. This follows the wrapper-entity path of Step 4 in `classification-framework.md`: a divergence that corrects the base entity.
- **Changelog bump → F-stale for that section.** The current content of the base entity already holds this divergence upstream. The base skill added the changelog step after someone wrote this line of the wrapper. Step 4 in `classification-framework.md` tests a self-label against the current content of the shipped entity. Here that rule applies to one wrapper section.

### Phase 6 / Phase 9 outcome

- An edit to the `SKILL.md` of `dotnet-backend-dev:example-deploy-service`. The release tag of the worked example changes from `v<version>` to `rel-<version>`, as the consuming pipelines require.
- The smoke-test opt-out bullet stays in `deploy-service-custom.md`, untouched. It is the own taste of this team, with no promotion or fix of any kind.
- Both other bullets are the partially superseded wrapper case of Phase 9d (`references/cleanup-and-provenance.md` of `promote-conventions`). The wrapper as a whole is not eligible for deletion, because its smoke-test section is still needed. But Phase 9d reports each superseded bullet on its own, with the shipped entity and the version that now covers it:
  - The **changelog-bump bullet** (F-stale, superseded by an unrelated earlier change to the base skill) can be trimmed now. This is the already-shipped, F-stale recovery route, which needs no PR merge first.
  - The **tag-prefix bullet** (E-fixed in this run) can be trimmed only after the promotion of this run is published. This is the recovery route for a promotion or E-fix of this run. It opens after the marketplace PR with the `dotnet-backend-dev:example-deploy-service` correction merges.

  Apart from that, the wrapper file stays exactly as it is. This run did not pass `--delete-personal-entities`, so both trims stay report-only until the user acts on the manual TODO.
