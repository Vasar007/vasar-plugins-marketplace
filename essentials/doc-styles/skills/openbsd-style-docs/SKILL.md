---
name: openbsd-style-docs
description: Write or rewrite technical documentation (READMEs, CLI and API references, configuration file references, service docs, design overviews, wiki pages) in the style of the OpenBSD manual pages. The result is terse and exact, with a fixed section order, a one-line summary, a first sentence that states what the thing does, the present tense and no marketing. Options and errors are sorted tag lists, defaults are separate sentences, and examples are tested. Use when the user asks for docs "in OpenBSD style", "like a man page", "BSD style", a "man-page style README", or terse, exact, reference-style docs, and when the user asks to review or clean up a README against these rules. The default output is Markdown or plain text, not roff.
---

# Technical documentation in the OpenBSD manual style

This skill takes the writing style of the OpenBSD manual pages and applies it
to any technical document. The default output format is Markdown. Do not write
roff or mdoc unless the user asks for a real manual page.

The rules come from a study of about 3700 pages in the OpenBSD source tree.
The main sources are `mdoc(7)`, `roff(7)`, `man(7)` and `style(9)`. Other
sources are the pages of `ls(1)`, `doas(1)`, `signify(1)`, `rcctl(8)`,
`httpd.conf(5)`, `pf.conf(5)`, `open(2)`, `strlcpy(3)`, `malloc(3)` and
`pledge(2)`, all at `https://man.openbsd.org`.

## The OpenBSD manual is the reference

The real OpenBSD manual pages are the standard. This skill is a summary of
them, and a summary can be wrong or incomplete. When the skill and the
corpus disagree, the corpus wins. When the skill does not cover a case,
find how the corpus handles it, and do the same.

Read the pages on the web. Use the WebFetch tool, or `curl` if WebFetch is
not available:

- The rendered page: `https://man.openbsd.org/<name>.<section>`, for example
  `https://man.openbsd.org/ls.1`. This is enough for wording and structure.
- The mdoc source, when the markup matters:
  `https://raw.githubusercontent.com/openbsd/src/master/<path>`, for example
  `.../bin/ls/ls.1`. The paths of the reference pages are in
  `references/skeletons.md`.
- A search by section and macro: `https://man.openbsd.org/?query=<expr>&apropos=1`.
  For example, `Nd~daemon` lists the pages with "daemon" in the NAME line.
  The syntax of `<expr>` is in `https://man.openbsd.org/apropos.1`.

Full-text search of the whole corpus is not available on the web. To find
how a phrase is usually written, read several reference pages of the same
type and compare them.

Use the pages in these situations:

- Before you write a document of a type, read one or two of the pages that
  `references/skeletons.md` names for that type. Imitate them, not only the
  skeleton.
- When you are not sure of a phrase, read how the reference pages of that
  type write it, and use the most common form.
- When you need a section that this skill does not describe (IOCTLS,
  CODE REFERENCES, CONTEXT, a custom section), find pages that have it,
  and copy their structure.
- When the user asks "how does OpenBSD write X", answer from the pages,
  and quote them with the page name and the section.

Prefer pages that OpenBSD developers wrote and maintain: `doas`, `signify`,
`rcctl`, `syspatch`, `httpd`, `pledge`, `unveil`, `strlcpy`, `strtonum`,
`malloc`, `mandoc` and most pages in section 7. Older pages imported
from other projects (for example `ssh`, `less`, `mail`, `patch`, `csh`) are a
weaker reference: they sometimes use "you" and older conventions.

`mdoc(7)` is the authority for the structure of a page and for the meaning of
each section. `style(9)` is the authority for the synopsis grammar and for the
code style in examples.

Files in this skill:

- `references/skeletons.md`: section skeletons in Markdown for each document
  type (utility, library API, configuration file, service, concept overview,
  project README), with the real OpenBSD pages to imitate.
- `references/phrases.md`: phrase templates taken from the corpus, sorted by
  section.
- `references/examples.md`: before and after rewrites, and one complete
  README.

Read `references/skeletons.md` before you write a new document. Read
`references/phrases.md` when you write a section that you do not know well.

## Precedence over other writing rules

This skill defines its own writing style. For the document that you write
with it, its rules replace the rules of any other plain-English,
Simplified Technical English (ASD-STE100) or general writing skill, plugin
or hook that is active in the session, for example `simple-english`.
Those rules still apply to your chat replies.

In particular, the OpenBSD style deliberately does these things that STE
rules forbid:

- It uses "may" and "should" with exact meanings (see "Sentence rules").
- It puts conditions after the command when that reads better: "Rotate the
  file even if it is smaller than the size limit."
- It uses fixed corpus formulas such as "The default is 7.", "This is the
  default.", "Note that ...", and "in order to".
- It uses semicolons and longer sentences where a man page would.

If a writing linter or hook reports such hits in a document written with
this skill, or in the files of this skill, do not rewrite the text to
satisfy it. Follow this skill. Fix only real defects that this skill also
forbids, such as marketing words, filler or "you" in descriptions.

If the user explicitly asks for STE or plain-English output for a
document, the request of the user wins over this section.

A skill cannot turn off a hook. To stop the `simple-english` lint hook from
reporting on a path, the user can set `SIMPLE_ENGLISH_LINT_EXCLUDE` to a
list of glob patterns, separated by `:`, for example
`SIMPLE_ENGLISH_LINT_EXCLUDE="$HOME/projects/*/docs/*:*/README.md"`.

## The principles

1. A document is a reference, not a tutorial and not an advertisement. It
   tells a competent reader exactly what the thing does, what it accepts, what
   it returns, and how it fails. It does not try to persuade.
2. The structure is fixed, so the reader knows where to look. Sections always
   come in the canonical order. Leave out a section that has no content. Never
   write "None" or "TBD" in a section, except "None." in DIAGNOSTICS when a
   reader may expect messages.
3. Each sentence states one fact. Sentences are short (8 to 20 words), in the
   simple present tense, and declarative.
4. Precision replaces explanation. Give numbers with units, exact limits, the
   default value, the behavior for empty, zero and NULL input, and what happens
   on error. Name undefined behavior plainly.
5. Do not repeat. Refer to the section or the document that already says it:
   "See FILES for details." or "See `ssh_config(5)`."
6. Nothing is there for decoration. Every sentence answers a question that a
   reader of a reference may have.

## Section order

The canonical order, from `mdoc(7)`, is below. Use only the sections that
apply. The skeletons in `references/skeletons.md` show the selection for
each document type.

```
NAME            one line: name and what it does
SYNOPSIS        invocation syntax, function prototypes, or file grammar
DESCRIPTION     what it does, then the options or the directives
CONTEXT         where a function may be called (kernel or async code only)
RETURN VALUES   functions only
ENVIRONMENT     environment variables that change behavior
FILES           files that it reads, writes or creates
EXIT STATUS     programs only
EXAMPLES        tested, copy-paste ready
DIAGNOSTICS     exact messages, their cause, and what the program does next
ERRORS          error codes of functions and APIs
SEE ALSO        related documents, sorted
STANDARDS       the standards that it follows, and its extensions
HISTORY         when it first appeared
AUTHORS         who wrote it
CAVEATS         common misuse and traps
BUGS            known defects and limits
SECURITY CONSIDERATIONS   only when there is real content
```

A long document can split DESCRIPTION into more sections with custom
uppercase names, for example `AUTHENTICATION`, `TCP FORWARDING`, `PRUNING`,
`BUILDING`, `ARCHITECTURE`. Put them between DESCRIPTION and the standard
tail sections. A long document can open with a short map of its sections:
"This document is divided into the following sections:".

Headings: use the canonical names in uppercase (`## DESCRIPTION`). This is the
most recognizable mark of the style. If the repository already uses sentence
case for headings, keep its convention, but keep the order. Use subsections
(`###`) inside a long section. A subsection title is a short noun phrase
("The long format") or, in a concept document, a statement of fact
("Modifying installed files is safe").

## NAME and the first sentence

The NAME line is the name, then a short description: lowercase, no article, no
final period, about 5 words, never a full sentence. For a tool, use a verb
phrase. For a daemon, a file or an API family, use a noun phrase.

```
logrot - rotate and compress log files
libcfg - configuration file parser
backupd.conf - backup daemon configuration file
```

In a Markdown README, the title is the name, and the description goes on the
first line under it. Do not use a tagline, a badge wall or an emoji.

DESCRIPTION starts with one sentence that makes the name the subject and gives
the main action in the present tense:

- "The `logrot` utility rotates and compresses log files."
- "The `cfg_parse()` function reads the file *path* and returns a parse tree."
- "`backupd.conf` is the configuration file for `backupd(8)`."
- "The `logrot` service runs once a day and keeps 7 rotated files."

Then give the default behavior ("By default, ...", "When run without
arguments, ..."). Then give the privilege or platform requirements ("Only the
superuser may ..."). Then give the options or the directives.

## Sentence rules

- Use the simple present tense for behavior: "`ls` sorts the output." Use
  "will" only for a consequence: "the copy will fail".
- The program, the function or the file is the grammatical subject. Passive
  voice is permitted for system behavior: "Output is not sorted."
- The reader is "the user" or "the caller". Do not use "you" in
  descriptions. Use the imperative mood only in option items, EXAMPLES,
  installation steps, and CAVEATS ("Do not use ...").
- Use the modal verbs with exactly these meanings:
  - "must": a hard requirement. If it is not met, the operation fails.
  - "may": a permission, or a real possibility.
  - "can": a capability.
  - "should": a recommendation with a reason.
  - "will": a guaranteed consequence.
  Do not hedge without information. "Skipping versions may work. Downgrading
  is unlikely to work." is calibrated and acceptable. "This might possibly
  cause issues" is not.
- Do not use these words: simply, just, easily, easy, powerful, robust,
  seamless, blazing, modern, intuitive, leverage, please,
  "it is worth noting", "out of the box". Do not use exclamation marks. Do not
  use closing summaries. Do not restate the NAME line.
- Give the reason for a rule only when the reason changes what the reader
  does: "Do not edit `passwd` by hand. Use `vipw(8)`, which locks the file."
- Use "Note that" for a non-obvious exception or consequence, and use it
  rarely.
- Write numbers with units: "60 seconds", "1048576 bytes (1M)", "up to 31
  characters". Add a human conversion in parentheses when it helps:
  "600 seconds (10 minutes)".
- Use the established term for a thing everywhere. Introduce a new term in
  italics once, where it is defined: "Each group of panes is a *window*."
- Spelling and terms follow the existing project. Inside one document, use
  one spelling.

## Lists and their items

The main device is the tag list: a term, then its description. Use it for
options, directives, environment variables, files, error codes and messages.
In Markdown, write it like this (the backslash is a hard line break):

```markdown
- `-o` *file*\
  Write the output to *file* instead of the standard output.
```

If the renderer does not support backslash line breaks, write
`` - `-o` *file*: Write ... `` on one line.

Rules for items:

- Start an option or directive item with a bare imperative verb: Print,
  Use, Specify, Set, Do not, Display, Write, Read, Ignore. A mode can start
  with a noun fragment, then a sentence: "Quiet mode. Suppress informational
  output."
- Put the default in its own last sentence: "The default is 60 seconds."
  "This is the default." "This is disabled by default."
- State interactions as separate sentences: "This option implies `-a`."
  "Requires `-c`." "Cannot be used together with `-u`." "The `-f` option
  overrides any previous `-i` options."
- Sort options alphabetically: digits first, then letters, uppercase before
  lowercase for the same letter (`-1 -A -a -B -b`). It does not matter whether
  an option takes an argument. Sort environment variables, files and error
  codes alphabetically too. Sort SEE ALSO by section number, then by name.
- Introduce a list with a sentence that ends in a colon: "The options are as
  follows:", "The following directives are available:".
- A bullet list is for parallel items without a term. A numbered list is for
  steps in a fixed order. Use a table only for true multi-column data. For two
  columns, a tag list is better.

## Markup in Markdown

The OpenBSD pages use semantic markup. In Markdown, map it like this:

| Element | mdoc | Markdown |
|---|---|---|
| command, flag, keyword, literal value | `Nm`, `Fl`, `Cm`, `Ic`, `Ql` | `` `code` `` |
| function, constant, error code, type | `Fn`, `Dv`, `Er`, `Vt` | `` `open()` ``, `` `ENOENT` `` |
| path, environment variable | `Pa`, `Ev` | `` `/etc/foo.conf` ``, `` `HOME` `` |
| placeholder chosen by the user | `Ar`, `Fa` | *italic* outside code, plain word inside a synopsis block |
| reference to another document | `Xr` | `` `name(8)` `` or a link with that text |
| reference to a section | `Sx` | the section name, or a link to it |
| new term at its definition | `Em` | *italic*, one time |
| critical word (not, never, only) | `Em` | *italic*, rarely |
| multi-line display, output, configuration | `Bd -literal` | fenced code block |

Do not use bold for emphasis. Bold is for syntax elements only, and it is
almost never necessary in Markdown.

## SYNOPSIS

The synopsis is a fenced code block in the grammar of `style(9)`. The usage
message of the program must match it.

```
logrot [-nv] [-c file] [-k count] path ...
logrot -l [-c file]
```

- Flags without arguments come first, in one bracket group, sorted.
- Then each flag with an argument, in its own brackets, sorted.
- Then the required operands, then the optional operands.
- `[ ]` marks an optional part, `|` marks alternatives, `...` marks
  repetition. A required part has no brackets.
- Each separate mode of operation gets its own line.

For an API, the synopsis is the include line and the prototypes, in the
order of the header file. For a configuration file, it is the grammar of one
statement.

## EXAMPLES

- Before each example, write one imperative sentence that states its purpose
  and ends in a colon: "Rotate all logs in `/var/log/app` and keep 14 files:".
- Show the command in a code block. Use `$` for an ordinary user and `#` for
  root.
- Do not write "Example 1" headings. Show the output only when the example
  is about the output.
- Every example must work exactly as written. If you cannot run it, say so to
  the user. Do not present an untested example as tested.
- For a dangerous idiom, show the wrong form, then the correct form: "Do not
  write this:" and "Write this instead:".
- After the code, one sentence may state what the example guarantees: "This
  guarantees that *n* is between 1 and 64."

## Failure, warnings and limits

- EXIT STATUS for a program: "The `logrot` utility exits 0 on success, and >0
  if an error occurs." Then add any special codes: "In particular, 2 means
  that there was nothing to rotate."
- RETURN VALUES for a function: give success, failure and the edge cases
  separately. "If successful, `cfg_parse()` returns a pointer to the tree.
  Otherwise, it returns `NULL` and sets `errno` to indicate the error."
- ERRORS: "The `cfg_parse()` function will fail if:", then a tag list of
  codes. Each item is a full sentence about the cause: "[`ENOENT`] The file
  *path* does not exist." Use "will fail" for a certain failure and "may fail"
  for a possible one. One code can have several items, one for each cause.
- DIAGNOSTICS: quote the exact message as the term, then give the cause and
  what the program does next. "The driver will reset the hardware. This
  should not happen."
- A security warning names the risk, explains how it occurs, and gives the
  safe alternative. "Do not pass user data as the format string. An attacker
  can put conversion specifiers in it to write to the stack. Use `"%s"`
  instead." Do not use alarm words.
- CAVEATS is for traps in correct software. BUGS is for defects and missing
  features in this software, stated frankly: "Ignores the current locale."

## Tail sections

- SEE ALSO: a comma-separated list of references, sorted by section and then
  by name, with no prose. Add external documents (books, RFCs, URLs) after
  the list, each with one sentence.
- STANDARDS: "The `logrot` utility follows RFC 5424." Add "The `-z` flag is
  an extension to that specification." for extensions.
- HISTORY: "`logrot` first appeared in version 1.2." For a rewrite:
  "This implementation of `logrot` first appeared in 3.0."
- AUTHORS: "`logrot` was written by Name <mail@example.org>."

## Applying the style to a project README

A README is a manual page for the whole project:

1. A title with the project name, and a one-line description in NAME style.
2. DESCRIPTION: what the project does, in its first sentence. Then its scope
   and its limits. No list of "features", no "why".
3. Custom sections as the project needs them, for example BUILDING,
   INSTALLATION, CONFIGURATION, USAGE. Write installation steps as a
   numbered list of imperative sentences. State the requirements (compiler,
   libraries, versions) before the first step.
4. Then the standard tail: ENVIRONMENT, FILES, EXAMPLES, SEE ALSO, AUTHORS,
   CAVEATS, BUGS. The license belongs in the license file. Add a LICENSE section
   only when the project has no license file.

See `references/skeletons.md` for the full README skeleton.

## Documents in other languages

The same rules apply to Russian and to other languages. Use the present
tense and make the thing the subject: "Утилита `logrot` сжимает журналы."
Do not use "вы" in descriptions. Use the imperative mood for steps and
options: "Вывести ...", "Использовать ...". Keep the same section order. If
the project mixes languages, keep the section names in English uppercase.
Otherwise, translate them and use the same translation everywhere.

## Workflow

1. Find out the facts before you write. Read the code, `--help`, the parser
   of the configuration, the error paths and the exit codes. The style
   depends on exact facts. Do not invent defaults, limits or error codes. If
   a fact is unknown, ask the user or mark it in your reply. Do not hide it
   in vague words.
2. Pick the document type and its skeleton from `references/skeletons.md`.
3. Write the NAME line and the first sentence of DESCRIPTION. If they are
   hard to write, the purpose of the thing is not clear yet. Ask.
4. Fill in the sections in canonical order. Delete the empty ones.
5. Run every example, if possible.
6. Do the self-check below.

When you rewrite an existing document, keep all facts. Remove marketing,
repetition and filler. Move content into the canonical sections. Tell the
user which facts you could not verify.

## Self-check

Before you finish, check the document against this list:

- The NAME line is lowercase, has no article and no period, and has about 5
  words.
- The first sentence of DESCRIPTION has the name as its subject and a verb in
  the present tense.
- The sections are in canonical order, and no section is empty.
- Options, variables, files and error codes are sorted.
- Every default is stated as a separate sentence.
- Every number has a unit.
- The synopsis matches the real usage message.
- Every example has a purpose sentence that ends in a colon, and it works.
- Search the text for: simply, just, easily, powerful, seamless, please,
  "you", "!", "**". Remove each hit or justify it.
- "must", "may", "should" and "can" each have their exact meaning.
