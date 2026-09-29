# OS-9 development skills

> **Pre-publication - not for distribution.** Circulated privately for review;
> no license is granted yet. See [LICENSE](LICENSE) for why, and
> [LICENSE.pending](LICENSE.pending) for the terms intended to replace it.
> [NOTICE](NOTICE) credits the sources and is in force regardless.

A working reference for programming **Microware OS-9** on the 6809 and the
68000, written to be read by a person or handed to an AI coding assistant.
BASIC09, Microware C, 68000 and 6809 assembly, the shell and its utilities,
modules, system calls and error codes; and below the application line, device
drivers, file managers and the kernel itself.

Microware wrote OS-9 at the turn of the 1980s for Motorola's 6809 and soon
brought it to the 68000. It put a real-time, multitasking, Unix-like system on
machines far too small for Unix, built from compact, reentrant modules that run
as happily from ROM as from disk, one shared copy of each program serving
every process that runs it. That made it at home in the Tandy Color Computer,
Fujitsu's FM machines and the Philips CD-i player, and on factory floors and in
instruments, where it starts "instant on" from reset. It never stopped: OS-9 is
still developed, sold and supported by Microware LP, at
[microware.com](https://www.microware.com).

Its documentation was thorough and well made, but it is now scattered across
decades of manuals, editions and scans. These files gather what a programmer
needs into one place, and every claim says where it came from - a Microware
manual, or a program actually run - so you can tell at a glance how far to lean
on it.

**What it covers:** the early OS-9 line, from the 6809 (Level One and Level
Two) up to OS-9/68000 at version 2.4. It has nothing specific to OS-9000, to
later OS-9 releases, or to Microware's other products such as MAUI, and
networking is covered only in outline; for those, Microware's own
documentation is the place to go. CD-RTOS, the OS-9 inside the Philips
CD-i player, is OS-9, and what applies to OS-9/68000 applies to it; but CD-i
itself, the "Green Book" hardware and software standard, is not covered. Nor
is every machine OS-9 ran on: the Tandy Color Computer and Dragon get some
hardware notes, and other machine-specific details are largely absent. For
those, the hardware manufacturer's manuals are the place to go.

This reference comes from OS-9's users, not from Microware. Microware isn't
responsible for it and doesn't endorse it, and anything it says about OS-9 is
ours, not theirs. Where it and a Microware manual disagree, trust the manual.

## What is here

| Skill | Covers |
|---|---|
| **`os9-dev`** | Programs that run on OS-9: BASIC09, Microware C, 68000 and 6809 assembly, the shell and utilities, modules, system calls, error codes, and how OS-9 differs from Unix |
| **`os9-systems-dev`** | Below the application line: device drivers, file managers, kernel internals, the scheduler, 6809 Level 2 memory management |

They are siblings and cite each other; keep both. Each opens with a
`SKILL.md`, and each has a `references/INDEX.md` that maps a topic to its file
and, separately, a symptom to its likely cause.

## Where to start

| If you want to... | Read |
|---|---|
| Understand how OS-9 thinks | `os9-dev/references/common/os9-mental-model.md` |
| Know how it differs from Unix | `os9-dev/references/common/unix-differences.md` |
| Port or write a **C** program | `os9-dev/references/c/kandr-vs-ansi.md`, then `c/os9-c-cheatsheet.md` |
| Work in **BASIC09** | `os9-dev/references/basic09/basic09-language.md` |
| Write **68000 or 6809 assembly** | `os9-dev/references/68k/os9-68k-assembly.md`, or `6809/assembly-and-tools.md` |
| Explain an **error or a symptom** | the symptom table in `os9-dev/references/INDEX.md` |
| Write a **driver, file manager or kernel** code | `os9-systems-dev/SKILL.md` |
| Work **without OS-9 hardware** | `os9-dev/references/common/using-os9exec-repl.md` (68000), `6809/using-nitros9-repl.md` (6809) |

## Using it

It is plain Markdown; there is nothing to build.

**Reading it yourself** - start with `os9-dev/SKILL.md`, then the `INDEX.md`
beside it.

**With an AI assistant that can read files** - point it at
[`AGENTS.md`](AGENTS.md). The files run to about 13,000 lines and are written
to be opened as needed, not read whole; the index is the way in.

**With a chat assistant that only takes attachments** - attach
`os9-dev/SKILL.md` and `os9-dev/references/INDEX.md` (or the `os9-systems-dev`
pair for driver and kernel work), describe the task, and ask which files it
needs; then attach those. Two or three usually settle a question.

**As skills** - each skill directory is a standard skill folder, a `SKILL.md`
with a `name` and `description` header and its `references/` beside it, so an
assistant that loads skills can pick them up when a task matches. In Claude
Code this repository is also a plugin, and both install together:

```
/plugin marketplace add peacedudes/os9-dev-skill
/plugin install os9@os9-dev-skill
```

Or link a checkout's two folders into a skills directory:

```sh
ln -s "$PWD/os9-dev"         ~/.claude/skills/os9-dev
ln -s "$PWD/os9-systems-dev" ~/.claude/skills/os9-systems-dev
```

## What you will need

To do the work, not to read about it:

- **An OS-9 system.** Real hardware if you have it. Without it, 68000 programs
  run under [os9exec](https://github.com/peacedudes/os9exec), a community
  emulator, and 6809 work runs on NitrOS-9 under the XRoar emulator.
- **Microware's own software**, legally held: its shell, C compiler and
  utilities are Microware's, and none of it is in this repository. You cannot
  compile C without Microware's `cc`.

## How far to trust it

Every claim carries a tag saying what stands behind it:

| Tag | Means |
|---|---|
| `Manual` | Stated in published Microware documentation |
| `Live` | Run and observed - the tag names what it ran on |
| `Source` | Read from an implementation's source, not run |
| `Absent` | Looked for and confirmed not to exist |
| `Hearsay` | Someone said so; lowest confidence |
| `Flag` | Sources disagree; unresolved |

Most of the practical material was checked by running it: 68000 programs under
os9exec, 6809 programs on NitrOS-9. Both are careful reimplementations, and
neither is OS-9, so a `Live` result is evidence about the emulator it ran on.
Where one disagrees with a manual, the manual is taken as the specification.
Nothing here has yet been checked on real OS-9 hardware, and silence on a topic
means it was not tested, not that OS-9 lacks it.

Some thirty Microware manuals, quick references and training guides stand
behind these files; each skill's `SOURCES.md` says which back which file.
`SOURCE-AUTHORITY.md` says what counts as Microware's word, and
`DIVERGENCES.md` lists the few places a manual contradicts itself or a
Microware program.

Found something wrong? [Corrections are welcome](CONTRIBUTING.md), even a bare
"this line is wrong, here is what I saw". A report from real hardware is the
most valuable thing this project can receive.

## Provenance

Everything here was learned from published or freely distributed documentation
and from preservation archives, and by running programs. No Microware source
code was used. Facts are stated as facts; the words around them are our own,
with short quotations, attributed by chapter and page, only where a manual's
exact wording is the evidence. The rest of the reasoning, and what was
deliberately left out, is in each skill's `SOURCES.md`.

## Related projects

- **os9exec** (https://github.com/peacedudes/os9exec) - an OS-9/68000
  emulator for macOS, Linux and Windows. Its conformance suite, CONF68K, also
  runs on real OS-9/68000 hardware; `CONTRIBUTING.md` says how to help with it.
- **A collection of OS-9/68000 freeware**, rebuilt and tested under os9exec,
  whose porting work found many of the traps recorded here.
  <!-- PUBLISH: when the collection is public, link it on the line above. -->

## Layout

```
os9-dev/                application skill: SKILL.md, SOURCES.md, references/
os9-systems-dev/        systems skill: SKILL.md, SOURCES.md, references/
AGENTS.md               entry point for any AI assistant
CLAUDE.md               the same, imported for Claude Code
.claude-plugin/         Claude Code plugin and marketplace manifests
NOTICE                  attribution: Microware and every other source
CONTRIBUTING.md         corrections, patches, and the checks every change passes
SOURCE-AUTHORITY.md     what counts as Microware's word
DIVERGENCES.md          where a manual contradicts itself or a Microware program
tools/                  the consistency checker, its tests, the pre-commit hook
.github/workflows/      the same checks, run on every push and pull request
```
