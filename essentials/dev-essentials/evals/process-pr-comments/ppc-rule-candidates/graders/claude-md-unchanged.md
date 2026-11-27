---
type: regex
pattern: '^# pager\r?\n\r?\nSmall Python package\. The code is in `src/`, and the tests are in `tests/`\.\r?\n\r?\n- Test command: `python3 -m unittest discover -s tests`\r?\n- The repo has no build step\. Do not look for one\.\r?\n(?![\s\S])'
target: { source: file, path: CLAUDE.md }
---
