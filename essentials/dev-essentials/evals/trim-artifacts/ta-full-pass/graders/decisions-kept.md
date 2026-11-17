---
type: regex
pattern: '^(?=[\s\S]*## DEC-1\r?\n\r?\nQuote: "Exports must work with no network\."\r?\nDecision: The export runs on the local host and writes CSV files only\.\r?\n)(?=[\s\S]*## DEC-2\r?\n\r?\nQuote: "Keep a cache of the last export\."\r?\nDecision: The tool keeps one file cache of the last export in the folder cache/\.\r?\n)(?=[\s\S]*## DEC-3\r?\n\r?\nQuote: "Do not delete old exports by hand\."\r?\nDecision: A nightly job deletes the exports that are older than 30 days\.(?:\r?\n|$))'
target: { source: file, path: notes/decisions.md }
---
