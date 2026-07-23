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

os9exec emulates the kernel side of every mechanism here, so its C source
(`Source/OS9exec_core/`) is a second, independent ground truth beyond the
manuals, and the emulator can host live tests for most of what's
documented here (driving it: os9-dev `common/using-os9exec-repl.md`) —
**except driver/file-manager module dispatch itself, confirmed
unimplemented, not just untested.** `Live` (2026-07-18, first real
attempt): a hand-written, correctly-assembled, CRC-valid `Drivr`-type
module was built, linked, and installed exactly per this skill's own
guidance — the kernel never invoked it, at any entry point. Root cause
confirmed at the source level: `os9exec`'s `I$Attach` (`icalls.c`) is an
explicit dummy that never allocates driver storage or calls `Init`; all
device I/O dispatches through a fixed C table keyed by hardcoded
path-prefix matching, never by executing an installed module's code; the
shell's `iniz` command has no emulator-side implementation at all
(`grep -rin iniz Source/` — zero hits). This is a real `os9exec` feature
gap (implementing it would be a substantial addition, not a bug fix),
not a documentation problem — but it means **no amount of reading either
skill will get a driver/file-manager's entry-point register convention
live-tested on this emulator as it stands.** The toolchain half (module
format, assembly/linking a `Drivr`/`Devic`-type module byte-correctly) IS
now live-confirmed working, per the same test — see
`test/68k-live-verification/dogfood-report-driver-2026-07-18.md`
in the `os9exec` repo. Reference files carry inline confidence tags —
legend in the sibling skill's `os9-dev/references/CONFIDENCE-TAGS.md`.

**Neither emulator is OS-9.** `os9exec` and NitrOS-9 are reverse-engineered
reimplementations built by the user community, and both have had real errors.
This matters more here than in the sibling skill: kernel structures, dispatch
conventions and scheduler behaviour are exactly where a reimplementation is
most likely to have simplified something, and `os9exec` in particular does not
implement large parts of what these files describe. A `Source` tag here means
"this is what os9exec's C does" — which is a statement about os9exec, not
about OS-9. Where an authoritative Microware manual disagrees with either
runtime, the manual is the specification and the disagreement is recorded in
`DIVERGENCES.md`; only Microware or genuine hardware resolves it. See
`SOURCE-AUTHORITY.md` for what counts as Microware's word.
**Confidence gap, refined**: the driver/file-manager/kernel files here
are mostly `Manual`, with several struct-layout offsets now `Source`
(checked against os9exec's own code) — the entry-point calling
convention itself remains untestable on this platform, not merely
untested. Don't assume "68k" implies "checked" in this skill.

## Rules of engagement

- State which target (6809/68k) an answer applies to; the 68k line is the
  default here, `6809-level2-mmu.md` is the 6809 exception.
- Sources are official Microware manuals plus cited third-party
  references — see `SOURCES.md`.
