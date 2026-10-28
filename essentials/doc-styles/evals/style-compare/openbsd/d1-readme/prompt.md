---
description: The model writes the README of snapsync from a fact sheet.
name: obsd-d1-readme
tags: [style-compare, style-compare-openbsd]
plugins: ["../../../.."]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: if a writing-style skill is installed for this kind of text, load it with the Skill tool before you write English text, and follow it. The rule covers files and your reply, not only documentation.'
---

In the OpenBSD man-page style, write `README.md` for the project snapsync.

Build facts: `make` needs a C99 compiler and libssh 0.10 or later. `make install` puts the binary in `/usr/local/bin`. Bugs go to <https://example.org/snapsync/issues>.

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
