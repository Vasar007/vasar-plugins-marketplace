# Starter CSS components

Copy-paste starting points for the recurring pieces described in
`SKILL.md`. Adapt colors/spacing to match a prior artifact in the same
series if one exists — these are a starting point for a brand-new series,
not a fixed design system.

## Color map (CSS variables)

```css
:root {
  --c-critical: #d92626;
  --c-major:    #e07b00;
  --c-minor:    #d1a500;
  --c-info:     #2b7fd1;
  --c-good:     #2e9e4f;
  --c-pending:  #8a8f98;
  --bg:         #ffffff;
  --bg-alt:     #f6f7f9;
  --border:     #e2e4e8;
  --text:       #1c1f26;
  --text-muted: #5c6270;
}
```

## Status/severity badge

```css
.badge { display:inline-flex; align-items:center; gap:.4em; padding:.15em .6em;
  border-radius:999px; font-size:.8em; font-weight:600; }
.badge::before { content:''; width:.6em; height:.6em; border-radius:50%; }
.badge.critical { color:var(--c-critical); }
.badge.critical::before { background:var(--c-critical); }
/* repeat for .major/.minor/.info/.good/.pending, swapping the variable */
```

## Stats grid

```css
.stats-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(140px,1fr));
  gap:1px; background:var(--border); border:1px solid var(--border); border-radius:8px; overflow:hidden; }
.stats-grid .cell { background:var(--bg); padding:1em; text-align:center; }
.stats-grid .cell .n { font-size:1.6em; font-weight:700; }
.stats-grid .cell .label { color:var(--text-muted); font-size:.8em; }
```

## Findings / AC grid table with deep-links

```css
table.findings { width:100%; border-collapse:collapse; }
table.findings th, table.findings td { padding:.5em .75em; border-bottom:1px solid var(--border); text-align:left; }
table.findings tr:hover { background:var(--bg-alt); }
table.findings a.jump { text-decoration:none; }
```

## Collapsible detail group

```html
<details class="group">
  <summary>Production changes (12 files, +340 / -58)</summary>
  <!-- file list / content -->
</details>
```

```css
details.group { border:1px solid var(--border); border-radius:8px; margin:.5em 0; }
details.group summary { padding:.6em .9em; cursor:pointer; font-weight:600; }
details.group[open] summary { border-bottom:1px solid var(--border); }
```

## Annotated line grid (diff / code + side chip)

```html
<div class="file" id="F-anchor-id">
  <div class="row">
    <div class="ln">42</div>
    <div class="code">    var result = DoThing();</div>
    <div class="ann">
      <span class="ann-card major"><span class="tag">major #3</span> uses inline string, not .SafeFormat</span>
    </div>
  </div>
</div>
```

```css
.file .row { display:grid; grid-template-columns:3em 1fr 22em; gap:.5em; font-family:monospace; font-size:.85em; }
.file .ln { color:var(--text-muted); text-align:right; user-select:none; }
.file .code { white-space:pre-wrap; }
.file .code.add { background:#eaffea; }
.file .code.del { background:#ffecec; }
.ann-card { display:block; border-left:3px solid var(--c-major); padding:.3em .6em; background:var(--bg-alt); border-radius:4px; }
.ann-card .tag { font-weight:700; margin-right:.4em; }
.ann-card.critical { border-color:var(--c-critical); }
.ann-card.minor    { border-color:var(--c-minor); }
.ann-card.info     { border-color:var(--c-info); }
.ann-card.good     { border-color:var(--c-good); }
.ann-card.pending  { border-color:var(--c-pending); }
```

`white-space: pre-wrap` on `.file .code` preserves the source's indentation — without it, default
HTML whitespace collapsing flattens leading spaces/tabs. Separately, always HTML-escape injected
code/diff text (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`) before inserting it into `.file .code` —
raw code/diff content routinely contains `<`, `>`, `&`, which would otherwise be parsed as markup
instead of rendered as text.

## Mockup / wireframe block

```html
<div class="mockup">
  <div class="mockup-box header">Header / nav</div>
  <div class="mockup-box sidebar">Sidebar</div>
  <div class="mockup-box main">Main content — <em>label the intent, not pixels</em></div>
</div>
```

```css
.mockup { display:grid; grid-template-columns:160px 1fr; grid-template-rows:auto 1fr; gap:.5em; border:1px dashed var(--border); padding:.5em; }
.mockup-box { border:1px solid var(--border); border-radius:4px; padding:.75em; color:var(--text-muted); background:var(--bg-alt); }
.mockup-box.header { grid-column:1 / -1; }
```
