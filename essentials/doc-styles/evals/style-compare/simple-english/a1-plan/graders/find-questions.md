---
type: llm
focus: { source: file, path: plan.md }
arm: both
---

For each question, find the answer in the text under test. The facts below are the key.

1. Which file parses the flags, and which function does it use?
2. Which setting wins, the flag or the directive?
3. What happens with a value above 1000000?

Facts:

- `src/main.c` parses the flags with `getopt`.
- `src/conf.c` reads the configuration.
- `src/xfer.c` already reads `conf->bandwidth`.
- `make test` runs the tests in `tests/`.
- The new flag `-b rate` limits the bandwidth like the `bandwidth` directive. The flag overrides the directive.
- 0 means no limit.
- A value above 1000000 is an error, with exit status 1.

If an answer is wrong or missing, the result is FAIL. If an answer is only in a part that does not name its subject, the result is FAIL. Otherwise the result is PASS.
