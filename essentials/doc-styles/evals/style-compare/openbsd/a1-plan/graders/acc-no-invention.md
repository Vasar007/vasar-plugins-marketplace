---
type: llm
focus: { source: file, path: plan.md }
arm: both
---

The text under test is about the tool snapsync. These are the facts that it can use:

- `src/main.c` parses the flags with `getopt`.
- `src/conf.c` reads the configuration.
- `src/xfer.c` already reads `conf->bandwidth`.
- `make test` runs the tests in `tests/`.
- The new flag `-b rate` limits the bandwidth like the `bandwidth` directive. The flag overrides the directive.
- 0 means no limit.
- A value above 1000000 is an error, with exit status 1.

Compare the text with the facts. If a value, default, limit, exit status, or date does not match, the result is FAIL. If the text states a fact that is not in the list, the result is FAIL. A retry count and a timeout are two examples. A one-sentence definition of a term is not a new fact. An obvious inference from the listed facts is not a new fact either. Otherwise the result is PASS.
