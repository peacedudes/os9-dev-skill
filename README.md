# OS-9 skills for AI coding assistants

Two agent skills that teach an AI coding assistant to work on **Microware
OS-9** for the 6809 and the 68000. With them loaded, an assistant can write,
port and debug BASIC09, Microware C and 68000 or 6809 assembly. It can drive
the shell and its utilities, build modules, make system calls, read error
codes, and work below the application line on device drivers, file managers
and the kernel.

Install them in Claude Code:

```
/plugin marketplace add peacedudes/os9-dev-skill
/plugin install os9@os9-dev-skill
```

Other assistants: see [Installing](#installing).

## Why it exists

AI models know very little about OS-9, and some of what they know is wrong.
Its documentation is spread across decades of manuals, editions and scans, so
a model has seen little of it and fills the gaps with Unix habits and
repeated folklore. Those habits fail here. Text lines end in CR, not LF.
Microware C is K&R C, with no prototypes, no `const` and no `string.h`.
BASIC09 is structured and typed, and turns its procedures into I-code; it is
not line-numbered BASIC. A program is a module with a header and a CRC, not a
flat executable. Facts about the 6809 and the 68000 get blended together. The
answer comes out fluent and plausible, and it is wrong.

These files supply what the model lacks: about 13,000 lines of OS-9 fact,
each claim tagged with the source that stands behind it. They are laid out so
an assistant loads only the part a task needs.

## Built for an assistant

A person can read these files, since they are plain Markdown, but every
choice in them was made for a model working on a task:

- **Loaded on demand.** Each skill's `SKILL.md` carries a description that
  tells the assistant when the skill applies, plus a short core model that it
  reads every time. Everything else lives in `references/` and is opened only
  when needed.
- **Routed by symptom.** An assistant usually arrives with an error number or
  a program that misbehaved, not a topic name. So each `references/INDEX.md`
  maps symptoms to causes, as well as topics to files.
- **Tagged for trust.** Every claim says what it rests on, so the assistant
  can judge how far to lean on it and tell you how sure it is:

  | Tag | Means |
  |---|---|
  | `Manual` | Stated in published Microware documentation |
  | `Live` | Run and observed; the tag names what it ran on |
  | `Source` | Read from an implementation's source, not run |
  | `Absent` | Looked for and confirmed not to exist |
  | `Hearsay` | Someone said so; lowest confidence |
  | `Flag` | Sources disagree; unresolved |

- **Told not to guess.** The skills tell the assistant to answer specifics
  from the files rather than from memory. If it cannot check a claim, it must
  say so. A confident wrong answer is the failure these files exist to
  prevent.
- **The manual outranks the emulator.** Most practical claims were checked
  by running them: 68000 programs under os9exec, 6809 programs on NitrOS-9.
  Neither emulator is OS-9, so a `Live` result is evidence about the emulator.
  Where an emulator and a Microware manual disagree, the assistant is told to
  treat the manual as the specification. Nothing here has yet been checked on
  real OS-9 hardware.

## Installing

| Assistant | How |
|---|---|
| **Claude Code** | The plugin commands above. Or link a checkout's two folders into `~/.claude/skills/` (shown below) |
| **Other assistants that load skills** | Each skill directory is a standard skill folder: a `SKILL.md` with a `name` and `description` header, with `references/` beside it. Install both folders |
| **Any agent that reads files** | Clone the repository and point the agent at [`AGENTS.md`](AGENTS.md) |
| **A chat assistant that only takes attachments** | Attach `os9-dev/SKILL.md` and `os9-dev/references/INDEX.md` (or the `os9-systems-dev` pair for driver and kernel work), describe the task, and ask which files it needs. Then attach those. Two or three usually settle a question |

```sh
ln -s "$PWD/os9-dev"         ~/.claude/skills/os9-dev
ln -s "$PWD/os9-systems-dev" ~/.claude/skills/os9-systems-dev
```

There is nothing to build. Each [release](https://github.com/peacedudes/os9-dev-skill/releases)
also carries a zip of both skills.

## The two skills

| Skill | The assistant uses it for |
|---|---|
| **`os9-dev`** | Programs that run on OS-9: BASIC09, Microware C, 68000 and 6809 assembly, the shell and utilities, modules, system calls, error codes, and how OS-9 differs from Unix |
| **`os9-systems-dev`** | Below the application line: device drivers, file managers, kernel internals, the scheduler, 6809 Level 2 memory management |

They are siblings and cite each other, so install both.

**Scope:** the early OS-9 line, from the 6809 (Level One and Level Two) up to
OS-9/68000 version 2.4. CD-RTOS, the OS-9 inside the Philips CD-i player, is
OS-9, and the 68000 material applies to it. Out of scope: OS-9000, later
OS-9 releases, Microware's other products such as MAUI, the CD-i "Green
Book" standard itself, and most machine-specific hardware detail beyond some
Tandy Color Computer and Dragon notes. Networking is covered only in outline.
When a question goes past these limits, the skills tell the assistant to say
so and point to Microware's manuals or the hardware maker's.

## What the assistant will need

To do the work, not just to talk about it:

- **An OS-9 system.** Real hardware if you have it. Without it, 68000 programs
  run under [os9exec](https://github.com/peacedudes/os9exec), a community
  emulator, and 6809 work runs on NitrOS-9 under the XRoar emulator. The
  skills teach the assistant to drive both.
- **Microware's own software**, legally held. The shell, the C compiler and
  the utilities belong to Microware, and none of them is in this repository.
  Nothing compiles C without Microware's `cc`.

## About OS-9

Microware wrote OS-9 at the turn of the 1980s for Motorola's 6809 and soon
brought it to the 68000. It put a real-time, multitasking, Unix-like system on
machines far too small for Unix. It is built from compact, reentrant modules
that run as well from ROM as from disk, with one shared copy of each program
serving every process that runs it. That design suited the Tandy Color
Computer, Fujitsu's FM machines and the Philips CD-i player, and also factory
floors and instruments, where it starts "instant on" from reset. OS-9 is
still developed, sold and supported by Microware LP, at
[microware.com](https://www.microware.com).

This project comes from OS-9's users, not from Microware. Microware is not
responsible for it and does not endorse it, and anything it says about OS-9 is
ours, not theirs. Where it and a Microware manual disagree, trust the manual.

## Sources and provenance

Some thirty Microware manuals, quick references and training guides stand
behind these files, and each skill's `SOURCES.md` says which ones back which
file. `SOURCE-AUTHORITY.md` defines what counts as Microware's word.
`DIVERGENCES.md` lists the few places where a manual contradicts itself or a
Microware program.

The material comes from published or freely distributed documentation,
preservation archives, and running programs. No Microware source code was
used. Facts are stated as facts and the surrounding wording is our own. Short
quotations, attributed by chapter and page, appear only where a manual's exact
wording is itself the evidence.

## Corrections

If your assistant told you something wrong because of these files, or OS-9 did
something they say it does not, [please report it](CONTRIBUTING.md). A bare
"this line is wrong, here is what I saw" is enough. A report from real
hardware is the most valuable thing this project can receive.

## Related projects

- **os9exec** (https://github.com/peacedudes/os9exec): an OS-9/68000
  emulator for macOS, Linux and Windows. Its conformance suite, CONF68K, also
  runs on real OS-9/68000 hardware. `CONTRIBUTING.md` explains how to help
  with it.
- **osk-freeware** (https://github.com/peacedudes/osk-freeware): over a
  thousand programs written for OS-9/68000 by the people who ran it, rebuilt
  and tested under os9exec. Porting them uncovered many of the traps recorded
  here. Try it live in a browser at
  https://peacedudes.github.io/osk-freeware/try/, or browse the catalogue at
  https://peacedudes.github.io/osk-freeware/.

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
