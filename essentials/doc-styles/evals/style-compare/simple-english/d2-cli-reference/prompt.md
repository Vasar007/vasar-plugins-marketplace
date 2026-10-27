---
description: The model writes the command-line reference of snapsync from a fact sheet.
name: se-d2-cli-reference
tags: [style-compare, style-compare-se]
plugins: ["../../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: before you write English text, load the simple-english:simple-english skill with the Skill tool, and follow it. The rule covers files and your reply.'
---

Write `docs/cli.md`, the command-line reference of snapsync.

Facts about the tool:

- `snapsync` copies a snapshot of a local directory to a remote host over SSH. It keeps a fixed number of snapshots there.
- Usage: `snapsync [-nqv] [-c file] [-k count] [-p port] source host:path` and `snapsync -l [-c file] host:path`.
- `-c file`: read the configuration from `file`. The default is `/etc/snapsync.conf`.
- `-k count`: keep `count` snapshots on the remote, and delete the older ones. The range is 1 to 365. The default is 30. The deletion starts after the new snapshot is complete, oldest first.
- `-l`: list the snapshots on the remote, and exit.
- `-n`: print the transfers, and change nothing. Not together with `-q`.
- `-p port`: the SSH port. The default is 22.
- `-q`: print errors only.
- `-v`: print each file name. A second `-v` also prints the size of each transfer.
- `SNAPSYNC_SSH`: the SSH program. The default is `ssh`.
- Files: `/etc/snapsync.conf`, and `/var/db/snapsync/state` with the time of the last snapshot of each source.
- Exit status: 0 on success and 1 on an error. If the remote disk is full, the exit status is 3, and `snapsync` deletes no snapshot.
- Files larger than 2 GiB go whole, with no delta transfer.
- Only root can sync a source that other users own.

Use only these facts.
