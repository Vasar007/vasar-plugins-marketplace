# Phrase templates

These phrases come from the OpenBSD manual pages. Each one is a fixed formula.
Use the formula exactly. The reader will recognize it and read faster. The
source page is given in parentheses.

## NAME line

- `<tool> - <verb> <object>`: "list directory contents" (`ls(1)`), "copy
  files" (`cp(1)`), "execute commands as another user" (`doas(1)`),
  "cryptographically sign and verify files" (`signify(1)`).
- `<daemon> - <noun>`: "HTTP daemon" (`httpd(8)`), "clock daemon"
  (`cron(8)`), "terminal multiplexer" (`tmux(1)`).
- `<file> - <program> configuration file`: "doas configuration file".
- `<file> - format of the <X> file`: "format of the password file".
- `<api> - <noun phrase>`: "size-bounded string copying and concatenation"
  (`strlcpy(3)`), "memory allocation and deallocation" (`malloc(3)`).
- `<concept> - overview of <X>`, `<X> and its effects`, `layout of <X>`.

The most common first verbs: display, control, print, create, configure,
manage, remove.

## First sentence of DESCRIPTION

- "The `<tool>` utility <verbs> <object>."
- "The `<daemon>` daemon is <a noun phrase> with <features>."
- "`<tool>` is a <noun> that <verbs> ..."
- "The `<f>()` function <verbs> <argument> ..."
- "`<file>` is the configuration file for `<program>`."
- "The `<program>` utility <verbs> according to the rules in the `<file>`
  configuration file."
- For several synopsis forms: "In the first synopsis form, `<tool>` <verbs>
  ... In the second synopsis form, ..."

## Defaults and behavior

- "By default, `<tool>` <verbs> ..."
- "When run without arguments, `<tool>` <verbs> ..."
- "The default is <value>."
- "This is the default."
- "This is the default when the output is not a terminal."
- "If not specified, it defaults to <value>."
- "<X> is disabled by default."
- "If set to <value>, <effect>. Otherwise, <fallback>."
- "Only the superuser may <action>."
- "`<daemon>` rereads its configuration file when it receives `SIGHUP`."

## Option and directive items

- Imperative verbs to start with: Print, Display, Use, Specify, Set, Do not,
  Write, Read, Ignore, Force, Enable, Disable, List, Revert, Check.
- "Quiet mode. Suppress informational output."
- "Verbose mode. Multiple `-v` options increase the verbosity."
- "Check that the configuration is valid, but do not start the server."
- "Same as `-RpP`." / "Equivalent to `-R`."
- "This option implies `-a`."
- "Requires `-c`."
- "Cannot be used together with `-u`."
- "The `-f` option overrides any previous `-i` options."
- "This option has no effect unless `-l` is also specified."
- "If more than one of these options is given, the last one is used."
- "Print usage information and exit."

## Lead-ins to lists

- "The options are as follows:"
- "The following options are available:"
- "The mode of operation is selected with the following options:" then "The
  other options are as follows:"
- "The following commands are available:"
- "Here are the settings that can be set globally:"
- "Rules consist of the following parts:"
- "The following <values | keywords | types> are defined:"
- "<X> is divided into the following main sections:"
- "Exactly one of the following must be specified:"
- "At least one option must be specified."

## Requirements, limits and undefined behavior

- "<X> must be <condition>."
- "<X> must not <action>."
- "The name can be up to 31 characters long."
- "Values less than 512 bytes or greater than 1 gigabyte are ignored."
- "If *ptr* is `NULL`, no action occurs."
- "If the strings overlap, the behavior is undefined."
- "The system guarantees <X> if <condition>, but in no other case."
- "It is an error to <action>."
- "It is not possible to <action>."
- "No command is executed."

## Warnings and recommendations

- "Do not use <X> to <purpose>. <Reason>. Use <Y> instead."
- "<X> should not be edited by hand. Use `<tool>` instead."
- "It is strongly recommended that <X>."
- "<X> should be enabled with caution."
- "Care should be taken when <action>: <consequence>."
- "Note that <exception>."
- "Be advised that it is best to <action>."

## Return values and exit status

- "The `<tool>` utility exits 0 on success, and >0 if an error occurs."
- "In particular, <code> indicates that <condition>."
- "`<tool>` may fail for one of the following reasons:" then short
  past-tense sentences: "The password was incorrect."
- "`<tool>` exits with the exit status of the remote command, or with 255 if
  an error occurred."
- "The `<f>()` function returns the value 0 if successful. Otherwise, it
  returns -1 and sets `errno` to indicate the error."
- "If successful, `<f>()` returns <value>. Otherwise, <value> is returned and
  `errno` is set to indicate the error."
- "Upon successful completion, `<f>()` returns <value>."
- "These functions are always successful, and no return value is reserved to
  indicate an error."
- "The `<f>()` function does not return."
- "It is the responsibility of the caller to <action>."

## ERRORS

- "The `<f>()` function will fail if:"
- "`<f>()` will succeed unless:"
- "Additionally, `<g>()` will fail if:"
- "In addition, `<f>()` may return the following errors:"
- Item: "*path* points outside the allocated address space of the process."
- Item: "A component of the pathname exceeded `NAME_MAX` characters."
- Item: "The *flags* argument is not valid."
- Item: "Too many descriptors are active."

## DIAGNOSTICS

- Term: the exact message. Body: the cause, then what happens next.
- "A fatal initialization error occurred."
- "The driver will reset the hardware. This should not happen."
- "This is likely due to <cause>."
- "Some common error messages are:"

## EXAMPLES

- "<Imperative purpose>:" for example "List the contents of the current
  directory in long format:", "Create a new key pair:", "Wait five seconds
  before running a command:".
- "The same example again, this time with <difference>:"
- "Either of these commands will remove the file `-f`:"
- "To <purpose>, something like the following can be used:"
- "The above example guarantees that <X>."
- For idioms: "Do not write this:", "Write this instead:", "This is
  correct:", "This is *not*:".

## SEE ALSO, STANDARDS, HISTORY, AUTHORS

- SEE ALSO: "`cp(1)`, `ln(1)`, `symlink(7)`". Sort by section, then by name.
- "The `<tool>` utility is compliant with <standard>."
- "The flags `[-av]` are extensions to that specification."
- "`<f>()` is an extension. The existing alternatives are difficult to use
  safely."
- "`<tool>` first appeared in <project> <version>."
- "A `<tool>` command appeared in <old system>." (for a reimplementation of
  an old tool)
- "This implementation of `<tool>` first appeared in <version>."
- "`<tool>` was written by <Name> <<mail>>."
- "`<tool>` was written by <Name>, based on code by <Name>."

## Cross-references

- "See `<page>(5)` for details."
- "See the CONFIGURATION section for details."
- "(see `login.conf(5)`)"
- "For more information on <topic>, see `<page>(8)`."
