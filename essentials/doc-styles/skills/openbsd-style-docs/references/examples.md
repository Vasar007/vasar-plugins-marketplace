# Examples

## Rewrites

Each pair shows a typical sentence and its rewrite in the manual style.

Opening of a README.

> Before: 🚀 **logrot** is a blazing-fast, modern and easy-to-use tool that
> helps you effortlessly manage your log files!
>
> After: The `logrot` utility rotates and compresses log files.

Option description.

> Before: `-k, --keep N`: You can use this option if you want to change how
> many old log files will be kept around (it's 7 by default, but you might
> want more).
>
> After:
>
> - `-k` *count*\
>   Keep *count* rotated files and delete older ones.
>   The default is 7.

Default and conflict.

> Before: Note: `--dry-run` doesn't actually do anything, so it won't work
> with `--force` (which forces rotation even if the file is small).
>
> After:
>
> - `-f`\
>   Rotate the file even if it is smaller than the size limit.
> - `-n`\
>   Print the actions, but do not perform them.
>   Cannot be used together with `-f`.

Limit.

> Before: Very large files may take a while and could potentially cause
> problems.
>
> After: Files larger than 4 gigabytes are not compressed.
> They are rotated and left uncompressed.

Error behavior.

> Before: If something goes wrong, logrot will let you know and exit.
>
> After: The `logrot` utility exits 0 on success, and >0 if an error occurs.
> In particular, 2 means that no file needed rotation.

Security warning.

> Before: ⚠️ **IMPORTANT!!!** Be very careful with permissions!
>
> After: The state file must be owned by root and must not be writable by
> other users. A user who can write the state file can make `logrot` delete
> any file on the system.

Example.

> Before: ### Example 1
> Here's how you might rotate logs:
> `logrot /var/log/app`
>
> After: Rotate all logs in `/var/log/app` and keep 14 files:
>
> ```text
> # logrot -k 14 /var/log/app
> ```

Concept.

> Before: Our architecture is built around the powerful concept of workers,
> which seamlessly handle jobs.
>
> After: The daemon runs one *worker* process for each CPU.
> Each worker takes one job at a time from the queue.
> A worker that fails is restarted after 5 seconds.

## A complete README

The README below documents a small fictional tool. It shows all the rules
together.

````markdown
# logrot

logrot - rotate and compress log files

## SYNOPSIS

```
logrot [-fnv] [-c file] [-k count] [-s size] path ...
logrot -l [-c file]
```

## DESCRIPTION

The `logrot` utility rotates and compresses log files.

For each *path*, `logrot` renames the file to *path*`.0`, renames each older
file *path*`.N` to *path*`.N+1`, and compresses the renamed files with
`gzip(1)`.
If *path* is a directory, `logrot` rotates each regular file in it whose name
ends in `.log`.
Subdirectories are not processed.

By default, `logrot` rotates a file only if it is larger than 1 megabyte.
Only the superuser may rotate files that other users own.

The options are as follows:

- `-c` *file*\
  Read the configuration from *file*.
  The default is `/etc/logrot.conf`.
- `-f`\
  Rotate each file even if it is smaller than the size limit.
- `-k` *count*\
  Keep *count* rotated files and delete older ones.
  The value must be between 1 and 999.
  The default is 7.
- `-l`\
  List the files that the configuration selects, and exit.
- `-n`\
  Print the actions, but do not perform them.
  Cannot be used together with `-f`.
- `-s` *size*\
  Set the size limit.
  The *size* is a number of bytes, optionally followed by `K`, `M` or `G`.
  The default is `1M`.
- `-v`\
  Verbose mode.
  Print each file name as it is rotated.

## ENVIRONMENT

- `LOGROT_GZIP`\
  The compression program to use.
  If not set, `logrot` uses `gzip`.

## FILES

- `/etc/logrot.conf`\
  Default configuration file.
- `/var/db/logrot.state`\
  The time of the last rotation of each file.

## EXIT STATUS

The `logrot` utility exits 0 on success, and >0 if an error occurs.
In particular, 2 means that no file needed rotation.

## EXAMPLES

Rotate all logs in `/var/log/app` and keep 14 files:

```
# logrot -k 14 /var/log/app
```

Show what a rotation with a 10 megabyte limit would do:

```
$ logrot -n -s 10M /var/log/app/access.log
```

## SEE ALSO

`gzip(1)`, `logrot.conf(5)`, `newsyslog(8)`

## HISTORY

`logrot` first appeared in version 1.0.

## AUTHORS

`logrot` was written by Jane Doe <jane@example.org>.

## CAVEATS

`logrot` does not signal the program that writes the log.
That program keeps writing to the renamed file until it reopens its log.
Use the `signal` directive in `logrot.conf(5)` to send it `SIGHUP`.

## BUGS

Files larger than 4 gigabytes are rotated but not compressed.
````

Things to see in this README:

- The NAME line has 6 words, is lowercase, and has no period.
- The first sentence has the tool as its subject and a present-tense verb.
- The second paragraph defines the exact behavior, including the directory
  case and the subdirectory limit.
- The options are sorted, each starts with an imperative verb, and each
  default is its own sentence.
- The range of `-k` and the unit syntax of `-s` are exact.
- The examples have purpose sentences that end in colons, and the prompt
  shows the privilege (`#` or `$`).
- CAVEATS describes a trap and gives the remedy. BUGS states a defect.
- The README does not use "you", bold, an emoji or an exclamation mark, and
  has no feature list.
