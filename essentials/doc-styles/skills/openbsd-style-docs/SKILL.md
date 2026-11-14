---
name: openbsd-style-docs
description: OpenBSD manual-page style for technical docs in Markdown. It writes uppercase sections in a fixed order, a one-line NAME summary, sorted tag lists, and each default as its own sentence.
when_to_use: Use it only when the user names the style, for example "OpenBSD style", "like a man page", "man-page style", or "BSD style", or asks to review a document against it. It sets no style for chat replies. For docs with no named style, use create-documentation.
---

# Technical documentation in the OpenBSD manual style

The default output format is Markdown. Do not write roff or mdoc unless the
user asks for a real manual page.

## The OpenBSD manual is the reference

The real OpenBSD manual pages are the standard. When the skill and the
corpus disagree, the corpus wins. When the skill does not cover a case,
find how the corpus handles it, and do the same. The URLs, the search
syntax and the pages to prefer are in "Reading the corpus" in
`references/skeletons.md`.

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

`mdoc(7)` is the authority for the structure of a page and for the meaning of
each section. `style(9)` is the authority for the synopsis grammar and for the
code style in examples.

Files in this skill:

- `references/skeletons.md`: a section skeleton for each document type
  (utility, library API, configuration file, service, concept overview,
  project README), with the pages to imitate. Read it before you write a
  new document.
- `references/phrases.md`: phrase templates from the corpus, by section.
  Read it when you write a section that you do not know well.
- `references/examples.md`: before and after rewrites, and one complete
  README.
- `scripts/openbsd_lint.py`: the linter for the rules that a script can
  test. The hook of this plugin runs it after each write of a document in
  this style. It needs Python 3 as `python3` on `PATH`.

## Precedence over other writing rules

This skill defines its own writing style. Inside the document that you
write with it, its rules replace the rules of any other plain-English,
Simplified Technical English (ASD-STE100) or general writing skill, plugin,
hook or standing instruction of the session, for example `simple-english`.
This holds for the structure and for each sentence, even when the other
rule says that it covers all files. A request for this style is the more
specific request.

In particular, the OpenBSD style deliberately does these things that STE
rules forbid:

- It uses "may" and "should" with exact meanings (see "Sentence rules").
- It puts conditions after the command when that reads better: "Rotate the
  file even if it is smaller than the size limit."
- It uses fixed corpus formulas such as "The default is 7.", "This is the
  default.", "Note that ...", and "in order to".
- It uses semicolons where a man page would.

If another writing linter or hook, for example the `simple-english` lint
hook, reports such hits in a document written with this skill, or in the
files of this skill, do not rewrite the text to satisfy it. Follow this
skill. Fix only real defects that this skill also forbids, such as
marketing words, filler or "you" in descriptions.

Only one case reverses this section: the message of the user asks for STE
or plain-English output for this document. A standing rule in a system
prompt, a `CLAUDE.md` file or a skill is not such a request.

The chat reply is not part of the document. Step 7 of "Workflow" gives
its rules.

A skill cannot turn off a hook. To stop a lint hook for some paths, the
user can set an environment variable to a list of glob patterns:
`SIMPLE_ENGLISH_LINT_EXCLUDE` for the `simple-english` lint hook, and
`OPENBSD_STYLE_LINT_EXCLUDE` for the hook of this plugin. The separator is
`:` on Linux and macOS and `;` on Windows. The pattern `*` turns the hook of
this plugin off. For example, on Linux:
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

The canonical order, from `mdoc(7)`, is below.

```text
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

```text
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
- Do not use the marketing and filler words simply, just, easily, easy,
  powerful, robust, seamless, blazing, modern, intuitive, leverage and
  please, the phrases "it is worth noting" and "out of the box",
  exclamation marks, bold or closing summaries. Do not restate the NAME
  line.
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
- State interactions as separate sentences: "This option implies `-a`."
  "Requires `-c`." "Cannot be used together with `-u`." "The `-f` option
  overrides any previous `-i` options."
- Sort options alphabetically: digits first, then letters, uppercase before
  lowercase for the same letter (`-1 -A -a -B -b`). It does not matter whether
  an option takes an argument. Sort environment variables, files and error
  codes alphabetically too.
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

## SYNOPSIS

The synopsis is a fenced code block in the grammar of `style(9)`. The usage
message of the program must match it.

```text
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
- Every example must work exactly as written. Do not present an untested
  example as tested.
- For a dangerous idiom, show the wrong form, then the correct form: "Do not
  write this:" and "Write this instead:".
- After the code, one sentence may state what the example guarantees: "This
  guarantees that *n* is between 1 and 64."

## Failure, warnings and limits

- EXIT STATUS for a program: "The `logrot` utility exits 0 on success, and >0
  if an error occurs." Then add each special code that the facts name:
  "In particular, 2 means that there was nothing to rotate." If the facts
  give an exact code for each error, use a tag list instead, as `grep(1)`
  does.
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
- STANDARDS, HISTORY and AUTHORS: use the formulas in
  `references/phrases.md`, for example "`logrot` first appeared in version
  1.2."

## Applying the style to a project README

A README is a manual page for the whole project. Before you write or review
one, read "Project README" in `references/skeletons.md`: its rules and its
skeleton.

## Documents in other languages

Before you write or review a document in a language other than English,
read "Documents in other languages" in `references/phrases.md`.

## Workflow

1. Find out the facts before you write. Read the code, `--help`, the parser
   of the configuration, the error paths and the exit codes. Do not invent
   defaults, limits or error codes. If a fact is unknown, ask the user or
   mark it in your reply. Do not hide it in vague words.
2. Pick the document type and its skeleton from `references/skeletons.md`.
3. Write the NAME line and the first sentence of DESCRIPTION. If they are
   hard to write, the purpose of the thing is not clear yet. Ask.
4. Fill in the sections in canonical order. Delete the empty ones.
5. Run every example, if possible.
6. Do the self-check below.
7. Reply in the chat. This skill sets no style for the reply. Follow the
   reply rules of the session, for example those of `simple-english`. If
   the session has none, write short prose with no headings, no bullet
   lists and no bold. Name the file that you wrote, the facts that you
   could not verify, and the examples that you could not run.

When you rewrite an existing document, keep all facts. Remove marketing,
repetition and filler. Move content into the canonical sections.

## Self-check

The hook of this plugin runs `scripts/openbsd_lint.py` after each write of
a document in this style. The script checks the section names, their
order and their content, the form of the NAME line, the sort order of
options, variables, files and error codes, defaults in their own sentence,
"you", and the words of "Sentence rules". Fix each hit, or keep it and
give the reason in the reply. With a shell tool, the script also runs by
hand: `python3 "${CLAUDE_SKILL_DIR}/scripts/openbsd_lint.py" <file>`.

The hook is silent for a document that it skips, or if `python3` is
missing, the same as for a document with no hit. So if `## DESCRIPTION`
is missing, is not uppercase, or is the only uppercase canonical heading,
run the script by hand. If no shell tool is available, or if `python3` is
missing, check the rules of the script by hand.

Then check the rest by hand:

- The NAME line has about 5 words and is not a full sentence.
- The first sentence of DESCRIPTION has the name as its subject and a verb
  in the present tense.
- Every number has a unit.
- The synopsis matches the real usage message.
- Every example has a purpose sentence that ends in a colon, and it works.
- "must", "may", "should" and "can" each have their exact meaning.
