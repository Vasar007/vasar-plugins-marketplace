# Mermaid gotchas

The facts below hold for mermaid 10.9.1 and its jison grammars. The STR rule of `flow.jison` is `[^"]+`. The TXT rule of `sequenceDiagram.jison` is `[^#\n;]+`.

- **Most "syntax errors" that mermaid reports in the browser are NOT a syntax bug**. One known cause comes from HTML artifacts in practice: `highlight.js@11/lib/core.min.js` on the same page. This file is CommonJS only, for Node and npm. It corrupts globals, and mermaid then reads `-->` as `STR` instead of `LINK`. This cause is a diagnosis from one past incident, and the jison grammar does not prove it. Treat it as a strong first guess, not as a certainty. Use the browser CDN build instead:
  - `@highlightjs/cdn-assets@11/highlight.min.js`
  - `@highlightjs/cdn-assets@11/languages/<lang>.min.js`

  `highlight.js@11/lib/*` is the npm and Node build. In a browser page, it throws `ReferenceError: module is not defined`. This error tells you that you loaded the wrong build.

- **Before you call a diagram broken, test it outside the page**:

  ```bash
  npx -p @mermaid-js/mermaid-cli@10.9.1 mmdc -i x.mmd -o x.svg
  ```

  This tool uses the same parser as the CDN build. If `mmdc` renders the diagram, the bug is in the page and not in the diagram text. The usual causes are the highlight.js conflict above and the content-level failures below.

- **Inside a quoted flowchart label `A["..."]`**: every character except `"` is fine. Em-dashes, parentheses, slashes, `=`, and commas are NOT the problem. The trailing `;` on `classDef` is optional, because the grammar accepts `NEWLINE | SEMI | EOF` as the separator.

- **Inside the message text of a sequence diagram** (after the `:`): every character except `#`, a newline, and `;` is fine. Em-dashes, parentheses, `=`, `/`, and `,` are NOT the bug, because the v10 grammar lexer allows them.

- **Init script**: put this script at the bottom of `<body>`:

  ```html
  <script>
    mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' /* ... */ });
    mermaid.run({ querySelector: '.mermaid' }).catch(console.error);
  </script>
  ```

  `startOnLoad: true` does nothing after `DOMContentLoaded` fired. The inline script of an artifact usually runs after that event. So always start the render explicitly with `mermaid.run(...)`.

## Content-level failure modes (the page looks fine, nothing renders)

The gotchas above are about the configuration: the wrong CDN bundle, the `startOnLoad` no-op, and the init order. A second class of failure is different. The configuration is correct (the right CDN, the right init, and the right script order), and the diagram still renders nothing. Two causes are known from practice. In both cases, a subagent looked only at the `<script>` tags and reported "looks correct".

- **Wrong or missing wrapper element**. `mermaid.run({ querySelector: '.mermaid' })` acts only on elements that match `.mermaid`. A Markdown-to-HTML transform often writes `<pre><code class="language-mermaid">…</code></pre>` instead of `<div class="mermaid">…</div>`. A generator that builds the artifact from Markdown content does the same. It can also leave the diagram source as plain `<p>` text. In each of these cases, `querySelector('.mermaid')` matches zero elements. Mermaid runs with no error and no message, and the page shows the raw diagram source or nothing.
- **Entity-encoded diagram source**. The `<div class="mermaid">` wrapper can be correct, with double-encoded text inside it: `<br/>` becomes `&amp;lt;br/&amp;gt;`, `"` becomes `&amp;quot;`, and `-->` becomes `--&amp;gt;`. Mermaid decodes one level of entities (it reads `innerHTML` and runs `entityDecode`), so a single `&gt;` is fine. A double-encoded `&amp;gt;` reaches the parser as `&gt;` and fails. A bare `&gt;` in an arrow fails at the first edge with `Expecting 'LINK', ... got 'STR'`. A DOM inspector shows the decoded text, so the source looks fine there, but the parse breaks. One encoded arrow can break a whole diagram. Then one root cause, repeated in each diagram, looks like several separate "syntax errors".

A fix pass that looks only at the `<script src>` tags and the `mermaid.initialize` call reports success for both failures above. Neither failure is in the configuration. The defect is in the diagram markup. Do not accept "looks correct" from a look at the configuration only. Ask for the verification artifacts below.

### Required verification artifacts

Before you finish an artifact with diagrams, produce item 1. If a diagram does not render, fix it and produce all three items. A claim that it is fixed is not enough.

1. **Grep counts for each file**. Run them on each HTML file with diagrams:
   - `<div class="mermaid">`: the count of open tags. Zero means that nothing renders, whatever the configuration.
   - `<pre><code class="language-mermaid">`: the count of wrong wrappers. Each hit is a diagram that mermaid.js never sees.
   - `&amp;lt;`, `&amp;gt;`, `&amp;quot;`, and other double-encoded fragments inside `.mermaid` blocks: the count of encoded source. Each hit is source that you must decode one level before it parses. Single-encoded entities such as `&lt;` are not a hit, because mermaid decodes them.
   - `core.min.js`: the count of the forbidden bundle. Each hit is the npm and Node build of highlight.js, which corrupts the mermaid tokenizer (see above). The count must be zero.
   - `mermaid@10.9.1` in the mermaid `<script src=...>` tag: the count of pinned versions. Where a mermaid CDN `<script>` tag exists, the count must be at least one. Zero means that the mermaid CDN reference has no pin, or a pin to another version than the `mmdc` build of item 2. The two parsers match only at the same version.
2. **At least one `mmdc` test**: copy one typical diagram into a `.mmd` file, and run `npx -p @mermaid-js/mermaid-cli@10.9.1 mmdc -i x.mmd -o x.svg`. It uses the same parser as the CDN build. If it succeeds, the diagram source is fine, and the defect is in the wiring of the page. If it reports a parse error, the defect is in the source, not in the page.
3. **An isolated test page `_test-mermaid.html`**, next to the production files. It holds one small `graph LR` diagram, with the same CDN `<script>` tags and the same init sequence as the production files. If this page renders and the production files do not, the defect is in the production content (the wrapper or the encoding). It is not in the browser, the CDN, or the network of the reader. If the user reports "still not rendering", give them this file as a control.

If the user says one of these phrases in a review or a fix pass, use this section: `I don't see the diagrams`, `mermaid not rendering`, `diagrams are blank`, `syntax error in text`, or `fix the HTML again`.
