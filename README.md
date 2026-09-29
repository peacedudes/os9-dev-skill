# OS-9 development skills

> **Pre-publication - not for distribution.** Circulated privately for review;
> no license is granted yet. See [LICENSE](LICENSE) for why, and
> [LICENSE.pending](LICENSE.pending) for the terms intended to replace it.
> [NOTICE](NOTICE) credits the sources and is in force regardless.

Two reference collections for working with Microware OS-9 - the real one, on
6809 and 68000. They are documentation, not a toolchain: plain Markdown with
nothing to build, readable by a person or by any coding agent, and [Claude
Code](https://claude.com/claude-code) can additionally load them as skills.
**Doing the work they describe needs an emulator and a Microware SDK that this
repository cannot supply** - see What you will need, below.

| Skill | Covers |
|---|---|
| **`os9-dev`** | Application work: BASIC09, Microware C, 68k and 6809 assembly, the shell and utilities, modules, syscalls, error codes, driving the emulators |
| **`os9-systems-dev`** | Below the application line: device drivers, file managers, kernel internals, the scheduler, 6809 Level 2 MMU/DAT |

They are siblings and cross-reference each other; keep both.

## Start here

Routing by what you are trying to do. If you are a person rather than an agent,
read `os9-dev/SKILL.md` first, then the `INDEX.md` beside it.

| If you want to... | Read |
|---|---|
| Port or write a **C** program | `os9-dev/references/c/kandr-vs-ansi.md` - the porting checklist - then `c/os9-c-cheatsheet.md` |
| Test on OS-9/68000 **without the hardware** | `os9-dev/references/common/using-os9exec-repl.md` (the os9exec emulator) |
| Drive **NitrOS-9 on a CoCo or Dragon** - XRoar, DriveWire, a scriptable shell | `os9-dev/references/6809/using-nitros9-repl.md` |
| Write **68k or 6809 assembly** | `os9-dev/references/68k/os9-68k-assembly.md`, or `6809/assembly-and-tools.md` |
| Work in **BASIC09** | `os9-dev/references/basic09/basic09-language.md` |
| Understand an **error or a symptom** you already hit | the symptom table in `os9-dev/references/INDEX.md` - it maps symptom to cause, which is the faster door once something has failed |
| Write a **driver, file manager or kernel** code | `os9-systems-dev/SKILL.md` |
| Know **how OS-9 differs from Unix** | `os9-dev/references/common/unix-differences.md` |

### What you will need

Nothing here is a toolchain, and two prerequisites gate most of the work:

- **An OS-9 system.** Real hardware if you have it. Without it, 68k programs
  run under the [os9exec](https://github.com/peacedudes/os9exec) emulator,
  built from source, and 6809 work runs on NitrOS-9 under XRoar. Neither is
  included here.
- **A legally-held Microware SDK or disk image.** Microware's shell, C compiler
  and utilities are proprietary and ship with nothing in this repository. A host
  directory of your own files is enough for basic testing, but **you cannot
  compile C without Microware's `cc`**, which you must hold a licence to.

Working under the emulator, `common/using-os9exec-repl.md` covers getting from
those two things to a shell prompt; read it before the language references, not
after.

## Not official, and not error-free

This is an **independent description**, assembled by reading published manuals
and by testing against emulators. It is not Microware's documentation, it is not
endorsed by or affiliated with any rights holder, and it certainly contains
mistakes.

You are not asked to take it on trust. Every claim carries a tag saying what
backs it - see [Confidence](#confidence) below, and read the tag on the line you
are about to rely on. The known limits, stated up front rather than buried:

- **Nothing here has been checked against real OS-9 hardware.** Not one claim.
- **`Live` means an emulator** - a community reimplementation, not a
  specification. Where a runtime and a manual disagree, the manual is treated as
  authoritative and the runtime as the candidate defect.
- **Open `Flag`s mark genuinely unresolved questions**, where sources contradict
  each other; `python3 tools/check_doc_consistency.py` prints the current
  inventory. Several of them need real hardware to settle.
- **Coverage follows what could be verified.** Silence on a topic means untested
  here, not absent from OS-9.

Found an error? [Corrections are wanted](CONTRIBUTING.md) - including a bare
"this line is wrong, here is what I saw instead". Reports from real hardware are
the rarest and most valuable thing this project can receive.

## Using it

Put the folder anywhere your agent can read files. There is nothing to build.

**Any agent that can read files** - point it at [`AGENTS.md`](AGENTS.md), which
says what the two collections cover and how to route within them. The material
is written to be **opened on demand rather than read whole**: together the
files run to roughly 13,000 lines, which is worth keeping out of a context
window until it is needed. Each collection's `references/INDEX.md` maps *topic
to file* and, separately, *symptom to cause* - when something has already
failed and you don't know which topic owns it, the symptom table is the faster
door.

**A chat assistant that cannot open files**, only accept attachments - attach
`os9-dev/SKILL.md` and `os9-dev/references/INDEX.md` (or the `os9-systems-dev`
pair for driver and kernel work), describe the task, and ask which reference
files it needs; then attach those. Two or three files usually settle a
question. Pasting everything at once works less well than it sounds: the
routing is what keeps an answer tied to the right file and its confidence tags.

**An agent that loads skills** - each of the two directories is a standard
skill folder: a `SKILL.md` whose YAML header carries `name` and `description`,
with `references/` beside it. Claude Code and other agents that read that
layout can load them on demand when a task matches.

In Claude Code the repository is also a plugin marketplace, so both skills
install together with two commands and nothing to link:

```
/plugin marketplace add peacedudes/os9-dev-skill
/plugin install os9@os9-dev-skill
```

They then appear as `os9:os9-dev` and `os9:os9-systems-dev`. To use a checkout
instead, link or copy the two folders into your skills directory:

```sh
ln -s "$PWD/os9-dev"         ~/.claude/skills/os9-dev
ln -s "$PWD/os9-systems-dev" ~/.claude/skills/os9-systems-dev
```

Another agent's skills directory takes the same two folders. Install both,
since they cite each other.

Where no skill loader exists, the YAML header is harmless to ignore.

## Scope

OS-9 is a living product - Microware still sells and supports it, and its
current documentation is Microware's to publish. These skills document the older end of
the line - the v2.4-era 68000 system
and 6809 Level 2 - whose documentation was never centralized and now
circulates through preservation archives: manuals in varying states of OCR,
editions of the same book that don't quite agree, and files whose names
misdescribe their contents.

Some thirty published manuals, quick references and training guides stand
behind these files; `SOURCES.md` in each skill says which ones back which
file. Where two manuals disagree, both readings are recorded and marked
`Flag` rather than silently resolved in favour of one.

## Confidence

Claims were not only read but **run** - 68k programs under the
[os9exec](https://github.com/peacedudes/os9exec) emulator, 6809 programs on
NitrOS-9 under XRoar. Every claim carries an inline tag:

| Tag | Means |
|---|---|
| `Hearsay` | Someone said so. Lowest confidence; expect testing to overwrite it. |
| `Manual` | Cross-referenced across published manuals. Not run. |
| `Source` | Checked against real source code, but not run for this claim. |
| `Live` | Actually run and observed. |
| `Absent` | Searched for and confirmed not to exist - not merely unchecked. |
| `Flag` | Sources disagree; unresolved. |

**A `Live` claim is evidence about a reimplementation, never about OS-9
itself.** Both emulators are community-written reverse-engineered work and
both have had real errors. Where a runtime and a Microware manual disagree,
the manual is the specification and the runtime is the candidate defect; the
claim records both readings rather than resolving in favour of whichever one
happened to run. Only Microware, or real hardware, settles those.
`DIVERGENCES.md` collects the handful worth raising directly.
`SOURCE-AUTHORITY.md` says what counts as Microware's word - several excellent
books do not.

The 68000 material has been through a thorough live-verification pass and is
largely `Live`. So has the 6809 side: the assembler and debugger core, roughly
70 of the ~93 documented syscalls, and most of the GFX2 calling sequences.
CoCo/Dragon hardware and the 68k networking material are `Manual` only.
Nothing has been checked against real hardware. The tags say which is which on
any given line.

## Provenance

The line was drawn conservatively at every step.

All source material is public-domain or freely-published Microware/Tandy
documentation, or historical-preservation archives. **No proprietary Microware
source code was used anywhere in this chain.** Facts are stated as facts - a
register contract, an error number, a struct offset - but the prose around
them is written here rather than borrowed: no manual text reproduced at
length, no worked code example kept verbatim, no file mirroring a source's
chapter structure. Short quotations do appear - a clause or a sentence, each
attributed to chapter and page - where the manual's exact wording *is* the
evidence: what it specifies on a disputed point, or one of its own errors
preserved so the citation can be checked.

What was deliberately *not* used is recorded too, in `SOURCES.md`, with the
reasoning. An archive of genuine Microware 6809 source sits in the wider
project's resource collection and has never been opened for any purpose;
NitrOS-9's open kernel source is held to cross-check-only use and is never
extracted at length.

## Related projects

Two sibling projects supplied most of the `Live` (os9exec) evidence here. Neither
is needed to use the skills.

- **os9exec** (https://github.com/peacedudes/os9exec) - an OS-9/68000 user-level
  emulator for macOS, Linux and Windows. Its conformance suite, CONF68K, also
  runs on real OS-9/68000 hardware; `CONTRIBUTING.md` says how to help with it.
- **A collection of OS-9/68000 freeware**, rebuilt and tested under os9exec,
  whose porting work found many of the traps recorded here.
  <!-- PUBLISH: when the collection is public, link it on the line above. -->

## Working on this

Two gates must be green before anything lands, and a tracked pre-commit hook
enforces both:

```sh
git config core.hooksPath tools/hooks     # re-run this after every fresh clone
python3 tools/check_doc_consistency.py    # presence, hygiene, cross-file drift
python3 tools/tests/test_check.py         # the checker's own test suite
```

**The hook is tracked but the config that arms it is local**, so a fresh clone
has no hook until you run that first line. The checker enforces more than
presence: no calendar dates, commit hashes or host paths in reference files;
well-formed confidence tags, and none inside code fences; no blanket `Live` or
`Source` claim without a stated exception; every hex-dump decode-table claim
checked against the dump above it; cross-file enumeration drift; and any error
symbol absent from the error-code table.

Conventions worth knowing before editing a reference file:

- **Every claim carries a confidence tag**, and a `Live` tag always names the
  implementation it ran on - `Live` (os9exec), not a bare `Live`.
- **Reference files carry no dates, hashes, host paths or narrative** about
  their own history. A correction states the rule positively and puts its
  provenance in the tag and the `Sources` footer - never in a story about what
  the file used to say.
- **Cross-check before you correct.** Anything that looks like a contradiction
  gets checked against the skill's own `Live` claims, and against a manual or a
  running system, *before* an edit. Overwriting an established fact on one
  session's reading is this project's known regression pattern.
- **An example ships only if it was run.** An unrun example is `Manual` at
  best. Where something could not be run, say which claim went unchecked.
- **Shared content lives in `os9-dev`**, which stands alone (see Layout below).

`tools/make-bundle.sh` builds a distributable zip from `git archive HEAD`: only
committed files can appear, it refuses a dirty tree, it runs both gates first,
and it aborts if maintainer material reaches the staging tree.

## Layout

```
os9-dev/
  SKILL.md              entry point
  SOURCES.md            which manuals stand behind which file
  references/
    CONFIDENCE-TAGS.md  the tag system above
    INDEX.md            topic -> file, and symptom -> cause
    common/ 68k/ 6809/ basic09/ c/
os9-systems-dev/
  SKILL.md  SOURCES.md  references/
AGENTS.md               entry point for any agent
CLAUDE.md               the same, imported for Claude Code
.claude-plugin/         Claude Code plugin and marketplace manifests
NOTICE                  attribution: Microware and every other source
CONTRIBUTING.md         how to send a correction, and what gets declined
DIVERGENCES.md          where a runtime disagrees with a manual
SOURCE-AUTHORITY.md     what counts as Microware's word
tools/                  the checker, its tests, the pre-commit hook, make-bundle.sh
```

**Shared content lives in `os9-dev`, which stands alone.** Anything both
skills need - the confidence tags, the provenance rules - belongs there.
`os9-systems-dev` may depend on `os9-dev` and cite its files by path;
`os9-dev` never depends on the sibling, and points at it only to mark
something as out of scope. Always name the skill when citing across the
split - a bare filename won't resolve from the other skill's directory.

`DIVERGENCES.md` and `SOURCE-AUTHORITY.md` are review material rather than part
of either collection; nothing under `os9-dev/` or `os9-systems-dev/` may
reference them, so that each collection stays self-contained wherever it is
installed.
