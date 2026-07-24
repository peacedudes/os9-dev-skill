---
name: os9-systems-dev
description: Use when writing an OS-9/68000 device driver or file manager, working with OS-9 kernel internal structures (System Globals, Process Descriptor), the scheduler algorithm, exception/IRQ vector handling, disk allocation/boot mechanics, 6809 Level 2 MMU/DAT register internals, or extending the os9exec emulator's own kernel-interface layer. Not for writing ordinary application programs — see the sibling os9-dev skill for that.
---

# OS-9 Systems Development Skill

> **Pre-publication — not for distribution.** Circulated privately for review;
> no license is granted yet. See `LICENSE` at the repo root.

The kernel/systems half of OS-9 development — extending OS-9 itself:

- **Device drivers** (Init/Read/Write/GetStat/SetStat/Term entry points,
  interrupt service routines, static storage layout)
- **File managers** (the layer between application I$ calls and a driver)
- **Kernel internal structures** — System Globals, Process Descriptor,
  module directory, scheduler data — and the exact scheduler algorithm,
  IRQ vector chaining, exception internals
- **Extending os9exec itself** where it emulates any of the above

Writing a program that merely *uses* drivers/file managers through
ordinary I$/F$ calls is the sibling **`os9-dev`** skill — most OS-9
questions belong there, not here.

## Core mental model

- Drivers and file managers are ordinary OS-9 modules (shared mechanics:
  os9-dev `common/module-format.md`); what differs is the **calling
  convention** — the kernel invokes specific entry points with a specific
  register setup instead of forking the module.
- **Driver static storage arrives zeroed, not initialized** — a driver has
  no data-initialization table; everything is set up explicitly in `Init`.
- RBF/SCF/SBF are the reference implementations of the file-manager
  pattern; a custom manager follows the same entry-point shape.

## Deeper information

Read `references/INDEX.md` first. If the task also has an application
side (e.g. testing a new driver from a C program), read `os9-dev` too.

## Verification

**Neither emulator is OS-9.** `os9exec` and NitrOS-9 are reverse-engineered
reimplementations built by the user community, and both have had real errors.
That matters more here than in the sibling skill: kernel structures, dispatch
conventions and scheduler behaviour are exactly where a reimplementation is
likeliest to have simplified something. A `Source` tag here means "this is
what os9exec's C does" — a statement about os9exec, not about OS-9. Where a
Microware manual disagrees with a runtime, the manual is the specification;
the disagreement is recorded in `DIVERGENCES.md` and only Microware or genuine
hardware resolves it. `SOURCE-AUTHORITY.md` defines what counts as Microware's
word. Tag legend: sibling skill's `os9-dev/references/CONFIDENCE-TAGS.md`.

**Driver and file-manager entry points cannot be tested on os9exec.** It has
no module dispatch for them: `I$Attach` (`icalls.c`) never allocates driver
storage or calls `Init`, device I/O routes through a fixed C table keyed by
hardcoded path prefixes rather than by executing an installed module, and
`iniz` has no emulator-side implementation. A correctly-assembled, CRC-valid
`Drivr` module installs and is never invoked. The toolchain half — assembling
and linking a `Drivr`/`Devic` module byte-correctly — does work.

So the files here are mostly `Manual`, with some struct offsets `Source`
against os9exec's code. Don't read "68k" as "checked" in this skill.

## Rules of engagement

- State which target (6809/68k) an answer applies to; the 68k line is the
  default here, `6809-level2-mmu.md` is the 6809 exception.
- Sources are official Microware manuals plus cited third-party
  references — see `SOURCES.md`.
