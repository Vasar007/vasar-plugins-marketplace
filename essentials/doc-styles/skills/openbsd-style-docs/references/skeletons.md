# Skeletons by document type

Each skeleton gives the sections in canonical order. Delete a section that has
no content. The placeholders are in angle brackets. The "Imitate" line names
real pages that show the type well. Each entry is the path in the OpenBSD
source tree. The page name is the file name: `bin/ls/ls.1` is `ls(1)`, at
`https://man.openbsd.org/ls.1`. The mdoc source is at
`https://raw.githubusercontent.com/openbsd/src/master/bin/ls/ls.1`.

## Command-line utility

Imitate: `bin/ls/ls.1`, `bin/cp/cp.1`, `usr.bin/doas/doas.1`,
`usr.bin/signify/signify.1`, `usr.sbin/rcctl/rcctl.8`,
`usr.sbin/syspatch/syspatch.8`.

````markdown
# <name>

<name> - <verb phrase, lowercase, no period>

## SYNOPSIS

```
<name> [-<flags without arguments>] [-x <arg>] <operand> ...
<name> -<mode flag> [-y <arg>]
```

## DESCRIPTION

The `<name>` utility <verb in present tense> <object>.

By default, `<name>` <default behavior>.
Only the superuser may <privileged action>.

The options are as follows:

- `-a`\
  <Imperative verb> <what it does>.
  This is the default.
- `-c` *file*\
  Read the configuration from *file*.
  The default is `/etc/<name>.conf`.
- `-n`\
  Do not <action>.
  This option implies `-v`.

## ENVIRONMENT

- `<VAR>`\
  If set, <effect>.
  Otherwise, `<name>` uses <fallback>.

## FILES

- `/etc/<name>.conf`\
  Default configuration file.
- `/var/db/<name>/`\
  Directory that holds the state.

## EXIT STATUS

The `<name>` utility exits 0 on success, and >0 if an error occurs.
In particular, <code> means <condition>.

## EXAMPLES

<Imperative purpose sentence>:

```
$ <name> -a foo
```

<Second purpose sentence, root needed>:

```
# <name> -c /etc/other.conf
```

## SEE ALSO

`<other>(1)`, `<name>.conf(5)`, `<daemon>(8)`

## HISTORY

`<name>` first appeared in <project> <version>.

## AUTHORS

`<name>` was written by <Name> <<mail@example.org>>.

## CAVEATS

<Trap in correct use, as a flat statement.>

## BUGS

<Known defect, stated frankly.>
````

For a tool with subcommands, use a tag list of subcommands instead of, or
after, the options list: "The following commands are available:", then
`` - `get` *service* [*variable*]\ ``.

If the tool has modes, use two lists (as `signify(1)` does): "The mode of
operation is selected with the following options:" and "The other options are
as follows:".

## Daemon or service

Imitate: `usr.sbin/httpd/httpd.8`, `usr.sbin/cron/cron.8`.

This is the utility skeleton with these changes:

- The NAME line is a noun phrase: `backupd - backup daemon`.
- The first sentence: "The `backupd` daemon <does what>."
- The DESCRIPTION also states the signals and the reload behavior:
  "`backupd` rereads its configuration file when it receives `SIGHUP`."
- The DESCRIPTION also states the privilege model: what runs as root, what
  runs chrooted, which user it switches to.
- FILES lists the configuration, the socket, the pid file and the logs.
- SEE ALSO always includes the configuration file page.

## Library or API

Imitate: `lib/libc/string/strlcpy.3`, `lib/libc/stdlib/strtonum.3`,
`lib/libc/stdlib/malloc.3`, `lib/libc/sys/open.2`, `lib/libtls/man/tls_init.3`.

The same structure fits an HTTP API: write the method and path as the
"prototype", and the status codes as ERRORS.

````markdown
# <func>

<func>, <func2> - <verb or noun phrase>

## SYNOPSIS

```c
#include <header.h>

int
<func>(const char *path, int flags);

void
<func2>(struct thing *t);
```

## DESCRIPTION

The `<func>()` function <verb> <object> *path* <how>.
The *flags* argument is the bitwise OR of zero or more of the following:

- `<FLAG_A>`\
  <Imperative fragment>.
- `<FLAG_B>`\
  <Imperative fragment>.

Exactly one of `<X>` and `<Y>` must be specified.

The `<func2>()` function is identical to `<func>()`, except that <difference>.
If *t* is `NULL`, no action occurs.

If the buffers overlap, the behavior is undefined.

## RETURN VALUES

If successful, `<func>()` returns <value>.
Otherwise, it returns -1 and sets `errno` to indicate the error.

The `<func2>()` function does not return a value.

## EXAMPLES

<Purpose sentence>:

```c
if ((fd = <func>(path, FLAG_A)) == -1)
	err(1, "%s", path);
```

<What the example guarantees, one sentence.>

## ERRORS

The `<func>()` function will fail if:

- `[ENOENT]`\
  The file *path* does not exist.
- `[EINVAL]`\
  The *flags* argument is not valid.
- `[EINVAL]`\
  <Second cause for the same code.>

## SEE ALSO

`<other>(2)`, `<other>(3)`

## STANDARDS

The `<func>()` function conforms to <standard>.
The `<FLAG_B>` flag is an extension to that specification.

## HISTORY

The `<func>()` function first appeared in <project> <version>.

## CAVEATS

<Correct-use trap, with the wrong code and the right code.>
````

Rules specific to an API:

- Name each argument in *italics* in prose, every time.
- State the NULL, zero-length and overflow cases.
- State who owns returned memory and when a returned pointer stops being
  valid.
- For async or kernel code, add a CONTEXT section after DESCRIPTION: "`<f>()`
  can be called from process context or from interrupt context."
- Write code examples in the code style of the project, with error checks on
  every call.

## Configuration file

Imitate: `usr.bin/doas/doas.conf.5`, `usr.sbin/httpd/httpd.conf.5`,
`share/man/man5/pf.conf.5`, `share/man/man5/fstab.5`.

````markdown
# <name>.conf

<name>.conf - <name> configuration file

## DESCRIPTION

`<name>.conf` is the configuration file for `<name>(8)`.

`<name>.conf` is divided into the following main sections:

- MACROS\
  Definitions of variables that can be used later.
- GLOBAL CONFIGURATION\
  Settings for the whole daemon.
- <SECTION>\
  <What it holds.>

The current line can be extended over several lines with a backslash (`\`).
Comments can be put anywhere in the file with a hash mark (`#`), and extend to
the end of the line.
Arguments that contain whitespace must be quoted.

Additional configuration files can be included with the `include` keyword,
for example:

```
include "/etc/<name>.d/local.conf"
```

## MACROS

A macro is defined with a line of the form `name=value`.
The name can contain letters, digits and underscores.

## GLOBAL CONFIGURATION

Here are the settings that can be set globally:

- `chroot` *directory*\
  Set the `chroot(2)` directory.
  If not specified, it defaults to `/var/<name>`.
- `prefork` *number*\
  Run the specified number of worker processes.
  The default is 3.
- `log` (`syslog` | `file` *path*)\
  Send log messages to `syslog(3)` or to *path*.
  The default is `syslog`.

## <SECTION>

<Rules for evaluation, as statements.>
The last matching rule determines the action.
If no rule matches, the action is denied.

## FILES

- `/etc/<name>.conf`\
  Default configuration file.
- `/etc/examples/<name>.conf`\
  Example configuration file.

## EXAMPLES

The following example <states the intent of each line in one sentence>:

```
<complete, valid configuration>
```

## SEE ALSO

`<name>(8)`, `<other>(5)`
````

Rules specific to a configuration file:

- For each directive, give the keyword in code, the placeholders in
  *italics*, and the alternatives with `|`.
- Put the default as the last sentence of each directive.
- State the order of evaluation exactly: "first match" or "last match".
- For a complex grammar, add a GRAMMAR section with BNF in a code block.
- The example is a complete file that the parser accepts, not a fragment.

## Concept or overview document

Imitate: `share/man/man7/hier.7`, `share/man/man7/environ.7`,
`share/man/man7/securelevel.7`, `share/man/man7/packages.7`,
`lib/libc/regex/re_format.7`.

Use this type for an architecture overview, a design note or a "how X works"
page.

````markdown
# <topic>

<topic> - <noun phrase: "overview of ...", "... and its effects">

## DESCRIPTION

<The first sentence defines the topic, or states the central fact.>
<If the document is long, one sentence gives the order of the document.>

### <Statement of fact as a subsection title>

<Explanation.>

### <Next statement of fact>

<Explanation.>

The following <levels | states | components> are defined:

- <term>\
  <Definition.>
  - <lowercase fragment, no period>
  - <lowercase fragment, no period>

## SEE ALSO
````

Rules specific to a concept document:

- Build definitions from the parts upward: "An ERE is one or more branches.
  A branch is one or more pieces."
- Put each new term in *italics* at its definition.
- Name the related concept that readers confuse with this one: "Globs should
  not be confused with regular expressions."
- Give the reason for a design only when it helps the reader predict
  behavior. "Highly secure mode is intended as a last line of defense."

## Project README

A README is the manual page of the whole project.

````markdown
# <project>

<project> - <verb or noun phrase, lowercase, no period>

## DESCRIPTION

`<project>` <does what>, in one sentence.
<Scope: what it handles.>
<Limits: what it does not handle.>

## BUILDING

`<project>` requires <compiler> <version> and <library> <version>.

1. Get the source:

   ```
   $ git clone <url>
   ```

2. Build it:

   ```
   $ make
   ```

If the build fails with <message>, install <package>.

## INSTALLATION

```
# make install
```

This installs `<binary>` in `/usr/local/bin` and the manual in
`/usr/local/man`.

## USAGE

```
<project> [-v] [-c file] path ...
```

<Short tag list of the main options, or a pointer:>
See `<project>(1)` for the full list of options.

## CONFIGURATION

<The configuration file, or a pointer to its document.>

## ENVIRONMENT

## FILES

## EXAMPLES

<Purpose sentence>:

```
$ <command>
```

## SEE ALSO

## AUTHORS

## CAVEATS

## BUGS

Report bugs at <url>.
````

Do not add sections for features, motivation, badges, a table of contents
(unless the README is very long), "contributing" boilerplate or thanks. If the
project has contribution rules, put them in `CONTRIBUTING`, and refer to them
in SEE ALSO.
