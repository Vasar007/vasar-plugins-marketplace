# Script results

Step 7 and the light path use this file to write the flags of `scripts/trim_report.py` and to read its result. Run the script with `--help` for all flags.

- Examples of a usage error (exit code 2) are a bad flag, an unreadable path, an absolute `--glob` and a backup inside the workspace.
- A regex that matches nothing in the backup is a failure.
- The script converts CRLF to LF in both trees before it matches or compares.
- A glob is one relative pattern from the root of the tree. `*.md` matches only top-level files. `notes/*.md` matches only files in `notes/`. `**/*.md` matches files at any depth.
- A protected block is exactly the text that its regex matches. Text that you add after the match, such as an `Update:` line below the decision line, is not tested.
- For each approved tombstone, add `--allow-changed REGEX`. The script tests REGEX against the string `PATH:FIRST_LINE`. PATH is the relative path with forward slashes. FIRST_LINE is the first line of the protected block.
- To allow a block in one file, write the file in the regex, for example `'^notes/decisions\.md:## DEC-3\b'`. To allow it in any file, write `':## DEC-3\b'`.
- The script reports a matching block as ALLOWED. After the trim, the same file must still hold a line that matches REGEX. If not, the script reports WITHDRAWN, NO TOMBSTONE and fails. Do not end REGEX with `$`, so that it matches both the old heading and the tombstone heading.
- The script reports a block that it finds intact in another file as IN OTHER FILE. This does not fail. The reviewer finds out whether the plan names the move or the deduplication. If it does not, the reviewer reports it.
- If no file with the name of a deleted file survives, a reference to it is DANGLING. If another file has that name, the line is AMBIGUOUS. This passes, but you must look at each AMBIGUOUS line by hand. The name match ignores case.
