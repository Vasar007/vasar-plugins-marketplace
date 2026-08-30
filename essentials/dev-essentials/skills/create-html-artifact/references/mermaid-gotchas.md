# Mermaid gotchas

Verified against mermaid 10.9.1 + the jison grammars (`flow.jison` STR rule
`[^"]+`; `sequenceDiagram.jison` TXT rule `[^#\n;]+`).

- **Most "syntax errors" reported by mermaid in the browser are NOT a
  syntax bug.** One known cause, observed in practice in HTML artifacts:
  loading `highlight.js@11/lib/core.min.js` (a CommonJS-only file, meant
  for Node/npm) on the same page corrupts globals and makes mermaid
  mis-tokenize `-->` as `STR` instead of `LINK`. This causal chain is a
  diagnosis from a past incident, not something re-derived from the
  jison grammar itself — treat it as a strong first guess, not a
  certainty. Use the browser CDN build instead:
  - `@highlightjs/cdn-assets@11/highlight.min.js`
  - `@highlightjs/cdn-assets@11/languages/<lang>.min.js`

  `highlight.js@11/lib/*` is the npm/Node distribution and will throw
  `ReferenceError: module is not defined` in a browser page — that's the
  tell you grabbed the wrong build.

- **Before declaring a diagram broken, verify it outside the page**:

  ```bash
  npx -p @mermaid-js/mermaid-cli@10.9.1 mmdc -i x.mmd -o x.svg
  ```

  Same parser as the CDN build. If `mmdc` renders it fine, the bug is in
  the page (usually the highlight.js conflict above, or one of the
  content-level failure modes below), not the diagram text.

- **Inside `A["..."]` quoted flowchart labels**: anything except `"` is
  fine — em-dashes, parentheses, slashes, `=`, commas are NOT the problem.
  The trailing `;` on `classDef` is optional (grammar accepts
  `NEWLINE | SEMI | EOF` as the separator).

- **Inside sequence-diagram message text** (after the `:`): anything
  except `#`, newline, `;` is fine. Em-dashes, parens, `=`, `/`, `,` are
  NOT the bug — the v10 grammar lexer allows them.

- **Init script** — put this at the bottom of `<body>`, not before mermaid
  renders on load:

  ```html
  <script>
    mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' /* ... */ });
    mermaid.run({ querySelector: '.mermaid' }).catch(console.error);
  </script>
  ```

  `startOnLoad: true` is a no-op once `DOMContentLoaded` has already
  fired, which it usually has by the time an inline artifact's script runs
  — always drive rendering explicitly with `mermaid.run(...)`.

## Content-level failure modes (the page looks fine, nothing renders)

The gotchas above are *config-level* (wrong CDN bundle, `startOnLoad`
no-op, init order). They do NOT cover a second, distinct class of failure
where the config is perfect — right CDN, right init, right script order —
and the diagram still renders nothing. Two confirmed causes, both observed
hiding behind a subagent's "looks correct" inspection of the `<script>`
tags alone:

- **Wrong or missing wrapper element.** `mermaid.run({ querySelector:
  '.mermaid' })` only touches elements matching `.mermaid`. A
  markdown→HTML transform (or an inline-template generator building the
  artifact from Markdown content) commonly emits
  `<pre><code class="language-mermaid">…</code></pre>` instead of
  `<div class="mermaid">…</div>` — or leaves the diagram source as plain
  `<p>` text. In every one of these cases `querySelector('.mermaid')`
  matches zero elements, mermaid runs successfully and silently, and the
  page shows the raw diagram source (or nothing) instead of a diagram.
  Observed in one review: CDN URLs and `mermaid.initialize` were both
  correct, yet the artifact contained four diagram captions as text and
  zero `<div class="mermaid">` elements — two consecutive review passes
  reported "FIXED" without ever grepping for the wrapper tag.
- **Entity-encoded diagram source.** Even with the right `<div
  class="mermaid">` wrapper, if its text content has been HTML-entity-encoded
  — `<br/>` → `&lt;br/&gt;`, `"` → `&quot;`, `-->` → `--&gt;` — mermaid's
  parser reads the encoded form literally and fails to parse it (or, for
  a bare `&gt;` inside an arrow, chokes on the very first edge with
  `Expecting 'LINK', ... got 'STR'`). This looks fine in a DOM inspector
  (the browser shows the decoded text) but breaks the actual parse, and a
  full diagram failure from one encoded arrow can be mistaken for several
  independent "syntax errors" when in fact it's one root cause repeated
  per diagram.

**Why this matters for verification:** a fix pass that only checks the
`<script src>` tags and `mermaid.initialize` call will report success on
both failure modes above, because neither touches config — the defect is
in the diagram markup itself. Don't accept "looks correct" from a
config-only inspection; require the verification artifacts below.

### Required verification artifacts

When fixing (or verifying) mermaid rendering in an HTML artifact, produce
all of these — not just a claim that it's fixed:

1. **Per-file grep counts**, run against every HTML file containing
   diagrams:
   - `<div class="mermaid">` — open-tag count; zero here means nothing
     will ever render regardless of config.
   - `<pre><code class="language-mermaid">` — wrong-wrapper count; any
     hit here is a diagram mermaid.js will never see.
   - `&lt;br/&gt;` / `&quot;` / `--&gt;` (and other entity-encoded
     fragments) inside `.mermaid` blocks — entity-encoded-source count;
     any hit here means the source needs decoding before it will parse.
   - `core.min.js` — forbidden-bundle count; any hit is the npm/Node
     highlight.js build that corrupts mermaid's tokenizer (see above);
     must be zero.
   - `mermaid@10.9.1` in the mermaid `<script src=...>` tag — pinned-version
     count; must be at least one wherever a mermaid CDN `<script>` tag is
     present. Zero here means the mermaid CDN reference is unpinned or
     pinned to a different version than the `mmdc` build used below to
     verify diagrams offline — the two parsers are only guaranteed to
     match at the same version.
2. **At least one `mmdc` validation** — extract one representative
   diagram to a `.mmd` file and run
   `npx -p @mermaid-js/mermaid-cli@10.9.1 mmdc -i x.mmd -o x.svg`. Same
   parser as the CDN build: green means the diagram source itself is
   fine and the defect is in the page wiring; a parse error here means
   the source is the defect, not the page.
3. **An isolated `_test-mermaid.html` test page**, written next to the
   production file(s), containing a single small `graph LR` diagram plus
   the exact same CDN `<script>` tags and init sequence used in
   production. If this minimal page renders and the production file(s)
   don't, the defect is specific to the production content (wrapper or
   encoding), not the reader's browser/CDN/network setup — hand this file
   to the user as a control if they report "still not rendering."

Trigger phrases that should pull this section in during a review or fix
pass: "I don't see the diagrams", "mermaid not rendering", "diagrams are
blank", "syntax error in text", "fix the HTML again".
