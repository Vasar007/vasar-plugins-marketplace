# Protect-set glob and regexes

Step 1 of the full pass and the light path use this file. It tells how to build the glob, the id regexes, and the protected-block regexes of the protect-set.

## Glob

List the file types in the workspace, for example with `find WORKSPACE -type f | sed -E 's|.*/||; s/.*\.//' | sort | uniq -c`. The script checks `**/*.md` by default. If other types can cite a trimmed file, such as `.txt` or `.log`, use `--glob '**/*'` in one run. A separate run for each type cannot see a `.txt` file that cites a deleted `.md` file. Record the glob in the protect-set.

The glob `**/*` also walks hidden folders such as `.git`. In a git workspace, a deleted file then shows as DANGLING in `.git/index`. The size table also counts git objects. Instead, compare the subfolder that holds every file that can cite a trimmed file, for example `--before BACKUP/docs --after WORKSPACE/docs`. The glob and the PATH in each `--allow-changed` regex are then relative to that subfolder. The default glob `**/*.md` does not match the git index or objects, so only `**/*` has this problem.

## Id families

To find id families, list the prefixes of tokens that look like ids:

```bash
grep -rhoE '\b[A-Z][A-Z0-9]*-?[0-9]+\b' --include='*.md' WORKSPACE \
  | sed -E 's/[0-9]+$//' | sort | uniq -c | sort -rn
```

Drop noise such as version strings. Turn each real family into one regex, for example `\bREQ-\d+\b`.

## Protected blocks

Write one multiline regex for each protected block type. It must cover only the byte-identical text, such as the quote and the decision line, not the whole section. Then the pass can still cut the agent framing around a decision. Example for files with a quote line and a decision line:

```text
(?m)^## Decision \d+\n\nQuote: .*\nDecision: .*$
```
