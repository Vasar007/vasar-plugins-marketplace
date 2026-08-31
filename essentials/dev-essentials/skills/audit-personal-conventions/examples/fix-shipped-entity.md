# Fix Shipped Entity — The E-Disposition Path, End to End

Three sanitized cases, each modeled on a real finding from the research this skill was built on.
Cases 1 and 2 end the same way: an edit to an already-shipped entity, and the source pruned — never
a new entity. Case 3 shows the mixed outcome a single wrapper file can produce once its sections are
diffed individually. Repo names and rule content are fictional; no marketplace is named.

---

## Case 1 — Self-labelled stopgap for a shipped skill's wrong example

### The source

`<claude-root>/projects/<project>/memory/dotnet-http-clients.md`, `type: reference`, contains:

```markdown
## Stopgap until dev-essentials:example-external-client is updated

The skill's worked example configures `HttpClient` with a `using` block around the injected
client instance. Don't do that — the client is injected via `IHttpClientFactory` and is
intentionally long-lived; wrapping it in `using` disposes the shared handler and breaks
connection pooling for every other caller sharing that named client. Until the skill's example
is fixed, remember to drop the `using` when copying its pattern.
```

### Phase 3 classification

- **Corroboration:** single source (this one memory file), which alone would not usually clear the
  bar for C/D — but disposition here does not hinge on corroboration at all.
- **Marker phrase:** "Stopgap until `dev-essentials:example-external-client` is updated" is the
  near-certain E marker named in `references/classification-framework.md` Step 4.
- **Verification before accepting the self-label:** read the shipped skill's current worked example.
  It still shows the `using`-wrapped `HttpClient` — the defect described is still present, so the
  disposition is confirmed as **E-fix-shipped**, not F-stale (which would apply if the shipped skill
  had already been corrected by an unrelated change).
- **Why not C/promote-new:** the content is not a new, independent rule to promote — it is a
  correction to something the shipped skill already teaches incorrectly. Promoting it as a new
  entity would leave the shipped skill's wrong example in place, still teaching the bug to every
  future reader of that skill.

### Phase 6 outcome

Edit to `dev-essentials:example-external-client`'s `SKILL.md`: the worked example's `using`
block around the injected `HttpClient` is removed, and one sentence is added noting that
`IHttpClientFactory`-injected clients are long-lived and must not be disposed by the caller. No new
entity is created.

Phase 9a prunes `<claude-root>/projects/<project>/memory/dotnet-http-clients.md` (fully-promoted —
its entire content is now folded into the shipped skill's correction):

```markdown
---
type: reference
---

Migrated to `dev-essentials:example-external-client` on 2026-08-20 (v2.1.0). See the
marketplace entity for current content; this file is intentionally left as a pointer only.
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

Read in isolation, this looks like a genuine personal addition — an extra step layered on top of a
correctly-working base skill. **The wrapper-entity landmine (`references/source-inventory.md`,
landmine 12) requires diffing against the base skill instead of reading the wrapper alone.**

### The diff against the base skill

Reading `dotnet-backend-dev:example-controller-pattern`'s own current `SKILL.md` in full (not just the
wrapper's summary of it) shows the base skill's own worked example already calls
`IAuditLogger.LogAsync` — but passes a field named `RequestId`, not `CorrelationId`. Grepping the
domain model referenced by that example confirms the model has no `RequestId` field at all; the
actual field is `CorrelationId`. The wrapper's "addition" is not new functionality layered on top of
a working base — it is silently working around a wrong field name in the base skill's own example,
by simply using the correct field name in the wrapper instead of ever reporting the base skill's
error.

### Phase 3 classification

- **Found via the diff** — exactly the scenario landmine 12 exists to catch. Reading the wrapper in
  isolation would have led to disposition C (promote the audit-log-call addition as a new rule),
  re-shipping the *correct* field name as if it were an independent enhancement while leaving the
  base skill's own example broken for everyone who reads only the base skill.
- **Marker:** no explicit "stopgap" self-label this time (Case 1 and Case 2 are the two different
  ways E gets found, per `references/classification-framework.md` calibration case 5) — the marker
  here is structural: the wrapper's stated delta, once diffed, turns out to be a corrected version
  of something the base skill's own example already attempts and gets wrong.
- **Disposition:** **E-fix-shipped.** The correction (`CorrelationId`, not `RequestId`) belongs in
  `dotnet-backend-dev:example-controller-pattern`'s own example, not in a derived wrapper entity.

### Phase 6 outcome

Edit to `dotnet-backend-dev:example-controller-pattern`'s `SKILL.md`: the worked example's
`IAuditLogger.LogAsync` call is corrected to pass `CorrelationId` instead of `RequestId`. No new
entity is created for the wrapper's audit-log-call content, since the base skill already covers it
correctly once fixed.

Phase 9d (personal-entities cleanup) lists the personal wrapper command
`create-controller-with-audit.md` as superseded by `dotnet-backend-dev:example-controller-pattern`, with
a suggested manual action of deletion — the wrapper's entire reason to exist was working around a
defect that no longer exists once the base skill is corrected. `--delete-personal-entities` was not
passed this run, so this is the report-only default: the file itself is left in place, pending that
manual action.

---

## Case 3 — Mixed wrapper: one section stays, one is extracted as E, one is F-stale

Unlike Cases 1 and 2, this wrapper does not resolve to a single disposition. Once diffed against the
base skill it wraps, its three sections each land on a different outcome — the worked instance of
`references/classification-framework.md` Step 4's orthogonality rule: "the wrapper is intentional" is
never a reason to skip diffing it, because the diff decides per DIVERGENCE, not per file.

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

Filename matches landmine 12 signal (ii) (`-custom.md`, contains the wrapped entity's name) and the
body contains a `$ARGUMENTS` forwarding line (signal (i)) — both trigger the mandatory diff. Reading
`dotnet-backend-dev:example-deploy-service`'s current `SKILL.md` in full:

1. **Smoke-test opt-out** — the base skill has no opinion on smoke-test cadence; this is purely this
   team's own staging-environment limitation, sourced from nothing but their own experience. No
   external authority anchors it.
2. **Tag prefix** — the base skill's own worked example tags releases `v<version>`, and states this
   is "the convention every consuming pipeline expects." Grepping the actual consuming pipelines'
   trigger configuration shows they match on `rel-` (the tag pattern the wrapper uses), not `v` — the
   base skill's own example is wrong, and has been since it was written.
3. **Changelog bump** — the base skill's current `SKILL.md` (checked at its latest on-disk version)
   already has a "Step 4: Update `CHANGELOG.md`" section, added since this wrapper was last touched.
   The wrapper's reminder is no longer accurate — the base skill does this automatically now.

### Phase 3 classification (per section, not per file)

- **Smoke-test opt-out → B-taste.** No external anchor — a preference sourced from this team's own
  environment limitation. The wrapper keeps it; not promoted, not fixed anywhere.
- **Tag prefix → E-fix-shipped.** The base skill's own example contradicts what its actual consumers
  require — a correction that belongs in the base skill, not a personal workaround. Per
  `classification-framework.md` Step 4's wrapper-entity path (a divergence that corrects the base
  entity).
- **Changelog bump → F-stale for that section.** The divergence is already upstream in the base
  entity's current content — the base skill added the changelog step after this wrapper line was
  written. Per `classification-framework.md` Step 4's own "verify the self-label against actual
  current content" rule, applied to a wrapper section.

### Phase 6 / Phase 9 outcome

- Edit to `dotnet-backend-dev:example-deploy-service`'s `SKILL.md`: the worked example's release tag is corrected from
  `v<version>` to `rel-<version>`, matching what its consuming pipelines actually require.
- The smoke-test opt-out bullet stays in `deploy-service-custom.md` untouched — it is this team's own
  taste, with no promotion or fix action of any kind.
- Both remaining bullets are the **partially-superseded wrapper case** from Phase 9d: the wrapper as
  a whole is not eligible for deletion (its smoke-test section is still needed), but Phase 9d reports
  each superseded bullet individually, naming the shipped entity+version that now covers it:
  - The **changelog-bump bullet** (F-stale, superseded by an unrelated earlier change to the base
    skill) is trimmable now — this is the already-shipped/F-stale recovery route, which needs no PR
    merge to become actionable.
  - The **tag-prefix bullet** (E-fixed this run) becomes trimmable only once this run's own promotion
    is published — this is the promoted/E-fixed-this-run recovery route, which is reachable once the
    marketplace PR containing the `dotnet-backend-dev:example-deploy-service` correction merges.
  The wrapper file itself is otherwise left exactly as-is; `--delete-personal-entities` was not
  passed this run, so both trims stay report-only pending the user acting on the manual TODO.
